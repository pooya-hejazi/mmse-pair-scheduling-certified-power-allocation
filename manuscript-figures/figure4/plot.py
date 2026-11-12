"""Plot the archived within-channel contrasts for Fig. 4, including bootstrap intervals."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

here = Path(__file__).resolve().parent
with (here / "paired-differences.csv").open() as f:
    rows = list(csv.DictReader(f))

panels = [
    ("Fixed-SQP", "(a) Fixed pairing + SQP"),
    ("DP-Fu-SCA", "(b) DP + Fu adaptation"),
    ("DP-Thu-IDE", "(c) DP + Thu adaptation"),
]
styles = [("#0072B2", "o", "-"), ("#C45210", "s", "--"), ("#008362", "^", ":")]
plt.rcParams.update({"font.size": 8.5, "pdf.fonttype": 42, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.linewidth": .7})
fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.8))
fig.subplots_adjust(left=.083, right=.983, bottom=.25, top=.78, wspace=.38)
for ax, (method, title) in zip(axes, panels):
    for j, (profile, (color, marker, line)) in enumerate(zip("ABC", styles)):
        cell = sorted((r for r in rows if r["comparator"] == method and r["profile"] == profile),
                      key=lambda r: int(r["snr_db"]))
        assert [int(r["snr_db"]) for r in cell] == [0, 10, 20]
        x = [int(r["snr_db"]) + (j - 1) * .40 for r in cell]
        mean = [float(r["mean_difference"]) for r in cell]
        lo = [v - float(r["low"]) for v, r in zip(mean, cell)]
        hi = [float(r["high"]) - v for v, r in zip(mean, cell)]
        ax.errorbar(x, mean, yerr=[lo, hi], fmt=marker, linestyle=line, label="CDL-" + profile,
                    color=color, lw=1.1, elinewidth=.85, capsize=2.2, ms=3.6)
    ax.set(title=title, xlim=(-1.6, 21.6), xticks=[0, 10, 20])
    ax.title.set_fontsize(9)
    ax.grid(axis="y", alpha=.22, linewidth=.6)
    ax.axhline(0, color="#777777", lw=.65, zorder=0)
    ax.tick_params(length=3)
axes[0].set(ylim=(-.12, 4.6), yticks=[0, 1, 2, 3, 4], ylabel="Mean SE gain (bit/s/Hz)")
for ax in axes[1:]:
    ax.set(ylim=(-.0015, .051), yticks=[0, .01, .02, .03, .04, .05])
fig.text(.53, .07, "Nominal SNR (dB)", ha="center")
fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=3, frameon=False,
           bbox_to_anchor=(.52, 1.015), handlelength=2.3)
fig.savefig(here.parent / "images/native_cdl_pairing_and_updates.pdf", bbox_inches="tight", pad_inches=.035)
