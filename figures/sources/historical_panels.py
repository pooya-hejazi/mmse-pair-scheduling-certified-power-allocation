"""Scientific drawing and data-reading functions extracted from make_figures.py (R5)."""

from __future__ import annotations

import csv

import hashlib

import io

import json

import math

import re

import zipfile

from collections import Counter

from dataclasses import dataclass

from fractions import Fraction

from pathlib import Path

from typing import Any

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

import numpy as np

from matplotlib.lines import Line2D

from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

from matplotlib.text import Text

from matplotlib.ticker import FuncFormatter, MaxNLocator, NullLocator

HERE = Path(__file__).resolve().parent

BUNDLE = HERE / "inputs" / "figure-inputs.zip"

PROVENANCE = HERE / "inputs" / "input-provenance.json"

WIDTH = 6.3

TARGET = 0.01

ARMS = ("T", "W", "S", "FU_SCA", "THU_IDE")

LABELS = {"T": "Proposed transfer", "W": "WMMSE", "S": "SLSQP",
          "FU_SCA": "Fu–SCA", "THU_IDE": "Thu–IDE"}

BLUE, ORANGE, GREEN, PURPLE, RED = "#0072B2", "#B96608", "#00856A", "#8064A2", "#C04C32"

INK, GRAY = "#252B30", "#78818A"

METHOD_LABELS = {"grid": "Grid", "full": "Grid + refinement", "joint": "WMMSE",
                 "curvature": "Curvature", "pricing": "Grid + pricing", "reference": "Reference"}

METHOD_COLORS = {"grid": BLUE, "full": RED, "joint": PURPLE,
                 "curvature": GREEN, "pricing": GREEN, "reference": GRAY}

METHOD_MARKERS = {"grid": "o", "full": "^", "joint": "s", "curvature": "D", "pricing": "s", "reference": "o"}

METHOD_LINES = {"grid": "-", "full": "-.", "joint": ":", "curvature": "--", "pricing": "--", "reference": "-"}

ARM_COLORS = dict(zip(ARMS, (BLUE, PURPLE, GREEN, ORANGE, RED)))

ARM_MARKERS = dict(zip(ARMS, ("o", "s", "^", "D", "v")))

GROUP_COLORS = (BLUE, ORANGE, GREEN, RED, PURPLE, "#287C8E", "#9B596E", "#566D2D", "#555555", "#3B58A0", "#9A6D42")

GROUP_MARKERS = ("o", "s", "^", "D", "v", "P", "X", "<", ">", "h", "p")

REGIMES = ("snr0_narrow", "snr0_broad", "snr30_narrow", "snr30_broad")

REGIME_LABELS = ("0 dB / narrow", "0 dB / broad", "30 dB / narrow", "30 dB / broad")

FORBIDDEN_TEXT = re.compile(r"TCOM|\bR[1-5]\b|2026|all groups retained|202611", re.I)

class FigureDataError(RuntimeError):
    pass

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")

def number(value: Any, label: str = "value") -> float:
    result = float(value)
    if not math.isfinite(result):
        raise FigureDataError(f"Non-finite {label}: {value!r}")
    return result

def exact(value: Any) -> Fraction:
    result = Fraction(value)
    number(result, "rational")
    return result

def require(condition: bool, message: str) -> None:
    if not condition:
        raise FigureDataError(message)

class Inputs:
    def __init__(self) -> None:
        self.provenance = json.loads(PROVENANCE.read_bytes())
        raw = BUNDLE.read_bytes()
        require(sha(raw) == self.provenance["bundle"]["sha256"], "Input bundle SHA-256 mismatch")
        self.archive = zipfile.ZipFile(io.BytesIO(raw))
        self.records = {row["member"]: row for row in self.provenance["members"]}
        self.consumed: dict[str, dict[str, Any]] = {}
        require(set(self.archive.namelist()) == set(self.records), "Bundle/provenance member sets differ")

    def raw(self, name: str) -> bytes:
        raw = self.archive.read(name)
        record = self.records[name]
        require(len(raw) == record["bytes"] and sha(raw) == record["sha256"], f"Input member mismatch: {name}")
        self.consumed[name] = {"member": name, "bytes": len(raw), "sha256": record["sha256"]}
        return raw

    def json(self, name: str) -> Any:
        return json.loads(self.raw(name).decode("utf-8-sig"))

    def csv(self, name: str) -> list[dict[str, str]]:
        return list(csv.DictReader(io.StringIO(self.raw(name).decode("utf-8-sig"))))

@dataclass
class Data:
    rows: list[dict[str, str]]
    diagnostics: list[dict[str, Any]]
    history_summary: dict[str, Any]
    history_contrasts: list[dict[str, Any]]
    history_rows: list[dict[str, str]]
    history_protocol: dict[str, Any]
    historic_scale: list[dict[str, str]]
    protocol: dict[str, Any]
    summary: dict[str, Any]
    cases: list[str]
    seeds: np.ndarray
    gains: dict[str, np.ndarray]
    times: dict[str, np.ndarray]
    verify_times: dict[str, np.ndarray]
    common_starts: list[dict[str, Any]]
    inputs: Inputs

def load_data(inputs: Inputs) -> Data:
    rows = inputs.csv("corrective/all-cells.csv")
    for scene in ("o1", "asu"):
        for panel, count, methods in (("main", 12, ("grid", "curvature", "full", "joint")), ("scale", 4, ("grid", "pricing", "joint"))):
            for method in methods:
                chosen = [r for r in rows if (r["scene"], r["panel"], r["method"]) == (scene, panel, method)]
                require(len(chosen) == count and {int(r["index"]) for r in chosen} == set(range(count)), f"Incomplete/duplicate {scene}/{panel}/{method} cases")
                for r in chosen:
                    gap, upper, lower = (number(r[k], k) for k in ("gap_nats", "upper_nats", "lower_nats"))
                    require(gap >= 0 and math.isclose(gap, upper - lower, rel_tol=2e-8, abs_tol=2e-10), f"Inconsistent gap: {r['case']}/{method}")
    history_rows = inputs.csv("historical/all-cells.csv")
    history_summary = inputs.json("historical/summary.json")
    history_contrasts = inputs.json("historical/contrasts.json")
    require(history_summary.get("complete") is True and history_summary["completed_valid_cells"] == 220, "Historical analysis incomplete")
    require(len(history_rows) == 220 and len(history_contrasts) == 44, "Historical all-case count changed")
    require(sorted(Counter(int(r["seed"]) for r in history_contrasts).values()) == [4] * 11, "Historical seed groups must each have four cases")
    summary, protocol = inputs.json("matched/summary.json"), inputs.json("matched/protocol.json")
    require(summary.get("complete_44_case_study") is True and summary["n_cases"] == 44 and summary["n_seed_groups"] == 11, "Matched analysis incomplete")
    cases = list(protocol["design"]["case_order"])
    require(tuple(protocol["design"]["arms"]) == ARMS and len(cases) == len(set(cases)) == 44, "Matched design changed")
    require(protocol["design"]["cells_planned"] == 220, "Matched design is not 220 cells")
    gains = {arm: np.empty(44) for arm in ARMS}
    times = {arm: np.empty(44) for arm in ARMS}
    verification = {arm: np.empty(44) for arm in ARMS}
    seeds = np.empty(44, dtype=np.int64)
    starts = []
    for index, case in enumerate(cases):
        identity = None
        for arm in ARMS:
            cell = inputs.json(f"matched/cells/{case}/{arm}.json")
            require((cell["case_id"], cell["arm"]) == (case, arm), f"Cell identity mismatch: {case}/{arm}")
            initial, final = cell["initial"], cell["final"]
            iv, fv = initial["independent_verification"], final["independent_verification"]
            require(initial["feasible_and_rate_checked"] and final["feasible_and_rate_checked"] and iv["valid"] and fv["valid"], f"Invalid feasibility/interval check: {case}/{arm}")
            gain = exact(cell["verified_lower_gain_nats"])
            require(gain == exact(fv["lower_nats"]) - exact(iv["lower_nats"]) and gain >= 0, f"Exact gain identity failed: {case}/{arm}")
            resources = len(initial["schedule"])
            require(resources > 0 and len(final["schedule"]) == resources, "Invalid resource count")
            current = (exact(iv["lower_nats"]), initial["schedule_sha256"], cell["initial_start_sha256"], resources, cell["seed"])
            require(current[1] and current[2], "Missing common-start hash")
            if identity is None:
                identity = current
            require(current == identity, f"Common-start mismatch: {case}/{arm}")
            gains[arm][index] = float(gain / (resources * math.log(2.0)))
            times[arm][index] = number(cell["refinement"]["elapsed_seconds"])
            verification[arm][index] = number(iv["seconds"]) + number(fv["seconds"])
            require(times[arm][index] >= 0 and verification[arm][index] >= 0, "Negative recorded time")
        seeds[index] = int(identity[4])
        starts.append({"case_id": case, "seed": int(identity[4]), "initial_lower_nats": str(identity[0]), "schedule_sha256": identity[1], "start_sha256": identity[2], "resources": identity[3]})
    require(sorted(Counter(seeds.tolist()).values()) == [4] * 11, "Matched seed groups must each have four cases")
    return Data(rows, inputs.json("corrective/diagnostics.json"), history_summary, history_contrasts,
                history_rows, inputs.json("historical/protocol.json"), inputs.csv("historical-scale/all-cells.csv"),
                protocol, summary, cases, seeds, gains, times, verification, starts, inputs)

def select(data: Data, scene: str, panel: str, method: str) -> list[dict[str, str]]:
    return sorted([r for r in data.rows if (r["scene"], r["panel"], r["method"]) == (scene, panel, method)], key=lambda r: int(r["index"]))

def values(data: Data, scene: str, panel: str, method: str, metric: str) -> np.ndarray:
    return np.array([number(row[metric], f"{row['case']}/{metric}") for row in select(data, scene, panel, method)])

def set_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.labelsize": 9,
        "axes.titlesize": 9.5, "axes.titleweight": "normal", "axes.titlepad": 8,
        "legend.fontsize": 8.5, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "axes.linewidth": .65, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.axisbelow": True, "grid.color": "#E2E5E8",
        "grid.linewidth": .55, "xtick.direction": "out", "ytick.direction": "out",
        "lines.linewidth": 1.1, "figure.facecolor": "white", "savefig.facecolor": "white",
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "svg.hashsalt": "publication-figures", "mathtext.fontset": "dejavusans",
        "figure.constrained_layout.h_pad": .08, "figure.constrained_layout.w_pad": .06,
        "figure.max_open_warning": 30,
    })

def panels(rows: int = 1, columns: int = 2, height: float = 2.8, **kw: Any) -> tuple[plt.Figure, Any]:
    return plt.subplots(rows, columns, figsize=(WIDTH, height), layout="constrained", **kw)

def title(ax: plt.Axes, text: str) -> None:
    ax.set_title(text, loc="left")

def clean(ax: plt.Axes, grid: str = "y") -> None:
    ax.grid(False)
    ax.grid(axis=grid, visible=True)
    ax.tick_params(length=3, width=.65)

def log_axis(ax: plt.Axes, which: str, lo: float, hi: float, ticks: list[float]) -> None:
    target = ax.xaxis if which == "x" else ax.yaxis
    getattr(ax, f"set_{which}scale")("log")
    getattr(ax, f"set_{which}lim")(lo, hi)
    getattr(ax, f"set_{which}ticks")(ticks)
    target.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}"))
    target.set_minor_locator(NullLocator())

def method_legend(fig: plt.Figure, methods: tuple[str, ...], columns: int | None = None) -> None:
    handles = [Line2D([], [], color=METHOD_COLORS[m], marker=METHOD_MARKERS[m], ls=METHOD_LINES[m], ms=4.5, label=METHOD_LABELS[m]) for m in methods]
    fig.legend(handles=handles, loc="outside upper center", ncol=columns or len(methods), frameon=False, handlelength=1.7, columnspacing=1.2)

def group_legend(fig: plt.Figure) -> None:
    handles = [Line2D([], [], color=GROUP_COLORS[g], marker=GROUP_MARKERS[g], ls="none", ms=4, label=f"{g+1:02d}") for g in range(11)]
    fig.legend(handles=handles, loc="outside upper center", ncol=11, frameon=False, handlelength=.7, handletextpad=.3, columnspacing=.65, fontsize=8)

def component_metrics(data: Data) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for scene in ("o1", "asu"):
        w, g, f = (values(data, scene, "main", m, "SE") for m in ("joint", "grid", "full"))
        result[scene] = {"wmmse": w.tolist(), "grid": g.tolist(), "full": f.tolist(),
                         "grid_gain": (g-w).tolist(), "refinement_gain": (f-g).tolist(),
                         "mean_grid_gain": float((g-w).mean()), "mean_refinement_gain": float((f-g).mean()),
                         "mean_total_gain": float((f-w).mean())}
    grid = (result["o1"]["mean_grid_gain"] + result["asu"]["mean_grid_gain"]) / 2
    ref = (result["o1"]["mean_refinement_gain"] + result["asu"]["mean_refinement_gain"]) / 2
    result["overall"] = {"mean_grid_gain": grid, "mean_refinement_gain": ref, "mean_total_gain": grid+ref,
                         "grid_share_percent": 100*grid/(grid+ref), "refinement_share_percent": 100*ref/(grid+ref)}
    return result

def component_bars(axes: Any, metrics: dict[str, Any], tags: str = "ab") -> None:
    for ax, key, heading, color, tag in zip(axes, ("mean_grid_gain", "mean_refinement_gain"),
            ("Grid − WMMSE", "Shared refinement"), (BLUE, RED), tags):
        x = np.array([metrics[s][key] for s in ("o1", "asu", "overall")])
        ax.barh(range(3), x, color=color, height=.52, alpha=.85)
        maxval = max(float(np.max(np.abs(x))), .001)
        for i, v in enumerate(x):
            ax.text(v + maxval*.035, i, f"{v:.6f}", va="center", fontsize=8.5)
        ax.set_yticks(range(3), ("O1", "ASU", "Pooled"))
        ax.invert_yaxis()
        ax.set_xlim(min(0, float(x.min())*1.2), maxval*1.52)
        ax.set_xlabel("Mean rate gain (bit/s/Hz)")
        ax.xaxis.set_major_locator(MaxNLocator(4))
        title(ax, f"({tag}) {heading}")
        clean(ax, "x")

def plot_components(data: Data, detail: bool = False) -> tuple[plt.Figure, dict[str, Any]]:
    metrics = component_metrics(data)
    if not detail:
        fig, axes = panels(height=2.35)
        component_bars(axes, metrics)
        return fig, metrics
    fig, axes = panels(2, 2, height=5.3, gridspec_kw={"height_ratios": (1.4, 1)})
    for col, scene in enumerate(("o1", "asu")):
        ax = axes[0, col]
        rates = np.column_stack([metrics[scene][k] for k in ("wmmse", "grid", "full")])
        for row in rates:
            ax.plot(range(3), row, color="#A4ABB1", lw=.75, alpha=.8)
        for index, method in enumerate(("joint", "grid", "full")):
            ax.scatter(np.full(12, index), rates[:, index], s=22, marker=METHOD_MARKERS[method], color=METHOD_COLORS[method], ec="white", lw=.35, zorder=3)
        ax.set_xticks(range(3), ("WMMSE", "Grid", "Grid +\nrefinement"))
        ax.set_xlim(-.35, 2.35)
        ax.set_ylabel("Achieved rate (bit/s/Hz)")
        title(ax, f"({'ab'[col]}) {scene.upper()}")
        clean(ax)
        ax.margins(y=.12)
    component_bars(axes[1], metrics, "cd")
    return fig, metrics

def plot_gaps(data: Data, detail: bool = False) -> tuple[plt.Figure, dict[str, Any]]:
    fig, axes = panels(2 if detail else 1, 1 if detail else 2, height=4.9 if detail else 2.85, sharey=True)
    metrics: dict[str, Any] = {"target_nats": TARGET, "scenes": {}}
    specs = (("full", "main", -.08), ("grid", "scale", -.12), ("pricing", "scale", .12))
    for ax, scene, tag in zip(np.ravel(axes), ("o1", "asu"), "ab"):
        ax.axvline(11.5, color="#AEB5BA", lw=.7)
        ax.axhline(TARGET, color=INK, ls=(0, (4, 3)), lw=.9)
        ax.text(.03, .14, "0.01-nat target", transform=ax.transAxes, ha="left", va="bottom", fontsize=8.5)
        scene_metrics = {}
        for method, panel, offset in specs:
            rows = select(data, scene, panel, method)
            y = values(data, scene, panel, method, "gap_nats")
            x = np.arange(len(rows)) + (12 if panel == "scale" else 0) + offset
            ax.scatter(x, y, color=METHOD_COLORS[method], marker=METHOD_MARKERS[method], s=27, ec="white", lw=.35, zorder=3)
            scene_metrics[method] = {"cases": [r["case"] for r in rows], "gap_nats": y.tolist(), "above_target": (y > TARGET).tolist(), "above_target_count": int(np.sum(y > TARGET)), "count": len(rows)}
        log_axis(ax, "y", .004, 100, [.01, .1, 1, 10, 100])
        ax.set_xlim(-.65, 15.65)
        if detail:
            ax.set_xticks(range(16), [f"M{i+1:02d}" for i in range(12)] + [f"S{i+1:02d}" for i in range(4)])
        else:
            ax.set_xticks([0, 3, 6, 9, 12, 15], ["M01", "M04", "M07", "M10", "S01", "S04"])
        ax.set_xlabel("Case (M: main; S: scale)")
        ax.set_ylabel("Upper − lower bound (nats)")
        title(ax, f"({tag}) {scene.upper()}")
        clean(ax)
        metrics["scenes"][scene] = scene_metrics
    method_legend(fig, ("full", "grid", "pricing"))
    return fig, metrics

def influence_metrics(data: Data) -> dict[str, Any]:
    seeds = np.array(sorted({int(r["seed"]) for r in data.history_contrasts}))
    row_seeds = np.array([int(r["seed"]) for r in data.history_contrasts])
    effects = np.array([number(r["absolute_modern"]) for r in data.history_contrasts])
    groups = np.array([effects[row_seeds == s].mean() for s in seeds])
    loo = np.array([effects[row_seeds != s].mean() for s in seeds])
    medians = np.array([np.median(effects[row_seeds != s]) for s in seeds])
    saved = data.history_summary["effects"]["absolute_modern"]
    require(np.allclose(groups, saved["group_effects"], atol=2e-14, rtol=2e-10), "Historical group effects mismatch")
    require(np.allclose(loo, saved["leave_one_group_out"], atol=2e-14, rtol=2e-10), "Historical leave-one-group-out means mismatch")
    return {"effect": "Proposed transfer minus the per-case maximum of adapted Fu–SCA and Thu–IDE; historical unequal-search pipelines",
            "seed_groups": seeds.tolist(), "display_groups": [f"{i+1:02d}" for i in range(11)],
            "case_effects_bit_per_s_Hz": effects.tolist(),
            "whole_seed_group_effects_bit_per_s_Hz": groups.tolist(),
            "leave_one_seed_out_means_bit_per_s_Hz": loo.tolist(),
            "leave_one_seed_out_medians_bit_per_s_Hz": medians.tolist(),
            "overall_mean_bit_per_s_Hz": float(effects.mean()), "overall_median_bit_per_s_Hz": float(np.median(effects)),
            "registered_substantial_threshold_bit_per_s_Hz": number(data.history_protocol["primary"]["absolute_substantial_threshold_bit_per_s_Hz"])}

def group_points(ax: plt.Axes, x: np.ndarray, y: np.ndarray, stems: bool = False) -> None:
    for i, (xx, yy) in enumerate(zip(x, y)):
        if not math.isfinite(float(yy)):
            continue
        if stems:
            ax.vlines(xx, 0, yy, color=GROUP_COLORS[i], lw=.8, alpha=.75)
        ax.scatter(xx, yy, marker=GROUP_MARKERS[i], color=GROUP_COLORS[i], s=26, ec="white", lw=.35, zorder=4)

def plot_influence(data: Data) -> tuple[plt.Figure, dict[str, Any]]:
    metrics = influence_metrics(data)
    groups = np.array(metrics["whole_seed_group_effects_bit_per_s_Hz"])
    means = np.array(metrics["leave_one_seed_out_means_bit_per_s_Hz"])
    medians = np.array(metrics["leave_one_seed_out_medians_bit_per_s_Hz"])
    special = int(np.argmax(np.abs(groups)))
    require(special == 3, "Historical influential-group identity changed")
    x = np.arange(11)
    fig, axes = panels(2, 2, height=5.65)
    group_points(axes[0, 0], x, groups*1e4, stems=True)
    axes[0, 0].set_ylabel("Mean effect (×10⁻⁴ bit/s/Hz)")
    axes[0, 0].annotate(f"Group {special+1:02d}", xy=(special, groups[special]*1e4), xytext=(5.1, -1.45), fontsize=8.5,
                        arrowprops={"arrowstyle": "->", "lw": .7, "color": GRAY})
    title(axes[0, 0], "(a) Group effects")
    axes[0, 0].set_ylim(groups.min()*1e4*1.12, .20)
    near = groups.copy()
    near[special] = np.nan
    group_points(axes[0, 1], x, near*1e9, stems=True)
    limit = max(abs(near[np.isfinite(near)]))*1e9*1.3
    axes[0, 1].set_ylim(-limit, limit*.32)
    axes[0, 1].scatter(special, -limit*.94, marker="v", color=GROUP_COLORS[special], s=27, zorder=4)
    axes[0, 1].text(.97, .06, "04 below detail range", transform=axes[0, 1].transAxes, ha="right", fontsize=8)
    axes[0, 1].set_ylabel("Mean effect (×10⁻⁹ bit/s/Hz)")
    title(axes[0, 1], "(b) Detail near zero")
    for ax, y, baseline, factor, label, tag in (
        (axes[1, 0], means, metrics["overall_mean_bit_per_s_Hz"], 1e5, "Mean (×10⁻⁵ bit/s/Hz)", "c"),
        (axes[1, 1], medians, metrics["overall_median_bit_per_s_Hz"], 1e9, "Median (×10⁻⁹ bit/s/Hz)", "d"),
    ):
        group_points(ax, x, y*factor)
        ax.axhline(baseline*factor, color=INK, ls=(0, (4, 3)), lw=.9, label="Full-sample " + ("mean" if tag == "c" else "median"))
        ax.set_ylabel(label)
        title(ax, f"({tag}) Leave-one-group-out " + ("mean" if tag == "c" else "median"))
        ax.legend(frameon=False, loc="lower right", fontsize=8)
        ax.margins(y=.2)
    for index, ax in enumerate(axes.flat):
        ax.axhline(0, color=GRAY, lw=.7)
        ax.set_xticks(x, metrics["display_groups"])
        ax.tick_params(axis="x", labelsize=8)
        ax.set_xlim(-.5, 10.5)
        ax.set_xlabel("Seed group" if index < 2 else "Omitted seed group")
        clean(ax)
    metrics["detail_outside_range_group"] = "04"
    metrics["influential_group"] = {"seed": metrics["seed_groups"][special], "display_group": "04", "effect_bit_per_s_Hz": float(groups[special])}
    return fig, metrics

CONTRAST_SPECS = (("T − W", "T", "W"), ("T − S", "T", "S"), ("T − Fu-SCA", "T", "FU_SCA"),
                  ("T − Thu-IDE", "T", "THU_IDE"), ("Fu-SCA − Thu-IDE", "FU_SCA", "THU_IDE"))

def matched_metrics(data: Data) -> dict[str, Any]:
    seed_values = np.array(sorted(set(data.seeds.tolist())))
    contrast_values = [data.gains[a] - data.gains[b] for _, a, b in CONTRAST_SPECS]
    group_matrix = np.array([[v[data.seeds == s].mean() for v in contrast_values] for s in seed_values])
    plan = data.protocol["analysis_plan"]["cluster_bootstrap"]
    replicates, seed = int(plan["replicates"]), int(plan["seed"])
    require(replicates == 20000, "Completed bootstrap replicate count changed")
    rng = np.random.Generator(np.random.PCG64(seed))
    indices = rng.integers(0, len(seed_values), size=(replicates, len(seed_values)))
    intervals = np.percentile(group_matrix[indices, :].mean(axis=1), (2.5, 97.5), axis=0).T
    result: dict[str, Any] = {"cases": 44, "whole_seed_groups": 11, "method_cells": 220,
        "case_order": data.cases, "seed_group_mapping": {f"{i+1:02d}": int(s) for i, s in enumerate(seed_values)},
        "common_start_checks": data.common_starts,
        "conversion": "verified_lower_gain_nats / (resources * ln(2)); gross occupied-resource bit/s/Hz",
        "gains_bit_per_s_Hz": {}, "refinement_seconds": {}, "verification_seconds": {}, "paired_contrasts_bit_per_s_Hz": {}}
    for arm in ARMS:
        for key, v in (("gains_bit_per_s_Hz", data.gains[arm]), ("refinement_seconds", data.times[arm]), ("verification_seconds", data.verify_times[arm])):
            result[key][arm] = {"values": v.tolist(), "mean": float(v.mean()), "median": float(np.median(v)), "minimum": float(v.min()), "maximum": float(v.max())}
    for i, ((key, a, b), v) in enumerate(zip(CONTRAST_SPECS, contrast_values)):
        result["paired_contrasts_bit_per_s_Hz"][key] = {"label": f"{LABELS[a]} − {LABELS[b]}", "values": v.tolist(), "mean": float(v.mean()),
            "median": float(np.median(v)), "whole_seed_bootstrap_95_percent_interval": intervals[i].tolist(),
            "whole_seed_group_means": group_matrix[:, i].tolist(), "bootstrap_replicates": replicates, "bootstrap_seed": seed}
    return result

def matched_distribution(ax: plt.Axes, data: Data, arrays: dict[str, np.ndarray], xlabel: str, heading: str) -> None:
    box = ax.boxplot([arrays[a] for a in ARMS], positions=np.arange(5), vert=False, widths=.52, whis=(5, 95),
                     showfliers=False, patch_artist=True, medianprops={"color": INK, "lw": 1.15},
                     whiskerprops={"color": GRAY, "lw": .7}, capprops={"color": GRAY, "lw": .7})
    for patch in box["boxes"]:
        patch.set(facecolor="#E8ECEF", edgecolor="#AEB7BF", alpha=.65, lw=.7)
    seeds = sorted(set(data.seeds.tolist()))
    offsets = np.linspace(-.19, .19, len(data.cases))
    for j, arm in enumerate(ARMS):
        for g, seed in enumerate(seeds):
            mask = data.seeds == seed
            ax.scatter(arrays[arm][mask], j + offsets[mask], s=13, color=GROUP_COLORS[g], marker=GROUP_MARKERS[g], ec="white", lw=.2, alpha=.85, zorder=3)
    ax.set_yticks(range(5), [LABELS[a].replace("Proposed transfer", "Proposed\ntransfer") for a in ARMS])
    ax.invert_yaxis()
    ax.set_xlabel(xlabel)
    title(ax, heading)
    ax.xaxis.set_major_locator(MaxNLocator(4))
    ax.margins(x=.09)
    clean(ax, "x")

def contrast_strip(ax: plt.Axes, item: dict[str, Any], factor: float, exponent: str, heading: str) -> None:
    v = np.array(item["whole_seed_group_means"])*factor
    for i, value in enumerate(v):
        ax.scatter(value, -.13 + .026*i, marker=GROUP_MARKERS[i], s=21, color=GROUP_COLORS[i], ec="white", lw=.3, zorder=3)
    mean = item["mean"]*factor
    low, high = np.array(item["whole_seed_bootstrap_95_percent_interval"])*factor
    ax.errorbar(mean, .23, xerr=[[mean-low], [high-mean]], fmt="D", color=INK, ms=4.5, capsize=3, lw=1.2, zorder=5)
    ax.text(.03, .93, f"Mean {mean:+.3f}".replace("-", "−"), transform=ax.transAxes, va="top", fontsize=8.5)
    ax.axvline(0, color=GRAY, lw=.75)
    ax.set_ylim(-.35, .67)
    ax.set_yticks([])
    ax.set_xlabel(f"Difference (×10{exponent} bit/s/Hz)", fontsize=8.5)
    ax.xaxis.set_major_locator(MaxNLocator(4))
    ax.margins(x=.15)
    title(ax, heading)
    clean(ax, "x")

def contrast_forest(ax: plt.Axes, metrics: dict[str, Any], keys: tuple[str, ...], factor: float, exponent: str, heading: str) -> None:
    for j, key in enumerate(keys):
        item = metrics["paired_contrasts_bit_per_s_Hz"][key]
        for g, value in enumerate(item["whole_seed_group_means"]):
            ax.scatter(value*factor, j + np.linspace(-.14, .14, 11)[g], s=17, color=GROUP_COLORS[g], marker=GROUP_MARKERS[g], ec="white", lw=.25, zorder=3)
        mean = item["mean"]*factor
        lo, hi = np.array(item["whole_seed_bootstrap_95_percent_interval"])*factor
        ax.errorbar(mean, j, xerr=[[mean-lo], [hi-mean]], fmt="D", color=INK, ms=4.5, capsize=3, lw=1.2, zorder=5)
    labels = [metrics["paired_contrasts_bit_per_s_Hz"][k]["label"].replace(" − ", "\n− ") for k in keys]
    ax.set_yticks(range(len(keys)), labels)
    ax.invert_yaxis()
    ax.set_ylim(len(keys)-.5, -.5)
    ax.axvline(0, color=GRAY, lw=.75)
    ax.set_xlabel(f"Paired difference\n(×10{exponent} bit/s/Hz)")
    ax.xaxis.set_major_locator(MaxNLocator(4))
    ax.margins(x=.14)
    title(ax, heading)
    clean(ax, "x")

def plot_matched(data: Data, detail: bool = False) -> tuple[plt.Figure, dict[str, Any]]:
    metrics = matched_metrics(data)
    if not detail:
        fig = plt.figure(figsize=(WIDTH, 3.35), layout="constrained")
        spec = fig.add_gridspec(2, 2, width_ratios=(1.2, 1))
        ax = fig.add_subplot(spec[:, 0])
        matched_distribution(ax, data, data.gains, "Gain from common start\n(bit/s/Hz)", "(a) Common-start gains")
        ax.set_xlim(-.002, .050)
        for row, key, factor, exponent, tag, comparator in (
            (0, "T − Fu-SCA", 1e9, "⁻⁹", "b", "Fu–SCA"), (1, "T − Thu-IDE", 1e6, "⁻⁶", "c", "Thu–IDE")):
            contrast_strip(fig.add_subplot(spec[row, 1]), metrics["paired_contrasts_bit_per_s_Hz"][key], factor, exponent, f"({tag}) Proposed transfer − {comparator}")
    else:
        fig = plt.figure(figsize=(WIDTH, 7.65), layout="constrained")
        spec = fig.add_gridspec(3, 2, height_ratios=(1, 1.15, 1.2))
        matched_distribution(fig.add_subplot(spec[0, :]), data, data.gains, "Gain from common start (bit/s/Hz)", "(a) Common-start gains")
        contrast_forest(fig.add_subplot(spec[1, 0]), metrics, ("T − W", "T − Thu-IDE", "Fu-SCA − Thu-IDE"), 1e6, "⁻⁶", "(b) Paired differences")
        contrast_forest(fig.add_subplot(spec[1, 1]), metrics, ("T − S", "T − Fu-SCA"), 1e9, "⁻⁹", "(c) Fine-scale differences")
        ax_time, ax_verify = fig.add_subplot(spec[2, 0]), fig.add_subplot(spec[2, 1])
        matched_distribution(ax_time, data, data.times, "Refinement wall time (s)", "(d) Refinement time")
        matched_distribution(ax_verify, data, data.verify_times, "Initial + final verification (s)", "(e) Verification time")
        deadline = number(data.protocol["design"]["seconds_per_cell_refinement_wall_deadline"])
        ax_time.axvline(deadline, color=INK, ls=(0, (4, 3)), lw=.9)
        ax_time.text(.97, .97, f"{deadline:g}-s limit", transform=ax_time.transAxes, ha="right", va="top", fontsize=8,
                     bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
        ax_time.set_xticks([0, 2, 4, 5])
        ax_time.set_xlim(-.15, max(deadline*1.1, max(float(v.max()) for v in data.times.values())*1.06))
        metrics["refinement_wall_deadline_seconds"] = deadline
    group_legend(fig)
    return fig, metrics

def corrected_metric_table(data: Data, panel: str, methods: tuple[str, ...], metric: str) -> dict[str, Any]:
    return {scene: {method: {"cases": [r["case"] for r in select(data, scene, panel, method)],
                             "values": values(data, scene, panel, method, metric).tolist()}
                    for method in methods} for scene in ("o1", "asu")}

def plot_certification_counts(data: Data) -> tuple[plt.Figure, dict[str, Any]]:
    methods = ("grid", "curvature", "full", "joint")
    fig, axes = panels(height=2.45, sharey=True)
    metrics: dict[str, Any] = {"target_nats": TARGET, "scenes": {}}
    for ax, scene, tag in zip(axes, ("o1", "asu"), "ab"):
        metrics["scenes"][scene] = {}
        for i, method in enumerate(methods):
            rows = select(data, scene, "main", method)
            counts = {"target_met": sum(r["operational_success"] == "True" for r in rows),
                      "target_not_met": sum(r["normal"] == "True" and r["operational_success"] == "False" for r in rows),
                      "abnormal_return": sum(r["normal"] != "True" and r["operational_success"] == "False" for r in rows),
                      "missing": sum(r["operational_success"] not in ("True", "False") for r in rows)}
            require(counts == {"target_met": 0, "target_not_met": 12, "abnormal_return": 0, "missing": 0}, "Saved main certification counts changed")
            ax.barh(i, counts["target_not_met"], color="#DDE2E6", ec=GRAY, lw=.6, hatch="///", height=.58)
            ax.text(11.6, i, "12", ha="right", va="center", fontsize=8.5)
            metrics["scenes"][scene][method] = counts
        ax.set_yticks(range(4), [METHOD_LABELS[m].replace(" + ", " +\n") for m in methods])
        ax.set_xlim(0, 13)
        ax.set_xticks([0, 4, 8, 12])
        ax.set_xlabel("Cases above the target")
        title(ax, f"({tag}) {scene.upper()}")
        clean(ax, "x")
    axes[0].invert_yaxis()
    return fig, metrics

def plot_ecdf(data: Data, fairness: bool = False) -> tuple[plt.Figure, dict[str, Any]]:
    methods = ("grid", "curvature", "full", "joint")
    metric = "jain_fairness" if fairness else "gap_nats"
    fig, axes = panels(height=3.05, sharey=True)
    table = corrected_metric_table(data, "main", methods, metric)
    for ax, scene, tag in zip(axes, ("o1", "asu"), "ab"):
        for method in methods:
            x = np.sort(np.array(table[scene][method]["values"]))
            ax.step(x, np.arange(1, 13)/12, where="post", marker=METHOD_MARKERS[method], color=METHOD_COLORS[method],
                    ls=METHOD_LINES[method], ms=3.8, mfc="white", mew=.8, lw=1.05)
        ax.set_ylim(0, 1.04)
        ax.set_yticks([0, .25, .5, .75, 1])
        if fairness:
            ax.set_xlim((.98, 1.001) if scene == "o1" else (0, 1.02))
            ax.set_xticks([.98, .99, 1] if scene == "o1" else [0, .5, 1])
            ax.set_xlabel("Jain index")
        else:
            log_axis(ax, "x", .007, 50, [.01, .1, 1, 10])
            ax.axvline(TARGET, color=INK, ls=(0, (4, 3)), lw=.8)
            ax.text(.08, .10, "0.01-nat\ntarget", transform=ax.transAxes, fontsize=8.5)
            ax.set_xlabel("Upper − lower bound (nats)")
        title(ax, f"({tag}) {scene.upper()}" + (" (detail)" if fairness and scene == "o1" else ""))
        clean(ax)
    if fairness:
        require(min(v for method in methods for v in table["o1"][method]["values"]) >= .98, "O1 fairness detail would crop observations")
    axes[0].set_ylabel("Fraction of 12 cases")
    method_legend(fig, methods, 2)
    return fig, {"metric": metric, "denominator_per_scene_method": 12, "scenes": table}

def plot_main_time(data: Data) -> tuple[plt.Figure, dict[str, Any]]:
    methods = ("grid", "curvature", "full", "joint")
    table = corrected_metric_table(data, "main", methods, "elapsed")
    fig, axes = panels(height=2.7, sharey=True)
    for ax, scene, tag in zip(axes, ("o1", "asu"), "ab"):
        for i, method in enumerate(methods):
            v = np.array(table[scene][method]["values"])
            ax.scatter(v, i + np.linspace(-.18, .18, 12), s=21, color=METHOD_COLORS[method], marker=METHOD_MARKERS[method], ec="white", lw=.3)
            ax.vlines(np.median(v), i-.26, i+.26, color=INK, lw=1.2)
        ax.set_yticks(range(4), [METHOD_LABELS[m].replace(" + ", " +\n") for m in methods])
        ax.axvline(18, color=INK, ls=(0, (4, 3)), lw=.8)
        ax.set_xlim(0, 20)
        ax.set_xticks([0, 5, 10, 15, 18])
        ax.set_xlabel("Measured wall time (s)")
        title(ax, f"({tag}) {scene.upper()}")
        clean(ax, "x")
    axes[0].invert_yaxis()
    return fig, {"wall_time_seconds": table, "charged_cap_seconds": 18, "summary_mark": "median"}

def plot_curvature(data: Data) -> tuple[plt.Figure, dict[str, Any]]:
    methods = ("reference", "curvature", "full")
    table: dict[str, Any] = {}
    require(len(data.diagnostics) == 8, "Expected all eight synthetic diagnostic cases")
    for method in methods:
        v = [exact(next(row for row in d["rows"] if row["method"] == method)["verification"]["gap_nats"]) for d in data.diagnostics]
        require(all(x >= 0 for x in v), "Negative diagnostic gap")
        table[method] = {"gap_nats_exact": [str(x) for x in v], "gap_nats": [float(x) for x in v]}
    fig, ax = panels(columns=1, height=2.85)
    # The earlier display used this floor; exact values are retained in the manifest.
    floor = 1e-10
    for j, method in enumerate(methods):
        v = np.array(table[method]["gap_nats"])
        x = np.arange(1, 9) + (j-1)*.07
        ax.plot(x, np.maximum(v, floor), color=METHOD_COLORS[method], ls=METHOD_LINES[method], lw=1)
        visible = v >= floor
        ax.scatter(x[visible], v[visible], s=25, marker=METHOD_MARKERS[method], color=METHOD_COLORS[method], facecolors="white", lw=.9, zorder=3)
        ax.scatter(x[~visible], np.full(sum(~visible), floor), s=30, marker="v", color=METHOD_COLORS[method], facecolors="white", lw=.9, zorder=3)
    ax.set_yscale("log")
    ax.set_ylim(bottom=4e-11)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.0e}"))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_xticks(range(1, 9))
    ax.set_xlabel("Synthetic case")
    ax.set_ylabel("Upper − lower bound (nats)")
    handles = [Line2D([], [], color=METHOD_COLORS[m], marker=METHOD_MARKERS[m], ls=METHOD_LINES[m], ms=4.5, label=METHOD_LABELS[m]) for m in methods]
    handles.append(Line2D([], [], color=INK, marker="v", mfc="white", ls="none", ms=4.5, label="Below 10⁻¹⁰"))
    fig.legend(handles=handles, loc="outside upper center", ncol=2, frameon=False)
    clean(ax)
    return fig, {"cases": 8, "methods": table, "display_floor_nats": floor}

def plot_scale(data: Data, certificates: bool = False) -> tuple[plt.Figure, dict[str, Any]]:
    methods = ("grid", "pricing", "joint")
    metric = "relative_gap" if certificates else "SE"
    table = corrected_metric_table(data, "scale", methods, metric)
    fig, axes = panels(height=3.15 if certificates else 2.9, sharey=True)
    for ax, scene, tag in zip(axes, ("o1", "asu"), "ab"):
        for j, method in enumerate(methods):
            v = np.array(table[scene][method]["values"])
            if certificates:
                bars = ax.bar(np.arange(1, 5)+(j-1)*.24, v*100, width=.23, color=METHOD_COLORS[method],
                              ec=INK, lw=.4, hatch=("//", "", "xx")[j], alpha=.85)
                ax.bar_label(bars, labels=[f"{x*100:.1f}" for x in v], padding=3, rotation=90, fontsize=8)
            else:
                ax.scatter(np.arange(1, 5)+(j-1)*.075, v, color=METHOD_COLORS[method], marker=METHOD_MARKERS[method], s=32,
                           facecolors="white" if method == "grid" else METHOD_COLORS[method], lw=.8, zorder=3)
        ax.set_xticks(range(1, 5))
        ax.set_xlabel("Scale case (16 users)")
        title(ax, f"({tag}) {scene.upper()}")
        ax.margins(y=.28 if certificates else .12)
        clean(ax)
    axes[0].set_ylabel("Relative gap (%)" if certificates else "Achieved rate (bit/s/Hz)")
    method_legend(fig, methods)
    return fig, {"metric": metric, "display_multiplier": 100 if certificates else 1, "scenes": table}

def plot_rate_fairness(data: Data) -> tuple[plt.Figure, dict[str, Any]]:
    fig, ax = panels(columns=1, height=3.1)
    metrics = {}
    for method in ("joint", "full"):
        metrics[method] = {"rate_bit_per_s_Hz": values(data, "asu", "main", method, "SE").tolist(),
                           "minimum_user_bit_per_s_Hz": values(data, "asu", "main", method, "min_user_SE").tolist()}
    for i in range(12):
        ax.plot([metrics[m]["rate_bit_per_s_Hz"][i] for m in ("joint", "full")],
                [metrics[m]["minimum_user_bit_per_s_Hz"][i] for m in ("joint", "full")], color="#AAB1B7", lw=.8, zorder=1)
    for method in ("joint", "full"):
        ax.scatter(metrics[method]["rate_bit_per_s_Hz"], metrics[method]["minimum_user_bit_per_s_Hz"],
                   s=28, marker=METHOD_MARKERS[method], color=METHOD_COLORS[method], facecolors="white" if method == "joint" else METHOD_COLORS[method], lw=.9, label=METHOD_LABELS[method], zorder=3)
    ax.set_xlabel("Achieved rate (bit/s/Hz)")
    ax.set_ylabel("Minimum-user rate (bit/s/Hz)")
    title(ax, "ASU")
    ax.legend(frameon=False, loc="upper left")
    clean(ax)
    return fig, {"scene": "asu", "cases": 12, "methods": metrics}

def plot_historical_cost(data: Data) -> tuple[plt.Figure, dict[str, Any]]:
    lookup = {(r["case_id"], r["arm"]): r for r in data.history_rows}
    times = {arm: np.array([number(lookup[case, arm]["charged_actual"]) for case in data.cases]) for arm in ARMS}
    minimum = {arm: np.array([number(lookup[case, arm]["minimum_user_SE"]) for case in data.cases]) for arm in ARMS}
    fig, axes = panels(height=3.3)
    matched_distribution(axes[0], data, times, "Charged time (s)", "(a) Historical charged time")
    matched_distribution(axes[1], data, minimum, "Minimum-user rate (bit/s/Hz)", "(b) Historical user rates")
    axes[0].axvline(20, color=INK, ls=(0, (4, 3)), lw=.8)
    axes[0].set_xlim(0, max(21, max(float(v.max()) for v in times.values())*1.05))
    group_legend(fig)
    return fig, {"cases": 44, "cells": 220, "charged_allowance_seconds": 20, "case_order": data.cases,
                 "charged_seconds": {a: v.tolist() for a, v in times.items()}, "minimum_user_bit_per_s_Hz": {a: v.tolist() for a, v in minimum.items()}}

def history_values(data: Data) -> dict[str, Any]:
    inputs = data.inputs.json("historical/inputs.json")["inputs"]
    grid = np.linspace(4, 20, 65)
    result: dict[str, Any] = {"time_grid_seconds": grid.tolist(), "regimes": {}}
    for regime in REGIMES:
        result["regimes"][regime] = {}
        chosen = [item for item in inputs if item["regime"] == regime]
        require(len(chosen) == 11, f"Incomplete historical regime: {regime}")
        for arm in ARMS:
            histories, case_records = [], []
            for item in chosen:
                prefix = f'historical/cells/{item["id"]}-{arm}/'
                cell = data.inputs.json(prefix + "result.json")
                points = []
                for receipt in cell["receipts"]:
                    if receipt["timely"]:
                        raw = data.inputs.raw(prefix + receipt["file"])
                        require(sha(raw) == receipt["sha256"], "Historical receipt SHA-256 mismatch")
                        check = json.loads(raw)
                        value = float(exact(check["verification"]["lower_nats"]))/(4*np.log(2))
                        points.append((4 + number(receipt["completed_at"]) - number(cell["started_at"]), value))
                points.sort()
                require(bool(points), "A historical cell has no timely receipt")
                base = points[0][1]
                trajectory = np.array([max([v for tt, v in points if tt <= t], default=np.nan)-base for t in grid])
                histories.append(trajectory)
                case_records.append({"case_id": item["id"], "timely_receipt_points_seconds_and_rate": [list(p) for p in points],
                                     "gain_on_grid_bit_per_s_Hz": [float(x) if np.isfinite(x) else None for x in trajectory]})
            matrix = np.array(histories)
            count = np.sum(np.isfinite(matrix), axis=0)
            mean = np.divide(np.nansum(matrix, axis=0), count, out=np.full(65, np.nan), where=count > 0)
            result["regimes"][regime][arm] = {"cases": case_records, "contributing_cases": count.tolist(),
                "mean_gain_bit_per_s_Hz": [float(x) if np.isfinite(x) else None for x in mean]}
    return result

def plot_histories(data: Data) -> tuple[plt.Figure, dict[str, Any]]:
    metrics = history_values(data)
    fig, axes = panels(2, 2, height=5.1, sharex=True)
    for ax, regime, label, tag in zip(axes.flat, REGIMES, REGIME_LABELS, "abcd"):
        display_scale = 1e4 if regime == "snr30_narrow" else 1e6 if regime == "snr30_broad" else 1
        for i, arm in enumerate(ARMS):
            y = np.array([np.nan if v is None else v for v in metrics["regimes"][regime][arm]["mean_gain_bit_per_s_Hz"]])
            ax.plot(metrics["time_grid_seconds"], y*display_scale, color=ARM_COLORS[arm], marker=ARM_MARKERS[arm], markevery=(i, 12), ms=3.5,
                    ls=("-", "--", "-.", ":", (0, (5, 2)))[i], lw=1.1, label=LABELS[arm])
        title(ax, f"({tag}) {label}")
        unit = "×10⁻⁴ bit/s/Hz" if display_scale == 1e4 else "×10⁻⁶ bit/s/Hz" if display_scale == 1e6 else "bit/s/Hz"
        ax.set_ylabel(f"Mean gain ({unit})")
        ax.set_xticks([4, 8, 12, 16, 20])
        ax.set_xlim(4, 20)
        clean(ax)
    for ax in axes[-1]:
        ax.set_xlabel("Charged receipt-completion time (s)")
    fig.legend(*axes[0, 0].get_legend_handles_labels(), loc="outside upper center", ncol=3, frameon=False)
    metrics["display_multipliers"] = {"snr0_narrow": 1, "snr0_broad": 1, "snr30_narrow": 1e4, "snr30_broad": 1e6}
    return fig, metrics

def diagram_setup() -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(3.15, 2.35))
    fig.subplots_adjust(left=.02, right=.98, bottom=.025, top=.98)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    return fig, ax

def diagram_text(ax: plt.Axes, x: float, y: float, text: str, color: str = INK, size: float = 8, **kw: Any) -> None:
    ax.text(x, y, text, ha="center", va="center", color=color, fontsize=size, **kw)

def arrow(ax: plt.Axes, points: list[tuple[float, float]], color: str, dashed: bool = False) -> None:
    xs, ys = zip(*points)
    ax.plot(xs, ys, color=color, lw=1, ls=(0, (3, 2)) if dashed else "-", zorder=3)
    tip_base = tuple(.96*b + .04*a for a, b in zip(points[-2], points[-1]))
    ax.annotate("", xy=points[-1], xytext=tip_base, zorder=3,
                arrowprops={"arrowstyle": "-|>", "color": color, "lw": 1, "mutation_scale": 6, "shrinkA": 0, "shrinkB": 0})

def user_icon(ax: plt.Axes, x: float, y: float, color: str, label: str, label_y: float | None = None) -> None:
    ax.add_patch(Circle((x, y+.037), .013, fc=color, ec="white", lw=.4, zorder=6))
    ax.plot([x, x], [y+.021, y-.018], color=color, lw=2.1, zorder=6)
    ax.plot([x-.017, x, x+.018], [y-.045, y-.013, y-.045], color=color, lw=1.4, zorder=6)
    ax.plot([x-.019, x, x+.025], [y-.002, y+.01, y+.004], color=color, lw=1.1, zorder=6)
    ax.add_patch(Rectangle((x+.021, y+.002), .013, .032, fc="white", ec=color, lw=.75, zorder=6))
    diagram_text(ax, x, y-.077 if label_y is None else label_y, label, color, 8, zorder=7)

def building(ax: plt.Axes, x: float, y: float, w: float, h: float) -> None:
    d = .025
    ax.add_patch(Rectangle((x, y), w, h, fc="#E3E8EB", ec=GRAY, lw=.7, zorder=1))
    ax.add_patch(Polygon([(x, y+h), (x+d, y+h+d), (x+w+d, y+h+d), (x+w, y+h)], fc="#F7F8F9", ec=GRAY, lw=.65, zorder=1))
    ax.add_patch(Polygon([(x+w, y), (x+w+d, y+d), (x+w+d, y+h+d), (x+w, y+h)], fc="#CDD6DB", ec=GRAY, lw=.65, zorder=1))
    for xx in (x+w*.25, x+w*.62):
        for yy in (y+h*.25, y+h*.65):
            ax.add_patch(Rectangle((xx, yy), .023, .025, fc="white", ec=GRAY, lw=.35, zorder=2))

def diagram_box(ax: plt.Axes, x: float, y: float, w: float, h: float, label: str, color: str = INK) -> None:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=.006,rounding_size=.016", fc="white", ec=color, lw=.8, zorder=4))
    diagram_text(ax, x+w/2, y+h/2, label, color, zorder=5)

def plot_system_pairing(_: Data) -> tuple[plt.Figure, dict[str, Any]]:
    fig, ax = diagram_setup()
    diagram_text(ax, .5, .96, "Illustrative single-AP campus", size=8.5)
    ax.add_patch(Polygon([(.025, .26), (.10, .77), (.84, .79), (.98, .32), (.77, .20), (.23, .19)], fc="#F6F8F5", ec="#CBD6C8", lw=.65))
    ax.plot([.11, .39, .54, .85], [.27, .42, .59, .37], color="#E3E4DD", lw=7, zorder=0)
    building(ax, .05, .56, .15, .14)
    building(ax, .80, .56, .14, .14)
    for points, color in (([(.13, .33), (.50, .70)], BLUE), ([(.36, .42), (.50, .70)], BLUE),
                          ([(.69, .30), (.50, .70)], RED), ([(.89, .42), (.50, .70)], RED)):
        arrow(ax, points, color)
    arrow(ax, [(.13, .33), (.20, .58), (.50, .70)], BLUE, True)
    arrow(ax, [(.89, .42), (.80, .60), (.50, .70)], RED, True)
    ax.plot([.50, .50], [.61, .735], color=INK, lw=1.7, zorder=5)
    ax.plot([.405, .595], [.735, .735], color=INK, lw=1, zorder=5)
    for k in range(8):
        x = .409 + .026*k
        ax.plot([x, x], [.735, .782], color=INK, lw=1, zorder=5)
        ax.add_patch(Circle((x, .785), .007, fc="white", ec=INK, lw=.7, zorder=6))
    diagram_text(ax, .50, .855, "Eight-antenna example (M = 8)")
    for x, y, color, label in ((.13, .32, BLUE, "$u_1$"), (.36, .41, BLUE, "$u_2$"), (.69, .29, RED, "$u_3$"), (.89, .41, RED, "$u_4$")):
        user_icon(ax, x, y, color, label)
    ax.plot([.09, .17], [.17, .17], color=INK, lw=.9)
    diagram_text(ax, .30, .17, "Direct")
    ax.plot([.52, .60], [.17, .17], color=INK, lw=.9, ls=(0, (3, 2)))
    diagram_text(ax, .77, .17, "Reflected")
    diagram_text(ax, .25, .095, "$s=1$: $\\{u_1,u_2\\}$", BLUE)
    diagram_text(ax, .75, .095, "$s=2$: $\\{u_3,u_4\\}$", RED)
    diagram_text(ax, .50, .025, "Orthogonal resources; K = 2S")
    return fig, {"kind": "illustration", "measured_geometry": False, "access_points": 1, "illustrated_antennas": 8, "illustrated_users": 4, "illustrated_resources": 2}

def plot_system_mmse(_: Data) -> tuple[plt.Figure, dict[str, Any]]:
    fig, ax = diagram_setup()
    diagram_text(ax, .5, .962, "One pair on resource s", size=8.5)
    user_icon(ax, .085, .81, BLUE, r"$u,\ p_u$", .73)
    user_icon(ax, .085, .59, BLUE, r"$v,\ p_v$", .51)
    arrow(ax, [(.135, .817), (.465, .765)], BLUE)
    arrow(ax, [(.135, .597), (.465, .630)], BLUE)
    diagram_text(ax, .285, .852, "$\\mathbf{h}_{us}$", BLUE)
    diagram_text(ax, .285, .576, "$\\mathbf{h}_{vs}$", BLUE)
    ax.plot([.49, .49], [.57, .85], color=INK, lw=.9, zorder=5)
    for k in range(8):
        y = .583 + .036*k
        ax.plot([.477, .513], [y, y], color=INK, lw=.7, zorder=5)
        ax.add_patch(Circle((.473, y), .007, fc="white", ec=INK, lw=.6, zorder=6))
    diagram_text(ax, .75, .866, "AP, M = 8")
    arrow(ax, [(.52, .71), (.62, .71)], INK)
    diagram_box(ax, .63, .612, .32, .19, "Linear MMSE\n(no SIC)")
    diagram_text(ax, .73, .54, "Channels + powers")
    ax.plot([.025, .975], [.475, .475], color="#CBD3D9", lw=.65)
    diagram_text(ax, .5, .43, "Whitened scalar-rate calculation")
    diagram_box(ax, .035, .265, .44, .13, "Gains / correlation\n$g_u,g_v,r$", BLUE)
    diagram_box(ax, .57, .265, .39, .13, "Powers\n$p_u,p_v$")
    arrow(ax, [(.255, .257), (.365, .225)], BLUE)
    arrow(ax, [(.765, .257), (.65, .225)], INK)
    diagram_box(ax, .035, .065, .93, .16, "Recomputed-MMSE SINRs $\\gamma_u,\\gamma_v$\n$q_r=\\ln(1+\\gamma_u)+\\ln(1+\\gamma_v)$")
    diagram_text(ax, .5, .025, "Filters use the channel vectors.")
    return fig, {"kind": "illustration", "receiver": "linear MMSE, no SIC", "scalar_rate": "ln(1+gamma_u)+ln(1+gamma_v)", "illustrated_antennas": 8}

def render_check(fig: plt.Figure, name: str) -> dict[str, Any]:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.bbox
    text_items, clipping, fonts = [], [], []
    undrawn_tick_labels = set()
    for axes in fig.axes:
        for axis in (axes.xaxis, axes.yaxis):
            low, high = sorted(axis.get_view_interval())
            tolerance = (high-low)*1e-10
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not axis.get_visible() or tick.get_loc() < low-tolerance or tick.get_loc() > high+tolerance:
                    undrawn_tick_labels.update((tick.label1, tick.label2))
    for artist in fig.findobj(Text):
        if artist in undrawn_tick_labels or not artist.get_visible() or not artist.get_text().strip():
            continue
        label = artist.get_text()
        require(FORBIDDEN_TEXT.search(label) is None, f"Branding/internal label in {name}: {label!r}")
        fonts.append(artist.get_fontsize())
        box = artist.get_window_extent(renderer)
        # Tick labels of hidden shared axes can remain marked visible by older Matplotlib.
        if not np.all(np.isfinite(box.extents)):
            continue
        if box.x0 < canvas.x0-.7 or box.y0 < canvas.y0-.7 or box.x1 > canvas.x1+.7 or box.y1 > canvas.y1+.7:
            clipping.append({"text": label, "bbox_pixels": box.extents.tolist()})
        text_items.append({"text": label, "base_font_pt": artist.get_fontsize()})
    require(min(fonts) >= 8, f"Text below 8 pt in {name}: {min(fonts)}")
    require(not clipping, f"Text leaves the fixed canvas in {name}: {clipping}")
    return {"base_font_minimum_pt": min(fonts), "base_font_maximum_pt": max(fonts), "visible_text_items": len(text_items),
            "clipped_text_items": clipping, "branding_matches": [], "text": [t["text"] for t in text_items],
            "axes": [{"xscale": a.get_xscale(), "yscale": a.get_yscale(), "xlim": list(a.get_xlim()), "ylim": list(a.get_ylim()),
                      "xlabel": a.get_xlabel(), "ylabel": a.get_ylabel(), "title": a.get_title(loc="left")} for a in fig.axes]}

BUILDERS = {
    'rate-trajectories': lambda d: plot_components(d, True),
    'certification-gaps-detail': lambda d: plot_gaps(d, True),
    'matched-comparison-detail': lambda d: plot_matched(d, True),
    'seed-influence': plot_influence,
    'main-certification-counts': plot_certification_counts,
    'main-gap-distribution': lambda d: plot_ecdf(d),
    'main-runtime': plot_main_time,
    'curvature-diagnostic': plot_curvature,
    'scale-rates': lambda d: plot_scale(d),
    'scale-certificates': lambda d: plot_scale(d, True),
    'rate-fairness': plot_rate_fairness,
    'historical-cost-fairness': plot_historical_cost,
    'historical-checked-histories': plot_histories,
    'system-pairing': plot_system_pairing,
    'system-mmse': plot_system_mmse,
}
