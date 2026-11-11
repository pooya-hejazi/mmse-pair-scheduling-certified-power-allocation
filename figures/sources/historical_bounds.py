"""Scientific drawing and data-reading functions extracted from make_bound_figures.py (R5)."""

from __future__ import annotations

import ast

import csv

import io

import json

import math

import statistics

import zipfile

from collections import Counter

from dataclasses import dataclass

from fractions import Fraction

from pathlib import Path

from typing import Any

import historical_panels as publication

import matplotlib.pyplot as plt

from matplotlib.lines import Line2D

from matplotlib.patches import Patch

from matplotlib.ticker import FuncFormatter, NullLocator

import numpy as np

HERE = Path(__file__).resolve().parent

BUNDLE = HERE / "inputs" / "bound-inputs.zip"

PROVENANCE = HERE / "inputs" / "bound-input-provenance.json"

GROUPS = (("o1", 8), ("asu", 8), ("o1", 16), ("asu", 16))

GROUP_LABELS = ("O1\nK = 8", "ASU\nK = 8", "O1\nK = 16", "ASU\nK = 16")

BLUE, GRAY, INK, RED = publication.BLUE, publication.GRAY, publication.INK, publication.RED

METHOD_NAMES = ("Proposed bound", "Generic price repair")

HISTORY_CASES = ("o1-main-00", "o1-main-06", "asu-main-00", "asu-main-06")

HISTORY_LABELS = ("O1 / 01", "O1 / 07", "ASU / 01", "ASU / 07")

HISTORY_COLORS = (BLUE, "#356397", RED, "#956319")

HISTORY_MARKERS = ("o", "s", "^", "D")

sha, write_json, require = publication.sha, publication.write_json, publication.require

def fraction(value: Any) -> Fraction:
    result = Fraction(value)
    require(math.isfinite(float(result)), "Non-finite endpoint")
    return result

def boolean(value: Any) -> bool:
    require(value in (True, False, "True", "False"), f"Invalid Boolean: {value!r}")
    return value is True or value == "True"

def literal_list(value: Any) -> list[Any]:
    parsed = ast.literal_eval(value) if isinstance(value, str) else value
    require(isinstance(parsed, list), "Expected an error/timeout list")
    return parsed

def close(actual: Any, expected: Any, label: str, relative: float = 2e-12, absolute: float = 2e-16) -> None:
    a, b = float(actual), float(expected)
    require(math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=relative, abs_tol=absolute),
            f"Inconsistent {label}: {a!r} versus {b!r}")

class BoundInputs:
    def __init__(self) -> None:
        self.provenance = json.loads(PROVENANCE.read_bytes())
        raw = BUNDLE.read_bytes()
        require(sha(raw) == self.provenance["bundle"]["sha256"], "Bound input bundle hash mismatch")
        self.archive = zipfile.ZipFile(io.BytesIO(raw))
        self.records = {r["member"]: r for r in self.provenance["members"]}
        require(set(self.archive.namelist()) == set(self.records), "Bound bundle/provenance member sets differ")
        self.consumed: dict[str, dict[str, Any]] = {}

    def raw(self, member: str) -> bytes:
        raw = self.archive.read(member)
        record = self.records[member]
        require(sha(raw) == record["sha256"] and len(raw) == record["bytes"], f"Bound input member mismatch: {member}")
        self.consumed[member] = {k: record[k] for k in ("member", "bytes", "sha256")}
        return raw

    def json(self, member: str) -> Any:
        return json.loads(self.raw(member).decode("utf-8-sig"))

    def csv(self, member: str) -> list[dict[str, str]]:
        return list(csv.DictReader(io.StringIO(self.raw(member).decode("utf-8-sig"))))

@dataclass
class BoundData:
    inputs: BoundInputs
    freeze: dict[str, Any]
    summary: dict[str, Any]
    descriptive: dict[str, Any]
    rows: list[dict[str, Any]]
    history: list[dict[str, Any]]
    endpoints: list[dict[str, Any]]
    history_errors: list[dict[str, Any]]
    checks: dict[str, Any]

def indexed(rows: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    result = {r[key]: r for r in rows}
    require(len(result) == len(rows), f"Duplicate {label}")
    return result

def load_data(inputs: BoundInputs) -> BoundData:
    freeze = inputs.json("FROZEN.json")
    bindings = inputs.json("INPUT_MANIFEST.json")
    output_manifest = inputs.json("final/OUTPUT_MANIFEST.json")
    summary = inputs.json("final/summary.json")
    descriptive = inputs.json("analysis/descriptive.json")
    raw_rows = inputs.json("final/rows.json")
    csv_rows = inputs.csv("final/results.csv")
    rate_rows = inputs.csv("analysis/all-case-rates.csv")
    history_rows = inputs.csv("analysis/historical-modern-rates.csv")
    inputs.raw("BOUND_STUDY_REPORT.md")
    require(freeze["n_cases"] == 32 and summary["population"] == summary["evaluated"] == summary["rows"] == 32, "Incomplete all-case study")
    require(sha(inputs.raw("FROZEN.json")) == output_manifest["freeze_sha256"], "Freeze/output binding mismatch")
    require(sha(inputs.raw("final/OUTPUT_MANIFEST.json")) == descriptive["output_manifest_sha256"], "Descriptive/output binding mismatch")
    for member in ("INPUT_MANIFEST.json", "PROTOCOL.md"):
        require(sha(inputs.raw(member)) == freeze["source_sha256"][member], f"Frozen source binding mismatch: {member}")
    for member in inputs.records:
        if member.startswith("final/") and member != "final/OUTPUT_MANIFEST.json":
            require(sha(inputs.raw(member)) == output_manifest["files"][member.removeprefix("final/")], f"Completed-record binding mismatch: {member}")
    tables = [indexed(rr, "name", label) for rr, label in ((raw_rows, "exact rows"), (csv_rows, "results rows"),
               (rate_rows, "rate rows"), (descriptive["all_case_rates"], "descriptive rate rows"), (bindings["cases"], "input cases"))]
    names = set(tables[0])
    require(len(names) == 32 and all(set(t) == names for t in tables), "All-case population differs between inputs")
    require(Counter((r["scene"], int(r["K"])) for r in raw_rows) == Counter({("o1", 8): 12, ("asu", 8): 12, ("o1", 16): 4, ("asu", 16): 4}), "Scene/user-count population changed")
    target = fraction(freeze["certificate_gap_nats"])
    endpoints, histories, history_errors = [], [], []
    historical_checks = 0
    for name in sorted(names):
        row, csv_row, rate, descriptive_rate, binding = (t[name] for t in tables)
        require(row == inputs.json(f"final/{name}/row.json"), f"Aggregated/per-case row mismatch: {name}")
        require(row["binding"] == binding["binding"] and row["K"] == binding["K"] and row["S"]*2 == row["K"], f"Case binding mismatch: {name}")
        for field in ("scene", "name"):
            require(csv_row[field] == rate[field] == row[field], f"Identity mismatch in {name}/{field}")
        require(int(csv_row["K"]) == int(rate["K"]) == row["K"], f"User count mismatch: {name}")
        require(literal_list(csv_row["errors"]) == row["errors"], f"Errors were altered: {name}")
        new = inputs.json(f"final/{name}/new-checked.json")
        witness = inputs.json(f"final/{name}/new-witness.json")
        baseline = inputs.json(f"final/{name}/baseline-checked.json")
        # case_sha256 hashes canonical JSON; case_file_sha256 hashes the original
        # archive-member bytes. Link them through the sealed saved witness.
        unsealed = {k: v for k, v in witness.items() if k != "witness_sha256"}
        object_hash = sha(json.dumps(unsealed, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
        require(object_hash == witness["witness_sha256"] == new["witness_sha256"], f"Checked witness binding mismatch: {name}")
        require(new["case_sha256"] == witness["case_sha256"] and witness["binding"] == row["binding"], f"Checked channel identity mismatch: {name}")
        require(new["valid"] and baseline["valid"] and row["baseline_verified"], f"Saved receipt invalid: {name}")
        require(row["new_complete"] and new["metrics"]["dp_complete"] and new["metrics"]["channels_reconstructed"], f"Incomplete saved integral bound: {name}")
        anchor = fraction(row["anchor_lower_nats"])
        prior = fraction(row["old_full_lower_nats"])
        require(anchor > 0 and prior > 0, "Rate and headroom denominators must be positive")
        require(float(csv_row["anchor_lower_nats"]) == float(anchor) and float(csv_row["old_full_lower_nats"]) == float(prior), f"CSV anchor/prior endpoint mismatch: {name}")
        require(boolean(csv_row["new_complete"]) == row["new_complete"], f"CSV completeness flag mismatch: {name}")
        require(fraction(new["anchor_lower_nats"]) == anchor == fraction(row["baseline_lower_nats"]), f"Common-grid anchor mismatch: {name}")
        exact_endpoints: dict[str, Fraction] = {"grid_lower_nats": anchor, "prior_lower_nats": prior}
        for prefix, receipt, label in (("new", new, "proposed"), ("baseline", baseline, "generic")):
            for key in ("lower_nats", "upper_nats", "gap_nats"):
                value = fraction(row[f"{prefix}_{key}"])
                require(value == fraction(receipt[key]), f"Exact receipt/row mismatch: {name}/{prefix}/{key}")
                require(float(value) == float(csv_row[f"{prefix}_{key}"]), f"CSV endpoint differs: {name}/{prefix}/{key}")
                exact_endpoints[f"{label}_{key}"] = value
            lower, upper, gap = (exact_endpoints[f"{label}_{k}"] for k in ("lower_nats", "upper_nats", "gap_nats"))
            require(gap == upper-lower and gap > 0, f"Inconsistent/nonpositive displayed gap: {name}/{label}")
            certificate = gap <= target
            require(certificate == row[f"{prefix}_certificate"] == receipt["certificate_mathematical"] == boolean(csv_row[f"{prefix}_certificate"]), f"Certificate threshold decision mismatch: {name}/{label}")
            for clock in ("producer", "checker"):
                value = float(row[f"{prefix}_{clock}_seconds"])
                require(value >= 0 and math.isfinite(value), f"Invalid callable time: {name}")
                require(value == float(csv_row[f"{prefix}_{clock}_seconds"]), f"Timing CSV mismatch: {name}")
        lower, upper = exact_endpoints["proposed_lower_nats"], exact_endpoints["proposed_upper_nats"]
        close(csv_row["old_full_headroom_fraction"], (upper-prior)/prior, f"{name}/CSV prior headroom")
        baseline_upper = exact_endpoints["generic_upper_nats"]
        new_fixed, old_fixed = upper-anchor, baseline_upper-anchor
        require(old_fixed > 0 and new_fixed >= 0, "Invalid fixed-anchor gaps")
        exact_endpoints.update({"proposed_fixed_anchor_gap_nats": new_fixed, "generic_fixed_anchor_gap_nats": old_fixed,
            "fixed_anchor_reduction_fraction": 1-new_fixed/old_fixed,
            "achieved_gain_from_grid_nats": lower-anchor, "achieved_gain_from_grid_fraction": (lower-anchor)/anchor,
            "grid_headroom_nats": upper-anchor, "grid_headroom_fraction": (upper-anchor)/anchor,
            "achieved_gain_from_prior_nats": lower-prior, "achieved_gain_from_prior_fraction": (lower-prior)/prior,
            "prior_headroom_nats": upper-prior, "prior_headroom_fraction": (upper-prior)/prior,
            "final_gap_reduction_fraction": 1-exact_endpoints["proposed_gap_nats"]/exact_endpoints["generic_gap_nats"]})
        rate_bindings = {"Q_grid_nats": anchor, "Q_new_nats": lower, "Q_old_full_or_pricing_nats": prior,
            "delta_grid_nats": lower-anchor, "delta_old_full_nats": lower-prior,
            "relative_delta_grid": (lower-anchor)/anchor, "relative_delta_old_full": (lower-prior)/prior,
            "verified_final_gap_nats": upper-lower, "verified_grid_headroom_nats": upper-anchor,
            "verified_grid_headroom_fraction": (upper-anchor)/anchor, "verified_old_full_headroom_nats": upper-prior,
            "verified_old_full_headroom_fraction": (upper-prior)/prior,
            "matched_fixed_alpha_repair_minus_integral_nats": fraction(new["metrics"]["fixed_alpha_upper_nats"])-fraction(new["metrics"]["integral_upper_nats"]),
            "final_receipt_computation_seconds": row["new_producer_seconds"]+row["new_checker_seconds"]}
        for key, value in rate_bindings.items():
            close(rate[key], value, f"{name}/{key}")
            close(descriptive_rate[key], value, f"descriptive/{name}/{key}")
        require(boolean(rate["new_certificate"]) == row["new_certificate"] == descriptive_rate["new_certificate"], "Rate-table certificate flag differs")
        roots = row["curvature"]
        require(roots == new["metrics"], "Curvature row differs from the saved checked receipt")
        require(sum(roots[k] for k in ("quadrant_roots", "finite_box_only_roots", "generic_roots")) == row["K"]*(row["K"]-1)//2*row["S"] == roots["price_rows"], f"Incomplete pair/resource box counts: {name}")
        case_history = inputs.json(f"final/{name}/historical-checks.json")
        historical_checks += len(case_history)
        old = next(h for h in case_history if h["label"] == "old_full_or_pricing")
        require(old["valid_schedule"] and fraction(old["checked_lower_nats"]) == prior, "Prior allocation endpoint mismatch")
        input_history = {h["label"]: h for h in binding["history"]}
        for item in case_history:
            require(item["valid_schedule"], f"Invalid retained historical allocation: {name}/{item['label']}")
            require(item["sha256"] == input_history[item["label"]]["sha256"], "Historical source hash mismatch")
            record = {"name": name, "label": item["label"], "saved_status": item["saved_status"],
                      "saved_errors": item["saved_errors"], "saved_verification_timeouts": item["saved_verification_timeouts"],
                      "valid_retained_allocation": item["valid_schedule"]}
            history_errors.append(record)
            if not item["label"].startswith("modern_"):
                continue
            require(item["common_anchor_identical"] is True and item["input_sha256"] == row["binding"]["case_file_sha256"], f"Historical same-channel/common-anchor mismatch: {name}/{item['method']}")
            h_lower = fraction(item["checked_lower_nats"])
            delta = lower-h_lower
            histories.append({"name": name, "method": item["method"], "case_sha256": item["input_sha256"],
                "same_common_anchor": True, "rate_nats": float(h_lower), "rate_nats_exact": str(h_lower),
                "delta_new_minus_modern_nats": float(delta), "delta_new_minus_modern_nats_exact": str(delta),
                "delta_new_minus_modern_SE": float(delta)/(row["S"]*math.log(2)), "fraction_new_minus_modern": float(delta/h_lower),
                "saved_charged": item["saved_charged"], "saved_elapsed": item["saved_elapsed"],
                "saved_allowance": item["saved_allowance"],
                "saved_errors": item["saved_errors"], "saved_timeouts": item["saved_verification_timeouts"]})
        case_index = int(name.rsplit("-", 1)[-1])+1
        displayed_values = {k: float(v) for k, v in exact_endpoints.items()}
        # Preserve the archived descriptive convention: convert the ratio to
        # binary64, then subtract from one. Exact fractions remain alongside it.
        displayed_values["fixed_anchor_reduction_fraction"] = 1-float(new_fixed/old_fixed)
        endpoints.append({"name": name, "scene": row["scene"], "K": row["K"], "S": row["S"],
            "display_case": f"{row['scene'].upper()} / K={row['K']} / {case_index:02d}",
            "exact": {k: str(v) for k, v in exact_endpoints.items()}, "values": displayed_values,
            "proposed_certificate": exact_endpoints["proposed_gap_nats"] <= target,
            "generic_certificate": exact_endpoints["generic_gap_nats"] <= target,
            "new_complete": row["new_complete"], "new_status": row["new_status"], "errors": list(row["errors"]),
            "times_seconds": {f"{label}_{clock}": row[f"{prefix}_{clock}_seconds"] for prefix, label in (("new", "proposed"), ("baseline", "generic")) for clock in ("producer", "checker")},
            "producer_cap_exceeded": {label: row[f"{prefix}_producer_seconds"] > freeze["producer_cap"] for prefix, label in (("new", "proposed"), ("baseline", "generic"))},
            "checker_cap_exceeded": {label: row[f"{prefix}_checker_seconds"] > freeze["checker_cap"] for prefix, label in (("new", "proposed"), ("baseline", "generic"))},
            "box_counts": {"quadrant": roots["quadrant_roots"], "finite_box_only": roots["finite_box_only_roots"], "generic": roots["generic_roots"]},
            "binding": row["binding"]})
    require(len(histories) == len(history_rows) == len(descriptive["modern_rows"]) == 20, "The physical historical comparison must contain 20 records")
    require({h["name"] for h in histories} == set(HISTORY_CASES), "Historical comparison includes a different physical cohort")
    for source, label in ((history_rows, "historical CSV"), (descriptive["modern_rows"], "descriptive history")):
        lookup = {(h["name"], h["method"]): h for h in source}
        require(len(lookup) == 20, f"Duplicate {label} rows")
        for item in histories:
            saved = lookup[item["name"], item["method"]]
            require(boolean(saved["same_common_anchor"]), f"Common anchor flag lost: {label}")
            for key in ("rate_nats", "delta_new_minus_modern_nats", "delta_new_minus_modern_SE", "fraction_new_minus_modern", "saved_charged", "saved_elapsed"):
                close(saved[key], item[key], label + "/" + key)
            require(literal_list(saved["saved_errors"]) == item["saved_errors"] and literal_list(saved["saved_timeouts"]) == item["saved_timeouts"], "Historical error/timeout records differ")
    require(historical_checks == 84, "Expected 84 retained historical allocation checks")
    data = BoundData(inputs, freeze, summary, descriptive, raw_rows, histories, endpoints, history_errors,
        {"exact_endpoint_identities": 64, "common_grid_anchors": 32, "physical_historical_rows": 20,
         "physical_same_channel_and_anchor_checks": 20, "historical_retained_allocations": 84})
    validate_summary(data)
    return data

def stats(values: list[float]) -> dict[str, Any]:
    ordered = sorted(float(v) for v in values)
    require(ordered and all(math.isfinite(v) for v in ordered), "Empty/non-finite descriptive endpoint")

    def quantile(probability: float) -> float:
        position = (len(ordered)-1)*probability
        index = int(position)
        return ordered[index] if index+1 == len(ordered) else ordered[index]+(ordered[index+1]-ordered[index])*(position-index)

    return {"n": len(ordered), "minimum": ordered[0], "maximum": ordered[-1], "mean": statistics.mean(ordered),
            "median": quantile(.5), "p10": quantile(.1), "p90": quantile(.9)}

def group_summary(rows: list[dict[str, Any]], freeze: dict[str, Any]) -> dict[str, Any]:
    result = {"n": len(rows), "certificates_new": sum(r["proposed_certificate"] for r in rows),
              "certificates_baseline": sum(r["generic_certificate"] for r in rows),
              "complete_new": sum(r["new_complete"] for r in rows), "errors": sum(bool(r["errors"]) for r in rows),
              "error_entries": sum(len(r["errors"]) for r in rows),
              "error_cases": sum(bool(r["errors"]) for r in rows),
              "gain_from_grid_at_least_one_percent": sum(fraction(r["exact"]["achieved_gain_from_grid_fraction"]) >= fraction(str(freeze["material_rate_gain_fraction"])) for r in rows),
              "gain_from_prior_at_least_one_percent": sum(fraction(r["exact"]["achieved_gain_from_prior_fraction"]) >= fraction(str(freeze["material_rate_gain_fraction"])) for r in rows),
              "quadrant_boxes": sum(r["box_counts"]["quadrant"] for r in rows),
              "finite_box_only": sum(r["box_counts"]["finite_box_only"] for r in rows),
              "generic_boxes": sum(r["box_counts"]["generic"] for r in rows)}
    for destination, value in (("new_gap_nats", "proposed_gap_nats"), ("baseline_gap_nats", "generic_gap_nats"),
            ("fixed_anchor_gap_reduction", "fixed_anchor_reduction_fraction"),
            ("final_gap_reduction", "final_gap_reduction_fraction"),
            ("achieved_gain_from_grid_fraction", "achieved_gain_from_grid_fraction"),
            ("achieved_gain_from_prior_fraction", "achieved_gain_from_prior_fraction"),
            ("old_full_remaining_headroom_fraction", "prior_headroom_fraction"),
            ("grid_remaining_headroom_fraction", "grid_headroom_fraction")):
        result[destination] = stats([r["values"][value] for r in rows])
    for clock in ("producer", "checker"):
        for label, suffix in (("proposed", "new"), ("generic", "baseline")):
            result[f"{clock}_seconds_{suffix}"] = stats([r["times_seconds"][f"{label}_{clock}"] for r in rows])
    result["final_call_total_seconds_new"] = stats([r["times_seconds"]["proposed_producer"]+r["times_seconds"]["proposed_checker"] for r in rows])
    result["final_call_total_seconds_baseline"] = stats([r["times_seconds"]["generic_producer"]+r["times_seconds"]["generic_checker"] for r in rows])
    return result

def all_groups(data: BoundData) -> dict[str, Any]:
    subsets = {"all": data.endpoints}
    subsets.update({s: [r for r in data.endpoints if r["scene"] == s] for s in ("o1", "asu")})
    subsets.update({f"K{k}": [r for r in data.endpoints if r["K"] == k] for k in (8, 16)})
    subsets.update({f"{s}-K{k}": [r for r in data.endpoints if (r["scene"], r["K"]) == (s, k)] for s, k in GROUPS})
    return {name: group_summary(rows, data.freeze) for name, rows in subsets.items()}

def validate_summary(data: BoundData) -> None:
    computed = all_groups(data)
    exact_fields = 0
    for group, saved in data.summary["groups"].items():
        result = computed[group]
        for key, value in saved.items():
            if isinstance(value, dict):
                for stat, expected in value.items():
                    require(result[key][stat] == expected, f"Saved summary value changed: {group}/{key}/{stat}")
                    exact_fields += 1
            else:
                require(result[key] == value, f"Summary count mismatch: {group}/{key}")
                exact_fields += 1
    for scene in ("o1", "asu"):
        result = computed[scene]
        saved = data.descriptive["data_suitability"][scene]
        total = result["quadrant_boxes"]+result["finite_box_only"]+result["generic_boxes"]
        require(total == saved["total_pair_boxes"] and result["quadrant_boxes"] == saved["whole_quadrant_boxes"] and result["quadrant_boxes"]+result["finite_box_only"] == saved["certified_full_boxes"], "Finite-box applicability counts differ")
        close((result["quadrant_boxes"]+result["finite_box_only"])/total, saved["full_box_qualifying_fraction"], "Pooled full-box fraction")
    data.checks["saved_summary_fields_exactly_equal"] = exact_fields

def group_rows(data: BoundData, group: tuple[str, int]) -> list[dict[str, Any]]:
    return sorted([r for r in data.endpoints if (r["scene"], r["K"]) == group], key=lambda r: r["name"])

def display_positions(data: BoundData) -> tuple[list[dict[str, Any]], np.ndarray, list[float], list[float]]:
    rows, positions, centers, boundaries = [], [], [], []
    start = 0
    for group in GROUPS:
        selected = group_rows(data, group)
        positions.extend(range(start, start+len(selected)))
        centers.append(start+(len(selected)-1)/2)
        rows.extend(selected)
        start += len(selected)+2
        boundaries.append(start-1.5)
    return rows, np.asarray(positions, dtype=float), centers, boundaries[:-1]

def power_label(value: float, _: Any = None) -> str:
    if value <= 0:
        return f"{value:g}"
    exponent = int(round(math.log10(value)))
    if not math.isclose(value, 10**exponent, rel_tol=1e-8):
        return f"{value:g}"
    if exponent == 0:
        return "1"
    superscript = str(exponent).translate(str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹"))
    return "10" + superscript

def log_scale(ax: plt.Axes, axis: str, limits: tuple[float, float], ticks: list[float]) -> None:
    getattr(ax, f"set_{axis}scale")("log")
    getattr(ax, f"set_{axis}lim")(*limits)
    getattr(ax, f"set_{axis}ticks")(ticks)
    target = ax.xaxis if axis == "x" else ax.yaxis
    target.set_major_formatter(FuncFormatter(power_label))
    target.set_minor_locator(NullLocator())

def method_handles(include_misses: bool = False) -> list[Line2D]:
    result = [Line2D([], [], color=BLUE, marker="o", ls="none", ms=4.5, label=METHOD_NAMES[0]),
              Line2D([], [], color=GRAY, marker="s", mfc="white", ls="none", ms=4.5, label=METHOD_NAMES[1])]
    if include_misses:
        result.append(Line2D([], [], color=RED, marker="o", mfc="white", ls="none", ms=5.5, label="Proposed misses"))
    return result

def plot_comparison(data: BoundData, groups: dict[str, Any]) -> tuple[plt.Figure, dict[str, Any]]:
    fig = plt.figure(figsize=(6.3, 2.6))
    ax = fig.add_axes((.105, .24, .49, .58))
    table = fig.add_axes((.655, .19, .33, .64))
    table.set(xlim=(0, 1), ylim=(0, 1))
    rows, x, centers, boundaries = display_positions(data)
    generic = np.array([r["values"]["generic_gap_nats"] for r in rows])
    proposed = np.array([r["values"]["proposed_gap_nats"] for r in rows])
    for xx, base, new in zip(x, generic, proposed):
        ax.plot([xx-.09, xx+.09], [base, new], color="#C3CAD0", lw=.65, zorder=1)
    ax.scatter(x-.09, generic, marker="s", facecolors="white", edgecolors=GRAY, s=13, lw=.7, zorder=3)
    ax.scatter(x+.09, proposed, marker="o", color=BLUE, s=13, ec="white", lw=.25, zorder=4)
    misses = np.array([not r["proposed_certificate"] for r in rows])
    ax.scatter(x[misses]+.09, proposed[misses], marker="o", facecolors="none", edgecolors=RED, s=32, lw=.9, zorder=5)
    target = float(fraction(data.freeze["certificate_gap_nats"]))
    ax.axhline(target, color=INK, ls=(0, (4, 3)), lw=.85, zorder=2)
    ax.text(.02, target*1.7, "0.01-nat target", transform=ax.get_yaxis_transform(), fontsize=8, va="bottom",
            bbox={"facecolor": "white", "edgecolor": "none", "pad": .5})
    for boundary in boundaries:
        ax.axvline(boundary, color="#E0E4E7", lw=.65, zorder=0)
    log_scale(ax, "y", (1e-12, 30), [1e-12, 1e-9, 1e-6, 1e-3, 1])
    ax.set_xlim(-1.2, max(x)+1.2)
    ax.set_xticks(centers, GROUP_LABELS, fontsize=8)
    ax.set_ylabel("Final gap U − L (nats)", fontsize=8.5)
    publication.title(ax, "(a) Paired final gaps")
    publication.clean(ax)
    table.axis("off")
    table.set_title("(b) Target certificates", loc="left", pad=8)
    table.text(.54, .94, "Proposed\nbound", ha="center", va="top", fontsize=8)
    table.text(.84, .94, "Generic\nprice repair", ha="center", va="top", fontsize=8)
    ys = (.64, .50, .36, .22, .08)
    keys = [f"{s}-K{k}" for s, k in GROUPS] + ["all"]
    labels = [f"{s.upper()}, K={k}" for s, k in GROUPS] + ["All cases"]
    for y, key, label in zip(ys, keys, labels):
        item = groups[key]
        table.text(0, y, label, va="center", fontsize=8)
        table.text(.54, y, f"{item['certificates_new']}/{item['n']}", color=BLUE, ha="center", va="center", fontsize=8.5)
        table.text(.84, y, f"{item['certificates_baseline']}/{item['n']}", color=GRAY, ha="center", va="center", fontsize=8.5)
    table.plot([0, .99], [.725, .725], transform=table.transAxes, color="#C7CDD2", lw=.6)
    table.plot([0, .99], [.15, .15], transform=table.transAxes, color="#C7CDD2", lw=.6)
    reduction = groups["all"]["fixed_anchor_gap_reduction"]["median"]*100
    table.text(.5, -.05, "Fixed-anchor $U-L_{\\mathrm{grid}}$\n" + f"median reduction: {reduction:.2f}%", ha="center", va="top", fontsize=8)
    fig.legend(handles=method_handles(True), loc="upper center", ncol=3, frameon=False, fontsize=8.5,
               columnspacing=1.1, handletextpad=.45, bbox_to_anchor=(.5, 1.0))
    return fig, {"case_order": [r["name"] for r in rows], "x_positions": x.tolist(),
        "proposed_final_gap_nats": proposed.tolist(), "generic_final_gap_nats": generic.tolist(),
        "proposed_miss_mask": misses.tolist(), "target_nats": target, "success_table_groups": keys,
        "fixed_anchor_median_reduction_percent": reduction,
        "fixed_anchor_note_definition": "median_i[100 * (1 - (U_proposed_i-L_grid_i)/(U_generic_i-L_grid_i))]"}

def categorical_axis(ax: plt.Axes) -> None:
    ax.set_xticks(range(4), GROUP_LABELS, fontsize=8)
    ax.set_xlim(-.55, 3.55)
    publication.clean(ax)

def plot_detail(data: BoundData, groups: dict[str, Any]) -> tuple[plt.Figure, dict[str, Any]]:
    fig, axes = plt.subplots(3, 2, figsize=(6.3, 7.8), layout="constrained")
    a, b, c, d, e, f = axes.flat
    panel_metrics: dict[str, Any] = {"case_order": [], "fixed_anchor_reductions_percent": [],
        "achieved_from_grid_percent": [], "possible_from_grid_percent": [], "timings_seconds": {},
        "box_applicability": {}, "same_channel_historical_rows": data.history}
    for gi, group in enumerate(GROUPS):
        rows = group_rows(data, group)
        offsets = np.linspace(-.28, .28, len(rows))
        reduction = np.array([r["values"]["fixed_anchor_reduction_fraction"]*100 for r in rows])
        a.scatter(gi+offsets, reduction, s=19, color=(BLUE, RED, BLUE, RED)[gi], marker=("o", "^", "s", "D")[gi], ec="white", lw=.3, zorder=3)
        gain = np.array([r["values"]["achieved_gain_from_grid_fraction"]*100 for r in rows])
        possible = np.array([r["values"]["grid_headroom_fraction"]*100 for r in rows])
        for x, lo, hi in zip(gi+offsets, gain, possible):
            b.plot([x-.025, x+.025], [lo, hi], color="#B4BEC6", lw=.7, zorder=1)
        b.scatter(gi+offsets-.025, gain, marker="o", color=BLUE, s=17, ec="white", lw=.25, zorder=3)
        b.scatter(gi+offsets+.025, possible, marker="s", facecolors="none", edgecolors=GRAY, s=22, lw=.75, zorder=2)
        panel_metrics["case_order"].extend(r["name"] for r in rows)
        panel_metrics["fixed_anchor_reductions_percent"].extend(reduction.tolist())
        panel_metrics["achieved_from_grid_percent"].extend(gain.tolist())
        panel_metrics["possible_from_grid_percent"].extend(possible.tolist())
        for ax, clock in ((c, "producer"), (d, "checker")):
            proposed = np.array([r["times_seconds"][f"proposed_{clock}"] for r in rows])
            generic = np.array([r["times_seconds"][f"generic_{clock}"] for r in rows])
            for x, new, base in zip(gi+offsets, proposed, generic):
                ax.plot([x-.025, x+.025], [new, base], color="#B4BEC6", lw=.7, zorder=1)
            ax.scatter(gi+offsets-.025, proposed, color=BLUE, marker="o", s=18, ec="white", lw=.25, zorder=3)
            ax.scatter(gi+offsets+.025, generic, marker="s", facecolors="white", edgecolors=GRAY, s=21, lw=.7, zorder=2)
            panel_metrics["timings_seconds"].setdefault(clock, {}).setdefault("proposed", []).extend(proposed.tolist())
            panel_metrics["timings_seconds"].setdefault(clock, {}).setdefault("generic", []).extend(generic.tolist())
    median = groups["all"]["fixed_anchor_gap_reduction"]["median"]*100
    a.axhline(median, color=INK, ls=(0, (4, 3)), lw=.85)
    a.text(.035, .08, f"Pooled median {median:.2f}%", transform=a.transAxes, fontsize=8)
    a.set_ylim(0, 105)
    a.set_yticks([0, 25, 50, 75, 100])
    a.set_ylabel("Fixed-anchor reduction (%)")
    publication.title(a, "(a) Upper-bound tightening")
    categorical_axis(a)
    log_scale(b, "y", (1e-9, 12), [1e-9, 1e-6, 1e-3, 1])
    threshold = data.freeze["material_rate_gain_fraction"]*100
    b.axhline(threshold, color=INK, ls=(0, (4, 3)), lw=.8)
    b.text(.02, threshold*1.35, "1% reference", transform=b.get_yaxis_transform(), va="bottom", fontsize=8)
    b.set_ylabel("Gain from grid (%)")
    b.legend(handles=[Line2D([], [], marker="o", color=BLUE, ls="none", ms=4, label="Achieved"),
                      Line2D([], [], marker="s", mfc="none", color=GRAY, ls="none", ms=4, label="Certified headroom")],
             frameon=False, loc="center left", fontsize=8, handletextpad=.5)
    publication.title(b, "(b) Rate gain and headroom")
    categorical_axis(b)
    log_scale(c, "y", (.075, 12), [.1, 1, 10])
    c.axhline(data.freeze["producer_cap"], color=INK, ls=(0, (4, 3)), lw=.8)
    c.set_ylabel("Producer call (s)")
    d.set_ylim(0, 1.85)
    d.set_yticks([0, .5, 1, 1.5])
    d.set_ylabel("Checker call (s)")
    for ax, tag, clock in ((c, "c", "producer"), (d, "d", "checker")):
        publication.title(ax, f"({tag}) Final {clock} time")
        categorical_axis(ax)
    c.legend(handles=method_handles(), frameon=False, loc="upper left", fontsize=8, handletextpad=.5)
    new_t = groups["all"]["producer_seconds_new"]["median"]
    base_t = groups["all"]["producer_seconds_baseline"]["median"]
    new_c = groups["all"]["checker_seconds_new"]["median"]
    base_c = groups["all"]["checker_seconds_baseline"]["median"]
    panel_metrics["pooled_median_seconds"] = {"producer": {"proposed": new_t, "generic": base_t}, "checker": {"proposed": new_c, "generic": base_c}}
    styles = (("quadrant_boxes", "Whole-quadrant", publication.PURPLE, ""),
              ("finite_box_only", "Finite-box only", BLUE, ""), ("generic_boxes", "Generic", "#E2E7EB", "///"))
    for si, scene in enumerate(("o1", "asu")):
        item = groups[scene]
        total = sum(item[k] for k, *_ in styles)
        left = 0.
        for key, _, color, hatch in styles:
            percent = 100*item[key]/total
            e.barh(si, percent, left=left, height=.48, color=color, edgecolor="white", lw=.5, hatch=hatch)
            left += percent
        qualified = item["quadrant_boxes"]+item["finite_box_only"]
        e.text(0, si-.36, f"{qualified}/{total} qualify", fontsize=8, va="bottom")
        panel_metrics["box_applicability"][scene] = {"total": total, "whole_quadrant": item["quadrant_boxes"],
            "finite_box_only": item["finite_box_only"], "generic": item["generic_boxes"], "qualified": qualified,
            "qualified_percent": 100*qualified/total}
    e.set_yticks([0, 1], ["O1", "ASU"])
    e.set_ylim(1.45, -.8)
    e.set_xlim(0, 100)
    e.set_xticks([0, 50, 100])
    e.set_xlabel("Pair–resource boxes (%)")
    e.legend(handles=[Patch(facecolor=color, hatch=hatch, edgecolor=GRAY, label=label) for _, label, color, hatch in styles],
             ncol=1, frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -.28), borderaxespad=0, handlelength=1.2)
    publication.title(e, "(e) Finite-box applicability")
    publication.clean(e, "x")
    lookup = {(r["name"], r["method"]): r for r in data.history}
    history_handles = []
    for ci, (name, label, color, marker) in enumerate(zip(HISTORY_CASES, HISTORY_LABELS, HISTORY_COLORS, HISTORY_MARKERS)):
        x = [lookup[name, method]["delta_new_minus_modern_nats"] for method in publication.ARMS]
        require(all(v > 0 for v in x), "The current historical rate display requires positive signed increments")
        f.scatter(x, np.arange(5)+(ci-1.5)*.10, marker=marker, color=color, s=21, ec="white", lw=.3, zorder=3)
        history_handles.append(Line2D([], [], marker=marker, color=color, ls="none", ms=4, label=label))
    log_scale(f, "x", (1e-11, .5), [1e-10, 1e-6, 1e-2])
    f.set_yticks(range(5), [publication.LABELS[a].replace("Proposed transfer", "Proposed\ntransfer") for a in publication.ARMS], fontsize=8)
    f.set_ylim(4.6, -1.65)
    f.set_xlabel("New − recorded rate\n(nats; logarithmic scale)", fontsize=8.5)
    f.legend(handles=history_handles, ncol=2, frameon=False, fontsize=8, loc="upper center", handlelength=.7, handletextpad=.3, columnspacing=.6)
    publication.title(f, "(f) Four same-channel cases")
    publication.clean(f, "x")
    return fig, panel_metrics
