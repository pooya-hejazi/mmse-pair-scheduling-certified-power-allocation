"""Run four serial arms on the frozen priced-assignment native-CDL holdout."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
import numba
import numpy as np
import scipy
from threadpoolctl import threadpool_info, threadpool_limits

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
PREVIOUS = HERE.parent / "independent-cdl-20261110"
ARMS = ("Price-DP-SQP", "DP-SQP", "DP-Fu-SCA", "DP-Thu-IDE")
CAP, BLOCK = 10.0, 5.0


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def start_id(schedule):
    encoded = json.dumps(schedule, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


prior = load_module("priced_reference_runner", PREVIOUS / "run_campaign.py")


def engine():
    module = load_module("priced_method", HERE / "method.py")
    prior.shared.dp_assignment = module.dp_assignment
    return module


def dependency_hashes():
    files = {HERE / name for name in (
        "run_study.py", "method.py", "verify_study.py", "analyze_study.py", "PROTOCOL.md",
        "generate_holdout.py", "verify_holdout.py", "GENERATOR_PROTOCOL.md", "seed_manifest.json",
        "generator_validation_main.json", "generator_validation_replay.json")}
    files.update(PREVIOUS / name for name in ("run_campaign.py", "audit_campaign.py", "analysis.py", "generator.py"))
    files.update(prior.ROOT / name for name in read(PREVIOUS / "source_manifest.json")["hashes"]
                 if name.endswith(".py"))
    files.update({prior.shared.CERT / "checker.py", prior.shared.CERT / "integer_logs.py"})
    for module in tuple(sys.modules.values()):
        raw = getattr(module, "__file__", None)
        if raw:
            path = Path(raw).resolve()
            if path.suffix == ".py" and path.is_relative_to(PROJECT):
                files.add(path)
    return {path.relative_to(PROJECT).as_posix(): sha(path) for path in sorted(files)}


def method_run(module, case, starts, arm, cap, block):
    # Each arm gets a fresh instance. All case-specific preprocessing outside the
    # measured search is the same Problem constructor and offered starts.
    problem = prior.Problem(case)
    if arm == ARMS[0]:
        result = module.solve(problem, starts, cap=cap, block=block)
    else:
        result = prior.solve(problem, starts, arm, case["metadata"]["search_seed"], cap, block)
    if result["arm"] != arm:
        raise ValueError(f"Wrong method result: {result['arm']}, expected {arm}")
    history = result["history"]
    if not history or history[-1]["schedule"] != result["schedule"] or history[0]["kind"] != "initial":
        raise ValueError("Missing retained allocation history")
    if result["cap_seconds"] != cap or result["block_seconds"] != block:
        raise ValueError("Inconsistent arm cap")
    if result["elapsed_seconds"] <= 0:
        raise ValueError(f"Invalid elapsed time: {result['elapsed_seconds']}")
    return result


def warm_process(module):
    # No holdout channel enters compilation or warm initialization.
    start = time.monotonic()
    module.warmup()
    historical = read(PREVIOUS / "cases/pilot-A-snr10.json")
    problem = prior.Problem(historical)
    starts = prior.starts_for(problem, historical["metadata"]["initialization_seed"])
    warm = {}
    for arm in ARMS:
        row = method_run(module, historical, starts, arm, 0.5, 0.25)
        warm[arm] = {"elapsed_seconds": row["elapsed_seconds"], "retained": len(row["history"])}
    return {"historical_case": historical["name"], "total_seconds": time.monotonic() - start,
            "arms": warm, "thread_pools": threadpool_info(), "numba_threads": numba.get_num_threads()}


def population():
    receipt = read(HERE / "generator_validation_main.json")
    if receipt["status"] != "PASS" or read(HERE / "generator_validation_replay.json")["status"] != "PASS":
        raise ValueError("Generator validation did not pass")
    seed_hash = sha(HERE / "seed_manifest.json")
    replay = read(HERE / "generator_validation_replay.json")
    if not (receipt["seed_manifest_sha256"] == replay["seed_manifest_sha256"] == seed_hash and
            replay["generation_receipt_sha256"] == sha(HERE / "generator_validation_main.json") and
            replay["regenerated_links_bitwise_equal"] == 960 and replay["coefficients_checked"] == 172800):
        raise ValueError("Generator receipts do not establish full input replay")
    generated_hashes = {row["case_path"]: row["case_sha256"] for profile in receipt["profiles"] for row in profile["cases"]}
    for profile in receipt["profiles"]:
        if sha(HERE / profile["native_path"]) != profile["native_sha256"]:
            raise ValueError("Native file changed since generation")
    cases = {}
    for path in sorted((HERE / "cases").glob("*.json")):
        case = read(path)
        meta = case["metadata"]
        key = (meta["block"], meta["profile"], meta["snr_db"])
        if sha(path) != generated_hashes.get(path.relative_to(HERE).as_posix()) or meta["seed_manifest_sha256"] != seed_hash:
            raise ValueError("Holdout input differs from generation receipt")
        if meta["pilot"] or key in cases or case["name"] != path.stem:
            raise ValueError(f"Unexpected case {path.name}")
        cases[key] = path
    expected = {(b, p, s) for b in range(20) for p in "ABC" for s in (0, 10, 20)}
    if set(cases) != expected:
        raise ValueError(f"Expected full 180-case crossed holdout, found {len(cases)}")
    return [cases[k] for k in sorted(cases)]


def run():
    module = engine()
    paths = population()
    frozen = read(HERE / "source_manifest.json")
    if frozen["hashes"] != dependency_hashes():
        raise ValueError("Source differs from holdout freeze")
    target = HERE / "runs/main"
    target.mkdir(parents=True, exist_ok=True)
    if list(target.glob("*-FAILURE.json")) or list(target.glob("*-rejected.json")):
        raise ValueError("Investigate the retained failure before resuming")
    source_hash = sha(HERE / "source_manifest.json")
    manifest = dict(source_manifest_sha256=source_hash, stage="main", arms=list(ARMS),
                    cap_seconds=CAP, block_seconds=BLOCK,
                    cases={p.relative_to(HERE).as_posix(): sha(p) for p in paths})
    manifest_path = target / "manifest.json"
    if manifest_path.exists() and read(manifest_path) != manifest:
        raise ValueError("Existing run manifest differs from current freeze")
    if not manifest_path.exists():
        dump(manifest_path, manifest)
    warm = warm_process(module)
    process_id = f"{time.time_ns()}-{os.getpid()}"
    process_path = HERE / "runs/processes" / (process_id + ".json")
    dump(process_path, dict(process=process_id, source_manifest_sha256=source_hash, **warm))
    for index, path in enumerate(paths):
        case = read(path)
        meta = case["metadata"]
        case_hash = sha(path)
        began = time.monotonic()
        problem = prior.Problem(case)
        starts = prior.starts_for(problem, meta["initialization_seed"])
        schedules = [problem.model.encode(a, p) for a, p in starts]
        preparation = time.monotonic() - began
        start_path = target / (path.stem + "-starts.json")
        offered = dict(case_sha256=case_hash, initialization_seed=meta["initialization_seed"],
                       start_ids=[start_id(s) for s in schedules], starts=schedules)
        if start_path.exists() and read(start_path) != offered:
            raise ValueError("Offered starts changed")
        if not start_path.exists():
            dump(start_path, offered)
        order = ARMS[index % len(ARMS):] + ARMS[:index % len(ARMS)]
        for position, arm in enumerate(order):
            destination = target / (path.stem + "-" + arm + ".json")
            binding = dict(arm=arm, case=path.stem, case_sha256=case_hash,
                           source_manifest_sha256=source_hash, starts_sha256=sha(start_path),
                           order=list(order), position=position)
            if destination.exists():
                existing = read(destination)
                if any(existing[k] != v for k, v in binding.items()):
                    raise ValueError("Resume binding mismatch")
                problem.model.decode(existing["schedule"])
                continue
            try:
                row = method_run(module, case, starts, arm, CAP, BLOCK)
                row.update(binding, stage="main", block=meta["block"], profile=meta["profile"],
                           snr_db=meta["snr_db"], initialization_seed=meta["initialization_seed"],
                           search_seed=meta["search_seed"], case_path=path.relative_to(HERE).as_posix(),
                           offered_start_ids=offered["start_ids"], preparation_seconds=preparation,
                           process=process_id, process_sha256=sha(process_path))
                if row["overrun_seconds"] >= 0.5:
                    dump(target/(path.stem+"-"+arm+"-rejected.json"),row)
                    raise ValueError("Unexpected deadline overrun; full result retained separately")
                dump(destination, row)
                print(f"{index+1}/180 {path.stem} {arm}: {row['se_bits']:.9f}, {row['elapsed_seconds']:.3f}s", flush=True)
            except Exception as error:
                dump(target / (path.stem + "-" + arm + "-FAILURE.json"), dict(binding, error=repr(error)))
                raise
    if frozen["hashes"] != dependency_hashes():
        raise ValueError("Scientific source changed during timed run")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("smoke", "freeze", "run"))
    action = parser.parse_args().action
    with threadpool_limits(limits=1):
        if action == "smoke":
            print(json.dumps(warm_process(engine()), indent=2))
        elif action == "freeze":
            engine()
            population()
            hashes = dependency_hashes()
            path = HERE / "source_manifest.json"
            if path.exists():
                if read(path)["hashes"] != hashes:
                    raise ValueError("Existing freeze differs. Preserve this study's provenance.")
            else:
                dump(path, dict(hashes=hashes, python=sys.version, numpy=np.__version__,
                     scipy=scipy.__version__, numba=numba.__version__, platform=platform.platform()))
            print("Frozen source manifest", sha(path))
        else:
            run()


if __name__ == "__main__":
    main()
