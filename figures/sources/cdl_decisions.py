"""Redraw the CDL certificate and adaptive-search comparisons from saved results."""
import argparse
import csv
from fractions import Fraction
from math import ceil, isclose, log
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdl_margins import ROOT, SNRS, STYLE, draws, plt, np, read, require, save, sha


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def headroom(out, name):
    study = ROOT / "cdl-headroom-20261111"
    audit = read(study / "results.json")
    exact = read(study / "paired_bounds.json")
    source = study / "cases.csv"
    require(audit["status"] == "PASS" and sha(source) == audit["cases_csv_sha256"],
            "Headroom case table differs from the archived replay")
    cases = read_rows(source)
    keys = {(int(r["block"]), r["profile"], int(r["snr_db"])) for r in cases}
    require(len(cases) == 180 and keys == {(b, p, s) for b in range(20) for p in "ABC" for s in SNRS},
            "Expected all 180 paired headroom cases")
    margin = Fraction(exact["threshold_bpshz"])
    rows = []
    for snr in SNRS:
        group = [r for r in cases if int(r["snr_db"]) == snr]
        bounds = exact["by_snr_db"][str(snr)]
        lower = Fraction(bounds["mean_achieved_gain_lower_bpshz"])
        upper = Fraction(bounds["mean_achieved_gain_upper_bpshz"])
        gain = float((lower + upper) / 2)
        caps = [Fraction(r["base_gap_upper_bpshz"]) for r in group]
        cap = mean(caps)
        original = sum(r["certificate_source"] == "published" for r in group)
        attained, excluded = bounds["provably_attained"], bounds["provably_impossible"]
        require(lower <= upper <= cap and abs(gain - mean(float(r["achieved_gain_bpshz"]) for r in group)) < 1e-12,
                "Achieved paired rate differs from exact enclosure")
        require(cap == Fraction(bounds["mean_base_gap_upper_bpshz"]) and excluded == sum(c < margin for c in caps)
                and attained + excluded == bounds["cases"] == len(group) and bounds["unresolved"] == 0,
                "Casewise certificate limits or classifications disagree")
        require(all(r["certificate_source"] == ("published" if r["profile"] == "B" and snr == 10 else "post-hoc")
                    for r in group), "Certificate cohort mismatch")
        # The decimal ceiling is rounded outward; the adjacent fraction is exact.
        ticks = ceil(cap * 10**12)
        rows.append(dict(snr_db=snr, cases=len(group), original_certificates=original,
                         retrospective_certificates=len(group) - original, mean_achieved_bpshz=gain,
                         mean_achieved_lower_exact=str(lower), mean_achieved_upper_exact=str(upper),
                         mean_global_gain_ceiling_bpshz=f"{ticks // 10**12}.{ticks % 10**12:012d}",
                         mean_global_gain_ceiling_exact=str(cap), threshold_bpshz=float(margin),
                         margin_attained=attained, margin_impossible=excluded))

    blue, rust = "#1A608A", "#A8451D"
    fig, (rate, count) = plt.subplots(1, 2, figsize=(3.50, 2.32))
    x = np.arange(len(SNRS))
    rate.plot(x, [r["mean_achieved_bpshz"] * 1000 for r in rows], color=blue, lw=1.35, marker="o",
              ms=4, label="Price–DP–SQP")
    rate.plot(x, [float(Fraction(r["mean_global_gain_ceiling_exact"])) * 1000 for r in rows],
              color=rust, lw=1.2, ls="--", marker="s", ms=4, markerfacecolor="white", label="Global ceiling")
    rate.axhline(float(margin) * 1000, color=".28", lw=.85, ls=":")
    rate.text(.05, float(margin) * 1000 - .45, "0.01 margin", fontsize=7, color=".28", va="top")
    rate.set(ylabel="Mean gain over DP–SQP\n($10^{-3}$ bit/s/Hz)", ylim=(-.4, 10.65),
             yticks=(0, 2, 4, 6, 8, 10), xlim=(-.21, 2.21), title="(a) Mean rate gain")

    for key, label, offset, color, hatch in (("margin_attained", "Attained", -.20, blue, ""),
                                             ("margin_impossible", "Impossible", .20, "white", "////")):
        heights = [r[key] for r in rows]
        bars = count.bar(x + offset, heights, width=.35, color=color, edgecolor=blue if not hatch else ".38",
                         linewidth=.7, hatch=hatch, label=label)
        count.bar_label(bars, padding=1.2, fontsize=7)
    count.set(ylabel="Number of cases", ylim=(0, 69), yticks=(0, 20, 40, 60),
              xlim=(-.52, 2.52), title="(b) 0.01 margin")
    for ax in (rate, count):
        ax.set_xticks(x, labels=SNRS)
        ax.grid(axis="y", color=".88", lw=.5)
        ax.set_axisbelow(True)
        ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.17), frameon=False, borderaxespad=0,
                  handlelength=1.9, handletextpad=.35, labelspacing=.2)
    fig.supxlabel("Nominal SNR (dB)", fontsize=8.2, y=.018)
    fig.subplots_adjust(left=.171, right=.987, top=.720, bottom=.200, wspace=.77)
    save(fig, out, name)
    return rows


def equal_power(out, name):
    folder = ROOT / "equal-power-bound-20261111"
    summary = read(folder / "summary.json")
    source = folder / "cases.csv"
    require(summary["status"] == "PASS" and sha(source) == summary["cases_sha256"],
            "Equal-power case table differs from the archived bound check")
    cases = read_rows(source)
    rows = []
    for snr in SNRS:
        group = [r for r in cases if int(r["snr_db"]) == snr]
        ref = summary["by_snr_db"][str(snr)]
        require(len(group) == ref["cases"] == 60 and
                {(int(r["block"]), r["profile"]) for r in group} == {(b, p) for b in range(20) for p in "ABC"},
                "Expected 60 paired equal-power cases at each SNR")
        row = dict(snr_db=snr, cases=len(group))
        for source_key, key in (("achieved_gain_lb_bpshz", "mean_feasible_lower_bpshz"),
                                ("analytic_gap_ub_bpshz", "mean_analytic_upper_bpshz"),
                                ("grid_gap_ub_bpshz", "mean_grid_upper_bpshz"),
                                ("combined_gap_ub_bpshz", "mean_combined_upper_bpshz")):
            value = ref[source_key]["mean"]
            require(abs(Fraction(value) - mean(Fraction(r[source_key]) for r in group)) <= Fraction(1, 10**12),
                    "Directed twelve-place mean differs from paired case data: " + source_key)
            row[key] = value
        require(all(Fraction(r["achieved_gain_lb_bpshz"]) <= Fraction(r["combined_gap_ub_bpshz"]) ==
                    min(Fraction(r["analytic_gap_ub_bpshz"]), Fraction(r["grid_gap_ub_bpshz"])) for r in group),
                "Per-case equal-power bracket failed")
        row.update(worst_analytic_upper_bpshz=ref["analytic_gap_ub_bpshz"]["max"],
                   analytic_tighter_than_grid=ref["analytic_tighter_than_grid"])
        rows.append(row)

    fig, ax = plt.subplots(figsize=(3.50, 2.60))
    for key, label, color, marker, line, size in (
            ("mean_feasible_lower_bpshz", "Feasible lower bound", "#1A608A", "o", "-", 3.6),
            ("mean_analytic_upper_bpshz", "Analytic upper bound", "#A8451D", "^", "-.", 5.0),
            ("mean_grid_upper_bpshz", "Grid upper bound", ".27", "s", "--", 7.2)):
        ax.plot(SNRS, [float(r[key]) for r in rows], label=label, color=color, marker=marker,
                linestyle=line, lw=1.25, ms=size, markerfacecolor=color if marker == "o" else "none",
                markeredgewidth=.95)
    ax.set(xlabel="Nominal SNR (dB)", ylabel="Mean loss from equal power\n(bit/s/Hz)", yscale="log",
           xticks=SNRS, xlim=(-1,21), ylim=(4e-5, 2), yticks=(1e-4, 1e-3, 1e-2, 1e-1, 1))
    ax.grid(axis="y", color=".88", lw=.5)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), frameon=False, ncol=2, fontsize=7.4,
              columnspacing=.7, handlelength=2.15, handletextpad=.38, borderaxespad=0, labelspacing=.28)
    fig.subplots_adjust(left=.225, right=.972, bottom=.200, top=.763)
    save(fig, out, name)
    return rows


CONTROLS = (("Price-DP-SQP", "Full pricing", "#1A608A", "o", "-"),
            ("DP-SQP", "Eight-start DP–SQP", "#A8451D", "s", "--"),
            ("Uniform-start-DP-SQP", "One unpriced start", "#00664C", "^", "-."),
            ("Always-short-price", "Always-short pricing", "#69528B", "D", ":"))


def screened_data():
    study = ROOT / "adaptive-pricing-20261111"
    folder = study / "analysis"
    summary, audit = read(folder / "results.json"), read(folder / "audit.json")
    require(summary["status"] == "COMPLETE" and audit["status"] == "PASS" and
            summary["audit_sha256"] == sha(folder / "audit.json") and
            (summary["blocks"], summary["cases"], audit["final_allocations"], summary["bootstrap_draws"]) ==
            (20, 180, 900, 20000), "Incomplete screened-search study")
    indices = draws(study)
    saved = {(r["comparator"], int(r["snr_db"])): r for r in read_rows(folder / "cell_contrasts.csv")
             if r["profile"] == "ALL"}
    pairs = {}
    for r in read_rows(folder / "case_values.csv"):
        if r["comparator"] == "DP-SQP-time-prefix":
            continue
        b, p, s = int(r["block"]), r["profile"], int(r["snr_db"])
        key = r["comparator"], b, p, s
        rate, log_ratio = float(r["rate_delta"]), float(r["log_time_ratio"])
        require(key not in pairs and r["case"] == f"native-b{b:02d}-{p}-snr{s:02d}" and
                isclose(rate, float(r["adaptive_se"]) - float(r["reference_se"]), abs_tol=1e-12) and
                isclose(log_ratio, log(float(r["adaptive_seconds"]) / float(r["reference_seconds"])), abs_tol=1e-12),
                "Paired rate or time mismatch on " + r["case"])
        pairs[key] = rate, log_ratio
    require(set(pairs) == {(a, b, p, s) for a, *_ in CONTROLS for b in range(20) for p in "ABC" for s in SNRS},
            "Expected all four independently timed controls on the fresh 180 cases")
    rows = []
    for arm, *_ in CONTROLS:
        groups = (*SNRS, "All") if arm == CONTROLS[0][0] else SNRS
        for snr in groups:
            levels = SNRS if snr == "All" else (snr,)
            block = np.array([[pairs[arm, b, p, s] for p in "ABC" for s in levels] for b in range(20)]).mean(axis=1)
            low, high = np.quantile(block[indices].mean(axis=1), (.025, .975), axis=0)
            estimates = np.stack((block.mean(axis=0), low, high)).T
            estimates[1] = np.exp(estimates[1])
            if snr == "All":
                published = [[summary["primary"][kind][stat] for stat in ("mean", "low", "high")]
                             for kind in ("rate", "time_ratio")]
            else:
                published = [[float(saved[arm, snr][kind + "_" + stat]) for stat in ("mean", "low", "high")]
                             for kind in ("rate", "time_ratio")]
            np.testing.assert_allclose(estimates, published, rtol=1e-12, atol=1e-14)
            row = dict(snr_db=snr, screened="Adaptive-DP-SQP", comparator=arm, blocks=20, cases=60 * len(levels),
                       screen_passes=sum(summary["screen_passes"][str(s)] for s in levels))
            for kind, result in zip(("rate_difference_bpshz", "geometric_time_ratio"), estimates):
                for stat, value in zip(("mean", "low95", "high95"), result):
                    row[kind + "_" + stat] = format(value, ".12g")
            losses = [(d, f"native-b{b:02d}-{p}-snr{s:02d}") for (a, b, p, s), (d, _) in pairs.items()
                      if a == arm and s in levels and d < -summary["tie_band"]]
            expected_losses = summary["primary"]["losses"] if snr == "All" else int(saved[arm, snr]["losses"])
            require(len(losses) == expected_losses, "Individual losses differ from the paired analysis")
            worst, case = min(losses) if losses else (0., "")
            row.update(losses_beyond_tie_band=len(losses), largest_individual_loss_bpshz=format(abs(worst), ".12g"),
                       largest_loss_case=case)
            row.update(rate_floor_bpshz=summary["rate_margin"], time_ratio_ceiling=summary["time_margin"],
                       pooled_primary_comparison=(snr == "All"))
            rows.append(row)
    return rows


def tradeoff(out, name):
    rows = screened_data()
    fig, axes = plt.subplots(2, 1, figsize=(3.50, 3.45), sharex=True)
    for ax, kind, scale, margin, baseline in (
            (axes[0], "rate_difference_bpshz", 1000, rows[0]["rate_floor_bpshz"], 0),
            (axes[1], "geometric_time_ratio", 1, rows[0]["time_ratio_ceiling"], 1)):
        ax.axvspan(2.60, 3.31, facecolor=".95", zorder=0)
        ax.axhline(baseline, color=".55", lw=.7, zorder=0)
        ax.axhline(margin * scale, color=".25", ls=(0, (4, 2.5)), lw=.9, zorder=1)
        for offset, (arm, label, color, marker, line) in zip((-.15, -.05, .05, .15), CONTROLS):
            points = [r for r in rows if r["comparator"] == arm]
            ys = np.array([[float(r[kind + "_" + stat]) for r in points]
                           for stat in ("mean", "low95", "high95")]) * scale
            center, low, high = ys
            errors = np.array([center - low, high - center])
            style = dict(color=color, marker=marker, ms=4.0, markerfacecolor=color if arm == CONTROLS[0][0]
                         else "white", markeredgewidth=.8, lw=1.1, elinewidth=.7, capsize=1.8)
            ax.errorbar(np.arange(3) + offset, center[:3], yerr=errors[:, :3], ls=line, label=label, **style)
            if len(points) == 4:
                ax.errorbar([3], center[3:], yerr=errors[:, 3:], ls="none", **style)
        ax.grid(axis="y", color=".88", lw=.5)
        ax.set_axisbelow(True)
    axes[0].set_title("(a) Screened minus control", loc="left", pad=3)
    axes[0].set_yscale("symlog", linthresh=1)
    axes[0].set_yticks((-3, -1, 0, 1, 5, 20), labels=("−3", "−1", "0", "1", "5", "20"))
    axes[0].set_ylabel("SE difference\n($10^{-3}$ bit/s/Hz)")
    axes[1].set_title("(b) Screened / control", loc="left", pad=3)
    axes[1].set_ylabel("Search-time ratio")
    axes[1].set_yscale("log", base=2)
    axes[1].set_yticks((.0625, .25, .5, 1, 4))
    axes[1].yaxis.set_major_formatter(lambda v, _: f"{v:g}")
    axes[1].set(xticks=(0, 1, 2, 3), xticklabels=("0", "10", "20", "All"), xlim=(-.37, 3.31),
                xlabel="Nominal SNR (dB)")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2, frameon=False,
               handlelength=2, handletextpad=.35, columnspacing=1.2, labelspacing=.35)
    fig.subplots_adjust(left=.217, right=.979, top=.815, bottom=.134, hspace=.50)
    save(fig, out, name)
    return rows


PLOTS = {"cdl_certified_headroom": headroom, "cdl_equal_power_bound": equal_power,
         "cdl_screened_tradeoff": tradeoff}


def generate(out, names=None):
    out.mkdir(parents=True, exist_ok=True)
    with plt.rc_context(STYLE):
        for name in (PLOTS if names is None else names):
            rows = PLOTS[name](out, name)
            with (out / (name + ".csv")).open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--only", choices=PLOTS, nargs="+", help="Redraw selected figures")
    options = parser.parse_args()
    generate(options.output, options.only)
