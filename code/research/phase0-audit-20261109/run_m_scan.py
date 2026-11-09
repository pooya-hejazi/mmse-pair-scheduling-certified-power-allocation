# -*- coding: utf-8 -*-
"""Phase-0b: does receive dimension M hide pairing headroom?"""
from pathlib import Path
import csv
import json
import math
import sys
from fractions import Fraction as F

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "research" / "manuscript-refinement-20261106" / "certification"
OUT = ROOT / "research" / "phase0-audit-20261109"
sys.path.insert(0, str(CERT))
from run_audit import q_rate, best_fixed_power_assignment, load_grid_powers, grid_pairs, quantile  # noqa: E402
import checker  # noqa: E402


def build_truncated(case, m_eff):
    k, s = case["K"], case["S"]
    re, im = case["channels_re"], case["channels_im"]
    vectors, gains = {}, {}
    for i in range(k):
        for t in range(s):
            vec = tuple((F(re[i][j][t]), F(im[i][j][t])) for j in range(m_eff))
            vectors[i, t] = vec
            gains[i, t] = sum(x * x + y * y for x, y in vec)
    data = {}
    for u in range(k):
        for v in range(u + 1, k):
            for t in range(s):
                g, h = gains[u, t], gains[v, t]
                real = sum(x * z + y * w for (x, y), (z, w) in zip(vectors[u, t], vectors[v, t]))
                imag = sum(x * w - y * z for (x, y), (z, w) in zip(vectors[u, t], vectors[v, t]))
                r = (real * real + imag * imag) / (g * h) if g * h else F(0)
                data[u, v, t] = (g, h, r)
    return data, gains


def main():
    rows = {}
    with open(CERT / "final" / "results.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[row["name"]] = row

    out = []
    for name in sorted(rows):
        case = json.loads((CERT / "inputs" / "corrected" / name / "case.json").read_text(encoding="utf-8"))
        grid = json.loads((CERT / "inputs" / "corrected" / name / "grid-result.json").read_text(encoding="utf-8"))
        k, s = case["K"], case["S"]
        pmin, pmax, budget = F(case["pmin"]), F(case["pmax"]), F(case["budget"])
        grid_p = load_grid_powers(grid["schedule"], k)
        pairs = grid_pairs(grid["schedule"], s)
        for m_eff in (2, 4, 8):
            if m_eff > case["M"]:
                continue
            data, gains = build_truncated(case, m_eff)
            # Uniform power is exactly the budget midpoint for these cases.
            uniform = [F(1, 10)] * k
            grid_uniform = sum(q_rate(data[u, v, t], uniform[u], uniform[v]) for t, (u, v) in enumerate(pairs))
            best_uniform, _ = best_fixed_power_assignment(k, s, data, uniform)
            grid_power_rate = sum(q_rate(data[u, v, t], grid_p[u], grid_p[v]) for t, (u, v) in enumerate(pairs))
            best_grid_power, _ = best_fixed_power_assignment(k, s, data, grid_p)
            corr = [float(coeff[2]) for coeff in data.values()]
            snr = [10 * math.log10(float(g) * 0.1) for g in gains.values() if float(g) > 0]
            rec = dict(
                name=name, scene=rows[name]["scene"], K=k, M_eff=m_eff,
                grid_uniform_rate=grid_uniform,
                best_uniform_rate=best_uniform,
                pairing_gain_uniform=(best_uniform - grid_uniform) / grid_uniform if grid_uniform > 0 else 0.0,
                grid_power_rate=grid_power_rate,
                best_grid_power_rate=best_grid_power,
                pairing_gain_grid_power=(best_grid_power - grid_power_rate) / grid_power_rate if grid_power_rate > 0 else 0.0,
                r_median=quantile(corr, 0.5),
                snr_median_db=quantile(snr, 0.5),
                zero_links=sum(float(g) == 0 for g in gains.values()),
            )
            out.append(rec)
            print(f"{name} M={m_eff}: pair_uniform={rec['pairing_gain_uniform']*100:.3f}% "
                  f"pair_grid={rec['pairing_gain_grid_power']*100:.3f}% r={rec['r_median']:.3f} "
                  f"snr={rec['snr_median_db']:.1f}", flush=True)

    with open(OUT / "phase0_m_scan.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)

    summary = {}
    for m_eff in (2, 4, 8):
        rs = [r for r in out if r["M_eff"] == m_eff]
        for scene in ("all", "o1", "asu"):
            subset = rs if scene == "all" else [r for r in rs if r["scene"] == scene]
            summary[f"{scene}_M{m_eff}"] = dict(
                n=len(subset),
                pair_uniform_median=quantile([r["pairing_gain_uniform"] for r in subset], 0.5),
                pair_uniform_p90=quantile([r["pairing_gain_uniform"] for r in subset], 0.9),
                pair_uniform_frac_gt1=sum(r["pairing_gain_uniform"] > 0.01 for r in subset) / len(subset),
                pair_grid_median=quantile([r["pairing_gain_grid_power"] for r in subset], 0.5),
                pair_grid_p90=quantile([r["pairing_gain_grid_power"] for r in subset], 0.9),
                pair_grid_frac_gt1=sum(r["pairing_gain_grid_power"] > 0.01 for r in subset) / len(subset),
            )
    (OUT / "phase0_m_scan_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)

    # Figures: pairing gain at uniform power vs M, by scene.
    fig, ax = plt.subplots(figsize=(5.4, 3.3))
    for scene, color in (("o1", "#1f77b4"), ("asu", "#d62728")):
        for m_eff, marker in ((2, "o"), (4, "s"), (8, "^")):
            vals = sorted(100 * r["pairing_gain_uniform"] for r in out if r["scene"] == scene and r["M_eff"] == m_eff)
            if vals:
                ax.plot(vals, np.linspace(0, 1, len(vals)), marker=marker, ms=3, color=color,
                        alpha={2: 0.45, 4: 0.7, 8: 1.0}[m_eff], label=f"{scene.upper()} M={m_eff}")
    ax.axvline(1.0, color="k", ls="--", lw=0.8)
    ax.set_xlabel("Pairing gain at uniform power (%)")
    ax.set_ylabel("Empirical CDF")
    ax.set_title("Pairing headroom vs receive dimension")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "figures" / "phase0_pairing_vs_M.pdf")
    fig.savefig(OUT / "figures" / "phase0_pairing_vs_M.png", dpi=200)
    plt.close(fig)

    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
