"""Plot paired rate differences from the four-arm native-CDL block analysis."""
import argparse
import csv
import math
from pathlib import Path
from statistics import fmean


ARMS = (
    ("casewise_best", "Best of three per case", "#292929", "-", "o", 6.2),
    ("DP-SQP", "DP–SQP", "#0072b2", "--", "s", 5.1),
    ("DP-Fu-SCA", "DP–Fu–SCA adaptation", "#009e73", "-.", "D", 3.8),
    ("DP-Thu-IDE", "DP–Thu–IDE adaptation", "#c84c00", ":", "^", 4.6),
)
PROFILES = "ABC"
SNRS = (0, 10, 20)


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_cells(directory):
    cases = {}
    for row in rows(directory / "case_values.csv"):
        key = int(row["block"]), row["profile"], int(row["snr_db"])
        if key in cases:
            raise ValueError(f"Duplicate case {key}")
        cases[key] = row
    if set(cases) != {(b, p, s) for b in range(20) for p in PROFILES for s in SNRS}:
        raise ValueError("Expected 180 paired cases in 20 complete blocks")
    cells = {}
    for row in rows(directory / "cell_contrasts.csv"):
        profile, snr, arm = row["profile"], int(row["snr_db"]), row["contrast"]
        key = profile, snr, arm
        mean, low, high = (float(row[name]) for name in ("mean", "low", "high"))
        differences = [float(cases[b, profile, snr]["new_minus_" + arm]) for b in range(20)]
        votes = sum(int(row[n]) for n in ("wins", "ties", "losses"))
        if key in cells or votes != 20 or not all(map(math.isfinite, (mean, low, high))):
            raise ValueError(f"Invalid cell {key}")
        if not low <= mean <= high or not math.isclose(fmean(differences), mean, abs_tol=1e-12):
            raise ValueError(f"Cell summary disagrees with case data: {key}")
        cells[key] = (mean, low, high)
    if set(cells) != {(p, s, a[0]) for p in PROFILES for s in SNRS for a in ARMS}:
        raise ValueError("Expected 36 contrast-by-profile-by-SNR cells")
    return cells


def plot(directory, output=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cells = load_cells(directory)
    plt.rcParams.update({"font.size": 8, "pdf.fonttype": 42, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.formatter.useoffset": False})
    fig, axes = plt.subplots(1, 3, figsize=(6.5, 2.6), sharey=True)
    for ax, profile in zip(axes, PROFILES):
        ax.axhline(0, color=".5", linewidth=.65, zorder=0)
        for arm, label, color, line, marker, size in ARMS:
            values = [cells[profile, snr, arm] for snr in SNRS]
            mean = [v[0] for v in values]
            error = [[m - l for m, l, h in values], [h - m for m, l, h in values]]
            ax.errorbar(SNRS, mean, yerr=error, label=label, color=color, linestyle=line,
                        marker=marker, markersize=size, markerfacecolor="none", markeredgewidth=.8,
                        linewidth=1.25, elinewidth=.7, capsize=2, capthick=.7)
        ax.set(title="CDL-" + profile, xlabel="Nominal SNR (dB)", xticks=SNRS, xlim=(-1.8, 21.8))
        ax.grid(axis="y", color=".86", linewidth=.5, zorder=0)
    axes[0].set_ylabel("SE difference (bit/s/Hz)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, fontsize=7.5,
               columnspacing=1.8, handlelength=2.8)
    fig.subplots_adjust(left=.12, right=.985, bottom=.36, top=.88, wspace=.17)
    target = output if output is not None else directory / "figures"
    target.mkdir(parents=True, exist_ok=True)
    for extension in ("pdf", "png"):
        kwargs = {"metadata": {"CreationDate": None, "ModDate": None}} if extension == "pdf" else {}
        fig.savefig(target / ("priced_cdl_comparison." + extension), dpi=300, **kwargs)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, default=Path(__file__).resolve().parent / "analysis")
    parser.add_argument("--output-dir", type=Path, help="Write the two figure files here")
    args = parser.parse_args()
    plot(args.analysis_dir, args.output_dir)
