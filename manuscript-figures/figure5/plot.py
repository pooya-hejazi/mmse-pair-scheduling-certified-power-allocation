"""Reproduce Figure 5(b) from the archived Set I search times."""
from pathlib import Path
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
with (root / "search-times.csv").open(newline="") as stream:
    records = list(csv.DictReader(stream))
methods = ["DP-SQP", "DP-Fu-SCA", "DP-Thu-IDE", "Fixed-SQP", "DP-uniform"]
times = [[float(row["seconds"]) for row in records if row["method"] == method] for method in methods]
assert all(len(values) == 180 for values in times)
plt.rcParams.update({"font.size": 8, "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(3.25, 2.05), layout="constrained")
ax.boxplot(times, tick_labels=["SQP", "Fu", "IDE", "Fixed\nSQP", "Uniform"],
           showfliers=True, flierprops={"markersize": 2})
ax.axhline(10, linestyle="--", color="0.5", linewidth=.7)
ax.set_ylabel("Search time (s)")
ax.set_ylim(bottom=-.30)
fig.savefig(root.parent / "images/cdl_solver_time.pdf", bbox_inches="tight", pad_inches=.035)
plt.close(fig)
