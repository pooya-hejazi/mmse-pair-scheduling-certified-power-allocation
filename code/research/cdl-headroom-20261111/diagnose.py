"""Replay the 180 native-CDL certificates and the paired gain bounds over DP-SQP."""
import argparse
import csv
import gzip
import json
import multiprocessing as mp
import os
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
ADD = HERE / "additional-witnesses"
ARMS = ("Price-DP-SQP", "DP-SQP")
SNRS = (0, 10, 20)


def initialize(snapshot, endpoints_only=False):
    global cert, study, manifest, source_hash, original_bound_hashes, log2, full_replay
    global audited_intervals, audited_runs, implementation
    study = snapshot / "code/research/priced-assignment-20261111"
    sys.path.insert(0, str(study / "native_certificate"))
    import certificate as cert
    implementation = cert.source_hashes()
    assert cert.read(cert.HERE / "freeze.json")["hashes"] == implementation
    manifest = cert.read(study / "runs/main/manifest.json")
    source_hash = cert.sha(study / "source_manifest.json")
    assert manifest["source_manifest_sha256"] == source_hash
    frozen = cert.read(cert.HERE / "witnesses/replay-receipt.json")
    original_bound_hashes = {row["block"]: row["witness_sha256"] for row in frozen["rows"]}
    assert set(original_bound_hashes) == set(range(20))
    audit = cert.read(study / "audit_study.json")
    intervals = study / "audit_final_intervals.json"
    assert audit["status"] == "PASS" and audit["source_manifest_sha256"] == source_hash
    assert cert.sha(intervals) == audit["final_intervals_sha256"]
    audited_intervals, audited_runs = cert.read(intervals), audit["runs_sha256"]
    log2 = cert.log_enclosure(Fraction(2))
    full_replay = not endpoints_only


def ordered_allocation(schedule):
    pairs = [tuple(sorted(row["users"])) for row in sorted(schedule, key=lambda row: row["resource"])]
    powers = {u: Fraction(p) for row in schedule for u, p in zip(row["users"], row["powers"], strict=True)}
    return pairs, powers


def check_case(saved):
    name = saved["case"]
    case_file = study / "cases" / (name + ".json")
    case = cert.read(case_file)
    m = case["metadata"]
    block, profile, snr = m["block"], m["profile"], m["snr_db"]
    assert name == case["name"] == f"native-b{block:02d}-{profile}-snr{snr:02d}"
    assert (case["K"], case["S"], case["M"]) == (16, 8, 2) and not m["pilot"]
    assert Fraction(case["budget"]) == Fraction(52, 25)
    d = cert.sha(case_file)
    assert manifest["cases"]["cases/" + name + ".json"] == d
    paths = [study / "runs/main" / (name + "-" + arm + ".json") for arm in ARMS]
    priced, base = runs = [cert.read(p) for p in paths]
    run_hashes = [cert.sha(p) for p in paths]
    relpaths = [p.relative_to(study).as_posix() for p in paths]
    for arm, run, rel, digest in zip(ARMS, runs, relpaths, run_hashes, strict=True):
        assert (run["arm"], run["case"], run["case_sha256"], run["source_manifest_sha256"]) == (arm, name, d, source_hash)
        assert run["cap_seconds"] == 10 and run["case_path"] == case_file.relative_to(study).as_posix()
        assert audited_runs[rel] == digest
    assert priced["offered_start_ids"] == base["offered_start_ids"]
    assert audited_intervals[relpaths[0]]["exact_best_controls"] == ["DP-SQP"]
    binding = dict(case_sha256=d, run_sha256=run_hashes[0], case=name, historical_pilot=False)
    original = profile == "B" and snr == 10
    if original:
        path = cert.HERE / "witnesses" / (name + ".json")
        assert cert.sha(path) == original_bound_hashes[block]
        witness = cert.read(path)
    else:
        path = ADD / (name + ".json.gz")
        witness = json.loads(gzip.decompress(path.read_bytes()))
    assert witness["binding"] == binding and witness["implementation"] == implementation
    assert witness["schedule"] == priced["schedule"] and len(witness["edges"]) == 960
    if full_replay:
        cert.make(case, priced, binding, witness)
        lo, hi = cert.check_schedule(base["schedule"], cert.reconstruct(case))
    else:
        lo, hi = map(Fraction, (saved["base_lower_nats"], saved["base_upper_nats"]))
    lp, hp = map(Fraction, (witness["feasible_lower_nats"], witness["feasible_upper_nats"]))
    for rel, lower, higher in zip(relpaths, (lp, lo), (hp, hi), strict=True):
        audited = audited_intervals[rel]
        assert lower <= Fraction(audited["lower_nats"]) <= Fraction(audited["upper_nats"]) <= higher
    price = Fraction(witness["price"])
    assert price == cert.select_price(priced) and int(witness["weight_scale"]) == cert.WEIGHT_SCALE
    upper = price * Fraction(case["budget"]) + Fraction(int(witness["dp_max_integer"]), cert.WEIGHT_SCALE)
    assert upper == Fraction(witness["global_upper_nats"])
    assert upper >= hi >= lo and upper >= hp >= lp
    denom = case["S"] * log2[0]
    gap_base = (upper - lo) / denom
    gap_priced = (upper - lp) / denom
    assert gap_priced == Fraction(witness["gap_upper_se"])
    bp, bw = ordered_allocation(base["schedule"])
    pp, pw = ordered_allocation(priced["schedule"])
    assert bw.keys() == pw.keys() == set(range(case["K"]))
    row = dict(case=name, block=block, profile=profile, snr_db=snr,
                certificate_source="published" if original else "post-hoc",
                case_sha256=d, priced_run_sha256=run_hashes[0], base_run_sha256=run_hashes[1],
                global_upper_nats=str(upper), base_lower_nats=str(lo), base_upper_nats=str(hi),
                priced_lower_nats=str(lp), priced_upper_nats=str(hp),
                base_gap_upper_bpshz=str(gap_base), priced_gap_upper_bpshz=str(gap_priced),
                achieved_gain_bpshz=priced["se_bits"]-base["se_bits"],
                same_resource_pairs=sum(a == b for a,b in zip(pp, bp, strict=True)),
                same_user_powers=sum(pw[u] == bw[u] for u in bw),
                base_mean_abs_power_deviation_from_uniform_W=float(mean(abs(p-Fraction(13,100)) for p in bw.values())),
                added_price_trials=priced["counts"]["price_dp_completed"])
    assert {k: str(v) for k, v in row.items()} == saved, f"Per-case record differs for {name}"
    return row


def summarize(rows):
    bg = [Fraction(r["base_gap_upper_bpshz"]) for r in rows]
    pg = [Fraction(r["priced_gap_upper_bpshz"]) for r in rows]
    target = Fraction(1,100)
    return dict(cases=len(rows), mean_gain_bpshz=mean(r["achieved_gain_bpshz"] for r in rows),
                mean_global_gap_over_base_upper_exact=str(mean(bg)),
                mean_global_gap_over_base_upper_bpshz=float(mean(bg)),
                mean_global_gap_over_priced_upper_exact=str(mean(pg)),
                mean_global_gap_over_priced_upper_bpshz=float(mean(pg)),
                base_gap_provably_below_0p01=sum(x<target for x in bg),
                same_assignment=sum(r["same_resource_pairs"] == 8 for r in rows),
                same_assignment_and_powers=sum(r["same_resource_pairs"] == 8 and r["same_user_powers"] == 16 for r in rows),
                mean_base_abs_deviation_from_uniform_W=mean(r["base_mean_abs_power_deviation_from_uniform_W"] for r in rows))


def paired_bounds(rows):
    """Enclose the achieved gain and compare each feasible gain and global gap with 1/100."""
    threshold = Fraction(1, 100)
    groups = {"all_cases": rows}
    groups.update({str(s): [r for r in rows if r["snr_db"] == s] for s in SNRS})
    summaries = {}
    for label, group in groups.items():
        base_gaps, priced_gaps, gains_lower, gains_upper = [], [], [], []
        impossible, attained = [], []
        for r in group:
            base_gap = Fraction(r["base_gap_upper_bpshz"])
            base_gaps.append(base_gap)
            priced_gaps.append(Fraction(r["priced_gap_upper_bpshz"]))
            lower = Fraction(r["priced_lower_nats"]) - Fraction(r["base_upper_nats"])
            upper = Fraction(r["priced_upper_nats"]) - Fraction(r["base_lower_nats"])
            # The sign determines which endpoint of ln(2) gives an outward bound.
            lower /= 8 * (log2[1] if lower >= 0 else log2[0])
            upper /= 8 * (log2[0] if upper >= 0 else log2[1])
            if r["same_resource_pairs"] == 8 and r["same_user_powers"] == 16:
                assert lower <= 0 <= upper
                lower = upper = Fraction(0)
            assert lower <= upper and lower <= base_gap
            gains_lower.append(lower)
            gains_upper.append(upper)
            if base_gap < threshold:
                impossible.append(r["case"])
            if lower > threshold:
                attained.append(r["case"])
        assert set(impossible).isdisjoint(attained)
        max_base, max_priced = max(base_gaps), max(priced_gaps)
        summaries[label] = dict(cases=len(group), provably_impossible=len(impossible),
                             provably_attained=len(attained), unresolved=len(group)-len(impossible)-len(attained),
                             mean_achieved_gain_lower_bpshz=str(mean(gains_lower)),
                             mean_achieved_gain_upper_bpshz=str(mean(gains_upper)),
                             mean_base_gap_upper_bpshz=str(mean(base_gaps)),
                             mean_priced_gap_upper_bpshz=str(mean(priced_gaps)),
                             max_base_gap_upper_bpshz=str(max_base),
                             max_base_gap_cases=[r["case"] for r, g in zip(group, base_gaps) if g == max_base],
                             max_priced_gap_upper_bpshz=str(max_priced),
                             max_priced_gap_cases=[r["case"] for r, g in zip(group, priced_gaps) if g == max_priced],
                             attained_cases=attained)
    overall = summaries.pop("all_cases")
    return dict(threshold_bpshz=str(threshold), all_cases=overall, by_snr_db=summaries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", nargs="?", type=Path, default=HERE.parents[2], help="Scientific repository root.")
    parser.add_argument("--workers", type=int, default=1, help="Number of witness checkers (default 1).")
    parser.add_argument("--endpoints-only", action="store_true",
                        help="Check paired bounds from the stored integer assignment values and audited rates.")
    parser.add_argument("--output", type=Path, help="Write the checked paired_bounds.json to this directory.")
    args = parser.parse_args()
    if args.workers < 1 or not __debug__:
        parser.error("Use at least one worker and run Python with assertions enabled.")
    snapshot = args.snapshot.resolve()
    os.environ["OPENBLAS_NUM_THREADS"] = os.environ["OMP_NUM_THREADS"] = os.environ["MKL_NUM_THREADS"] = "1"
    sys.dont_write_bytecode = True
    initialize(snapshot, args.endpoints_only)
    with (study / "analysis/case_values.csv").open(encoding="utf-8", newline="") as f:
        published = {r["case"]: r for r in csv.DictReader(f)}
    names = [f"native-b{b:02d}-{p}-snr{s:02d}" for b in range(20) for p in "ABC" for s in SNRS]
    assert set(names) == set(published) and len(published) == 180
    assert all(row["exact_best_controls"] == "DP-SQP" for row in published.values())
    extra_names = {name + ".json.gz" for name in names if not name.endswith("-B-snr10")}
    assert {p.name for p in ADD.glob("*.json.gz")} == extra_names
    with (HERE / "cases.csv").open(encoding="utf-8", newline="") as f:
        saved = list(csv.DictReader(f))
    assert [r["case"] for r in saved] == names
    original = cert.read(HERE / "results.json")
    assert original["cases_csv_sha256"] == cert.sha(HERE / "cases.csv")
    assert original["certificate_implementation"] == implementation and original["study_source_sha256"] == source_hash
    mode = "saved endpoints" if args.endpoints_only else "full grid witnesses and paired rates"

    def collect(checked):
        rows = []
        for row in checked:
            expected = float(published[row["case"]]["new_minus_DP-SQP"])
            assert abs(row["achieved_gain_bpshz"] - expected) < 1e-12
            rows.append(row)
            if len(rows) % 15 == 0:
                print(f"Verified {mode} for {len(rows)}/180 cases", flush=True)
        return rows

    if args.workers == 1:
        rows = collect(map(check_case, saved))
    else:
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=mp.get_context("spawn"),
                                 initializer=initialize, initargs=(snapshot, args.endpoints_only)) as pool:
            rows = collect(pool.map(check_case, saved))
    assert len(rows) == 180 and sum(r["certificate_source"] == "published" for r in rows) == 20
    assert summarize(rows) == original["all_cases"]
    assert {str(s): summarize([r for r in rows if r["snr_db"] == s]) for s in SNRS} == original["by_snr_db"]
    paired = paired_bounds(rows)
    assert paired == cert.read(HERE / "paired_bounds.json"), "Published paired bounds differ"
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=args.output) as pending:
            path = Path(pending) / "paired_bounds.json"
            path.write_bytes((json.dumps(paired, indent=2, allow_nan=False) + "\n").encode("utf-8"))
            path.replace(args.output / path.name)
    print(f"PASS. Checked {mode} and reproduced the exact paired bounds for all 180 cases.", flush=True)


if __name__ == "__main__":
    main()
