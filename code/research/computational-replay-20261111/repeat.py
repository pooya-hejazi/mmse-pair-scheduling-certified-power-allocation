"""Run the frozen optimizer once for every case/arm in a fresh work directory."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = Path("research/priced-assignment-20261111")
PRIOR = Path("research/independent-cdl-20261110")
PROTOCOL_HASH = "471eb53cf3fac4f7dbe72070c47065cfba9122b2d04b56270b5e87ddf5e99462"


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, obj):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(obj, stream, indent=2, allow_nan=False)
        stream.write("\n")


def git(checkout, *args):
    return subprocess.check_output(["git", "-c", "safe.directory="+checkout.as_posix(), "-C", str(checkout), *args],
                                   text=True).strip()


def safe(base, relative):
    target = (base/relative).resolve()
    require(target.is_relative_to(base.resolve()), "Path outside working tree")
    return target


def checked_copy(root, target, rel, expected):
    original = safe(root, rel)
    require(sha(original) == expected, "Input checksum mismatch: " + str(rel))
    dest = safe(target, rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original, dest)
    require(sha(dest) == expected, "Copy checksum mismatch: " + str(rel))


def populate(checkout, work):
    """Install only frozen source and channel inputs. Omit all arm and start outputs."""
    code = checkout/"code"
    source = code/STUDY
    frozen = read(source/"source_manifest.json")["hashes"]
    for rel, expected in frozen.items():
        checked_copy(code, work/"code", rel, expected)
    for rel in [STUDY/"source_manifest.json", PRIOR/"source_manifest.json", PRIOR/"cases/pilot-A-snr10.json"]:
        checked_copy(code, work/"code", rel, sha(code/rel))
    evidence = read(source/"generator_validation_main.json")
    bycase = {}
    for profile in evidence["profiles"]:
        checked_copy(code, work/"code", STUDY/profile["native_path"], profile["native_sha256"])
        for case in profile["cases"]:
            checked_copy(code, work/"code", STUDY/case["case_path"], case["case_sha256"])
            bycase[case["case_path"]] = case["case_sha256"]
    reference = read(source/"runs/main/manifest.json")
    require(bycase == reference["cases"] and len(bycase) == 180 and len(evidence["profiles"]) == 60,
            "Published case binding/coverage mismatch")
    require(not (work/"code"/STUDY/"runs").exists(), "Existing results found in fresh workspace")
    return reference


def call(study, script, arguments, logfile):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"
    env["MPLCONFIGDIR"] = str(logfile.parent/"mpl-cache")
    for key in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS","NUMBA_NUM_THREADS"):
        env[key] = "1"
    with logfile.open("x",encoding="utf-8") as out:
        subprocess.run([sys.executable,"-B","-X","utf8",str(study/script),*arguments],cwd=study,env=env,
                       stdout=out,stderr=subprocess.STDOUT,check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--work", type=Path, required=True, help="New directory")
    parser.add_argument("--wheels", type=Path, required=True, help="Wheelhouse containing wheel-provenance.json")
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    work = args.work.resolve()
    require(len(args.commit)==40 and git(checkout,"rev-parse","HEAD") == args.commit, "Unexpected source commit")
    require(git(checkout,"status","--porcelain","--untracked-files=no") == "", "Tracked checkout files changed")
    require(sha(HERE/"SURVEY/PROTOCOL.md") == PROTOCOL_HASH, "Preregistered protocol changed")
    require(sys.prefix != sys.base_prefix and sys.flags.isolated, "Launch using the isolated verification venv and -I")
    require(not work.exists(), "Work directory must be new")
    work.mkdir(parents=True)
    published_manifest = populate(checkout, work)
    wdir = args.wheels.resolve()
    wheels = read(wdir/"wheel-provenance.json")
    dist_root = Path(sys.prefix)/"Lib/site-packages"
    for item in wheels:
        dist = importlib.metadata.distribution(item["name"])
        require(dist.version == item["version"] and Path(dist.locate_file("")).resolve() == dist_root.resolve(),
                "Distribution version/location mismatch " + item["name"])
        require(sha(wdir/item["filename"]) == item["sha256"], "Wheel hash mismatch")
    require(len(wheels) == 18 and sha(wdir/"requirements-lock.txt") ==
            "eb52d6e804acd4fb4b0f071854a1d04364fdaaa5dd3f3304444e1e04c9efa7ab", "Unexpected replay lock")
    runtime = {p.relative_to(dist_root).as_posix():sha(p) for p in sorted(dist_root.rglob("*"))
               if p.is_file() and p.suffix.lower() in (".dll",".pyd")}
    source = checkout/"code"/STUDY
    lock = dict(study="one computational repeat of the 180 published native cases",commit=args.commit,
                protocol_sha256=PROTOCOL_HASH,launcher_sha256=sha(Path(__file__)),
                source_manifest_sha256=sha(source/"source_manifest.json"),seed_manifest_sha256=sha(source/"seed_manifest.json"),
                original_stage_sha256=sha(source/"runs/main/manifest.json"),original_audit_sha256=sha(source/"audit_study.json"),
                original_analysis_sha256=sha(source/"analysis/results.json"),cases=published_manifest["cases"],
                bootstrap_seed=read(source/"seed_manifest.json")["bootstrap"]["effective_seed"],
                interpreter=sys.version,interpreter_launcher_sha256=sha(Path(sys.executable)),
                interpreter_base_sha256=sha(Path(sys._base_executable)),runtime_binary_sha256=runtime,
                wheels=wheels,wheel_lock_sha256=sha(wdir/"requirements-lock.txt"),prior_results_copied=0,
                expected_new_runs=720,expected_offered_starts=1440,utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()))
    save(work/"prerun.json",lock)
    call(work/"code"/STUDY,"run_study.py",["run"],work/"timed-search.log")
    print("Timed search completed", work, flush=True)


if __name__ == "__main__":
    main()
