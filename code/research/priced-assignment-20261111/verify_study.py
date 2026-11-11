"""Independent replay of a complete 720-allocation priced-assignment holdout."""
import argparse
import hashlib
import importlib.util
import json
import math
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
PREVIOUS = HERE.parent / "independent-cdl-20261110"
spec = importlib.util.spec_from_file_location("prior_independent_replay", PREVIOUS / "audit_campaign.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
# Only the input root used by the old Fourier/physical array checker changes.
audit.HERE = HERE
read, sha, require, local_path = audit.read, audit.sha, audit.require, audit.local_path
ARMS = ("Price-DP-SQP", "DP-SQP", "DP-Fu-SCA", "DP-Thu-IDE")


def save(path, obj):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)


def seed_inventory(ledger):
    profiles = {(row["block"], row["profile"]): row for row in ledger["profiles"]}
    require(len(profiles) == len(ledger["profiles"]) == 60 and
            set(profiles) == {(b, p) for b in range(20) for p in "ABC"}, "Invalid fresh profile design")
    records = [ledger["bootstrap"]]
    for row in profiles.values():
        require(row["phase"] == "main" and len(row["channels"]) == len(row["factors"]) == 16,
                "Invalid profile namespace")
        records.extend(row["channels"] + row["factors"] + [row["initialization"], row["search"]])
    values, keys = [], []
    for row in records:
        entropy = int(row["entropy"])
        key = tuple(row["spawn_key"])
        require(entropy == int(ledger["root_entropy"]), "Different root entropy")
        expected = int(np.random.SeedSequence(entropy, spawn_key=key).generate_state(1, dtype=np.uint32)[0])
        require(expected == row["effective_seed"], "Seed lineage mismatch")
        keys.append(key)
        values.append(expected)
    require(len(set(keys)) == len(set(values)) == ledger["effective_seed_count"] == 2041,
            "Duplicate or missing purpose seed")
    historical = set(ledger["historical_audit"]["seeds"])
    require(not set(values).intersection(historical), "Historical seed collision")
    return profiles, {"purpose_seeds": len(values), "excluded_identifiers": len(historical)}


def objective_product(schedule, model):
    """Exact rational product whose natural logarithm is the sum rate."""
    total = Fraction(1)
    for row in schedule:
        u, v = row["users"]
        g, h, rho = model[5][u, v, row["resource"]]
        p, q = map(Fraction, row["powers"])
        x, y = g*p, h*q
        d = 1+x+y+(1-rho)*x*y
        total *= d*d / ((1+x)*(1+y))
    return total


def run_audit():
    frozen_path = HERE / "source_manifest.json"
    frozen_hash = sha(frozen_path)
    for name, digest in read(frozen_path)["hashes"].items():
        require(sha(local_path(PROJECT, name)) == digest, "Source mismatch: " + name)
    seed_hash = sha(HERE / "seed_manifest.json")
    ledger = read(HERE / "seed_manifest.json")
    profiles, seed_report = seed_inventory(ledger)
    for rel in ("generator_validation_main.json", "generator_validation_replay.json"):
        require(read(HERE / rel)["status"] == "PASS", "Input validation failed")
    generation = read(HERE/"generator_validation_main.json")
    replay = read(HERE/"generator_validation_replay.json")
    gen_hashes = {c["case_path"]:c["case_sha256"] for p in generation["profiles"] for c in p["cases"]}
    require(generation["seed_manifest_sha256"] == replay["seed_manifest_sha256"] == seed_hash and
            replay["generation_receipt_sha256"] == sha(HERE/"generator_validation_main.json") and
            replay["regenerated_links_bitwise_equal"] == 960 and replay["coefficients_checked"] == 172800 and
            len(gen_hashes) == 180, "Input replay/seed ledger mismatch")
    require(ledger["sources"]["generator_sha256"] == sha(PREVIOUS / "generator.py") and
            ledger["sources"]["wrapper_sha256"] == sha(HERE / "generate_holdout.py") and
            ledger["sources"]["protocol_sha256"] == sha(HERE / "GENERATOR_PROTOCOL.md"),
            "Generator source binding mismatch")
    folder = HERE / "runs/main"
    manifest = read(folder / "manifest.json")
    require(manifest["source_manifest_sha256"] == frozen_hash and manifest["arms"] == list(ARMS) and
            (manifest["cap_seconds"], manifest["block_seconds"]) == (10, 5), "Stage manifest mismatch")
    expected = {(b, p, s) for b in range(20) for p in "ABC" for s in (0, 10, 20)}
    seen = set()
    native, receipts, result_hashes, evidence_hashes, finals = {}, [], {}, {}, {}
    shared_starts, checked_process = {}, set()
    total_starts = total_history = total_unique = 0
    max_scalar = max_matrix = 0.0
    ordered = []
    for rel in manifest["cases"]:
        meta = read(local_path(HERE, rel))["metadata"]
        ordered.append((meta["block"], meta["profile"], meta["snr_db"], rel))
    ordered.sort()
    require(len(ordered) == 180, "Incomplete case manifest")
    paths_expected = {"manifest.json"}
    for index, (block, profile, snr, rel) in enumerate(ordered):
        key = block, profile, snr
        require(key in expected and key not in seen, f"Unexpected or repeated design cell {key}")
        seen.add(key)
        case_path = local_path(HERE, rel)
        case_hash = sha(case_path)
        require(case_hash == manifest["cases"][rel] == gen_hashes[rel], "Case hash mismatch")
        evidence_hashes[rel] = case_hash
        case = read(case_path)
        meta = case["metadata"]
        require(case["name"] == case_path.stem and not meta["pilot"] and
                meta["seed_manifest_sha256"] == seed_hash, "Invalid holdout identity")
        require((case["K"], case["S"], case["M"]) == (16, 8, 2) and
                tuple(map(Fraction, (case["pmin"], case["pmax"], case["budget"]))) ==
                (Fraction(1,1000), Fraction(1,5), Fraction(52,25)), "Physical domain mismatch")
        channels = audit.native_audit(case, profiles[block, profile], native)
        model = audit.checker.reconstruct(case)
        schedule_cache = {}
        start_path = folder / (case_path.stem + "-starts.json")
        start_hash = sha(start_path)
        evidence_hashes[start_path.relative_to(HERE).as_posix()] = start_hash
        paths_expected.add(start_path.name)
        start_file = read(start_path)
        starts = start_file["starts"]
        ids = [hashlib.sha256(audit.canonical(s).encode()).hexdigest() for s in starts]
        require(len(set(ids)) == len(starts) == 8 and ids == start_file["start_ids"] and
                start_file["initialization_seed"] == meta["initialization_seed"] and
                start_file["case_sha256"] == case_hash, "Common-start identity failed")
        require(shared_starts.setdefault((block, profile), ids) == ids, "Different starts across paired SNRs")
        for schedule in starts:
            audit.checker.check_schedule(schedule, model)
            total_starts += 1
        unit_order = ARMS[index % 4:] + ARMS[:index % 4]
        products, run_names = {}, {}
        for pos, arm in enumerate(unit_order):
            path = folder / (case_path.stem + "-" + arm + ".json")
            row = read(path)
            paths_expected.add(path.name)
            require((row["block"], row["profile"], row["snr_db"], row["arm"]) == (*key, arm) and
                    row["stage"] == "main" and row["case_path"] == rel and row["case"] == case_path.stem and
                    row["case_sha256"] == case_hash and row["source_manifest_sha256"] == frozen_hash and
                    row["starts_sha256"] == start_hash and row["offered_start_ids"] == ids and
                    row["initialization_seed"] == meta["initialization_seed"] and
                    row["search_seed"] == meta["search_seed"] and row["position"] == pos and
                    row["order"] == list(unit_order), "Run provenance mismatch: " + path.name)
            proc = local_path(HERE / "runs/processes", row["process"] + ".json")
            require(sha(proc) == row["process_sha256"], "Warm initialization receipt hash mismatch")
            if proc not in checked_process:
                warm = read(proc)
                require(warm["source_manifest_sha256"] == frozen_hash and warm["numba_threads"] == 1 and
                        set(warm["arms"]) == set(ARMS) and all(p["num_threads"] == 1 for p in warm["thread_pools"]),
                        "Incomplete warmup or multithreaded timing")
                evidence_hashes[proc.relative_to(HERE).as_posix()] = sha(proc)
                checked_process.add(proc)
            elapsed = row["elapsed_seconds"]
            require(math.isfinite(elapsed) and elapsed > 0 and (row["cap_seconds"], row["block_seconds"]) ==
                    (10, 5) and 0 <= row["overrun_seconds"] < 0.5 and
                    abs(row["overrun_seconds"]-max(0,elapsed-10)) < 1e-8, "Invalid timing")
            history = row["history"]
            require(history and history[0]["kind"] == "initial" and history[0]["schedule"] == starts[0] and
                    row["counts"]["accepted"] == len(history)-1 and isinstance(row["diagnostics"],list),
                    "Missing initial allocation or history")
            last_time, last_rate, last_upper = -1, -math.inf, None
            result_name = path.relative_to(HERE).as_posix()
            for j, item in enumerate([*history, row]):
                if j < len(history):
                    require(last_time <= item["seconds"] <= min(10, elapsed) and
                            item["rate_nats"] >= last_rate and
                            (j == 0 or (item["kind"] == "improvement" and
                             Fraction(item["lower_nats"]) > last_upper)), "Invalid retained improvement")
                    last_time, last_rate, last_upper = item["seconds"], item["rate_nats"], Fraction(item["upper_nats"])
                    total_history += 1
                signature = audit.canonical(item["schedule"])
                if signature not in schedule_cache:
                    schedule_cache[signature] = audit.evaluate(item["schedule"], model, channels)
                checked = schedule_cache[signature]
                scalar, matrix = audit.check_reported(item, checked)
                max_scalar, max_matrix = max(max_scalar, scalar), max(max_matrix, matrix)
                receipts.append(dict(result=result_name, event=j if j<len(history) else "final",
                    scalar_error_nats=scalar, matrix_error_nats=matrix,
                    independent_lower_nats=str(checked["lower"]), independent_upper_nats=str(checked["upper"])))
            require(all(row[field] == history[-1][field] for field in
                    ("schedule","rate_nats","se_bits","lower_nats","upper_nats")), "Final differs from retained incumbent")
            # Use the tighter independently reconstructed decimal enclosure to resolve
            # tiny true rate differences. Identical schedules can be detected separately.
            finals[result_name] = dict(lower_nats=str(checked["decimal_lower"]), upper_nats=str(checked["decimal_upper"]),
                                       schedule_sha256=hashlib.sha256(signature.encode()).hexdigest())
            products[arm] = objective_product(row["schedule"], model)
            run_names[arm] = result_name
            result_hashes[result_name] = sha(path)
        best_product = max(products[a] for a in ARMS[1:])
        comparisons = {**{a:products[a] for a in ARMS[1:]}, "casewise_best":best_product}
        finals[run_names[ARMS[0]]]["exact_sign_vs"] = {
            a:int(products[ARMS[0]] > score)-int(products[ARMS[0]] < score)
            for a,score in comparisons.items()}
        finals[run_names[ARMS[0]]]["exact_best_controls"] = [
            a for a in ARMS[1:] if products[a] == best_product]
        total_unique += len(schedule_cache)
    require(seen == expected and len(result_hashes) == 720 and len(native) == 60 and total_starts == 1440,
            "Incomplete holdout")
    require({p.name for p in folder.glob("*.json")} == paths_expected,
            "Unexpected failed, rejected or extra raw run")
    evidence_hashes.update({p.relative_to(HERE).as_posix(): sha(p) for p in native})
    evidence_hashes["runs/main/manifest.json"] = sha(folder / "manifest.json")
    save(HERE/"audit_receipts.json",receipts)
    save(HERE/"audit_final_intervals.json",finals)
    return dict(status="PASS", final_allocations=720, cases=len(seen), native_profiles=len(native),
        retained_history_allocations=total_history, offered_starts_checked=total_starts,
        unique_schedules_evaluated=total_unique, max_scalar_error_nats=max_scalar,
        max_matrix_error_nats=max_matrix, max_fourier_error=max(x["_fourier_error"] for x in native.values()),
        seed_audit=seed_report, source_manifest_sha256=frozen_hash, seed_manifest_sha256=seed_hash,
        runs_sha256=result_hashes, evidence_sha256=evidence_hashes,
        receipts_sha256=sha(HERE/"audit_receipts.json"), final_intervals_sha256=sha(HERE/"audit_final_intervals.json"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    if parser.parse_args().self_test:
        audit.self_test()
        return
    began = time.monotonic()
    try:
        result = run_audit()
    except Exception as error:
        result = dict(status="FAIL", error=repr(error))
    result["seconds"] = time.monotonic()-began
    save(HERE/"audit_study.json",result)
    print(json.dumps({k:result[k] for k in ("status","seconds","final_allocations","error") if k in result}))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
