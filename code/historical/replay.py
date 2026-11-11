"""Replay the scientific members of the historical S10 and R1 through R4 releases."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import runpy
import subprocess
import sys
import tempfile
import types
import zipfile


DATA = Path(__file__).resolve().parents[2] / "data" / "historical"
MANIFEST = "SCIENCE-MANIFEST.json"
PUBLIC_SHA256 = {
    "r1": "6c4c2a70d209dfbc48857999abe380f61a993e604423cf5f14d17aa2a53b99bb",
    "r2": "20971951eb6233a20473aec29830dc7b2f88b30f68db71c73268ff27b029a167",
    "r3": "eeff021bae547c2522f5f630b58dbac18de850c4231bd4d4400b96dd68579970",
    "r4": "ccbf62a9a87d5e487d7fab9f424eb9193b92864bfaa4f42cd7081eb1a50e28a8",
    "s10-development": "29ee58f2c84b6f91e3f50a002800166f0880749d93bea5e57bec04c24960f514",
    "s10-four-ap": "5a4adc4aeb06687c209c244f114ed7be6462d6b4be220b5e70cfeb63c8e6b185",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_archive(path, digest):
    require(hashlib.sha256(path.read_bytes()).hexdigest() == digest, f"public archive mismatch: {path.name}")
    with zipfile.ZipFile(path) as z:
        manifest = json.loads(z.read(MANIFEST))
        names = [row["path"] for row in manifest["files"]]
        require(len(names) == len(set(names)) and sorted(names + [MANIFEST]) == sorted(z.namelist()),
                f"public archive membership mismatch: {path.name}")
        for row in manifest["files"]:
            name = row["path"]
            p = PurePosixPath(name)
            require(not p.is_absolute() and str(p) == name and ".." not in p.parts and "\\" not in name and ":" not in name,
                    f"unsafe archive path: {name}")
            data = z.read(name)
            require(len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
                    f"source member mismatch: {name}")
    return manifest


def module_from_member(z, name, module_name):
    module = types.ModuleType(module_name)
    module.__file__ = str(z.filename) + "/" + name
    exec(compile(z.read(name), module.__file__, "exec"), module.__dict__)
    return module


def replay_r2(path, manifest, seconds):
    with zipfile.ZipFile(path) as z:
        old = module_from_member(z, "reproduce_r2.py", "historical_r2")

        class PublicArchiveReplay(old.Replay):
            def integrity(self):
                # The public export has its own verified membership, without the private nested ZIP.
                self.z = z
                self.hashes = {r["path"]: r["sha256"] for r in manifest["files"]}
                self.sizes = {r["path"]: r["bytes"] for r in manifest["files"]}
                require(self.hashes[old.CHECKER_MEMBER] == old.CHECKER_SHA, "R2 checker source mismatch")
                self.checker = module_from_member(z, old.CHECKER_MEMBER, "historical_checker")
                self.report["counts"]["manifest_files"] = len(self.hashes)
                self.report["integrity"] = "Public archive digest, original member bytes and pinned checker verified."
                del self.report["expected_nested_R1_sha256"]

        replay = PublicArchiveReplay(path, seconds, "retained")
        return replay.run(), replay.checker


def run(script, *args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONOPTIMIZE", None)  # Some original receipt checks use assert.
    cmd = [sys.executable, "-B", "-X", "utf8", str(script), *map(str, args)]
    proc = subprocess.run(cmd, cwd=script.parent, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          encoding="utf-8", errors="replace")
    if proc.returncode:
        raise RuntimeError(f"{script.name} exited {proc.returncode}\n{proc.stdout[-3000:]}")


def read(path):
    return json.loads(path.read_bytes())


def same_beta_endpoint(actual, saved):
    if type(actual) is not float or type(saved) is not float or not (-1 <= actual <= 1 and -1 <= saved <= 1):
        return False
    if actual == saved:
        return True
    if actual in (-1, 0, 1) or saved in (-1, 0, 1) or (actual < 0) != (saved < 0):
        return False
    # The frozen Conda and PyPI SciPy 1.16.3 beta quantiles differ by up to two binary64 steps.
    return math.nextafter(math.nextafter(saved, actual), actual) == actual


def same_statistics(actual, saved, beta_intervals, path=()):
    if type(actual) is not type(saved):
        return False
    if path in beta_intervals:
        return isinstance(actual, list) and len(actual) == len(saved) == 2 and all(
            same_beta_endpoint(x, y) for x, y in zip(actual, saved))
    if isinstance(actual, dict):
        return actual.keys() == saved.keys() and all(
            same_statistics(actual[k], saved[k], beta_intervals, path + (k,)) for k in saved)
    if isinstance(actual, list):
        return len(actual) == len(saved) and all(
            same_statistics(x, y, beta_intervals, path + (i,)) for i, (x, y) in enumerate(zip(actual, saved)))
    return actual == saved


def replay_r3(path, r2_zip, work):
    dest = work / "new-coverage"
    with zipfile.ZipFile(path) as z:
        helper = Path(z.extract("author/extract_coverage.py", work))
        run(helper, "--archive", r2_zip, "--output", dest)
        for table in ("COVERAGE_SUMMARY.json", "DISPLAY_CONTRASTS.json", "INPUT_HASHES.json"):
            require(read(dest / table) == json.loads(z.read("author/coverage/" + table)), f"R3 {table} differs")
        name = "COVERAGE_CELLS.csv"
        lines = (dest / name).read_bytes().splitlines()
        require(len(lines) == 221 and lines == z.read("author/coverage/" + name).splitlines(), "R3 cell table differs")
    return {"cases": 44, "arm_cells": 220, "coverage_summary_and_44_display_contrasts_reproduced": True}


def replay_r1(path, tmp, fix, seconds):
    results = {}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.startswith(("reproduction/code/", "reproduction/studies/")):
                if "/analysis/" not in name and not name.endswith("/CERTIFICATE_REPLAY.json"):
                    z.extract(name, tmp)
        for study in ("original", "corrected"):
            prefix = f"reproduction/studies/{study}/"
            root = tmp / prefix
            run(tmp / "reproduction" / "code" / study / "analyze.py", root)
            summary = read(root / "analysis" / "summary.json")
            saved_summary = json.loads(z.read(prefix + "analysis/summary.json"))
            beta_intervals = {("strata", i, "conservative_interval") for i in range(len(saved_summary["strata"]))}
            beta_intervals.add(("interval_95_bonferroni",))
            require(same_statistics(summary, saved_summary, beta_intervals), f"{study}: R1 statistics differ")
            require((root / "analysis" / "all-cells.csv").read_bytes().splitlines() ==
                    z.read(prefix + "analysis/all-cells.csv").splitlines(), f"{study}: R1 cell table differs")
            run(fix, root, "--seconds", seconds)
            fresh = read(root / "CERTIFICATE_REPLAY.json")
            saved = json.loads(z.read(prefix + "CERTIFICATE_REPLAY.json"))
            require(fresh["valid"] and fresh["planned_cells"] == fresh["cells_checked"] == 128 and
                    fresh["checks"] == saved["checks"] and fresh["receipts_checked"] == saved["receipts_checked"],
                    f"{study}: R1 certificate coverage differs")
            results[study] = {"cells": fresh["cells_checked"], "timely_receipts": fresh["receipts_checked"],
                              "summary_and_cell_table_reproduced": True, "difference": summary["difference"],
                              "interval_95_bonferroni": summary["interval_95_bonferroni"],
                              "superiority_established": summary["superiority_established"]}
    return results


def check_physical_kernels(root, reports, checker, seconds):
    rows = read(root / "global-kernel-summary.json")["results"]
    expected = {(b, a) for b in ("physical-bundle-a", "physical-bundle-b") for a in ("T", "W", "S", "FU_SCA", "THU_IDE")}
    require(len(rows) == len(expected) and {(r["bundle"], r["arm"]) for r in rows} == expected, "physical kernel coverage differs")
    for row in rows:
        bundle, arm = row["bundle"], row["arm"]
        case = read(root / bundle / "case.json")
        require(row == read(root / bundle / "kernel-comparison" / (arm + ".json")), f"physical summary mismatch: {bundle}/{arm}")
        digest = hashlib.sha256(json.dumps(case, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        proof = {"schema": "MMSE_PARTITION_PROOF_V1", "case_sha256": digest, "universal": True, "dual": None, "spatial": None}
        for endpoint in ("initial", "final"):
            saved = row[endpoint]
            checker.clear_caches()
            got = checker.verify(case, {"schedule": saved["schedule"], "proof": proof}, seconds=seconds)
            require(got["valid"] and all(got[k] == saved["independent_verification"][k]
                    for k in ("lower_nats", "upper_nats", "incumbent_upper_nats")), f"physical {endpoint} mismatch: {bundle}/{arm}")
        upper = Fraction(reports[bundle]["upper_nats"])
        deficit = upper - Fraction(row["final"]["independent_verification"]["lower_nats"])
        require(Fraction(row["global_upper_nats"]) == upper and deficit == Fraction(row["deficit_nats"]) and deficit >= 0 and
                math.isclose(float(deficit) / (case["S"] * math.log(2)), row["deficit_bit_per_s_Hz"], rel_tol=0, abs_tol=1e-12),
                f"physical deficit mismatch: {bundle}/{arm}")
    return len(rows)


def replay_r4(root, r2_zip, checker, seconds):
    matched_path = root / "new-matched-report.json"
    run(root / "r4-method" / "replay_matched.py", root / "matched-kernel-results-v2", "--archive", r2_zip,
        "--legacy-method", root / "legacy-method" / "CR033" / "method", "--output", matched_path)
    matched = read(matched_path)
    require(matched["valid"] and matched["cells_checked"] == 220 and matched["independent_initial_final_numerical_checks"] == 440,
            "R4 matched replay incomplete")
    global_root = root / "r4-global"
    reports = {}
    fields = ("valid", "coverage_status", "target_status", "assignments_verified", "lower_nats", "upper_nats", "gap_nats")
    for name in ("physical-bundle-a", "physical-bundle-b", "binary64-bundle", "rational-bundle"):
        path = root / (name + "-replay.json")
        run(global_root / "replay_nonorthogonal.py", global_root / name, "--seconds", seconds, "--report", path)
        got = read(path)
        saved = read(global_root / name / "verification-report.json")
        require(got["valid"] and got["assignments_verified"] == 6 and all(got[k] == saved[k] for k in fields),
                f"{name}: global witness replay differs")
        reports[name] = {key: got[key] for key in fields}
    return {"matched": matched, "global": reports,
            "physical_kernel_deficits_checked": check_physical_kernels(global_root, reports, checker, seconds)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="new JSON report; default prints the report")
    parser.add_argument("--seconds", type=float, default=300, help="replay allowance for each bounded historical checker")
    args = parser.parse_args()
    if not __debug__:
        parser.error("run without -O or PYTHONOPTIMIZE so the frozen assertion checks execute")
    if not math.isfinite(args.seconds) or args.seconds <= 0 or (args.output and args.output.exists()):
        parser.error("use a positive finite replay allowance and a fresh output filename")
    paths = {stage: DATA / (stage + "-science.zip") for stage in PUBLIC_SHA256}
    report = {"status": "INCOMPLETE", "archives": {}, "scope": "Saved numerical evidence only."}
    try:
        manifests = {}
        for stage, path in paths.items():
            manifest = check_archive(path, PUBLIC_SHA256[stage])
            manifests[stage] = manifest
            report["archives"][stage] = {"public_zip_sha256": PUBLIC_SHA256[stage],
                                        "source_zip_sha256": manifest["source_container_sha256"],
                                        "original_members": len(manifest["files"])}
        print("Verified six public archives. Replaying numerical evidence.", file=sys.stderr, flush=True)
        report["r2"], checker = replay_r2(paths["r2"], manifests["r2"], args.seconds)
        with tempfile.TemporaryDirectory(dir=args.output.resolve().parent if args.output else None) as temp:
            work = Path(temp).resolve()
            r4 = work / "r4"
            with zipfile.ZipFile(paths["r4"]) as z:
                z.extractall(r4)
            report["r3"] = replay_r3(paths["r3"], paths["r2"], work)
            s10 = runpy.run_path(str(Path(__file__).with_name("s10.py")))
            report["s10"] = s10["replay_s10"](paths, work, run, args.seconds, same_statistics)
            report["r4"] = replay_r4(r4, paths["r2"], checker, args.seconds)
            report["r1"] = replay_r1(paths["r1"], work / "r1", r4 / "r4-fixes" / "replay_certificates.py", args.seconds)
        report["status"] = "PASS"
    except Exception as exc:
        report.update(status="FAIL", error=f"{type(exc).__name__}: {exc}")
        print(report["error"], file=sys.stderr)
    result = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(result)
        print(f"{report['status']} {args.output}")
    else:
        print(result, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
