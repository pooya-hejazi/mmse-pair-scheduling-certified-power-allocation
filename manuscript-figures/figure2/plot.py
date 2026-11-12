"""Redraw Figure 2 from the paired gaps in the archived ray-tracing study."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

here = Path(__file__).resolve().parent
with (here / "paired-gaps.csv").open(newline="", encoding="utf-8") as stream:
    rows = list(csv.DictReader(stream))
groups = [("O1", 8), ("ASU", 8), ("O1", 16), ("ASU", 16)]
assert len({r["network"] for r in rows}) == len(rows) == 32
threshold = 0.01
blue, gray, ink, orange = "#11649a", "#606b76", "#152b3c", "#ba5328"
plt.rcParams.update({"font.size": 8, "font.family": "DejaVu Sans", "pdf.fonttype": 42,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8d959b", "axes.linewidth": .55,
                     "xtick.major.width": .6, "ytick.major.width": .6,
                     "xtick.major.size": 3, "ytick.major.size": 3})
fig, (left, right) = plt.subplots(1, 2, figsize=(7.05, 2.7),
                                   gridspec_kw={"width_ratios": [1.3, 1]})
fig.subplots_adjust(left=.088, right=.985, top=.74, bottom=.23, wspace=.40)
all_reductions, hits = [], []
for i, (scene, users) in enumerate(groups):
    cases = [r for r in rows if r["scene"] == scene and int(r["users"]) == users]
    assert len(cases) == (12 if users == 8 else 4)
    x = i + np.linspace(-.36, .36, len(cases))
    generic = np.array([float(r["generic_final_gap"]) for r in cases])
    proposed = np.array([float(r["proposed_final_gap"]) for r in cases])
    assert np.all(generic > threshold) and np.all(proposed > 0)
    left.vlines(x, proposed, generic, colors="#aab5bd", linewidth=.65, zorder=1)
    left.scatter(x, generic, marker="^", s=12, facecolor="white", edgecolor=gray, linewidth=.7, zorder=3)
    left.scatter(x, proposed, s=12, c=blue, edgecolors="white", linewidth=.3, zorder=4)
    miss = proposed > threshold
    left.scatter(x[miss], proposed[miss], s=32, facecolors="none", edgecolors=orange, linewidth=.8, zorder=5)
    hits.append(int(sum(~miss)))
    reductions = np.array([100 * (1 - float(r["proposed_grid_gap"]) / float(r["generic_grid_gap"])) for r in cases])
    assert np.all((0 < reductions) & (reductions <= 100))
    # Vertical offsets expose coincident points while every horizontal value stays exact.
    y = i + np.linspace(-.22, .22, len(cases))
    right.hlines(i, reductions.min(), reductions.max(), color="#c2cbd2", lw=.8, zorder=1)
    right.scatter(reductions, y, s=12, color=blue, alpha=.85, linewidths=.2, edgecolors="white", zorder=2)
    right.scatter(np.median(reductions), i, marker="|", s=110, color=ink, linewidths=1.8, zorder=3)
    all_reductions.extend(reductions)
assert hits == [12, 11, 4, 0] and round(float(np.median(all_reductions)), 2) == 97.82
left.set(yscale="log", ylim=(8e-13, 35), xlim=(-.51, 3.51), ylabel="Final gap  $U-L$  (nats)")
left.set_yticks([1e-12, 1e-9, 1e-6, 1e-3, 1])
left.set_xticks(range(4), [f"{s}\n$K={k}$" for s,k in groups])
left.axhline(threshold, color=ink, linestyle=(0, (3, 2)), linewidth=.8, zorder=0)
for x in [.5, 1.5, 2.5]:
    left.axvline(x, color="#e1e4e7", linewidth=.5, zorder=0)
left.set_title("(a) Final gaps by network", loc="left", fontsize=9.4, pad=6)
right.set_title("(b) Gap reduction by network", loc="left", fontsize=9.1, pad=6)
right.set(xlim=(0, 103), ylim=(3.52, -.52), xlabel="Reduction in $U-L_{\\mathrm{grid}}$ (%)")
right.set_xticks([0, 25, 50, 75, 100])
right.set_yticks(range(4), [f"{s}, $K={k}$" for s,k in groups])
right.grid(axis="x", color="#e1e4e7", linewidth=.5)
right.set_axisbelow(True)
symbols = [
    Line2D([],[],marker="^",ls="none",markersize=4.2,mfc="white",mec=gray,label="Generic repair"),
    Line2D([],[],marker="o",ls="none",markersize=4,mfc=blue,mec=blue,label="Proposed"),
    Line2D([],[],marker="o",ls="none",markersize=5,mfc="none",mec=orange,label="Proposed miss"),
    Line2D([],[],color=ink,ls=(0,(3,2)),lw=.9,label="0.01-nat target"),
    Line2D([],[],marker="|",ls="none",markersize=8,mew=1.8,color=ink,label="Group median (b)"),
]
fig.legend(handles=symbols, loc="upper center", bbox_to_anchor=(.52,.995), ncol=5,
           frameon=False, fontsize=7.5, handlelength=1.4, columnspacing=1.4, handletextpad=.4)
fig.savefig(here.parent / "images/integral-bound-comparison.pdf", metadata={"CreationDate":None})
plt.close(fig)

