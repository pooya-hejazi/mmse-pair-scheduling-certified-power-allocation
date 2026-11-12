from pathlib import Path
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

here = Path(__file__).resolve().parent
with (here / "paired-differences.csv").open() as f:
    rows = list(csv.DictReader(f))
plt.rcParams.update({"font.size": 8.5, "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(3.45, 2.1), layout="constrained")
for j, (profile, color, style) in enumerate(zip("ABC", ["#0072B2", "#C45210", "#008362"], ["o-", "s--", "^:"])):
    cell = sorted((r for r in rows if r["profile"] == profile), key=lambda r: int(r["snr_db"]))
    x = [int(r["snr_db"]) + (j - 1) * .35 for r in cell]
    mean = [float(r["mean_difference"]) for r in cell]
    lo = [m - float(r["low"]) for r, m in zip(cell, mean)]
    hi = [float(r["high"]) - m for r, m in zip(cell, mean)]
    ax.errorbar(x, mean, yerr=[lo, hi], fmt=style, color=color, label="CDL-" + profile,
                lw=1.15, ms=3.7, capsize=2.2)
ax.set(yscale="log", ylabel="Mean SE gain (bit/s/Hz)", xlabel="Nominal SNR (dB)", xticks=[0, 10, 20], xlim=(-1.6, 21.6))
ax.grid(axis="y", alpha=.22)
ax.legend(loc="lower left", frameon=False, fontsize=7.5)
fig.savefig(here.parent / "images/native_power_gain.pdf", bbox_inches="tight", pad_inches=.035)
