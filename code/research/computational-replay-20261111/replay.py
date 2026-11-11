"""Verify the saved computational repeat, re-audit its schedules and reproduce both study decisions."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import compare
import repeat

SOURCE_COMMIT = "2a9b228cdba68abf6620725dc9850b30f3374d29"
ARCHIVE = "data/rerun-priced-20261111.zip"


def equivalent(actual, expected, label):
    if isinstance(expected, dict):
        repeat.require(isinstance(actual, dict) and actual.keys() == expected.keys(), "Different fields in " + label)
        for key in expected:
            equivalent(actual[key], expected[key], f"{label}.{key}")
    elif isinstance(expected, list):
        repeat.require(isinstance(actual, list) and len(actual) == len(expected), "Different lengths in " + label)
        for index, (a, b) in enumerate(zip(actual, expected)):
            equivalent(a, b, f"{label}[{index}]")
    elif isinstance(expected, float):
        repeat.require(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), "Numerical difference in " + label)
    else:
        repeat.require(actual == expected, "Different value in " + label)


def compare_csv(path, archived):
    def rows(text):
        reader = csv.DictReader(io.StringIO(text))
        return reader.fieldnames, list(reader)
    names, current = rows(path.read_text(encoding="utf-8"))
    fields, saved = rows(archived.decode("utf-8"))
    repeat.require(names == fields and len(current) == len(saved), "CSV shape mismatch " + path.name)
    for a, b in zip(current, saved):
        for field in fields:
            if a[field] != b[field]:
                equivalent(float(a[field]), float(b[field]), path.name + " " + field)


def validate(checkout, archive, output):
    descriptor = repeat.read(HERE/"archive.json")
    repeat.require(descriptor["source_commit"] == SOURCE_COMMIT and descriptor["archive"] == ARCHIVE
                   and archive.stat().st_size == descriptor["bytes"] and repeat.sha(archive) == descriptor["sha256"],
                   "Unexpected computational repeat archive")
    repeat.require(repeat.sha(HERE/"SURVEY/PROTOCOL.md") == repeat.PROTOCOL_HASH, "Published protocol mismatch")
    original = checkout/"code"/repeat.STUDY
    with tempfile.TemporaryDirectory(prefix="cr-study-") as work, zipfile.ZipFile(archive) as zf:
        scratch = Path(work).resolve()
        reference = repeat.populate(checkout, scratch)
        fresh = scratch/"code"/repeat.STUDY
        names = zf.namelist()
        inventory = json.loads(zf.read("members.json"))
        repeat.require(len(set(names)) == len(names) and set(names) == set(inventory) | {"members.json"}
                       and len(inventory) == descriptor["payload_members"], "Archive inventory mismatch")
        # Only the actual run, start and process JSONs enter the fresh auditor workspace.
        for name, spec in inventory.items():
            parts = PurePosixPath(name).parts
            repeat.require(bool(parts) and ".." not in parts and not PurePosixPath(name).is_absolute()
                           and "\\" not in name and ":" not in name, "Unsafe archive member")
            content = zf.read(name)
            repeat.require(len(content) == spec["bytes"] and hashlib.sha256(content).hexdigest() == spec["sha256"],
                           "Archive payload hash mismatch " + name)
            if name.startswith("study/runs/"):
                repeat.require(len(parts) == 4 and parts[2] in ("processes","main") and name.endswith(".json"),
                               "Unexpected run path")
                target = repeat.safe(fresh, PurePosixPath(*parts[1:]))
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as item:
                    item.write(content)
        def record(name):
            return json.loads(zf.read(name))
        lock = record("meta/prerun.json")
        repeat.require(lock["commit"] == SOURCE_COMMIT and lock["protocol_sha256"] == repeat.PROTOCOL_HASH
                       and lock["launcher_sha256"] == repeat.sha(HERE/"repeat.py")
                       and lock["prior_results_copied"] == 0 and lock["expected_new_runs"] == 720
                       and lock["cases"] == reference["cases"] and lock["expected_offered_starts"] == 1440
                       and lock["bootstrap_seed"] == repeat.read(original/"seed_manifest.json")["bootstrap"]["effective_seed"],
                       "Pre-run provenance mismatch")
        for rel, key in [("source_manifest.json","source_manifest_sha256"),("seed_manifest.json","seed_manifest_sha256"),
                         ("runs/main/manifest.json","original_stage_sha256"),("audit_study.json","original_audit_sha256"),
                         ("analysis/results.json","original_analysis_sha256")]:
            repeat.require(repeat.sha(original/rel) == lock[key], "Different original reference " + rel)
        saved_audit = record("study/audit_study.json")
        saved_analysis = record("study/analysis/results.json")
        for key, name in [("receipts_sha256","study/audit_receipts.json"),
                          ("final_intervals_sha256","study/audit_final_intervals.json")]:
            repeat.require(inventory[name]["sha256"] == saved_audit[key], "Saved audit binding mismatch")
        repeat.require(saved_analysis["audit_sha256"] == inventory["study/audit_study.json"]["sha256"],
                       "Saved analysis binding mismatch")
        os.environ.pop("PYTHONOPTIMIZE", None)
        repeat.call(fresh, "verify_study.py", [], output/"independent-audit.log")
        repeat.call(fresh, "analyze_study.py", [], output/"analysis.log")
        current_audit = repeat.read(fresh/"audit_study.json")
        # Audit elapsed time and binary floating-point error receipts depend on the reader's machine.
        # The exact rational final enclosures and all input and schedule hashes must still match.
        for key in saved_audit.keys() - {"seconds", "receipts_sha256"}:
            equivalent(current_audit[key], saved_audit[key], "audit." + key)
        current_analysis = repeat.read(fresh/"analysis/results.json")
        for key in saved_analysis.keys() - {"audit_sha256"}:
            equivalent(current_analysis[key], saved_analysis[key], "analysis." + key)
        for key in ("run_values","case_values","block_effects","cell_contrasts","losses"):
            compare_csv(fresh/"analysis"/(key+".csv"), zf.read("study/analysis/"+key+".csv"))
        summary = compare.compare(original, fresh, lock, output/"comparison")
        equivalent(summary, record("comparison/comparison.json"), "paired comparison")
        for key in ("allocation_pairs", "case_endpoints"):
            compare_csv(output/"comparison"/(key+".csv"), zf.read("comparison/"+key+".csv"))
    return dict(status="PASS", archive_sha256=descriptor["sha256"], payload_members=descriptor["payload_members"],
                source_commit=SOURCE_COMMIT, cases=180, allocations=720, bootstrap_seed=summary["bootstrap_seed"],
                original=summary["original"], repeat=summary["repeat"], arms=summary["arms"],
                endpoint_differences=summary["endpoint_differences"], decision_changed=summary["decision_changed"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Empty or nonexistent output directory")
    parser.add_argument("--checkout", type=Path, default=HERE.parents[2], help=argparse.SUPPRESS)
    parser.add_argument("--archive", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    output = args.output.resolve()
    archive = (args.archive or checkout/ARCHIVE).resolve()
    output.mkdir(parents=True, exist_ok=True)
    repeat.require(not any(output.iterdir()), "Output directory must be empty")
    try:
        report = validate(checkout, archive, output)
    except Exception as error:
        repeat.save(output/"report.json", dict(status="FAIL", reason=str(error)))
        raise
    repeat.save(output/"report.json", report)
    print("PASS: re-audited 720 allocations, 180 shared start sets and all paired endpoints", flush=True)


if __name__ == "__main__":
    main()
