# -*- coding: utf-8 -*-
"""Analyse Phase-1 M=2 benchmark and produce figures/tables."""
from pathlib import Path
import csv
import json
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "phase1-benchmark-20261109"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)


def read_csv(name):
    with open(OUT / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def boot(vals, B=10000, seed=20261109):
    rng = np.random.default_rng(seed)
    vals = np.asarray(vals, float)
    idx = rng.integers(0, len(vals), size=(B, len(vals)))
    means = vals[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main():
    m2 = read_csv("m2_results.csv")
    ctl = read_csv("controlled_results.csv")
    abl = {r["name"]: r for r in read_csv("m2_ablation.csv")}
    cert = {r["name"]: r for r in read_csv("m2_certification.csv")}

    methods = ["grid", "slsqp", "iwmmse", "matching", "proposed"]
    for rows in (m2, ctl):
        for r in rows:
            vals = {m: float(r[m + "_rate"]) for m in methods if r.get(m + "_rate")}
            best = max((vals[m], m) for m in methods if m != "proposed")
            r["best_base"] = best[0]
            r["best_method"] = best[1]
            r["gain_vs_best"] = (vals["proposed"] - best[0]) / best[0] if best[0] else 0.0

    def summarize(rows):
        out = {}
        for m in methods:
            vals = [float(r[m + "_rate"]) for r in rows if r.get(m + "_rate")]
            out[m] = dict(mean=float(np.mean(vals)), median=float(np.median(vals)),
                          min=float(np.min(vals)), max=float(np.max(vals)))
        g = [r["gain_vs_best"] for r in rows]
        out["gain_vs_best"] = dict(
            median=float(np.median(g)), mean=float(np.mean(g)),
            p10=float(np.percentile(g, 10)), p90=float(np.percentile(g, 90)),
            ci=boot(g), wins=sum(x > 1e-4 for x in g), ties=sum(abs(x) <= 1e-4 for x in g),
            losses=sum(x < -1e-4 for x in g), n=len(g),
        )
        out["speedup_vs_slsqp"] = float(np.median([float(r["slsqp_time"]) / float(r["proposed_time"])
                                                   for r in rows if r.get("slsqp_time") and r.get("proposed_time")]))
        out["speedup_vs_matching"] = float(np.median([float(r["matching_time"]) / float(r["proposed_time"])
                                                      for r in rows if r.get("matching_time") and r.get("proposed_time")]))
        return out

    summary = dict(
        K8_ray=summarize([r for r in m2 if r["K"] == "8"]),
        K16_ray=summarize([r for r in m2 if r["K"] == "16"]),
        K16_controlled=summarize(ctl),
        K16_pooled=summarize([r for r in m2 if r["K"] == "16"] + ctl),
    )
    (OUT / "phase1_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)

    # Ablation decomposition by scene/K.
    abl_rows = []
    for name, r in abl.items():
        u = float(r["uniform"])
        a = float(r["assignment"])
        p = float(r["power_only"])
        j = float(r["joint"])
        abl_rows.append(dict(name=name, scene=r["scene"], K=r["K"],
                             assignment_gain=(a - u) / u, power_gain=(p - u) / u,
                             joint_gain=(j - u) / u))
    with open(OUT / "m2_ablation_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(abl_rows[0])); w.writeheader(); w.writerows(abl_rows)

    # Figures.
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9})
    # 1. Paired gain vs best baseline.
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    groups = [("K=8 ray", [100 * r["gain_vs_best"] for r in m2 if r["K"] == "8"], "#1f77b4"),
              ("K=16 ray", [100 * r["gain_vs_best"] for r in m2 if r["K"] == "16"], "#d62728"),
              ("K=16 ctl", [100 * r["gain_vs_best"] for r in ctl], "#2ca02c")]
    for i, (label, vals, color) in enumerate(groups):
        ax.scatter(np.full(len(vals), i) + np.linspace(-0.12, 0.12, len(vals)), vals,
                   s=22, color=color, alpha=0.85)
        ax.errorbar(i, np.mean(vals), yerr=[[np.mean(vals) - boot(vals)[0]], [boot(vals)[1] - np.mean(vals)]],
                    fmt="D", color="k", capsize=3)
    ax.axhline(0, color="k", lw=0.7)
    ax.axhline(2, color="r", ls="--", lw=0.8, label="2% material")
    ax.set_xticks(range(3)); ax.set_xticklabels([g[0] for g in groups])
    ax.set_ylabel("Proposed − best baseline (%)")
    ax.set_title("Paired rate difference")
    ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "phase1_paired_gain.pdf"); fig.savefig(FIG / "phase1_paired_gain.png", dpi=200); plt.close(fig)

    # 2. Rate by method and K.
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.3), sharey=False)
    for ax, K, title in [(axes[0], "8", "K=8"), (axes[1], "16", "K=16")]:
        rows = [r for r in m2 if r["K"] == K] + ([r for r in ctl] if K == "16" else [])
        data = [[float(r[m + "_rate"]) for r in rows if r.get(m + "_rate")] for m in methods]
        ax.boxplot(data, tick_labels=methods, showfliers=False)
        ax.set_title(title); ax.set_ylabel("Sum rate (nats)")
        ax.grid(alpha=0.3, axis="y"); ax.tick_params(axis="x", rotation=25)
    fig.tight_layout(); fig.savefig(FIG / "phase1_rate_by_K.pdf"); fig.savefig(FIG / "phase1_rate_by_K.png", dpi=200); plt.close(fig)

    # 3. Runtime.
    fig, ax = plt.subplots(figsize=(5.6, 3.3))
    for i, m in enumerate(methods):
        vals = [float(r[m + "_time"]) for r in m2 if r.get(m + "_time")]
        ax.scatter(np.full(len(vals), i) + np.linspace(-0.12, 0.12, len(vals)), vals, s=16, alpha=0.7)
        ax.errorbar(i, np.median(vals), fmt="D", color="k")
    ax.set_yscale("log"); ax.set_xticks(range(len(methods))); ax.set_xticklabels(methods, rotation=20)
    ax.set_ylabel("Seconds (log scale)"); ax.set_title("M=2 runtime")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(FIG / "phase1_runtime.pdf"); fig.savefig(FIG / "phase1_runtime.png", dpi=200); plt.close(fig)

    # 4. Ablation decomposition.
    fig, ax = plt.subplots(figsize=(5.8, 3.4))
    scenes = ["o1", "asu"]
    width = 0.25
    x = np.arange(len(scenes))
    for j, (key, label) in enumerate([("assignment_gain", "Assignment only"),
                                      ("power_gain", "Power only"),
                                      ("joint_gain", "Joint")]):
        vals = [100 * np.mean([r[key] for r in abl_rows if r["scene"] == s]) for s in scenes]
        ax.bar(x + (j - 1) * width, vals, width, label=label)
    ax.set_xticks(x); ax.set_xticklabels([s.upper() for s in scenes])
    ax.set_ylabel("Mean gain over uniform (%)"); ax.set_title("Attribution at M=2")
    ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "phase1_ablation.pdf"); fig.savefig(FIG / "phase1_ablation.png", dpi=200); plt.close(fig)

    # 5. Certification gap CDF / scatter.
    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    gaps = [float(r["gap_nats"]) for r in cert.values()]
    ax.hist(gaps, bins=np.logspace(-12, 2, 30), color="#1f77b4", alpha=0.8)
    ax.set_xscale("log"); ax.set_xlabel("Certified gap U−L (nats)")
    ax.set_ylabel("Cases"); ax.set_title("M=2 certification boundary")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(FIG / "phase1_certification.pdf"); fig.savefig(FIG / "phase1_certification.png", dpi=200); plt.close(fig)

    # 6. Pairing gain vs M from Phase 0.
    ms = list(csv.DictReader(open(ROOT / "research" / "phase0-audit-20261109" / "phase0_m_scan.csv",
                                  encoding="utf-8")))
    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    for scene, color in (("o1", "#1f77b4"), ("asu", "#d62728")):
        for m_eff, marker in ((2, "o"), (4, "s"), (8, "^")):
            vals = [100 * float(r["pairing_gain_uniform"]) for r in ms if r["scene"] == scene and r["M_eff"] == str(m_eff)]
            ax.scatter([m_eff] * len(vals), vals, marker=marker, color=color, alpha=0.55, s=20)
    ax.set_xticks([2, 4, 8]); ax.set_xlabel("Receive dimension M")
    ax.set_ylabel("Pairing gain at uniform power (%)")
    ax.set_title("Pairing headroom collapses at M=8")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(FIG / "phase1_pairing_vs_M.pdf"); fig.savefig(FIG / "phase1_pairing_vs_M.png", dpi=200); plt.close(fig)

    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
