"""Plot paired CDL rate differences and checked continuous-gap coverage from frozen runs."""
import argparse
import csv
from fractions import Fraction
import hashlib
import json
from math import ceil
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "code/research"
NATIVE = ROOT / "independent-cdl-20261110"
PRICED = ROOT / "priced-assignment-20261111"
sys.path.insert(0, str(ROOT / "manuscript-refinement-20261106/certification"))
from checker import check_schedule, reconstruct, require
from integer_logs import log_enclosure

SNRS = (0, 10, 20)
ARMS = ("Price-DP-SQP", "DP-SQP", "DP-Fu-SCA", "DP-Thu-IDE")
NAMES = ("native_assignment_power_margins", "priced_snr_margins", "native_certified_coverage")
STYLES = (("#0072B2", "o", "-"), ("#C34D00", "s", "--"), ("#00795B", "^", "-."))
STYLE = {"font.size": 8.2, "axes.titlesize": 8.5, "axes.labelsize": 8.1,
         "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.7,
         "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": .6,
         "pdf.fonttype": 42, "font.family": "DejaVu Sans"}


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audited_runs(study, arms, audit_name, expected):
    audit = read(study / audit_name)
    require(audit["status"] == "PASS" and audit["final_allocations"] == expected, "study audit failed")
    runs = {}
    for b in range(20):
        for p in "ABC":
            for s in SNRS:
                for arm in arms:
                    name = f"runs/main/native-b{b:02}-{p}-snr{s:02}-{arm}.json"
                    raw = (study / name).read_bytes()
                    require(hashlib.sha256(raw).hexdigest() == audit["runs_sha256"][name], name)
                    row = json.loads(raw)
                    key = b, p, s, arm
                    require(key == (row["block"], row["profile"], row["snr_db"], row["arm"]), name)
                    runs[key] = row
    return runs, audit


def draws(study):
    seed = read(study / "seed_manifest.json")["bootstrap"]["effective_seed"]
    return np.random.default_rng(seed).integers(0, 20, (20000, 20))


def estimate(blocks, indices):
    values = np.array(blocks)
    require(values.shape == (20,) and np.isfinite(values).all(), "incomplete block means")
    lo, hi = np.quantile(values[indices].mean(axis=1), [.025, .975])
    return dict(blocks=20, mean_bpshz=values.mean(), low95_bpshz=lo, high95_bpshz=hi)


def native_data():
    controls = ("Fixed-SQP", "DP-uniform")
    runs, _ = audited_runs(NATIVE, ("DP-SQP", *controls), "audit_campaign.json", 960)
    indices = draws(NATIVE)
    with (NATIVE / "analysis/cell_contrasts.csv").open(newline="") as stream:
        reference = {(r["profile"], int(r["snr_db"]), r["comparator"]): r for r in csv.DictReader(stream)}
    rows = []
    for arm in controls:
        for p in "ABC":
            for s in SNRS:
                differences = [runs[b,p,s,"DP-SQP"]["se_bits"] - runs[b,p,s,arm]["se_bits"] for b in range(20)]
                est = estimate(differences, indices)
                ref = reference[p,s,arm]
                np.testing.assert_allclose([est[k] for k in ("mean_bpshz","low95_bpshz","high95_bpshz")],
                                           [float(ref[k]) for k in ("mean_difference","low","high")], rtol=0, atol=1e-13)
                rows.append(dict(reference="DP-SQP", comparator=arm, profile=p, snr_db=s, **est))
    return rows


def priced_data(runs, audit):
    indices = draws(PRICED)
    path = PRICED / "audit_final_intervals.json"
    require(sha(path) == audit["final_intervals_sha256"], "final interval audit changed")
    exact = read(path)
    for b in range(20):
        for p in "ABC":
            for s in SNRS:
                name = f"runs/main/native-b{b:02}-{p}-snr{s:02}-Price-DP-SQP.json"
                require(exact[name]["exact_best_controls"] == ["DP-SQP"], "casewise-best identity changed")

    rows = []
    published = read(PRICED / "analysis/results.json")
    for ref, arm in [*(("Price-DP-SQP", a) for a in ARMS[1:]), ("DP-SQP", "DP-Fu-SCA")]:
        for s in SNRS:
            blocks = [np.mean([runs[b,p,s,ref]["se_bits"] - runs[b,p,s,arm]["se_bits"] for p in "ABC"])
                      for b in range(20)]
            rows.append(dict(reference=ref, comparator=arm, profiles="ABC", snr_db=s, **estimate(blocks, indices)))
        if ref == "Price-DP-SQP":
            np.testing.assert_allclose(np.mean([r["mean_bpshz"] for r in rows[-3:]]),
                                       published["contrasts"][arm]["rate_difference"]["mean"], rtol=0, atol=1e-13)
    return rows


def coverage_data(runs, audit):
    folder = PRICED / "native_certificate/witnesses"
    receipt = read(folder / "replay-receipt.json")
    require(receipt["action"] == "replay" and receipt["coverage"] == receipt["planned"] == 20, "incomplete upper replay")
    rows = []
    for b, previous in enumerate(receipt["rows"]):
        name = f"native-b{b:02}-B-snr10"
        path = folder / (name + ".json")
        case = PRICED / "cases" / (name + ".json")
        require(previous["block"] == b and previous["status"] == "PASS" and
                sha(path) == previous["witness_sha256"], "wrong upper witness")
        witness = read(path)
        case_hash = sha(case)
        require(witness["binding"] == dict(case=name, case_sha256=case_hash, historical_pilot=False,
                    run_sha256=audit["runs_sha256"][f"runs/main/{name}-Price-DP-SQP.json"]), "wrong upper binding")
        model = reconstruct(read(case))
        upper = Fraction(witness["global_upper_nats"])
        norm_lower = model[1] * log_enclosure(Fraction(2))[0]
        for arm in ARMS:
            run = runs[b,"B",10,arm]
            require(run["case_sha256"] == case_hash, "different channel")
            lower, feasible_upper = check_schedule(run["schedule"], model)
            require(upper >= feasible_upper, "upper below feasible rate")
            gap = (upper - lower) / norm_lower
            if arm == "Price-DP-SQP":
                require(gap == Fraction(witness["gap_upper_se"]) == Fraction(previous["gap_upper_se"]),
                        "price-guided endpoint differs from original replay")
            # Round upward so each printed tolerance is sufficient for its claimed count.
            ticks = ceil(gap * 10**12)
            rows.append(dict(block=b, case=name, method=arm, global_upper_nats=str(upper),
                             feasible_lower_nats=str(lower), gap_upper_bpshz_rational=str(gap),
                             tolerance_bpshz=f"{ticks // 10**12}.{ticks % 10**12:012d}"))
    require(len(rows) == 80, "incomplete certificate subset")
    for arm in ARMS:
        arm_rows = [r for r in rows if r["method"] == arm]
        for r in arm_rows:
            count = sum(Fraction(t["tolerance_bpshz"]) <= Fraction(r["tolerance_bpshz"]) for t in arm_rows)
            r.update(certified_cases=count, total_cases=20, certified_fraction=count / 20)
    return rows


def draw_lines(ax, groups, scale=1):
    for rows, label, (color, marker, line) in groups:
        x = [r["snr_db"] for r in rows]
        ys = np.array([[r[k] for r in rows] for k in ("mean_bpshz","low95_bpshz","high95_bpshz")]) * scale
        y, lo, hi = ys
        ax.errorbar(x, y, yerr=[y-lo, hi-y], color=color, marker=marker, linestyle=line, label=label,
                    markersize=5.8 if marker == "o" else 3.8, markerfacecolor="none", markeredgewidth=.85,
                    linewidth=1.15, elinewidth=.65, capsize=2)
    ax.set(xticks=SNRS, xlim=(-1.6, 21.6), xlabel="Nominal SNR (dB)")
    ax.grid(axis="y", color=".88", linewidth=.45)


def save(fig, target, name):
    for ext in ("pdf", "png"):
        metadata = {"CreationDate": None, "ModDate": None} if ext == "pdf" else {}
        fig.savefig(target / f"{name}.{ext}", dpi=300, metadata=metadata)
    plt.close(fig)


def plot_native(rows, target):
    fig, axes = plt.subplots(1, 2, figsize=(3.50, 2.30))
    for ax, arm, title in zip(axes, ("Fixed-SQP", "DP-uniform"), ("(a) Fixed pairing", "(b) Uniform power")):
        draw_lines(ax, [([r for r in rows if r["comparator"] == arm and r["profile"] == p],
                         "CDL-" + p, style) for p, style in zip("ABC", STYLES)])
        ax.set_title(title)
    axes[0].set(ylim=(0,4.5), yticks=(0,1,2,3,4), ylabel="SE gain (bit/s/Hz)")
    axes[1].set_yscale("log")
    axes[1].set(ylim=(1e-5,1), yticks=(1e-5,1e-3,1e-1,1))
    fig.legend(*axes[0].get_legend_handles_labels(), ncol=3, frameon=False, loc="upper center",
               handlelength=2, columnspacing=1, handletextpad=.35)
    fig.subplots_adjust(left=.137, right=.973, bottom=.210, top=.733, wspace=.53)
    save(fig, target, NAMES[0])


def plot_priced(rows, target):
    fig, axes = plt.subplots(1, 2, figsize=(3.50, 2.48), gridspec_kw={"width_ratios": [1.15,1]})
    groups = []
    for arm, label, style in zip(ARMS[1:], ("DP–SQP (best)", "DP–Fu–SCA", "DP–Thu–IDE"), STYLES):
        selected = [r for r in rows if r["reference"] == ARMS[0] and r["comparator"] == arm]
        groups.append((selected, label, style))
    draw_lines(axes[0], groups, scale=1000)
    draw_lines(axes[1], [([r for r in rows if r["reference"] == "DP-SQP"], "Fu", STYLES[1])])
    axes[0].set(title="(a) Price − control", ylabel=r"SE gain ($10^{-3}$ bit/s/Hz)")
    axes[1].set(title="(b) Best − Fu", ylabel="SE difference (bit/s/Hz)", yscale="log",
                ylim=(1e-9,.001), yticks=(1e-9,1e-7,1e-5,1e-3))
    fig.legend(*axes[0].get_legend_handles_labels(), ncol=2, frameon=False, loc="upper center",
               handlelength=2, columnspacing=1.1, handletextpad=.35)
    fig.subplots_adjust(left=.137, right=.973, bottom=.197, top=.69, wspace=.76)
    save(fig, target, NAMES[1])


def plot_coverage(rows, target):
    fig, axes = plt.subplots(1, 2, figsize=(3.50, 2.05), sharex=True, sharey=True)
    spec = [(ARMS[0], "Price–DP–SQP", "#0072B2", "-", "o"), (ARMS[1], "DP–SQP", "#262626", "--", "s"),
            (ARMS[2], "DP–Fu–SCA", "#C34D00", "-.", "D"), (ARMS[3], "DP–Thu–IDE", "#00795B", ":", "^")]
    for i, (arm,label,color,ls,marker) in enumerate(spec):
        ax = axes[i//2]
        selected = sorted((r for r in rows if r["method"] == arm), key=lambda r: Fraction(r["tolerance_bpshz"]))
        x = [float(r["tolerance_bpshz"]) for r in selected]
        y = [r["certified_fraction"] for r in selected]
        ax.step([.00072,*x,.08], [0,*y,1], where="post", color=color, linewidth=1.2, linestyle=ls,
                marker=marker, markersize=3.5, markevery=[5,10,15,20], markerfacecolor="white", label=label)
        ax.set(xscale="log", xlim=(.00072,.08), ylim=(-.03,1.045), xticks=(.001,.01),
               yticks=(0,.25,.50,.75,1), yticklabels=("0","25","50","75","100"))
        ax.grid(axis="y", color=".88", linewidth=.45)
    for ax in axes:
        ax.axvline(.0015, color=".46", linestyle=(0, (1, 2)), linewidth=.8, zorder=.5)
        ax.set_xticks((.0015, .01, .05), labels=("0.0015", "0.01", "0.05"))
    axes[0].set_ylabel("Certified cases (%)")
    fig.supxlabel("Gap tolerance (bit/s/Hz)", fontsize=8.1, y=.025)
    for ax in axes:
        ax.legend(loc="lower center", bbox_to_anchor=(.5,1.00), frameon=False, ncol=1, borderaxespad=0,
                  handlelength=2, handletextpad=.38, labelspacing=.16)
    fig.subplots_adjust(left=.14, right=.978, bottom=.235, top=.755, wspace=.115)
    save(fig, target, NAMES[2])


def generate(out):
    out.mkdir(parents=True, exist_ok=True)
    native = native_data()
    runs, audit = audited_runs(PRICED, ARMS, "audit_study.json", 720)
    priced = priced_data(runs, audit)
    coverage = coverage_data(runs, audit)
    with plt.rc_context(STYLE):
        for name, rows, plot in zip(NAMES, (native, priced, coverage), (plot_native, plot_priced, plot_coverage)):
            with (out / (name + ".csv")).open("w", encoding="utf8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            plot(rows, out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    generate(parser.parse_args().output)
