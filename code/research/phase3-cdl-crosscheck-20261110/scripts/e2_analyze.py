# -*- coding: utf-8 -*-
"""E2 analysis: pre-registered gates, bootstrap intervals and diagnostics."""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (GAIN_EPS, PHASE1, PHASE3, bootstrap_ci, case_gain, spearman)

OUT = PHASE3 / "output"
CASES = PHASE3 / "cases"
M0 = 0.013103914212041167
BAND = (0.5 * M0, 1.5 * M0)


def original_rows() -> dict[str, dict]:
    rows = list(csv.DictReader((PHASE1 / "cdl_results.csv").open(encoding="utf-8")))
    return {r["name"]: r for r in rows}


def base_name(name: str) -> str:
    return re.sub(r"-sionna-r\d+$", "", name)


def r_values(paths) -> np.ndarray:
    vals = []
    for p in paths:
        case = json.loads(p.read_text(encoding="utf-8"))
        vals.extend(float(F(row["r"])) for row in case["pairs"])
    return np.asarray(vals, float)


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.stats import ks_2samp

    orig = original_rows()
    rows = list(csv.DictReader((OUT / "e2_results.csv").open(encoding="utf-8")))
    by_case = defaultdict(list)
    for r in rows:
        by_case[base_name(r["name"])].append(r)

    cases = []
    real_rows = []
    for name in sorted(orig):
        recs = sorted(by_case.get(name, []), key=lambda x: int(x["realization"]))
        if not recs:
            raise SystemExit(f"missing Sionna results for {name}")
        gains = [float(x["gain"]) for x in recs]
        abs_gains = []
        for x in recs:
            base = max(float(x["grid_rate"]), float(x["slsqp_rate"]),
                       float(x["iwmmse_rate"]), float(x["matching_rate"]))
            abs_gains.append((float(x["proposed_rate"]) - base) / (8 * np.log(2)))
        rates = {k: float(orig[name][k]) for k in
                 ("grid_rate", "slsqp_rate", "iwmmse_rate", "matching_rate", "proposed_rate")}
        orig_gain = case_gain(rates)
        orig_base = max(rates["grid_rate"], rates["slsqp_rate"],
                        rates["iwmmse_rate"], rates["matching_rate"])
        orig_abs = (rates["proposed_rate"] - orig_base) / (8 * np.log(2))
        meta = recs[0]
        cases.append(dict(name=name, profile=meta["profile"],
                          separation=float(meta["separation"]),
                          seed=int(meta["seed"]), orig_gain=orig_gain,
                          orig_abs_bpshz=orig_abs,
                          sionna_gain_case_mean=float(np.mean(gains)),
                          sionna_abs_bpshz_mean=float(np.mean(abs_gains)),
                          sionna_gain_sd=float(np.std(gains, ddof=1)) if len(gains) > 1 else 0.0,
                          n_real=len(gains)))
        for x in recs:
            real_rows.append(dict(name=x["name"], base=name, profile=x["profile"],
                                  realization=int(x["realization"]),
                                  gain=float(x["gain"]),
                                  proposed_rate=float(x["proposed_rate"]),
                                  grid_rate=float(x["grid_rate"]),
                                  slsqp_rate=float(x["slsqp_rate"]),
                                  iwmmse_rate=float(x["iwmmse_rate"]),
                                  matching_rate=float(x["matching_rate"]),
                                  proposed_time=float(x["proposed_time"]),
                                  slsqp_time=float(x["slsqp_time"]),
                                  matching_time=float(x["matching_time"])))

    g = np.asarray([c["sionna_gain_case_mean"] for c in cases], float)
    go = np.asarray([c["orig_gain"] for c in cases], float)
    M_hat = float(np.median(g))
    mean_hat = float(np.mean(g))
    med_ci = bootstrap_ci(g, np.median, seed=20261109)
    mean_ci = bootstrap_ci(g, np.mean, seed=20261109)
    wins = int((g > GAIN_EPS).sum())
    ties = int((np.abs(g) <= GAIN_EPS).sum())
    losses = int((g < -GAIN_EPS).sum())
    rho = spearman(go, g)

    orig_r = r_values(sorted((PHASE1 / "cases").glob("*.json")))
    sion_r = r_values(sorted(CASES.glob("*-sionna-r*.json")))
    ks = ks_2samp(orig_r, sion_r)

    profiles = {}
    for p in ("A", "B", "C"):
        sub = [c for c in cases if c["profile"] == p]
        profiles[p] = dict(n=len(sub),
                           median=float(np.median([c["sionna_gain_case_mean"] for c in sub])),
                           mean=float(np.mean([c["sionna_gain_case_mean"] for c in sub])),
                           median_original=float(np.median([c["orig_gain"] for c in sub])))

    gates = dict(
        G1=dict(pass_=None, note="filled from e1_audit.json"),
        G2=dict(pass_=bool(M_hat > 0 and med_ci[0] > 0),
                M_hat=M_hat, ci_median=list(med_ci)),
        G3=dict(pass_=bool(BAND[0] <= M_hat <= BAND[1]), band=list(BAND)),
        G4=dict(pass_=bool(wins >= 48), wins=wins, threshold=48),
        G5=dict(pass_=bool(rho >= 0.5), spearman=rho, threshold=0.5),
    )
    e1 = json.loads((OUT / "e1_audit.json").read_text(encoding="utf-8"))
    gates["G1"]["pass_"] = len(e1["e1a"]["errors"]) == 0
    g2 = gates["G2"]["pass_"]
    if not g2:
        bucket = "c"
    elif all(v["pass_"] for k, v in gates.items() if k != "G1") and e1["verdict"] == "clean":
        bucket = "a"
    else:
        bucket = "b"

    summary = dict(
        n_cases=len(cases), n_real=int(cases[0]["n_real"]), M0=M0,
        M_hat=M_hat, mean_hat=mean_hat,
        ci_median=list(med_ci), ci_mean=list(mean_ci),
        abs_median=float(np.median([c["sionna_abs_bpshz_mean"] for c in cases])),
        abs_median_original=float(np.median([c["orig_abs_bpshz"] for c in cases])),
        wins=wins, ties=ties, losses=losses,
        spearman_rho=rho,
        ks_D=float(ks.statistic), ks_p=float(ks.pvalue),
        r_median_orig=float(np.median(orig_r)), r_median_sionna=float(np.median(sion_r)),
        r_p90_orig=float(np.percentile(orig_r, 90)),
        r_p90_sionna=float(np.percentile(sion_r, 90)),
        gates=gates, e1_verdict=e1["verdict"], bucket=bucket,
        profiles=profiles,
        runtime_median=dict(
            proposed=float(np.median([r["proposed_time"] for r in real_rows])),
            slsqp=float(np.median([r["slsqp_time"] for r in real_rows])),
            matching=float(np.median([r["matching_time"] for r in real_rows])),
        ),
        within_case_sd_median=float(np.median([c["sionna_gain_sd"] for c in cases])),
    )
    (OUT / "e2_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    with (OUT / "e2_cases.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cases[0]))
        w.writeheader(); w.writerows(cases)
    with (OUT / "e2_realizations.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(real_rows[0]))
        w.writeheader(); w.writerows(real_rows)

    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    ax.scatter(go * 100, g * 100, s=16)
    lo = min(go.min(), g.min()) * 100
    hi = max(go.max(), g.max()) * 100
    ax.plot([lo, hi], [lo, hi], "k--", lw=0.8)
    ax.set_xlabel("Original hand-rolled gain [%]")
    ax.set_ylabel("Sionna CDL gain [%]")
    ax.set_title(f"r = {rho:.2f}")
    fig.tight_layout(); fig.savefig(OUT / "figures" / "gain_scatter_orig_vs_sionna.png", dpi=180)
    fig.savefig(OUT / "figures" / "gain_scatter_orig_vs_sionna.pdf"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(4.2, 3.4))
    for vals, lab in ((orig_r, "hand-rolled"), (sion_r, "Sionna 2.2.0")):
        xs = np.sort(vals)
        ax.plot(xs, np.arange(1, xs.size + 1) / xs.size, lw=1.2, label=lab)
    ax.set_xlabel("squared correlation r")
    ax.set_ylabel("empirical CDF")
    ax.set_title(f"KS D = {ks.statistic:.3f}")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "figures" / "r_cdf_overlay.png", dpi=180)
    fig.savefig(OUT / "figures" / "r_cdf_overlay.pdf"); plt.close(fig)

    rng = np.random.default_rng(20261109)
    draws = rng.choice(g, size=(10000, g.size), replace=True)
    meds = np.median(draws, axis=1) * 100
    fig, ax = plt.subplots(figsize=(4.2, 3.2))
    ax.hist(meds, bins=50)
    ax.axvline(M_hat * 100, color="k", lw=1)
    ax.axvline(M0 * 100, color="C1", ls="--", lw=1, label="original 1.31%")
    ax.set_xlabel("bootstrap median gain [%]")
    ax.set_ylabel("count")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "figures" / "bootstrap_histogram.png", dpi=180)
    fig.savefig(OUT / "figures" / "bootstrap_histogram.pdf"); plt.close(fig)

    print(json.dumps({k: summary[k] for k in
                      ("n_cases", "n_real", "M_hat", "ci_median", "wins", "ties",
                       "losses", "spearman_rho", "ks_D", "bucket")}, indent=2))
    print("gates", {k: v["pass_"] for k, v in gates.items()})


if __name__ == "__main__":
    main()
