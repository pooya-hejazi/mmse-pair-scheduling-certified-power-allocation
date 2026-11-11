"""Replayable, exact-integer post-run certificate for the prespecified M=2 subset."""
import argparse
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
CHECK = STUDY.parent / "manuscript-refinement-20261106/certification"
sys.path.insert(0, str(CHECK))
from checker import check_schedule, integral_maximum, reconstruct, require
from integer_logs import log_enclosure

D = 10**9
Q = 1 << 80
WEIGHT_SCALE = 1 << 44
EXP_DENOM = Q**4 * D**4
PROTOCOL_SHA256 = "329ce412aabae599150eaeedec1323a1a64ec75a391a8c06e455959447843218"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    temp.replace(path)


def source_hashes():
    require(sha(HERE/"PROTOCOL.md") == PROTOCOL_SHA256, "certificate protocol changed")
    paths = [HERE/name for name in ("certificate.py", "tests.py", "PROTOCOL.md", "PROOF.md")]
    paths.extend([CHECK/"integer_logs.py", CHECK/"checker.py"])
    return {p.relative_to(STUDY.parent).as_posix(): sha(p) for p in paths}


def grid():
    points = [D//1000]
    while points[-1] < D//5:
        points.append(min(D//5, 17*points[-1]//16))
    require(all(a < b and 16*b <= 17*a for a,b in zip(points, points[1:])), "bad grid interval")
    return points


def select_price(run):
    for row in reversed(run["diagnostics"]):
        if row.get("method") == "GRID_PRICE":
            value = row["price"]
            if type(value) in (int,float) and math.isfinite(value) and value >= 0:
                return F(value)
    return F(0)


def exp_negative_upper(x):
    """Upper for exp(-x), from exp(x) >= its degree-28 Taylor polynomial."""
    require(x >= 0, "negative exponential price")
    term = total = F(1)
    for j in range(1, 29):
        term *= x/j
        total += term
    return 1/total


def axis_tables(points, price, gains):
    """Integer upper factors for exp(-price*p)/(1+g*p), and interpolation slack."""
    ps = [F(n,D) for n in points]
    exponentials = [exp_negative_upper(price*p) for p in ps]
    factors, errors = {}, {}
    for g in set(gains):
        factors[g] = np.array([math.ceil(Q*ep/(1+g*p)) for ep,p in zip(exponentials,ps)], dtype=object)
        ratio = max(g*(b-a)/(1+g*a) for a,b in zip(ps,ps[1:]))
        errors[g] = ratio**2/8
    return factors, errors


def coefficients(g,h,r):
    """Round nonnegative physical coefficients upwards before any node products."""
    require(g >= 0 and h >= 0 and 0 <= r <= 1, "invalid coefficients")
    return tuple(math.ceil(Q*z) for z in (g,h,(1-r)*g*h))


def node_max(parameters, points, products, first, second):
    g,h,c = parameters
    d = Q*D**2 + (g*D)*points[:,None] + (h*D)*points[None,:] + c*products
    return int(np.max(d*d*first[:,None]*second[None,:]))


def verify_node_max(maximum, parameters, points, first, second):
    """Independent row-wise coverage and attainment check of the producer's maximum."""
    g,h,c = parameters
    attained = False
    for n, fi in zip(points, first):
        d = (Q*D**2 + g*D*n) + (h*D+c*n)*points
        value = int(fi*max(d*d*second))
        require(value <= maximum, "node above witness maximum")
        attained |= value == maximum
    require(attained, "witness maximum unattained")


def make(case, run, binding, witness=None):
    model = reconstruct(case)
    k,s,low,high,budget,data,gains = model
    require((low,high) == (F(1,1000),F(1,5)), "unexpected box")
    schedule_lower, schedule_upper = check_schedule(run["schedule"], model)
    price = select_price(run)
    nodes = grid()
    points = np.array(nodes, dtype=object)
    products = points[:,None]*points[None,:]
    factors, errors = axis_tables(nodes,price,gains.values())
    edges, weights = [], {}
    keys = sorted(data)
    if witness is not None:
        require(witness["binding"] == binding and len(witness["edges"]) == len(keys), "witness binding/coverage")
    for i,key in enumerate(keys):
        g,h,r = data[key]
        parameters = coefficients(g,h,r)
        if witness is None:
            maximum = node_max(parameters,points,products,factors[g],factors[h])
        else:
            maximum = int(witness["edges"][i][3])
            verify_node_max(maximum,parameters,points,factors[g],factors[h])
        edge_upper = log_enclosure(F(maximum,EXP_DENOM))[1] + errors[g]+errors[h]
        weights[key] = math.ceil(WEIGHT_SCALE*edge_upper)
        edges.append([*key,str(maximum),str(weights[key])])
    optimum, states = integral_maximum(k,weights)
    upper = price*budget+F(optimum,WEIGHT_SCALE)
    require(upper >= schedule_upper, "global upper below checked feasible value")
    gap = upper-schedule_lower
    result = dict(schema="native-m2-priced-grid-v1", binding=binding,
                  implementation=source_hashes(), schedule=run["schedule"], price=str(price),
                  grid_nanowatts=nodes, coefficient_scale=str(Q), weight_scale=str(WEIGHT_SCALE),
                  edges=edges, dp_max_integer=str(optimum), dp_states=states,
                  feasible_lower_nats=str(schedule_lower), feasible_upper_nats=str(schedule_upper),
                  global_upper_nats=str(upper), gap_upper_nats=str(gap),
                  gap_upper_se=str(gap/(s*log_enclosure(F(2))[0])))
    if witness is not None:
        require(result == witness, "witness differs from independent replay")
    return result


def inputs(block,pilot):
    name = f"native-b{block:02d}-B-snr10"
    case_path = (STUDY.parent/"independent-cdl-20261110" if pilot else STUDY)/"cases"/(name+".json")
    run_path = STUDY/"development"/(name+".json") if pilot else STUDY/"runs/main"/(name+"-Price-DP-SQP.json")
    case, run = read(case_path), read(run_path)
    meta = case["metadata"]
    require((case["K"],case["S"],case["M"],meta["block"],meta["profile"],meta["snr_db"]) ==
            (16,8,2,block,"B",10) and case["name"] == name, "unexpected case identity")
    require(F(case["budget"]) == F(52,25) and not meta["pilot"], "unexpected physical case")
    require(run["case"] == name and run["case_sha256"] == sha(case_path) and run["arm"] == "Price-DP-SQP"
            and run["cap_seconds"] == 10., "unexpected allocation identity")
    if not pilot:
        manifest = read(STUDY/"runs/main/manifest.json")
        require(run["case_path"] == case_path.relative_to(STUDY).as_posix() and
                manifest["cases"][run["case_path"]] == sha(case_path) and
                run["source_manifest_sha256"] == sha(STUDY/"source_manifest.json") ==
                manifest["source_manifest_sha256"], "case/run manifest mismatch")
    binding = dict(case_sha256=sha(case_path), run_sha256=sha(run_path), case=name, historical_pilot=pilot)
    return case,run,binding


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("freeze","pilot","produce","replay","replay-pilot"))
    action = parser.parse_args().action
    hashes = source_hashes()
    manifest = HERE/"freeze.json"
    if action == "freeze":
        if manifest.exists():
            require(read(manifest)["hashes"] == hashes,"existing implementation freeze differs")
        else:
            write(manifest,dict(utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),hashes=hashes))
        return
    require(read(manifest)["hashes"] == hashes, "frozen implementation mismatch")
    pilot = action in ("pilot","replay-pilot")
    replay = action.startswith("replay")
    directory = HERE/("historical-pilot" if pilot else "witnesses")
    directory.mkdir(exist_ok=True)
    results = []
    for block in ([0] if pilot else range(20)):
        began = time.monotonic()
        try:
            case,run,binding = inputs(block,pilot)
            path = directory/(case["name"]+".json")
            if replay:
                result = make(case,run,binding,read(path))
            else:
                result = make(case,run,binding)
                if path.exists():
                    require(read(path) == result,"existing witness differs")
                else:
                    write(path,result)
            gap = F(result["gap_upper_se"])
            results.append(dict(block=block,status="PASS",witness_sha256=sha(path),
                                gap_upper_nats=result["gap_upper_nats"],gap_upper_se=str(gap),
                                seconds=time.monotonic()-began))
        except Exception as failure:
            results.append(dict(block=block,status="FAIL",error=repr(failure),seconds=time.monotonic()-began))
        print(block,results[-1]["status"],round(results[-1]["seconds"],3),flush=True)
    passed = [F(row["gap_upper_se"]) for row in results if row["status"] == "PASS"]
    summary = dict(action=action, rows=results, coverage=len(passed), planned=len(results))
    if len(passed) == len(results):
        summary.update(min_upper_se=str(min(passed)),median_upper_se=str(statistics.median(passed)),
                       max_upper_se=str(max(passed)),mean_upper_se=str(sum(passed)/len(passed)))
    write(directory/(action+"-receipt.json"), summary)
    if len(passed) != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

