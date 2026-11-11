"""Freeze the study, test historical controls, or run the five interleaved searches."""
import argparse
import gzip
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

import method as m
import numba
import numpy as np
import scipy
from threadpoolctl import threadpool_info, threadpool_limits

HERE, CODE = m.HERE, m.HERE.parents[1]
read, sha, dump = m.published.read, m.published.sha, m.published.dump


def case_names(blocks=20):
    return [f"native-b{b:02d}-{profile}-snr{snr:02d}"
            for b in range(blocks) for profile in "ABC" for snr in (0, 10, 20)]


def load_raw(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def save_raw(path, row):
    data = json.dumps(row, separators=(",", ":"), allow_nan=False).encode()
    temp = path.with_suffix(".tmp")
    temp.write_bytes(gzip.compress(data, compresslevel=6, mtime=0))
    temp.replace(path)


def freeze_hashes():
    previous = read(m.PREVIOUS / "source_manifest.json")
    files = {CODE/path for path in previous["hashes"] if path.endswith(".py")}
    files.update(HERE/name for name in ("method.py", "run_study.py", "audit_analysis.py", "PROTOCOL.md",
                                        "generate.py", "GENERATOR.md", "seed_manifest.json", "input_check.json",
                                        "historical_check.json"))
    return {f.relative_to(CODE).as_posix(): sha(f) for f in sorted(files)}


def freeze():
    receipt = read(HERE / "input_check.json")
    if receipt["status"] != "PASS" or set(receipt["cases"]) != set(case_names()):
        raise ValueError("Missing validated fresh inputs")
    if (receipt["seed_manifest_sha256"] != sha(HERE/"seed_manifest.json") or
        receipt["generator_sha256"] != sha(HERE/"generate.py") or receipt["historical_collisions"] != 0 or
        receipt["regenerated_links_bitwise_equal"] != 960 or receipt["coefficients_checked"] != 172800 or
        receipt["catalog_sha256"] != sha(HERE/"inputs/catalog.json.gz")):
        raise ValueError("Incomplete native replay or different seed/source binding")
    checks = read(HERE/"historical_check.json")
    if checks["historical_case_count"] != 18 or any(sha(HERE/f)!=v for f,v in checks["hashes"].items()):
        raise ValueError("Incomplete historical validation or changed code")
    for name, digest in receipt["profiles"].items():
        if sha(HERE / name) != digest:
            raise ValueError("Native input hash mismatch")
    files = freeze_hashes()
    freeze_path = HERE / "source_manifest.json"
    if freeze_path.exists():
        if read(freeze_path)["hashes"] != files:
            raise ValueError("Existing source freeze differs")
    else:
        dump(freeze_path, dict(hashes=files, python=sys.version, numpy=np.__version__,
                               scipy=scipy.__version__, numba=numba.__version__,
                               platform=platform.platform(), arms=list(m.ARMS), cap=m.CAP, block=m.BLOCK,
                               created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
    return sha(freeze_path)


def prepare(case):
    start = time.perf_counter()
    problem = m.prior.Problem(case)
    starts = m.prior.starts_for(problem, case["metadata"]["initialization_seed"])
    offered = [problem.model.encode(a, powers) for a, powers in starts]
    return starts, offered, time.perf_counter() - start


def warmup():
    started = time.perf_counter()
    m.price.warmup()
    checks = []
    for snr in (0, 20):
        name = f"native-b00-A-snr{snr:02d}"
        case = read(m.PREVIOUS/"cases"/(name+".json"))
        starts, _, _ = prepare(case)
        rows = {}
        for arm in m.ARMS:
            result = m.solve(m.prior.Problem(case), starts, case["metadata"]["search_seed"], arm)
            rows[arm] = dict(elapsed=result["elapsed_seconds"], se=result["se_bits"],
                             screen=result["screen"], counts=result["counts"])
        chosen = m.ONE if rows[m.ADAPT]["screen"]["passed"] else m.SHORT
        if rows[m.ADAPT]["se"] != rows[chosen]["se"]:
            raise ValueError("Screen and matched branch differ on historical data")
        checks.append(dict(case=name, arms=rows))
    if {x["arms"][m.ADAPT]["screen"]["passed"] for x in checks} != {False, True}:
        raise ValueError("Historical warmup did not exercise both branches")
    pools = threadpool_info()
    if numba.get_num_threads() != 1 or not all(p["num_threads"] == 1 for p in pools):
        raise ValueError("Unexpected numerical thread count")
    return dict(arms=checks, thread_pools=pools, numba_threads=numba.get_num_threads(),
                elapsed_seconds=time.perf_counter()-started, python=sys.version, numpy=np.__version__,
                scipy=scipy.__version__, numba=numba.__version__, platform=platform.platform(),
                processor=platform.processor(), logical_cpus=os.cpu_count())


def execute_case(case, index, bound, path=None, process_binding=None):
    starts, offered, setup = prepare(case)
    meta = case["metadata"]
    shift = index % len(m.ARMS)
    order = m.ARMS[shift:] + m.ARMS[:shift]
    header = dict(case=case["name"], block=meta["block"], profile=meta["profile"], snr_db=meta["snr_db"],
                  initialization_seed=meta["initialization_seed"], search_seed=meta["search_seed"],
                  offered_starts=offered, start_ids=[m.published.start_id(x) for x in offered],
                  order=list(order), **bound)
    if path is not None and path.exists():
        row = load_raw(path)
        if any(row[k] != v for k, v in header.items()) or set(row["arms"]).difference(order):
            raise ValueError("Checkpoint binding differs")
    else:
        row = dict(**header, arms={}, preparation_seconds=setup)
    for position, arm in enumerate(order):
        if arm in row["arms"]:
            continue
        # Every arm starts with its own, identically prepared, problem instance.
        prepared = time.perf_counter()
        problem = m.prior.Problem(case)
        model_seconds = time.perf_counter() - prepared
        result = m.solve(problem, starts, meta["search_seed"], arm)
        result.update(position=position, model_setup_seconds=model_seconds, **(process_binding or {}))
        row["arms"][arm] = result
        if path is not None:
            save_raw(path, row)
    return row


def historical():
    m.price.self_check()
    warmed = warmup()
    entries = []
    for index, name in enumerate(case_names(2)):
        path = m.PREVIOUS/"cases"/(name+".json")
        case = read(path)
        row = execute_case(case, index, dict(case_sha256=sha(path)))
        data = row["arms"]
        adaptive = data[m.ADAPT]
        chosen = m.ONE if adaptive["screen"]["passed"] else m.SHORT
        if adaptive["schedule"] != data[chosen]["schedule"] or adaptive["se_bits"] != data[chosen]["se_bits"]:
            raise ValueError("Matched branch differs on development cases")
        for arm in (m.DP, m.FULL):
            original = read(m.PREVIOUS/"runs/main"/(name+"-"+arm+".json"))
            if abs(original["se_bits"] - data[arm]["se_bits"]) > 1e-7:
                raise ValueError("Replayed full method differs on historical inputs")
        event, checkpoint = m.prefix(row)
        entries.append(dict(case=name, minimum=adaptive["screen"]["minimum"], passed=adaptive["screen"]["passed"],
            arms={arm:dict(se=r["se_bits"], seconds=r["elapsed_seconds"], starts=r["counts"]["starts_started"],
                           price=r["counts"].get("price_dp_completed",0)) for arm,r in data.items()},
            prefix_se=event["se_bits"], prefix_inside_clock=checkpoint))
    report = dict(cases=entries, previous_population=m.PREVIOUS.name, historical_case_count=len(entries),
                  warmup=warmed, hashes={name:sha(HERE/name) for name in ("method.py","run_study.py","PROTOCOL.md")})
    dump(HERE/"historical_check.json", report)
    print("PASS historical cases", len(entries), "screen passes", sum(e["passed"] for e in entries), flush=True)


def run(output):
    import generate
    source = sha(HERE/"source_manifest.json")
    if read(HERE/"source_manifest.json")["hashes"] != freeze_hashes():
        raise ValueError("Scientific sources changed after the freeze")
    inputs = read(HERE/"input_check.json")
    if inputs["status"] != "PASS" or set(inputs["cases"]) != set(case_names()):
        raise ValueError("Input inventory mismatch")
    output.mkdir(exist_ok=True, parents=True)
    manifest = dict(source_manifest_sha256=source, input_check_sha256=sha(HERE/"input_check.json"),
                    arms=list(m.ARMS), names=case_names())
    manifest_path = output/"manifest.json"
    if manifest_path.exists() and read(manifest_path) != manifest:
        raise ValueError("Run directory is bound to another source freeze")
    if not manifest_path.exists():
        dump(manifest_path, manifest)
    process = f"{time.time_ns()}-{os.getpid()}"
    process_path = output/"processes"/(process+".json")
    dump(process_path, dict(process=process, source_manifest_sha256=source, **warmup()))
    process_hash = sha(process_path)
    for index,name in enumerate(case_names()):
        case = generate.load_case(name)
        digest = hashlib.sha256(generate.case_bytes(case)).hexdigest()
        if digest != inputs["cases"][name]:
            raise ValueError("Reconstructed case hash mismatch: "+name)
        destination = output/(name+".json.gz")
        bound = dict(case_sha256=digest, source_manifest_sha256=source)
        if destination.exists():
            saved = load_raw(destination)
            if any(saved[k]!=v for k,v in bound.items()):
                raise ValueError("Run checkpoint source mismatch")
            if len(saved["arms"]) == len(m.ARMS):
                continue
        # Bind each arm to its own process on a partial-case resume.
        execute_case(case, index, bound, destination, dict(process=process, process_sha256=process_hash))
        if (index+1)%9 == 0:
            print(f"Finished {index+1}/180 complete cases", flush=True)
    if read(HERE/"source_manifest.json")["hashes"] != freeze_hashes():
        raise ValueError("Scientific sources changed during the run")
    print("COMPLETE 900 final allocations", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["historical", "freeze", "run"])
    parser.add_argument("--output", type=Path, default=HERE/"runs/main")
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        if args.action == "historical":
            historical()
        elif args.action == "freeze":
            print("Source freeze", freeze())
        else:
            run(args.output)
