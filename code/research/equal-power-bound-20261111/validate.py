"""Certify equal-power regret on the original 180-case priced-assignment panel."""
import argparse
import csv
import hashlib
import io
import json
import math
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
from pathlib import Path
from time import perf_counter

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent / "priced-assignment-20261111"
GRID = HERE.parent / "cdl-headroom-20261111"
CHECK = HERE.parent / "manuscript-refinement-20261106/certification"
sys.path.insert(0, str(CHECK))
from checker import check_schedule, integral_maximum, reconstruct, require
from integer_logs import log_enclosure

SCALE = 1 << 44
ROOT_SCALE = 1 << 64
LOG2_LO, LOG2_HI = log_enclosure(F(2))


def axis_upper(g, c, left):
    """Outward correction on [left,1] in units of b, where g and c include b."""
    if left == 1 or g == 0:
        return 1 - left

    def bound(lo, hi):
        ratio = (1+c*hi)**2 * (1+g) / ((1+c)**2 * (1+g*lo))
        return log_enclosure(ratio)[1] + (1-lo)

    best = max(F(0), bound(left, left))
    # The derivative has the sign of -cg*z²+(cg-c-g)*z+2c-g-1.
    cg = c*g
    center = (cg-c-g)/(2*cg)
    radicand = center**2 + (2*c-g-1)/cg
    if radicand > 0:
        # Only the larger root can change the derivative from positive to negative.
        n = math.isqrt(radicand.numerator*ROOT_SCALE**2 // radicand.denominator)
        lo = max(left, center + F(n, ROOT_SCALE))
        hi = min(F(1), center + F(n+1, ROOT_SCALE))
        if lo <= hi:
            best = max(best, bound(lo, hi))
    return best


def edge_weights(coefficients, low, b):
    """Return upward integer weights for equal power and the continuous bound."""
    if b == 0:
        return 0, 0
    g, h, r = coefficients
    g, h = g*b, h*b
    a = 1-r
    d = 1+g+h+a*g*h
    uniform = log_enclosure(d*d / ((1+g)*(1+h)))[1]
    first = axis_upper(g, g*(1+a*h)/(1+h), low/b)
    second = axis_upper(h, h*(1+a*g)/(1+g), low/b)
    return math.ceil(SCALE*uniform), math.ceil(SCALE*(uniform+first+second))


def upper_bounds(model):
    k, s, low, high, budget, data, _ = model
    # K*b is the effective network budget, including when all upper rails bind.
    b = min(budget/k, high)
    equal, analytic = {}, {}
    for key, coefficients in data.items():
        equal[key], analytic[key] = edge_weights(coefficients, low, b)
    ue, ne = integral_maximum(k, equal)
    ua, na = integral_maximum(k, analytic)
    require(ne == na == 1 << (k-1) and ua >= ue, "subset DP coverage or ordering")
    return b, F(ue, SCALE), F(ua, SCALE)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def checked_case(path, base_path, priced_path=None, grid=None):
    case = read(path)
    model = reconstruct(case)
    k, s = model[:2]
    metadata = case["metadata"]
    digest = sha(path)
    b, equal_upper, analytic = upper_bounds(model)
    base = read(base_path)
    require(base["case"] == case["name"] and base["case_sha256"] == digest
            and base["arm"] == "DP-SQP", "wrong DP-SQP allocation")
    candidates = [item["schedule"] for item in base["history"]
                  if all(F(p) == b for edge in item["schedule"] for p in edge["powers"])]
    require(bool(candidates), "no archived equal-power allocation")
    # The fixed-power subset DP also bounds the distance of this feasible witness
    # from the true equal-power optimum, independently of the search history.
    equal_lo, equal_hi, chosen = max(
        ((*check_schedule(sch, model), i) for i, sch in enumerate(candidates))
    )
    require(equal_upper >= equal_hi and equal_upper-equal_lo < F(1,10**10),
            "equal-power witness or matching upper bound is loose")
    base_lo, base_hi = check_schedule(base["schedule"], model)
    require(analytic >= max(equal_hi, base_hi), "analytic bound below a feasible rate")
    pairs = ["-".join(map(str, edge["users"]))
             for edge in sorted(candidates[chosen], key=lambda edge: edge["resource"])]
    row = dict(case=case["name"], block=metadata["block"], profile=metadata["profile"],
               snr_db=metadata["snr_db"], case_sha256=digest, equal_pairs="|".join(pairs),
               equal_feasible_lower_nats=equal_lo, equal_dp_upper_nats=equal_upper,
               analytic_upper_nats=analytic, base_lower_nats=base_lo)
    achieved = base_lo
    if priced_path is not None:
        priced = read(priced_path)
        require(priced["case"] == case["name"] and priced["case_sha256"] == digest
                and priced["arm"] == "Price-DP-SQP", "wrong priced allocation")
        priced_lo, priced_hi = check_schedule(priced["schedule"], model)
        grid_ub = F(grid["global_upper_nats"])
        require(grid["case_sha256"] == digest and grid["base_run_sha256"] == sha(base_path)
                and grid["priced_run_sha256"] == sha(priced_path), "grid case/run binding")
        require((base_lo, base_hi, priced_lo, priced_hi) == tuple(F(grid[key]) for key in
                ("base_lower_nats","base_upper_nats","priced_lower_nats","priced_upper_nats")),
                "allocation and grid checker disagree")
        achieved = max(base_lo, priced_lo)
        require(min(analytic, grid_ub) >= max(base_hi, priced_hi, equal_hi),
                "upper below independently checked allocation")
        row.update(priced_lower_nats=priced_lo, grid_upper_nats=grid_ub)
        row.update(grid_gap_ub_bpshz=(grid_ub-equal_lo)/(s*LOG2_LO),
                   combined_gap_ub_bpshz=(min(analytic,grid_ub)-equal_lo)/(s*LOG2_LO),
                   combined_dp_sqp_gap_ub_bpshz=(min(analytic,grid_ub)-base_lo)/(s*LOG2_LO))
    row.update(achieved_gain_lb_bpshz=max(F(0), achieved-equal_upper)/(s*LOG2_HI),
               analytic_gap_ub_bpshz=(analytic-equal_lo)/(s*LOG2_LO),
               analytic_dp_sqp_gap_ub_bpshz=(analytic-base_lo)/(s*LOG2_LO))
    return row


def check_archived(grid):
    name = grid["case"]
    path = STUDY / "cases" / (name+".json")
    runs = STUDY / "runs/main"
    return checked_case(path, runs/(name+"-DP-SQP.json"), runs/(name+"-Price-DP-SQP.json"), grid)


def decimal_bound(value, upward):
    """Directed decimal for display and plotting. All thresholds use exact fractions."""
    scale = 10**12
    units = (math.ceil if upward else math.floor)(value*scale)
    require(units >= 0, "negative regret")
    return f"{units//scale}.{units%scale:012d}"


def summary(rows):
    fields = ("achieved_gain_lb_bpshz", "analytic_gap_ub_bpshz", "grid_gap_ub_bpshz",
              "combined_gap_ub_bpshz", "analytic_dp_sqp_gap_ub_bpshz",
              "combined_dp_sqp_gap_ub_bpshz")
    result = dict(cases=len(rows), tolerance_bpshz="0.01")
    for field in fields:
        values = [r[field] for r in rows]
        upward = "_ub_" in field
        hi = max(values)
        result[field] = dict(mean=decimal_bound(statistics.mean(values),upward),
                             median=decimal_bound(statistics.median(values),upward),
                             min=decimal_bound(min(values),upward),
                             max=decimal_bound(hi,upward),
                             max_case=rows[values.index(hi)]["case"],
                             at_most_0p01=sum(v <= F(1,100) for v in values))
    result["analytic_tighter_than_grid"] = sum(r["analytic_upper_nats"] < r["grid_upper_nats"] for r in rows)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run","check","pilot"))
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.action == "pilot":
        prior = HERE.parent / "independent-cdl-20261110"
        name = "pilot-A-snr10"
        start = perf_counter()
        row = checked_case(prior/"cases"/(name+".json"), prior/"runs/pilot"/(name+"-DP-SQP.json"))
        print(json.dumps({key:str(value) for key,value in row.items()}, indent=2))
        print(f"{perf_counter()-start:.3f} seconds", flush=True)
        return
    require(args.workers >= 1, "workers must be positive")
    table = GRID / "cases.csv"
    grid_summary = read(GRID / "results.json")
    require(grid_summary["status"] == "PASS" and sha(table) == grid_summary["cases_csv_sha256"],
            "grid replay table checksum")
    with table.open(encoding="utf-8", newline="") as f:
        grid_rows = list(csv.DictReader(f))
    names = [f"native-b{n:02d}-{profile}-snr{snr:02d}"
             for n in range(20) for profile in "ABC" for snr in (0,10,20)]
    require([r["case"] for r in grid_rows] == names, "expected all 180 original cases")
    manifest = read(STUDY / "runs/main/manifest.json")
    require(all(manifest["cases"]["cases/"+r["case"]+".json"] == r["case_sha256"]
                for r in grid_rows), "original main panel binding")
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(check_archived, grid_rows):
            rows.append(row)
            if len(rows) % 15 == 0:
                print(f"Checked {len(rows)}/180", flush=True)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=rows[0], lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key:decimal_bound(v,"_ub_" in key) if key.endswith("_bpshz") else v
                         for key,v in row.items()})
    csv_bytes = buffer.getvalue().encode("utf-8")
    result = dict(status="PASS", panel="original 180 priced-assignment cases", aggregate_unit="nats",
                  gap_unit="occupied-band bit/s/Hz", weight_scale=SCALE, root_scale=ROOT_SCALE,
                  cases_sha256=hashlib.sha256(csv_bytes).hexdigest(),
                  input_grid_sha256=sha(table), checker_sha256=sha(CHECK/"checker.py"),
                  integer_logs_sha256=sha(CHECK/"integer_logs.py"),
                  all_cases=summary(rows), by_snr_db={
                      str(s):summary([r for r in rows if r["snr_db"] == s]) for s in (0,10,20)})
    files = {"cases.csv":csv_bytes, "summary.json":(json.dumps(result,indent=2)+"\n").encode("utf-8")}
    for name, payload in files.items():
        path = HERE / name
        if args.action == "check":
            require(path.read_bytes() == payload, f"stored {name} disagrees with replay")
        else:
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(payload)
            tmp.replace(path)
    print(json.dumps(result["by_snr_db"], indent=2))


if __name__ == "__main__":
    main()
