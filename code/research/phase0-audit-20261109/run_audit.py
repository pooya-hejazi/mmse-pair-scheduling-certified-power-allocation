# -*- coding: utf-8 -*-
"""Phase-0 dataset / headroom audit for Paper 2.

Computes per-case SNR, correlation, fixed-power pairing gain, power-only gain,
joint gain, and certified headroom on the existing 32 DeepMIMO cases.
"""
from pathlib import Path
import csv
import json
import math
import sys
import time
from fractions import Fraction as F

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "research" / "manuscript-refinement-20261106" / "certification"
OUT = ROOT / "research" / "phase0-audit-20261109"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "figures").mkdir(exist_ok=True)

sys.path.insert(0, str(CERT))
import checker  # noqa: E402
import producer  # noqa: E402


def q_rate(coefficients, p, q):
    g1, g2, r = coefficients
    x = float(g1) * float(p)
    y = float(g2) * float(q)
    d = 1.0 + x + y + (1.0 - float(r)) * x * y
    return 2.0 * math.log(d) - math.log1p(x) - math.log1p(y)


def best_fixed_power_assignment(k, s, data, powers):
    """Exact resource-labelled assignment DP at fixed user powers."""
    n = 1 << k
    weights = {}
    for (u, v, t), coeff in data.items():
        weights[(u, v, t)] = q_rate(coeff, powers[u], powers[v])
    neg = -1e300
    values = [neg] * n
    choice = [None] * n
    values[0] = 0.0
    for mask in range(1, n):
        bits = mask.bit_count()
        if bits % 2:
            continue
        t = bits // 2 - 1
        best = neg
        best_pair = None
        remaining = mask
        while remaining:
            ub = remaining & -remaining
            remaining -= ub
            u = ub.bit_length() - 1
            tail = remaining
            while tail:
                vb = tail & -tail
                tail -= vb
                v = vb.bit_length() - 1
                old = mask ^ ub ^ vb
                cand = values[old] + weights[(u, v, t)]
                if cand > best:
                    best = cand
                    best_pair = (u, v)
        values[mask] = best
        choice[mask] = best_pair
    pairs = [None] * s
    mask = n - 1
    for t in reversed(range(s)):
        u, v = choice[mask]
        pairs[t] = (u, v)
        mask ^= (1 << u) | (1 << v)
    return values[-1], pairs


def load_grid_powers(schedule, k):
    powers = [None] * k
    for row in schedule:
        for user, power in zip(row["users"], row["powers"]):
            powers[user] = F(power)
    if any(p is None for p in powers):
        raise RuntimeError("incomplete grid schedule")
    return powers


def grid_pairs(schedule, s):
    pairs = [None] * s
    for row in schedule:
        pairs[row["resource"]] = tuple(row["users"])
    return pairs


def quantile(values, q):
    values = sorted(values)
    if not values:
        return float("nan")
    x = (len(values) - 1) * q
    i = int(x)
    if i + 1 == len(values):
        return values[i]
    return values[i] + (values[i + 1] - values[i]) * (x - i)


def main():
    rows = {}
    with open(CERT / "final" / "results.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[row["name"]] = row

    headroom = {}
    analysis_csv = CERT / "analysis" / "all-case-rates.csv"
    with open(analysis_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            headroom[row["name"]] = row

    records = []
    for name in sorted(rows):
        case_path = CERT / "inputs" / "corrected" / name / "case.json"
        grid_path = CERT / "inputs" / "corrected" / name / "grid-result.json"
        case = json.loads(case_path.read_text(encoding="utf-8"))
        grid = json.loads(grid_path.read_text(encoding="utf-8"))
        k, s, low, high, budget, data, gains = checker.reconstruct(case)
        grid_p = load_grid_powers(grid["schedule"], k)
        pairs = grid_pairs(grid["schedule"], s)
        grid_rate = float(checker.check_schedule(grid["schedule"], (k, s, low, high, budget, data, gains))[0])

        t0 = time.perf_counter()
        best_fixed, best_pairs = best_fixed_power_assignment(k, s, data, grid_p)
        pairing_seconds = time.perf_counter() - t0

        # Power-only refinement on the grid assignment.
        deadline = time.perf_counter() + 5.0
        refined_p, status = producer.refine(pairs, grid_p, data, low, high, budget, deadline)
        power_rate = sum(q_rate(data[u, v, t], refined_p[u], refined_p[v]) for t, (u, v) in enumerate(pairs))

        new_rate = float(F(rows[name]["new_lower_nats"]))
        old_full = float(F(rows[name]["old_full_lower_nats"]))
        snr_db = [10.0 * math.log10(float(g) * 0.1) if float(g) > 0 else float("-inf")
                  for g in gains.values()]
        snr_db = [x for x in snr_db if math.isfinite(x)]
        corr = [float(coeff[2]) for coeff in data.values()]
        h = headroom.get(name, {})
        rec = dict(
            name=name, scene=rows[name]["scene"], K=int(rows[name]["K"]),
            grid_rate_nats=grid_rate,
            best_fixed_rate_nats=best_fixed,
            power_only_rate_nats=power_rate,
            new_rate_nats=new_rate,
            old_full_rate_nats=old_full,
            pairing_gain_frac=(best_fixed - grid_rate) / grid_rate if grid_rate > 0 else 0.0,
            power_gain_frac=(power_rate - grid_rate) / grid_rate if grid_rate > 0 else 0.0,
            joint_gain_frac=(new_rate - grid_rate) / grid_rate if grid_rate > 0 else 0.0,
            residual_gain_frac=(new_rate - best_fixed) / grid_rate if grid_rate > 0 else 0.0,
            headroom_grid_frac=float(h.get("verified_grid_headroom_fraction", "nan")),
            headroom_old_full_frac=float(h.get("verified_old_full_headroom_fraction", "nan")),
            snr_median_db=quantile(snr_db, 0.5),
            snr_p10_db=quantile(snr_db, 0.1),
            snr_p90_db=quantile(snr_db, 0.9),
            r_median=quantile(corr, 0.5),
            r_p10=quantile(corr, 0.1),
            r_p90=quantile(corr, 0.9),
            zero_links=sum(float(g) == 0 for g in gains.values()),
            pairing_seconds=pairing_seconds,
            power_status=status.get("message", ""),
            best_pairs=[list(x) for x in best_pairs],
            grid_pairs=[list(x) for x in pairs],
        )
        records.append(rec)
        print(f"{name}: grid={grid_rate:.4f} pair={best_fixed:.4f} "
              f"pairgain={rec['pairing_gain_frac']*100:.3f}% powergain={rec['power_gain_frac']*100:.3f}% "
              f"joint={rec['joint_gain_frac']*100:.3f}% headroom={rec['headroom_grid_frac']*100:.3f}% "
              f"snr={rec['snr_median_db']:.1f}dB", flush=True)

    # Save CSV/JSON.
    keys = [k for k in records[0] if k not in ("best_pairs", "grid_pairs")]
    with open(OUT / "phase0_case_metrics.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in records:
            w.writerow({k: r[k] for k in keys})
    (OUT / "phase0_case_metrics.json").write_text(json.dumps(records, indent=2), encoding="utf-8")

    def summarize(rs):
        def q(vals): return quantile(vals, 0.5)
        return dict(
            n=len(rs),
            pairing_median=q([r["pairing_gain_frac"] for r in rs]),
            pairing_p90=quantile([r["pairing_gain_frac"] for r in rs], 0.9),
            power_median=q([r["power_gain_frac"] for r in rs]),
            power_p90=quantile([r["power_gain_frac"] for r in rs], 0.9),
            joint_median=q([r["joint_gain_frac"] for r in rs]),
            joint_p90=quantile([r["joint_gain_frac"] for r in rs], 0.9),
            headroom_median=q([r["headroom_grid_frac"] for r in rs if math.isfinite(r["headroom_grid_frac"])]),
            headroom_p90=quantile([r["headroom_grid_frac"] for r in rs if math.isfinite(r["headroom_grid_frac"])], 0.9),
            frac_pair_gt1=sum(r["pairing_gain_frac"] > 0.01 for r in rs) / len(rs),
            frac_power_gt1=sum(r["power_gain_frac"] > 0.01 for r in rs) / len(rs),
            frac_joint_gt1=sum(r["joint_gain_frac"] > 0.01 for r in rs) / len(rs),
            frac_headroom_gt2=sum((r["headroom_grid_frac"] > 0.02) for r in rs) / len(rs),
        )

    summary = {
        "all": summarize(records),
        "by_scene": {s: summarize([r for r in records if r["scene"] == s]) for s in ("o1", "asu")},
        "by_K": {str(k): summarize([r for r in records if r["K"] == k]) for k in (8, 16)},
    }
    (OUT / "phase0_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)

    # Figures.
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9})
    scenes = ["o1", "asu"]
    colors = {"o1": "#1f77b4", "asu": "#d62728"}

    # 1. SNR CDF by scene
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    for s in scenes:
        vals = sorted(r["snr_median_db"] for r in records if r["scene"] == s)
        ax.plot(vals, np.linspace(0, 1, len(vals)), marker="o", ms=3, color=colors[s], label=s.upper())
    ax.set_xlabel("Median received SNR per case (dB)")
    ax.set_ylabel("Empirical CDF")
    ax.set_title("Case-level SNR")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "figures" / "phase0_snr_cdf.pdf")
    fig.savefig(OUT / "figures" / "phase0_snr_cdf.png", dpi=200)
    plt.close(fig)

    # 2. Correlation CDF
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    for s in scenes:
        vals = sorted(r["r_median"] for r in records if r["scene"] == s)
        ax.plot(vals, np.linspace(0, 1, len(vals)), marker="o", ms=3, color=colors[s], label=s.upper())
    ax.set_xlabel("Median squared correlation per case")
    ax.set_ylabel("Empirical CDF")
    ax.set_title("Case-level channel correlation")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "figures" / "phase0_corr_cdf.pdf")
    fig.savefig(OUT / "figures" / "phase0_corr_cdf.png", dpi=200)
    plt.close(fig)

    # 3. Pairing gain vs power gain
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    for s in scenes:
        xs = [100 * r["pairing_gain_frac"] for r in records if r["scene"] == s]
        ys = [100 * r["power_gain_frac"] for r in records if r["scene"] == s]
        ax.scatter(xs, ys, s=30, alpha=0.8, color=colors[s], label=s.upper())
    ax.axhline(0, color="k", lw=0.6)
    ax.axvline(0, color="k", lw=0.6)
    ax.set_xlabel("Pairing gain at fixed grid powers (%)")
    ax.set_ylabel("Power-only gain at fixed grid assignment (%)")
    ax.set_title("Where the headroom is")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "figures" / "phase0_pair_vs_power.pdf")
    fig.savefig(OUT / "figures" / "phase0_pair_vs_power.png", dpi=200)
    plt.close(fig)

    # 4. Headroom vs SNR
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    for s in scenes:
        xs = [r["snr_median_db"] for r in records if r["scene"] == s]
        ys = [100 * r["headroom_grid_frac"] for r in records if r["scene"] == s]
        ax.scatter(xs, ys, s=30, alpha=0.8, color=colors[s], label=s.upper())
    ax.set_xlabel("Median received SNR (dB)")
    ax.set_ylabel("Certified headroom over grid (%)")
    ax.set_title("Certified rate headroom")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "figures" / "phase0_headroom_vs_snr.pdf")
    fig.savefig(OUT / "figures" / "phase0_headroom_vs_snr.png", dpi=200)
    plt.close(fig)

    # 5. Gain distributions
    fig, ax = plt.subplots(figsize=(5.8, 3.4))
    labels = ["Pairing", "Power-only", "Joint"]
    vals = [
        [100 * r["pairing_gain_frac"] for r in records],
        [100 * r["power_gain_frac"] for r in records],
        [100 * r["joint_gain_frac"] for r in records],
    ]
    ax.boxplot(vals, tick_labels=labels, showfliers=True)
    ax.axhline(1.0, color="r", ls="--", lw=0.8, label="1% material")
    ax.set_ylabel("Gain over grid (%)")
    ax.set_title("All 32 cases")
    ax.grid(alpha=0.3, axis="y")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "figures" / "phase0_gain_box.pdf")
    fig.savefig(OUT / "figures" / "phase0_gain_box.png", dpi=200)
    plt.close(fig)

    # 6. Scene-stratified gains
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    width = 0.25
    x = np.arange(len(scenes))
    for j, (key, label) in enumerate([("pairing_gain_frac", "Pairing"),
                                      ("power_gain_frac", "Power-only"),
                                      ("joint_gain_frac", "Joint")]):
        med = [100 * quantile([r[key] for r in records if r["scene"] == s], 0.5) for s in scenes]
        p90 = [100 * quantile([r[key] for r in records if r["scene"] == s], 0.9) for s in scenes]
        ax.bar(x + (j - 1) * width, med, width, label=label)
        ax.errorbar(x + (j - 1) * width, med, yerr=[np.zeros(len(med)), np.array(p90) - np.array(med)],
                    fmt="none", ecolor="k", capsize=2, lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([s.upper() for s in scenes])
    ax.set_ylabel("Gain over grid (%)")
    ax.set_title("Median (bar) and 90th percentile (whisker)")
    ax.grid(alpha=0.3, axis="y")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "figures" / "phase0_scene_gains.pdf")
    fig.savefig(OUT / "figures" / "phase0_scene_gains.png", dpi=200)
    plt.close(fig)

    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
