"""Replay all retained schedules and compute prospective paired block endpoints."""
import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

import numpy as np
import generate

sys.dont_write_bytecode = True
HERE, CODE = Path(__file__).resolve().parent, Path(__file__).resolve().parents[2]
PREVIOUS = HERE.parent/"independent-cdl-20261110"
ADAPT, ONE, SHORT, DP, FULL = ARMS = (
    "Adaptive-DP-SQP", "Uniform-start-DP-SQP", "Always-short-price", "DP-SQP", "Price-DP-SQP")
PREFIX = "DP-SQP-time-prefix"
spec = importlib.util.spec_from_file_location("independent_model_audit", PREVIOUS/"audit_campaign.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
audit.HERE = HERE
read, sha, require = audit.read, audit.sha, audit.require
TIE, DRAWS, FLOOR, LIMIT = 1e-5, 20_000, -.001, .5
STAGES = ("screen", "fixed_dp", "price_dp", "grid_setup", "initial_price", "sqp")


def save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    temp.replace(path)


def csv_file(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def uniform_tables():
    """Index all fixed-cardinality subsets for a vectorized independent DP."""
    bits = np.array([i.bit_count() for i in range(1 << 16)], dtype=np.uint8)
    pair_bits = [(u,v,(1<<u)|(1<<v)) for u in range(16) for v in range(u+1,16)]
    tables = []
    for s in range(8):
        layer = np.flatnonzero(bits == 2*(s+1))
        table = []
        for u,v,mask in pair_bits:
            destinations = layer[(layer & mask) == mask]
            table.append((u,v,destinations,destinations ^ mask))
        tables.append(table)
    return tables


def check_screen(screen, model, offered, tables):
    q = F(screen["equal_power"])
    require(all(F(p)==q for r in offered[0] for p in r["powers"]) and q==F(13,100), "Equal-power screen")
    assigned = [tuple(x) for x in screen["uniform_assignment"]]
    require(sorted(i for pair in assigned for i in pair)==list(range(16)) and len(assigned)==8, "Screen assignment")
    values = np.full(1<<16,-np.inf)
    values[0] = 0.
    marginals, selected_total = np.zeros(16), 0.
    for s,table in enumerate(tables):
        for u,v,dst,src in table:
            g,h,rho = model[5][u,v,s]
            x,y = g*q,h*q
            d = 1+x+y+(1-rho)*x*y
            weight = math.log(float(d*d/((1+x)*(1+y))))
            values[dst] = np.maximum(values[dst], values[src]+weight)
            if (u,v)==assigned[s]:
                selected_total += weight
                marginals[u] = float(x*(2*(1+(1-rho)*y)/d-1/(1+x)))
                marginals[v] = float(y*(2*(1+(1-rho)*x)/d-1/(1+y)))
    require(abs(values[-1]-selected_total)<1e-10, "Screen assignment is suboptimal at equal power")
    require(np.allclose(screen["elasticities"],marginals,rtol=1e-12,atol=1e-12) and
            abs(screen["minimum"]-float(min(marginals)))<1e-12 and
            screen["passed"] == bool(min(marginals)>=.9), "Independent rational marginal screen")


def replay(folder):
    source = sha(HERE/"source_manifest.json")
    for name,digest in read(HERE/"source_manifest.json")["hashes"].items():
        require(sha(CODE/name)==digest, "Changed source or input receipt: "+name)
    inputs, registry, manifest = read(HERE/"input_check.json"), read(HERE/"seed_manifest.json"), read(folder/"manifest.json")
    require(inputs["status"]=="PASS" and inputs["seed_manifest_sha256"]==sha(HERE/"seed_manifest.json") and
            inputs["generator_sha256"]==sha(HERE/"generate.py") and inputs["historical_collisions"]==0 and
            inputs["regenerated_links_bitwise_equal"]==960 and inputs["coefficients_checked"]==172800 and
            manifest["source_manifest_sha256"]==source and manifest["input_check_sha256"]==sha(HERE/"input_check.json") and
            manifest["arms"]==list(ARMS), "Scientific manifest or input validation mismatch")
    design = [(b,p,s) for b in range(20) for p in "ABC" for s in (0,10,20)]
    names = [f"native-b{b:02d}-{p}-snr{s:02d}" for b,p,s in design]
    require(names==manifest["names"] and set(names)==set(inputs["cases"]) and
            set(p.name for p in folder.glob("*.json.gz"))=={n+".json.gz" for n in names}, "Incomplete design")
    profile = {(r["block"],r["profile"]):r for r in registry["profiles"]}
    process_hashes, run_hashes, native_cache, starts_by_profile = {}, {}, {}, {}
    tables = uniform_tables()
    events = allocations = checked_starts = checked_prefixes = unique_count = 0
    max_scalar = max_matrix = 0.
    run_values, cases = [], []
    for index,(name,(block,p,snr)) in enumerate(zip(names,design)):
        path = folder/(name+".json.gz")
        run_hashes[path.name] = sha(path)
        rec = json.loads(gzip.decompress(path.read_bytes()))
        case = generate.load_case(name)
        require(rec["case"]==name and (rec["block"],rec["profile"],rec["snr_db"])==(block,p,snr) and
                rec["case_sha256"]==inputs["cases"][name]==hashlib.sha256(generate.case_bytes(case)).hexdigest() and
                rec["source_manifest_sha256"]==source, "Case binding: "+name)
        require(rec["initialization_seed"]==case["metadata"]["initialization_seed"] and
                rec["search_seed"]==case["metadata"]["search_seed"], "Search or initialization seed mismatch")
        channels = audit.native_audit(case,profile[block,p],native_cache)
        model = audit.checker.reconstruct(case)
        starts = rec["offered_starts"]
        ids = [hashlib.sha256(audit.canonical(x).encode()).hexdigest() for x in starts]
        require(ids==rec["start_ids"] and len(set(ids))==8 and starts_by_profile.setdefault((block,p),ids)==ids,
                "Eight common starts or SNR pairing failed")
        for start in starts:
            audit.checker.check_schedule(start,model)
            checked_starts += 1
        shift = index%5
        order = list(ARMS[shift:]+ARMS[:shift])
        require(rec["order"]==order and set(rec["arms"])==set(ARMS), "Incomplete arm pairing")
        cache = {}
        for position,arm in enumerate(order):
            row = rec["arms"][arm]
            proc = folder/"processes"/(row["process"]+".json")
            if row["process"] not in process_hashes:
                evidence = read(proc)
                require(evidence["source_manifest_sha256"]==source and evidence["numba_threads"]==1 and
                        all(pool["num_threads"]==1 for pool in evidence["thread_pools"]) and
                        len(evidence["arms"])==2 and all(set(x["arms"])==set(ARMS) for x in evidence["arms"]),
                        "Single-thread historical warmup binding")
                process_hashes[row["process"]] = sha(proc)
            require(row["process_sha256"]==process_hashes[row["process"]] and row["arm"]==arm and
                    row["position"]==position, "Timed method binding")
            t = row["elapsed_seconds"]
            stage = row["stage_seconds"]
            require(row["cap_seconds"]==10 and row["block_seconds"]==5 and 0<t<10.5 and
                    set(stage)==set(STAGES)|{"other"} and set(row["stage_calls"])==set(STAGES) and
                    all(math.isfinite(x) and x>=0 for x in stage.values()) and
                    abs(sum(stage.values())-t)<1e-8 and abs(row["overrun_seconds"]-max(0,t-10))<1e-8,
                    "Timed work accounting")
            history, counts, calls = row["history"],row["counts"],row["stage_calls"]
            require(history[0]["kind"]=="initial" and history[0]["schedule"]==starts[0] and
                    counts["accepted"]==len(history)-1 and row["status"] in ("deadline","starts_exhausted") and
                    counts["starts_completed"]<=counts["starts_started"] and
                    counts["power_calls"]==calls["sqp"] and calls["screen"]==int(arm==ADAPT) and
                    row["uniform_dp_cache_hits"]==int(arm==ADAPT) and
                    (calls["fixed_dp"]+calls["price_dp"]-counts["dp_completed"] in (0,1)),
                    "Retained history or work counts")
            max_starts = {ONE:1,SHORT:2,FULL:8,DP:8,ADAPT:(1 if arm==ADAPT and row["screen"]["passed"] else 2)}[arm]
            max_prices = {ONE:0,SHORT:6,FULL:14,DP:0,ADAPT:(0 if arm==ADAPT and row["screen"]["passed"] else 6)}[arm]
            require(counts["starts_started"]<=max_starts and calls["price_dp"]<=max_prices and
                    (row["status"]=="deadline" or counts["starts_completed"]==max_starts), "Truncation work cap")
            if arm==ADAPT:
                check_screen(row["screen"],model,starts,tables)
            else:
                require(row["screen"] is None, "Unexpected screen work")
            previous_upper,last_time = None,-1.
            dispatch_last = -1.
            for event in history:
                require(last_time<=event["seconds"]<=min(t,10) and
                        (previous_upper is None or (event["kind"]=="improvement" and
                         F(event["lower_nats"])>previous_upper)), "Invalid retained improvement")
                previous_upper,last_time = F(event["upper_nats"]),event["seconds"]
                if arm==DP:
                    dispatch = event["dispatch_seconds"]
                    require(dispatch_last<=dispatch<=t and dispatch>=event["seconds"]-1e-7, "DP clock timestamps")
                    dispatch_last = dispatch
                key = audit.canonical(event["schedule"])
                if key not in cache:
                    cache[key] = audit.evaluate(event["schedule"],model,channels)
                a,b = audit.check_reported(event,cache[key])
                max_scalar,max_matrix = max(a,max_scalar),max(b,max_matrix)
                events += 1
            require(all(row[field]==history[-1][field] for field in
                        ("schedule","rate_nats","se_bits","lower_nats","upper_nats")), "Final allocation mismatch")
            require(F(row["total_power"])==sum(F(pwr) for r in row["schedule"] for pwr in r["powers"]),
                    "Wrong retained power sum")
            allocations += 1
            run_values.append(dict(block=block,profile=p,snr_db=snr,case=name,arm=arm,se_bits=row["se_bits"],
                elapsed_seconds=t,position=position,status=row["status"],starts=counts["starts_started"],
                starts_completed=counts["starts_completed"],prices=calls["price_dp"],
                price_schedules=counts.get("price_schedules",0),dp_completed=counts["dp_completed"],
                power_calls=counts["power_calls"],accepted=counts["accepted"],
                **{k+"_seconds":v for k,v in stage.items()}))
        unique_count += len(cache)
        adaptive = rec["arms"][ADAPT]
        chosen = ONE if adaptive["screen"]["passed"] else SHORT
        if all(rec["arms"][a]["status"]!="deadline" for a in (ADAPT,chosen)):
            require(adaptive["schedule"]==rec["arms"][chosen]["schedule"], "Inconsistent same-branch schedule")
        full_dp = rec["arms"][DP]
        within = [e for e in full_dp["history"] if e["dispatch_seconds"]<=adaptive["elapsed_seconds"]]
        event = within[-1] if within else full_dp["history"][0]
        checked_prefixes += 1
        for target in (FULL,DP,ONE,SHORT,PREFIX):
            ref = event if target==PREFIX else rec["arms"][target]
            ref_time = None if target==PREFIX else ref["elapsed_seconds"]
            cases.append(dict(block=block,profile=p,snr_db=snr,case=name,comparator=target,
                rate_delta=adaptive["se_bits"]-ref["se_bits"],
                log_time_ratio=None if ref_time is None else math.log(adaptive["elapsed_seconds"]/ref_time),
                adaptive_seconds=adaptive["elapsed_seconds"],reference_seconds=ref_time,
                adaptive_se=adaptive["se_bits"],reference_se=ref["se_bits"],
                screen_pass=adaptive["screen"]["passed"],minimum_elasticity=adaptive["screen"]["minimum"],
                prefix_event_seconds=(event["dispatch_seconds"] if within else 0.) if target==PREFIX else None,
                prefix_initial_fallback=(not bool(within)) if target==PREFIX else None))
    require(allocations==900 and checked_starts==1440 and checked_prefixes==180 and len(native_cache)==60,
            "Incomplete complete-case independent replay")
    return cases,run_values,dict(status="PASS",source_manifest_sha256=source,input_check_sha256=sha(HERE/"input_check.json"),
        cases=180,final_allocations=allocations,common_starts=checked_starts,dp_prefixes=checked_prefixes,
        screen_optima_and_rational_gradient_vectors=180,retained_events=events,unique_schedules=unique_count,
        max_matrix_error_nats=max_matrix,max_scalar_error_nats=max_scalar,raw_sha256=run_hashes,
        processes_sha256=process_hashes)


def interval(values, draws, exponent=False):
    a = np.asarray(values, dtype=float)
    require(a.shape==(20,) and np.all(np.isfinite(a)), "Incomplete block estimand")
    low,high = np.quantile(a[draws].mean(axis=1),(.025,.975))
    data = np.array([a.mean(),low,high])
    return dict(zip(("mean","low","high"),map(float,np.exp(data) if exponent else data)))


def effects(rows, draws):
    by_block = [[r for r in rows if r["block"]==i] for i in range(20)]
    require(len({len(z) for z in by_block})==1 and by_block[0], "Unbalanced paired cells")
    delta = np.array([r["rate_delta"] for r in rows])
    result = dict(rate=interval([np.mean([r["rate_delta"] for r in z]) for z in by_block],draws),
                  wins=int(sum(delta>TIE)),ties=int(sum(abs(delta)<=TIE)),losses=int(sum(delta < -TIE)),
                  worst_case=min(rows,key=lambda r:r["rate_delta"])["case"],minimum_delta=float(min(delta)))
    if rows[0]["log_time_ratio"] is not None:
        result["time_ratio"] = interval([np.mean([r["log_time_ratio"] for r in z]) for z in by_block],draws,True)
    return result


def analyze(folder, output):
    cases,runs,report = replay(folder)
    output.mkdir(exist_ok=True,parents=True)
    save(output/"audit.json",report)
    seed = read(HERE/"seed_manifest.json")["bootstrap"]["effective_seed"]
    draws = np.random.default_rng(seed).integers(0,20,(DRAWS,20))
    contrasts,blocks,cells = {},[],[]
    for target in (FULL,DP,ONE,SHORT,PREFIX):
        subset = [r for r in cases if r["comparator"]==target]
        contrasts[target] = effects(subset,draws)
        for b in range(20):
            z = [r for r in subset if r["block"]==b]
            blocks.append(dict(block=b,comparator=target,rate_delta=float(np.mean([r["rate_delta"] for r in z])),
                log_time_ratio=None if target==PREFIX else float(np.mean([r["log_time_ratio"] for r in z]))))
        for p in ("A","B","C","ALL"):
            for snr in (0,10,20):
                z = [r for r in subset if (r["profile"]==p or p=="ALL") and r["snr_db"]==snr]
                est = effects(z,draws)
                cells.append(dict(profile=p,snr_db=snr,comparator=target,cases=len(z),
                    screen_passes=sum(r["screen_pass"] for r in z),wins=est["wins"],ties=est["ties"],
                    losses=est["losses"],rate_mean=est["rate"]["mean"],rate_low=est["rate"]["low"],
                    rate_high=est["rate"]["high"],time_ratio_mean=est.get("time_ratio",{}).get("mean"),
                    time_ratio_low=est.get("time_ratio",{}).get("low"),time_ratio_high=est.get("time_ratio",{}).get("high")))
    activity = {}
    for arm in ARMS:
        z = [r for r in runs if r["arm"]==arm]
        require(Counter(r["position"] for r in z)==dict.fromkeys(range(5),36), "Unbalanced arm order")
        activity[arm] = dict(mean_se=float(np.mean([r["se_bits"] for r in z])),
            mean_seconds=float(np.mean([r["elapsed_seconds"] for r in z])),
            median_seconds=float(np.median([r["elapsed_seconds"] for r in z])),
            deadlines=sum(r["status"]=="deadline" for r in z),starts=Counter(r["starts"] for r in z),
            total={k:sum(r[k] for r in z) for k in ("prices","price_schedules","dp_completed","power_calls","accepted")},
            mean_stage_seconds={k:float(np.mean([r[k+"_seconds"] for r in z])) for k in (*STAGES,"other")})
    primary = contrasts[FULL]
    rate_ok,time_ok = primary["rate"]["low"]>=FLOOR,primary["time_ratio"]["high"]<LIMIT
    summary = dict(status="COMPLETE",cases=180,blocks=20,allocations=900,bootstrap_seed=seed,bootstrap_draws=DRAWS,
        rate_margin=FLOOR,time_margin=LIMIT,tie_band=TIE,primary=primary,
        decisions=dict(rate=rate_ok,time=time_ok,joint=rate_ok and time_ok),contrasts=contrasts,arms=activity,
        screen_passes={snr:sum(r["comparator"]==FULL and r["screen_pass"] and r["snr_db"]==snr for r in cases)
                       for snr in (0,10,20)},audit_sha256=sha(output/"audit.json"))
    csv_file(output/"case_values.csv",cases)
    csv_file(output/"run_values.csv",runs)
    csv_file(output/"block_effects.csv",blocks)
    csv_file(output/"cell_contrasts.csv",cells)
    save(output/"results.json",summary)
    print(json.dumps({k:summary[k] for k in ("status","primary","decisions","screen_passes")},indent=2))


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs",type=Path,default=HERE/"runs/main")
    parser.add_argument("--output",type=Path,default=HERE/"analysis")
    args = parser.parse_args()
    analyze(args.runs,args.output)
