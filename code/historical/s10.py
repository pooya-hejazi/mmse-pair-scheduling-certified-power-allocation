"""Replay saved October 31 results from the public S10 study members."""
from collections import defaultdict
import json
import math
import runpy
import zipfile

import numpy as np


def read(path):
    return json.loads(path.read_bytes())


def require(test, label):
    if not test:
        raise ValueError("S10 replay mismatch: " + label)


def fixed_csi(base, tmp):
    source = runpy.run_path(str(base / "forward.py"))
    study = base / "run-01"
    saved = read(study / "analysis.json")
    rows = source["collect_rows"](study, saved["stage_status"])
    require(len(rows) == 1440 and rows == read(study / "all-rows.json"), "fixed-CSI checkpoints")
    result = tmp / "fixed-csi"
    result.mkdir()
    source["summarize_rows"](result, saved["stage_status"], rows)
    require(read(result / "analysis.json") == saved, "fixed-CSI complete summary, intervals and secondary tables")
    return {k: saved[k] for k in ("expected_cells", "complete_pairs", "failure_cells", "mean",
                                   "student_t_CI95", "paired_bootstrap_CI95", "confirmatory_superiority")}


def four_ap(base, tmp, run, seconds):
    result = tmp / "four-ap-verification.json"
    run(base / "postprocessing" / "verify_nominal_artifacts.py", "--root", base.parents[1], "--geometry", "all",
        "--output", result, "--max-seconds", seconds)
    checked = read(result)
    saved = read(base / "postprocessing" / "actual-verification.json")
    keys = ("expected_cells", "expected_cases", "eligible_schedules_checked", "geometry_pair_rows_checked",
            "global_upper_bounds_independently_reproved")
    require(checked["status"] == "PASS" and not checked["errors"] and all(checked[k] == saved[k] for k in keys),
            "four-AP saved schedules, receipts and channel geometry")
    campaign = base / "campaign-run"
    primary = tmp / "four-ap-primary.json"
    conf = base / "confirmation"
    run(conf / "nominal_analysis.py", "--results", conf / "run-01-results", "--output", primary)
    fresh, prior = read(primary), read(campaign / "primary-analysis.json")
    require(len(fresh["complete_ledger"]) == 176 and fresh["primary"] == prior["primary"] and
            fresh["failure_accounting"] == prior["failure_accounting"], "four-AP operational primary")
    strict = campaign / "strict-return-sensitivity.json"
    reference = read(strict)
    strict.rename(tmp / "stored-strict-return.json")
    run(base / "strict_return_sensitivity.py")
    require(read(strict) == reference, "four-AP strict-return sensitivity")
    return {**{k: checked[k] for k in keys}, "primary": fresh["primary"], "normal_return": reference["paired_sensitivity"]}


def development(root):
    learned = read(root / "innovation" / "learned-results.json")
    groups = defaultdict(list)
    keys = ("noise", "T", "split", "method")
    for row in learned["rows"]:
        groups[tuple(row[k] for k in keys)].append(row)
    require(len(groups) == len(learned["summary"]) == 54, "learned stopping settings")
    no_gain = 0
    for summary in learned["summary"]:
        items = groups[tuple(summary[k] for k in keys)]
        require(len(items) == summary["N"] and sum(x["early"] for x in items) == summary["early_stops"] and
                sum(x["false_certificate"] for x in items) == summary["false_certificates"] and
                math.isclose(np.mean([x["net_se"] for x in items]), summary["mean_net_se"], rel_tol=0, abs_tol=1e-12),
                "learned stopping outcomes")
        fixed = {k: np.mean([r["fixed_" + k] for r in items]) for k in ("4", "8", "16")}
        require(all(math.isclose(v, summary["fixed_means"][k], rel_tol=0, abs_tol=1e-12) for k, v in fixed.items()),
                "fixed pilot budget rates")
        if summary["split"] == "iid_development" and summary["method"] == "learned_contrast":
            no_gain += int(summary["mean_net_se"] <= max(fixed.values()) + 1e-12)
    require(no_gain == 9, "learned policy versus the best fixed development budget")
    comparison = root / "comparison"
    summary = read(comparison / "summary.json")
    rows = read(comparison / "results.json")["rows"]
    require([r for r in rows if r["mode"] == "power"] == summary["power_rows"], "minimum-power records")
    for context in summary["contexts"]:
        arms = {(r["sample"], r["arm"]): r["result"] for r in rows
                if r["mode"] == "info" and r["context"] == context["context"] and r["status"] == "COMPLETED"}
        diff = np.array([arms[i, "joint"]["actual_bandwidth_SE"] - arms[i, "weakest"]["actual_bandwidth_SE"] for i in range(8)])
        rng = np.random.default_rng(132000)
        boot = diff[rng.integers(0, 8, (2000, 8))].mean(axis=1)
        paired = context["paired"]["joint-weakest_actual_bandwidth_SE"]
        require(paired["N"] == 8 and math.isclose(diff.mean(), paired["mean"], rel_tol=0, abs_tol=1e-12) and
                np.allclose(np.quantile(boot, [.025, .975]), paired["CI95"], rtol=0, atol=1e-12), "joint/weakest contrast")
        require(sum(v["certificate_stopped"] for v in arms.values()) == 0, "certificate stops")
    cases = [r["result"] for r in read(root / "headroom" / "frozen-results.json")["rows"]]
    stored = read(root / "headroom" / "frozen-summary.json")
    denom = sum(r["no_probe_net"] for r in cases)
    for field, label in (("B_exact", "exact_grid_decision_only_positive_opportunity"), ("B_LP", "LP_positive_opportunity_upper")):
        require(math.isclose(sum(max(0, r[field]) for r in cases) / denom, stored[label], rel_tol=0, abs_tol=1e-12), label)
    require(len(cases) == 32 and sum(r["B_exact"] <= 0 for r in cases) == stored["no_acquisition_certificates_exact"],
            "finite-grid no-acquisition count")
    return {"learned_settings_checked": len(groups), "no_gain_development_settings": no_gain,
            "paired_contexts_checked": len(summary["contexts"]), "power_rows_bound_to_summary": len(summary["power_rows"]),
            "headroom": {k: stored[k] for k in ("N", "exact_grid_decision_only_positive_opportunity",
                                                 "LP_positive_opportunity_upper", "no_acquisition_certificates_exact")}}


def gpu(research):
    root = research / "completion-20261031" / "gpu"
    checks = runpy.run_path(str(root / "checks.py"))
    prior = read(root / "csr-repair" / "verification.json")
    original = {r["users"]: r for r in read(research / "gpu" / "results.json")["rows"]}
    for name in ("gpu-8", "gpu-16", "gpu-32", "repair-8"):
        require(read(root / (name + ".execution.json"))["status"] == "WALL_TIMEOUT", "original GPU timeout")
    feasible = {}
    for row in prior["rows"]:
        n = row["users"]
        _, A, _, _, _ = checks["old"].matrices(n)
        with np.load(research / "gpu" / f"instance-{n}.npz", allow_pickle=False) as case:
            saved_row = original[n]
            target = saved_row["minimum_power_target_Mbps"]
            require(math.isclose(target, .95 * saved_row["fixed_power_MILP"]["rate_Mbps"], rel_tol=0, abs_tol=1e-10),
                    "minimum-power throughput target")
            for name in ("fixed_power_MILP", "joint_power_MILP", "minimum_power_MILP"):
                sol = saved_row[name]
                x = np.zeros(len(case["q"]))
                x[sol["selected"]] = 1
                limits = checks["old"].feasibility(x, A, case["power"], saved_row["power_budget_W"], True,
                                                   case["q"], target if name == "minimum_power_MILP" else None)
                require(limits["valid"] and abs(case["q"] @ x - sol["rate_Mbps"]) < 1e-6 and
                        abs(case["power"] @ x - sol["power_W"]) < 1e-6, f"{name} saved allocation")
            for filename, keys in ((root / f"cpu-{n}-vectors.npz", ("x",)),
                                   (root / "csr-repair" / f"gpu-{n}-vectors.npz", ("last", "average"))):
                with np.load(filename, allow_pickle=False) as v:
                    for key in keys:
                        got = checks["evaluate"](v[key], v["lam"], float(v["mu"]), A, case["q"], case["power"], .1 * n)
                        saved = row["CPU"] if key == "x" else row["GPU_candidates"][key]
                        for field in saved:
                            if isinstance(saved[field], bool):
                                require(bool(got[field]) == saved[field], "CPU/GPU feasibility")
                            else:
                                require(math.isclose(got[field], saved[field], rel_tol=1e-12, abs_tol=1e-10), "CPU/GPU vector metrics")
                        if key == "last":
                            feasible[str(n)] = bool(got["feasible_at_1e-6"])
    return {"original_timeouts": 4, "cpu_and_gpu_iterate_metrics_replayed": 9, "grid_milp_allocations_checked": 9,
            "minimum_power_throughput_fraction": .95, "gpu_last_iterate_feasible": feasible}


def replay_s10(paths, work, run, seconds):
    root = work / "s10"
    for stage in ("s10-development", "s10-four-ap"):
        with zipfile.ZipFile(paths[stage]) as z:
            for name in z.namelist():
                if name.startswith("research/"):
                    z.extract(name, root)
    research = root / "research"
    base = research / "completion-20261031"
    return {"fixed_csi": fixed_csi(base / "csi-forward", work), "four_ap": four_ap(base, work, run, seconds),
            "development": development(research), "gpu": gpu(research)}
