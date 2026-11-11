"""Prespecified whole-block analysis after independent replay of the four-arm study."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
PREVIOUS = HERE.parent / "independent-cdl-20261110"
spec = importlib.util.spec_from_file_location("prior_block_analysis", PREVIOUS / "analysis.py")
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)
ARMS = ("Price-DP-SQP", "DP-SQP", "DP-Fu-SCA", "DP-Thu-IDE")
BEST = "casewise_best"
TIE = 1e-5
SUPERIORITY = 0.01
RATE_FLOOR = -0.001
TIME_LIMIT = math.log(0.5)
DRAWS = 20_000


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def design():
    return [(b, p, s) for b in range(20) for p in "ABC" for s in (0,10,20)]


def decisions(rate95, rate975, time975):
    return dict(
        rate_superiority=bool(rate95["low"] > SUPERIORITY),
        secondary_rate_condition=bool(rate975["low"] > RATE_FLOOR),
        secondary_time_condition=bool(time975["high"] < TIME_LIMIT),
        secondary_efficiency=bool(rate975["low"] > RATE_FLOOR and time975["high"] < TIME_LIMIT))


def estimate(values, draws, confidence=.95):
    blocks = np.array(values, dtype=float).reshape(20,-1).mean(axis=1)
    return ref.mean_interval(blocks, draws, confidence)


def comma_file(path, rows, fields=None):
    with path.open("w",encoding="utf-8",newline="") as file:
        writer = csv.DictWriter(file,fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def collect():
    report = read(HERE/"audit_study.json")
    if report["status"] != "PASS" or report["final_allocations"] != 720:
        raise ValueError("A complete passing 720-allocation audit is required")
    for name,digest in read(HERE/"source_manifest.json")["hashes"].items():
        if sha(PROJECT/name) != digest:
            raise ValueError("Scientific freeze changed: " + name)
    for key,rel in (("source_manifest_sha256","source_manifest.json"),("seed_manifest_sha256","seed_manifest.json"),
                    ("final_intervals_sha256","audit_final_intervals.json"),("receipts_sha256","audit_receipts.json")):
        if sha(HERE/rel) != report[key]:
            raise ValueError("Audit binding failed: " + rel)
    for group in ("runs_sha256","evidence_sha256"):
        for rel,digest in report[group].items():
            if sha(HERE/rel) != digest:
                raise ValueError("Audited evidence changed: " + rel)
    # Presence of an unexpected failed/extra result invalidates a previous audit.
    actual = {p.relative_to(HERE).as_posix() for p in (HERE/"runs/main").glob("*.json")
              if p.name != "manifest.json" and not p.name.endswith("-starts.json")}
    if actual != set(report["runs_sha256"]):
        raise ValueError("Raw results added or removed since audit")
    exact = read(HERE/"audit_final_intervals.json")
    rows, intervals = {}, {}
    for rel in sorted(actual):
        row = read(HERE/rel)
        key = row["block"],row["profile"],row["snr_db"],row["arm"]
        if key in rows:
            raise ValueError("Repeated case/arm identity")
        rows[key],intervals[key] = row,exact[rel]
    if set(rows) != {(*key,a) for key in design() for a in ARMS}:
        raise ValueError("Incomplete paired design")
    return rows,intervals,report


def analyze():
    rows,intervals,audit = collect()
    seed = read(HERE/"seed_manifest.json")["bootstrap"]["effective_seed"]
    draws = np.random.default_rng(seed).integers(0,20,(DRAWS,20))
    cases,raw = [],[]
    for key in design():
        block,profile,snr = key
        data = {a:rows[(*key,a)] for a in ARMS}
        new = data[ARMS[0]]
        controls = [data[a] for a in ARMS[1:]]
        best = max(r["se_bits"] for r in controls)
        fastest = min(r["elapsed_seconds"] for r in controls)
        exact = intervals[(*key,ARMS[0])]
        row = dict(block=block,profile=profile,snr_db=snr,case=new["case"],
                   best_control_se=best,exact_best_controls="|".join(exact["exact_best_controls"]),
                   fastest_control_time=fastest,fastest_controls="|".join(a for a in ARMS[1:] if data[a]["elapsed_seconds"]==fastest),
                   new_se=new["se_bits"],new_elapsed_seconds=new["elapsed_seconds"],
                   new_minus_casewise_best=new["se_bits"]-best,
                   time_ratio=new["elapsed_seconds"]/fastest,log_time_ratio=math.log(new["elapsed_seconds"]/fastest))
        diag_upper = new.get("numerical_upper_nats")
        row["numerical_upper_se"] = diag_upper/(8*math.log(2)) if diag_upper is not None else None
        row["numerical_headroom_vs_best_control"] = (row["numerical_upper_se"]-best if diag_upper is not None else None)
        for arm in ARMS:
            r = data[arm]
            raw.append(dict(block=block,profile=profile,snr_db=snr,case=r["case"],arm=arm,se_bits=r["se_bits"],
                      rate_nats=r["rate_nats"],elapsed_seconds=r["elapsed_seconds"],status=r["status"],
                      order_position=r["position"],accepted=r["counts"]["accepted"],start_count=r["counts"]["starts_started"]))
        for arm in ARMS[1:]:
            row["new_minus_"+arm] = new["se_bits"]-data[arm]["se_bits"]
        for target in (*ARMS[1:],BEST):
            row["exact_sign_vs_"+target] = exact["exact_sign_vs"][target]
        cases.append(row)
    def column(name):
        return np.array([x[name] for x in cases],dtype=float).reshape(20,3,3)
    delta = column("new_minus_casewise_best")
    logs = column("log_time_ratio")
    rate95,rate975,time975 = estimate(delta,draws),estimate(delta,draws,.975),estimate(logs,draws,.975)
    blocks = []
    for b in range(20):
        row = dict(block=b,mean_new_minus_best=float(delta[b].mean()),mean_log_time_ratio=float(logs[b].mean()))
        for a in ARMS[1:]:
            row["mean_new_minus_"+a] = float(column("new_minus_"+a)[b].mean())
        blocks.append(row)
    effects,cell_rows,losses = {},[],[]
    for target in (BEST,*ARMS[1:]):
        values = column("new_minus_"+target)
        signs = column("exact_sign_vs_"+target)
        effects[target] = dict(rate_difference=estimate(values,draws),case_wtl=ref.wtl(values),
                block_wtl=ref.wtl(values.mean(axis=(1,2))),exact_case_sign=dict(
                positive=int((signs>0).sum()),equal=int((signs==0).sum()),negative=int((signs<0).sum())))
        for i,p in enumerate("ABC"):
            for j,s in enumerate((0,10,20)):
                x = values[:,i,j]
                est = estimate(x,draws)
                cell_rows.append(dict(profile=p,snr_db=s,contrast=target,mean=est["mean"],
                       low=est["low"],high=est["high"],**ref.wtl(x)))
        for r in cases:
            if r["exact_sign_vs_"+target]<0:
                losses.append(dict(case=r["case"],block=r["block"],profile=r["profile"],snr_db=r["snr_db"],
                    comparator=target,difference_bpshz=r["new_minus_"+target],
                    outside_tie_band=r["new_minus_"+target]<-TIE))
    arm_info = {}
    for a in ARMS:
        ordered = [rows[(*k,a)] for k in design()]
        rates = [r["se_bits"] for r in ordered]
        times = [r["elapsed_seconds"] for r in ordered]
        arm_info[a] = dict(mean_rate=estimate(rates,draws),mean_search_seconds=estimate(times,draws),
            median_search_seconds=float(np.median(times)),diagnostics=ref.summarize_diagnostics(ordered))
    summary = dict(status="COMPLETE",n_cases=180,n_allocations=720,n_independent_blocks=20,bootstrap_draws=DRAWS,
        bootstrap_seed=seed,tie_band_bpshz=TIE,primary_margin_bpshz=SUPERIORITY,secondary_floor_bpshz=RATE_FLOOR,
        secondary_time_ratio_threshold=.5,primary_rate=rate95,
        secondary_rate=rate975,secondary_log_time_ratio=time975,
        geometric_time_ratio={k:math.exp(time975[k]) for k in ("mean","low","high")},
        decisions=decisions(rate95,rate975,time975),contrasts=effects,arm_summaries=arm_info,
        interval_scope="Primary two-sided 95%; two marginal two-sided 97.5% intervals for joint secondary endpoint; individual/cell contrasts pointwise 95%. All resample whole blocks.",
        efficiency_scope="Matched warm-runtime search on the recorded single-thread host under the 10-second cap.",
        bounds_scope="Exact signs use rational objective products. Price-grid numerical upper diagnostics are floating-point quantities.",
        audit_sha256=sha(HERE/"audit_study.json"),source_manifest_sha256=audit["source_manifest_sha256"],
        seed_manifest_sha256=audit["seed_manifest_sha256"])
    out = HERE/"analysis"
    out.mkdir(exist_ok=True)
    comma_file(out/"run_values.csv",raw)
    comma_file(out/"case_values.csv",cases)
    comma_file(out/"block_effects.csv",blocks)
    comma_file(out/"cell_contrasts.csv",cell_rows)
    comma_file(out/"losses.csv",losses,["case","block","profile","snr_db","comparator","difference_bpshz","outside_tie_band"])
    (out/"results.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    plot(out,summary,cell_rows,blocks)
    print(json.dumps({k:summary[k] for k in ("status","primary_rate","secondary_rate","geometric_time_ratio","decisions")},indent=2))


def plot(out,summary,cells,blocks):
    os.environ.setdefault("MPLCONFIGDIR",str(HERE/"matplotlib-cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size":9,"pdf.fonttype":42,"axes.spines.top":False,"axes.spines.right":False})
    folder = out/"figures"
    folder.mkdir(exist_ok=True)
    def save(fig,label):
        fig.tight_layout()
        for ext in ("pdf","png"):
            fig.savefig(folder/(label+"."+ext),bbox_inches="tight",dpi=200)
        plt.close(fig)
    fig,axes = plt.subplots(1,3,figsize=(8.2,3.2))
    for ax,field,est,margin,label in (
        (axes[0],"mean_new_minus_best",summary["primary_rate"],SUPERIORITY,"New minus best control (bit/s/Hz)"),
        (axes[1],"mean_new_minus_best",summary["secondary_rate"],RATE_FLOOR,"New minus best (bit/s/Hz)"),
        (axes[2],"mean_log_time_ratio",summary["secondary_log_time_ratio"],TIME_LIMIT,"Log time ratio to fastest control")):
        vals = [r[field] for r in blocks]
        ax.scatter(vals,np.linspace(-.13,.13,20),s=16,alpha=.62)
        ax.plot([est["low"],est["high"]],[0,0],color="black",lw=2.5)
        ax.scatter(est["mean"],0,s=34,c="black",marker="D")
        ax.axvline(margin,color="#a12a30",ls="--",label="Prespecified margin")
        ax.set(yticks=[],xlabel=label,title=f"Mean and {100*est['confidence']:g}% interval")
        ax.legend(fontsize=7,loc="upper left")
    save(fig,"holdout_endpoints")
    fig,axes = plt.subplots(1,3,figsize=(7.5,3.25),sharey=True)
    for ax,p in zip(axes,"ABC"):
        for j,(target,label,marker) in enumerate(zip((BEST,*ARMS[1:]),("Best","SQP","Fu","IDE"),("D","o","s","^"))):
            subset = [r for r in cells if r["contrast"]==target and r["profile"]==p]
            x = np.array([r["snr_db"] for r in subset])+0.65*(j-1.5)
            y = [r["mean"] for r in subset]
            ax.vlines(x,[r["low"] for r in subset],[r["high"] for r in subset],color=f"C{j}",lw=1)
            ax.scatter(x,y,label=label,marker=marker,s=17)
        ax.axhline(0,color="black",lw=.6)
        ax.set(title="CDL-"+p,xticks=[0,10,20],xlabel="Nominal SNR (dB)")
    axes[0].set_ylabel("New minus control (bit/s/Hz)")
    axes[-1].legend(fontsize=7,frameon=False)
    save(fig,"holdout_cell_contrasts")


def self_test():
    idx=np.random.default_rng(17).integers(0,20,(DRAWS,20))
    x=np.broadcast_to(np.arange(20)[:,None,None]/10,(20,3,3))
    assert abs(estimate(x,idx)["mean"]-.95)<1e-14
    assert ref.wtl([-2*TIE,-TIE,0,TIE,2*TIE])==dict(wins=1,ties=3,losses=1)
    good=decisions({"low":.011},{"low":-.0009},{"high":TIME_LIMIT-.1})
    assert all(good.values())
    boundary=decisions({"low":SUPERIORITY},{"low":RATE_FLOOR},{"high":TIME_LIMIT})
    assert not any(boundary.values())
    assert not decisions({"low":.02},{"low":.001},{"high":TIME_LIMIT+.1})["secondary_efficiency"]
    print("PASS: whole-block estimates, strict decision boundaries, dual conditions and tie band")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    self_test() if parser.parse_args().self_test else analyze()
