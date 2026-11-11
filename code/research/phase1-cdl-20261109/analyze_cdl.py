# -*- coding: utf-8 -*-
"""Analyse the 3GPP CDL benchmark and generate main-paper figures."""
from pathlib import Path
import csv
import json
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
CDL = ROOT / "research" / "phase1-cdl-20261109"
FIG = CDL / "figures"
FIG.mkdir(exist_ok=True)


def read():
    with open(CDL / "cdl_results.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def boot(v, B=10000, seed=20261109):
    v = np.asarray(v, float); rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), (B, len(v)))
    return np.percentile(v[idx].mean(1), [2.5, 97.5])


def main():
    rows = read()
    methods = ["grid", "slsqp", "iwmmse", "matching", "proposed"]
    for r in rows:
        vals = {m: float(r[m + "_rate"]) for m in methods}
        best = max(vals[m] for m in methods if m != "proposed")
        r["best_base"] = best
        r["gain"] = (vals["proposed"] - best) / best
        r["gain_bpshz"] = (vals["proposed"] - best) / (8 * math.log(2))

    def summarize(rs):
        g = [r["gain"] for r in rs]
        a = [r["gain_bpshz"] for r in rs]
        return dict(n=len(rs), median=float(np.median(g)), mean=float(np.mean(g)),
                    ci=[float(x) for x in boot(g)], abs_median=float(np.median(a)),
                    wins=sum(x > 1e-4 for x in g), ties=sum(abs(x) <= 1e-4 for x in g),
                    losses=sum(x < -1e-4 for x in g))

    summary = dict(all=summarize(rows),
                   by_profile={p: summarize([r for r in rows if r["profile"] == p]) for p in "ABC"})
    (CDL / "cdl_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)

    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9})

    # Rate boxplots
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    data = [[float(r[m + "_rate"]) for r in rows] for m in methods]
    ax.boxplot(data, tick_labels=methods, showfliers=True)
    ax.set_ylabel("Sum rate (nats)")
    ax.set_title("3GPP CDL-A/B/C, K=16, M=2")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(FIG / "cdl_rate_by_method.pdf"); fig.savefig(FIG / "cdl_rate_by_method.png", dpi=200); plt.close(fig)

    # Absolute gain per case
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    vals = sorted(r["gain_bpshz"] for r in rows)
    ax.bar(np.arange(len(vals)), vals, color="#d62728", width=0.85)
    ax.axhline(0, color="k", lw=0.8)
    ax.axhline(0.05, color="k", ls="--", lw=0.8, label="0.05 bit/s/Hz")
    ax.set_xlabel("CDL cases (sorted)")
    ax.set_ylabel("Gain over best baseline (bit/s/Hz)")
    ax.set_title(f"All {len(vals)} cases improve")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(FIG / "cdl_absolute_gain.pdf"); fig.savefig(FIG / "cdl_absolute_gain.png", dpi=200); plt.close(fig)

    # Profile gains
    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    xs = np.arange(3)
    med = [100 * summary["by_profile"][p]["median"] for p in "ABC"]
    mean = [100 * summary["by_profile"][p]["mean"] for p in "ABC"]
    ax.bar(xs - 0.18, med, 0.36, label="Median")
    ax.bar(xs + 0.18, mean, 0.36, label="Mean")
    ax.set_xticks(xs); ax.set_xticklabels([f"CDL-{p}" for p in "ABC"])
    ax.set_ylabel("Gain over best baseline (%)")
    ax.set_title("Profile breakdown")
    ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "cdl_profile_gain.pdf"); fig.savefig(FIG / "cdl_profile_gain.png", dpi=200); plt.close(fig)

    # Runtime
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    for i, m in enumerate(methods):
        vals = [float(r[m + "_time"]) for r in rows]
        ax.scatter(np.full(len(vals), i) + np.linspace(-0.12, 0.12, len(vals)), vals, s=14, alpha=0.7)
        ax.errorbar(i, np.median(vals), fmt="D", color="k")
    ax.set_yscale("log"); ax.set_xticks(range(len(methods))); ax.set_xticklabels(methods, rotation=20)
    ax.set_ylabel("Seconds (log scale)"); ax.set_title("CDL runtime")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(FIG / "cdl_runtime.pdf"); fig.savefig(FIG / "cdl_runtime.png", dpi=200); plt.close(fig)

    # Correlation CDF from stored cases
    rs = []
    for path in sorted((CDL / "cases").glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        rs.extend(float(__import__("fractions").Fraction(row["r"])) for row in case["pairs"])
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    ax.plot(sorted(rs), np.linspace(0, 1, len(rs)))
    ax.set_xlabel("Squared correlation r")
    ax.set_ylabel("Empirical CDF")
    ax.set_title("CDL pair/resource correlations")
    ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIG / "cdl_correlation_cdf.pdf"); fig.savefig(FIG / "cdl_correlation_cdf.png", dpi=200); plt.close(fig)
    # Ablation
    abl = list(csv.DictReader(open(CDL / "cdl_ablation.csv", encoding="utf-8")))
    fig, ax = plt.subplots(figsize=(5.8, 3.2))
    scenes = ["A", "B", "C"]
    width = 0.25
    xs = np.arange(len(scenes))
    for j, (key, label) in enumerate([("assignment", "Assignment only"), ("power", "Power only"), ("joint", "Joint")]):
        vals = [100 * np.mean([(float(r[key]) - float(r["uniform"])) / float(r["uniform"])
                               for r in abl if r["profile"] == p]) for p in scenes]
        ax.bar(xs + (j - 1) * width, vals, width, label=label)
    ax.set_xticks(xs); ax.set_xticklabels([f"CDL-{p}" for p in scenes])
    ax.set_ylabel("Mean gain over uniform (%)")
    ax.set_title("Attribution on CDL")
    ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "cdl_ablation.pdf"); fig.savefig(FIG / "cdl_ablation.png", dpi=200); plt.close(fig)
    print("WROTE", FIG)


if __name__ == "__main__":
    main()
