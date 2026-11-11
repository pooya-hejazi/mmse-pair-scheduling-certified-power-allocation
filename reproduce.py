"""Recompute the published results from the saved inputs in this checkout."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parent
NATIVE = Path("research/independent-cdl-20261110")
PRICED = Path("research/priced-assignment-20261111")
SCAN = Path("research/phase0-audit-20261109")
COMPONENTS = Path("research/review-20261110/comparison")
STATS = Path("research/review-20261110/statistics")
STUDIES = ("native", "priced", "certificates", "native-certificate", "subarray", "components",
           "historical", "figures", "computational", "optimizer")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_equal(expected, actual, name):
    """Allow roundoff in numerical fields; all keys, counts and labels must match."""
    if isinstance(expected, dict) and isinstance(actual, dict) and expected.keys() == actual.keys():
        for key in expected:
            check_equal(expected[key], actual[key], f"{name}.{key}")
        return
    if isinstance(expected, list) and isinstance(actual, list) and len(expected) == len(actual):
        for index, (a, b) in enumerate(zip(expected, actual)):
            check_equal(a, b, f"{name}[{index}]")
        return
    if isinstance(expected, float) and isinstance(actual, (float, int)):
        if math.isclose(expected, actual, rel_tol=1e-11, abs_tol=1e-12):
            return
    elif expected == actual:
        return
    raise ValueError(f"Saved and recomputed values differ at {name}")


def check_table(original, regenerated):
    def rows(path):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.reader(handle))
    saved, new = rows(original), rows(regenerated)
    if len(saved) != len(new):
        raise ValueError(f"Table row count changed in {original.name}")
    for index, (a, b) in enumerate(zip(saved, new)):
        if len(a) != len(b):
            raise ValueError(f"Table columns changed in {original.name}, row {index}")
        for left, right in zip(a, b):
            if left != right:
                check_equal(float(left), float(right), f"{original.name}, row {index}")


def bind_component_table(folder):
    """Compare every column of the earlier plotting table with its audited allocation."""
    expected = {p.name for p in folder.glob("*-DP-*.json")}
    seen = set()
    with (folder/"raw.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            name = f"{row['case']}-{row['arm']}.json"
            if name not in expected or name in seen:
                raise ValueError("Unexpected or duplicate comparison record "+name)
            seen.add(name)
            source = read(folder/name)
            fields = {**source, **source["counts"], "matrix_discrepancy":source["audit"]["discrepancy"]}
            for key, value in row.items():
                original = fields[key]
                if type(original)(value) != original:
                    raise ValueError(f"Comparison table differs from {name}, field {key}")
    if seen != expected or len(seen) != 72:
        raise ValueError("Incomplete comparison table")


def compare_study(saved, fresh, audit_name, expected_count):
    """Validate run-specific hashes on both sides before comparing their contents."""
    reports, summaries = [], []
    is_priced = expected_count == 720
    for directory in (saved, fresh):
        audit = read(directory / audit_name)
        if audit["status"] != "PASS" or audit["final_allocations"] != expected_count:
            raise ValueError(f"Incomplete {audit_name}")
        del audit["seconds"]
        if is_priced:
            for key, file in (("receipts_sha256", "audit_receipts.json"),
                              ("final_intervals_sha256", "audit_final_intervals.json")):
                check_equal(audit.pop(key), digest(directory / file), file)
        result = read(directory / "analysis/results.json")
        owner, key = (result, "audit_sha256") if is_priced else (result["provenance"], "auditor_report_sha256")
        check_equal(owner.pop(key), digest(directory / audit_name), key)
        reports.append(audit)
        summaries.append(result)
    check_equal(*reports, audit_name)
    check_equal(*summaries, "analysis/results.json")
    files = ["audit_receipts.json"]
    files.append("audit_final_intervals.json" if is_priced else "channel_diagnostics.json")
    for file in files:
        check_equal(read(saved / file), read(fresh / file), file)
    for file in (saved / "analysis").glob("*.csv"):
        check_table(file, fresh / "analysis" / file.name)
    return {"allocations": expected_count, "checked_history": reports[1]["retained_history_allocations"],
            "checked_starts": reports[1]["offered_starts_checked"],
            "results": summaries[1]["decisions" if is_priced else "primary"]}


def replay(selected, output):
    published_code = ROOT / "code"
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError(f"Choose a new or empty output directory: {output}")
    report = {"studies": {}, "commands": [], "python": sys.version}
    with tempfile.TemporaryDirectory(prefix="mmse-replay-") as temp:
        work = Path(temp).resolve()
        code = work / "code"
        omitted = {}
        if "native" in selected:
            omitted[published_code/NATIVE] = {"analysis", "audit_campaign.json", "audit_receipts.json",
                                              "channel_diagnostics.json"}
        if "priced" in selected:
            omitted[published_code/PRICED] = {"analysis", "audit_study.json", "audit_receipts.json",
                                              "audit_final_intervals.json"}
        def ignore(directory, names):
            return set(names) & (omitted.get(Path(directory), set()) | {"__pycache__", "matplotlib-cache"})
        shutil.copytree(published_code, code, ignore=ignore)
        for name in ("data", "figures"):
            if (ROOT / name).is_dir():
                shutil.copytree(ROOT / name, work / name)
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "MPLBACKEND": "Agg",
               "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
               "MPLCONFIGDIR": str(work / "mpl")}
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONOPTIMIZE", None)

        def run(script, *arguments, source=code):
            path = (source / script).resolve()
            rel = path.relative_to(source.parent).as_posix()
            log = output / f"{len(report['commands'])+1:02d}-{path.stem}.log"
            print("Running", rel, *arguments, flush=True)
            start = time.monotonic()
            with log.open("w", encoding="utf-8") as handle:
                proc = subprocess.run([sys.executable, "-B", "-X", "utf8", str(path), *map(str, arguments)],
                                      cwd=work, env=env, stdout=handle, stderr=subprocess.STDOUT)
            if proc.returncode:
                raise RuntimeError(f"{rel} exited {proc.returncode}. See {log}\n"
                                   + "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-10:]))
            report["commands"].append({"script": rel, "seconds": time.monotonic()-start, "log": log.name})

        if "native" in selected:
            for name in ("audit_campaign.py", "analysis.py", "channel_diagnostics.py"):
                run(NATIVE / name)
            report["studies"]["native"] = compare_study(published_code/NATIVE, code/NATIVE, "audit_campaign.json", 960)
            shutil.copytree(code / NATIVE / "analysis", output / "native")
        if "priced" in selected:
            for name in ("verify_holdout.py", "verify_study.py", "analyze_study.py", "plot_comparison.py", "plot_endpoints.py"):
                run(PRICED / name)
            report["studies"]["priced"] = compare_study(published_code/PRICED, code/PRICED, "audit_study.json", 720)
            shutil.copytree(code / PRICED / "analysis", output / "priced")
        if "certificates" in selected:
            run("m8_replay/replay.py")
            report["studies"]["certificates"] = read(output / report["commands"][-1]["log"])
        if "native-certificate" in selected:
            folder = PRICED/"native_certificate"
            run(folder/"tests.py")
            run(folder/"certificate.py", "replay")
            receipt = read(code/folder/"witnesses/replay-receipt.json")
            original = read(published_code/folder/"witnesses/produce-receipt.json")
            check_equal((receipt["planned"],receipt["coverage"]),(20,20),"native certificate coverage")
            for saved, new in zip(original["rows"], receipt["rows"], strict=True):
                for key in ("block","status","witness_sha256","gap_upper_nats","gap_upper_se"):
                    check_equal(saved[key],new[key],"native certificate "+key)
            report["studies"]["native-certificate"] = {
                key:receipt[key] for key in ("coverage","min_upper_se","median_upper_se","max_upper_se")}
        if "components" in selected:
            bind_component_table(code/COMPONENTS/"campaign")
            for file in (COMPONENTS/"audit_retained.py", COMPONENTS/"analyze_comparison.py",
                         STATS/"audit_statistics.py", STATS/"audit_raytraced_contrasts.py"):
                run(file)
            for file in (COMPONENTS/"results_summary.json", STATS/"corrected_statistics.json",
                         STATS/"raytraced_contrasts.json"):
                original, regenerated = read(published_code/file), read(code/file)
                if file.name == "corrected_statistics.json":
                    for item in (original, regenerated):
                        item["input_hashes"] = {k.replace(chr(92), "/"):v for k,v in item["input_hashes"].items()}
                check_equal(original, regenerated, file.name)
            report["studies"]["components"] = {"saved_allocations": 72, "cases": 24}
        if "subarray" in selected:
            (code / SCAN / "figures").mkdir(exist_ok=True)
            run(SCAN / "run_m_scan.py")
            file = SCAN / "phase0_m_scan_summary.json"
            summary = read(code/file)
            check_equal(read(published_code/file), summary, file.name)
            check_table(published_code/SCAN/"phase0_m_scan.csv", code/SCAN/"phase0_m_scan.csv")
            report["studies"]["subarray"] = {m: summary["all_M"+m]["pair_uniform_median"] for m in ("2","4","8")}
        if "historical" in selected:
            record = output/"historical-replay.json"
            run("historical/replay.py","--output",record)
            check_equal("PASS",read(record)["status"],"historical replay")
            report["studies"]["historical"] = {"receipt":record.name,"sha256":digest(record)}
        if "figures" in selected:
            args = ["--output", output / "figures"]
            if "native" in selected:
                args.extend(["--native-plots", code / NATIVE / "analysis/figures"])
            run("../figures/reproduce.py", *args)
            if "priced" not in selected:
                run(PRICED/"analyze_study.py")
                run(PRICED/"plot_comparison.py")
                run(PRICED/"plot_endpoints.py")
            historical = {row["asset"] for row in read(work/"figures/manifest.json")["figures"]}
            current = read(work/"figures/manifest-priced.json")
            published = {}
            for row in current["figures"]:
                asset = row["asset"]
                if Path(asset).name != asset or not asset.endswith(".pdf"):
                    raise ValueError("Unexpected figure name")
                check_equal(row["pdf_sha256"], digest(work/"figures"/asset), asset)
                if asset not in historical:
                    for ext in (".pdf",".png"):
                        name = Path(asset).with_suffix(ext).name
                        shutil.copyfile(code/PRICED/"analysis/figures"/name, output/"figures"/name)
                published[asset] = digest(output/"figures"/asset)
            check_equal(current["figure_asset_count"], len(published), "edition figure count")
            report["studies"]["figures"] = {"published_panels_redrawn":len(published),
                                            "regenerated_pdf_sha256":published}
        if "computational" in selected:
            destination = output / "computational"
            # The sensitivity reader compares with the original releases and creates its own working copy.
            run("research/computational-replay-20261111/replay.py", "--output", destination, source=published_code)
            receipt = destination / "report.json"
            check_equal("PASS", read(receipt)["status"], "same-channel computational repeat")
            report["studies"]["computational"] = {"receipt": "computational/report.json", "sha256": digest(receipt)}
        if "optimizer" in selected:
            # Exercise the production runner on one preselected case in the disposable copy.
            case = "native-b00-A-snr00"
            arms = ("Price-DP-SQP","DP-SQP","DP-Fu-SCA","DP-Thu-IDE")
            folder = code/PRICED/"runs/main"
            stored = work/"original-example"
            stored.mkdir()
            for arm in arms:
                path = folder/f"{case}-{arm}.json"
                path.rename(stored/path.name)
            run(PRICED/"run_study.py", "run")
            run(PRICED/"verify_study.py")
            audit = read(code/PRICED/"audit_study.json")
            check_equal((audit["status"], audit["final_allocations"]), ("PASS",720), "optimizer replay")
            values = {}
            for arm in arms:
                name = f"{case}-{arm}.json"
                old, new = read(stored/name), read(folder/name)
                check_equal(old["case_sha256"], new["case_sha256"], name+" input")
                check_equal(old["offered_start_ids"], new["offered_start_ids"], name+" starts")
                if old["process"] == new["process"]:
                    raise ValueError("Optimizer did not produce a fresh run")
                values[arm] = {"published_se":old["se_bits"], "new_se":new["se_bits"],
                               "new_seconds":new["elapsed_seconds"]}
            report["studies"]["optimizer"] = {"case":case,"recomputed":values,"allocation_audit":"PASS"}
    report["status"] = "PASS"
    (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print("PASS. Results, figures and logs in", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=STUDIES, help="Reproduce one part of the study.")
    parser.add_argument("--output", type=Path, default=ROOT/"reproduced", help="New or empty results directory.")
    args = parser.parse_args()
    replay((args.only,) if args.only else STUDIES, args.output.resolve())
