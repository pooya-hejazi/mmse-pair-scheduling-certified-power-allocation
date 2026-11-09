# -*- coding: utf-8 -*-
"""Clear absolute-gain figure: where the proposed method wins, ties and loses."""
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


def read(name):
    with open(OUT / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    m2 = read("m2_results.csv")
    ctl = read("controlled_results.csv")
    for rows in (m2, ctl):
        for r in rows:
            vals = {m: float(r[m + "_rate"]) for m in ("grid", "slsqp", "iwmmse", "matching", "proposed")}
            best = max(vals[m] for m in ("grid", "slsqp", "iwmmse", "matching"))
            r["gain_nats"] = vals["proposed"] - best
            r["gain_bpshz"] = r["gain_nats"] / ((int(r["K"]) / 2) * math.log(2))

    k8 = [r for r in m2 if r["K"] == "8"]
    k16r = [r for r in m2 if r["K"] == "16"]
    k16c = ctl

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.5), gridspec_kw={"width_ratios": [1, 1.15]})
    ax = axes[0]
    for rows, label, color in [(k8, "K=8, ray", "#1f77b4")]:
        vals = sorted(r["gain_bpshz"] for r in rows)
        ax.bar(np.arange(len(vals)), vals, color=color, width=0.8)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_title("K=8: parity with SLSQP")
    ax.set_xlabel("Cases (sorted)")
    ax.set_ylabel("Gain over best baseline (bit/s/Hz)")
    ax.grid(alpha=0.3, axis="y")

    ax = axes[1]
    ray = sorted([r["gain_bpshz"] for r in k16r])
    ctl = sorted([r["gain_bpshz"] for r in k16c])
    ax.bar(np.arange(len(ray)), ray, color="#d62728", width=0.85, label="Ray-traced (8)")
    ax.bar(np.arange(len(ray), len(ray) + len(ctl)), ctl, color="#2ca02c", width=0.85, label="Controlled (12)")
    ax.axhline(0, color="k", lw=0.8)
    ax.axhline(0.05, color="k", ls="--", lw=0.8, label="0.05 bit/s/Hz")
    ax.set_title("K=16: every case improves")
    ax.set_xlabel("Cases (sorted within pool)")
    ax.set_ylabel("Gain over best baseline (bit/s/Hz)")
    ax.grid(alpha=0.3, axis="y")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "phase1_absolute_gain.pdf")
    fig.savefig(FIG / "phase1_absolute_gain.png", dpi=200)
    plt.close(fig)
    print("wrote", FIG / "phase1_absolute_gain.png")
    print("K8 min/median/max", min(r["gain_bpshz"] for r in k8), np.median([r["gain_bpshz"] for r in k8]), max(r["gain_bpshz"] for r in k8))
    print("K16 ray min/median/max", min(ray), np.median(ray), max(ray))
    print("K16 ctl min/median/max", min(ctl), np.median(ctl), max(ctl))


if __name__ == "__main__":
    main()
