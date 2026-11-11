"""Regenerate historical and paired native-CDL figures from their scientific evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent / "code" / "research"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_release_files(index):
    record = read_json(index)
    figures = record["figures"]
    if len(figures) != len({r["asset"] for r in figures}) or len(figures) != record["figure_asset_count"]:
        raise ValueError("Distinct figure count differs from " + index.name)
    hashes = {}
    for row in figures:
        pdf = Path(row["asset"])
        if pdf.name != row["asset"] or pdf.suffix != ".pdf":
            raise ValueError("Invalid figure asset: " + row["asset"])
        for key, ext in (("asset", "pdf"), ("png", "png"), ("data", "csv")):
            if key == "data" and key not in row:
                continue
            filename = pdf.with_suffix("." + ext).name
            digest = row[("data" if key == "data" else ext) + "_sha256"]
            if row[key] != filename or sha(HERE / filename) != digest:
                raise ValueError("Release asset hash mismatch: " + filename)
            hashes[filename] = digest
    return figures, hashes


def redraw_historical(out):
    import matplotlib.pyplot as plt
    sys.path.insert(0, str(HERE / "sources"))
    import historical_panels as panels
    import historical_bounds as bounds

    def export(fig, name):
        panels.render_check(fig, name)
        fig.savefig(out / (name + ".pdf"), metadata={"Title": name, "Creator": "Publication figure generator",
                                                    "CreationDate": None, "ModDate": None})
        fig.savefig(out / (name + ".png"), dpi=300, metadata={"Software": "Publication figure generator", "Title": name})
        plt.close(fig)

    panels.set_style()
    data = panels.load_data(panels.Inputs())
    for name, builder in panels.BUILDERS.items():
        fig, _ = builder(data)
        export(fig, name)
    bound_inputs = bounds.BoundInputs()
    data = bounds.load_data(bound_inputs)
    groups = bounds.all_groups(data)
    for name, builder in [("integral-bound-comparison", bounds.plot_comparison), ("integral-bound-detail", bounds.plot_detail)]:
        fig, _ = builder(data, groups)
        export(fig, name)


def redraw_native(out, rows, native_plots):
    from tempfile import TemporaryDirectory
    source = RESEARCH / "independent-cdl-20261110"
    with TemporaryDirectory(dir=out) as temp:
        if native_plots is None:
            analysis = load_module("frozen_native_figure_analysis", source / "analysis.py")
            main, _ = analysis.load_stage("main")
            summary = read_json(source / "analysis/results.json")
            analysis.plot(summary, main, Path(temp))
            native_plots = Path(temp) / "figures"
        for row in rows:
            if row["source_group"] == "native":
                for key in ("asset", "png"):
                    shutil.copyfile(native_plots / row[key], out / row[key])


def compare_m_scan(out):
    """Recompute all 96 receive-dimension records using the archived channels and grid schedules."""
    source = RESEARCH / "phase0-audit-20261109"
    sys.path.insert(0, str(source))
    scan = load_module("archived_m_scan", source / "run_m_scan.py")
    scan.OUT = out / "m-scan"
    (scan.OUT / "figures").mkdir(parents=True)
    scan.main()
    def read_csv(path):
        with path.open(encoding="utf-8-sig", newline="") as stream:
            return {(row["name"], row["M_eff"]): row for row in csv.DictReader(stream)}

    old = read_csv(source / "phase0_m_scan.csv")
    fresh = read_csv(scan.OUT / "phase0_m_scan.csv")
    if old.keys() != fresh.keys() or len(old) != 96:
        raise ValueError("M-scan row coverage mismatch")
    for key, original in old.items():
        for col, value in original.items():
            got = fresh[key][col]
            if col in ("name", "scene"):
                good = got == value
            else:
                good = math.isclose(float(got), float(value), rel_tol=1e-12, abs_tol=1e-12)
            if not good:
                raise ValueError(f"M-scan row mismatch {key}, {col}: {got} versus {value}")
    saved = read_json(source / "phase0_m_scan_summary.json")
    new = read_json(scan.OUT / "phase0_m_scan_summary.json")
    if new.keys() != saved.keys():
        raise ValueError("Missing M-scan summary group")
    for group, metrics in saved.items():
        for key, value in metrics.items():
            if not math.isclose(new[group][key], value, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"M-scan summary mismatch: {group}/{key}")
    return {str(m): new["all_M"+str(m)]["pair_uniform_median"] for m in (2,4,8)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Empty or new directory for PDFs, PNGs and replay receipt")
    parser.add_argument("--verify-only", action="store_true", help="Check the edition PDFs, PNGs and plotted-data CSVs against their hash manifest")
    parser.add_argument("--native-plots", type=Path, help="Use plots from a separate fresh native analysis replay")
    parser.add_argument("--recompute-m-scan", action="store_true", help="Also repeat all 96 fixed-power receive-dimension checks from raw case channels")
    args = parser.parse_args()
    historical = HERE / "manifest.json"
    rows, _ = check_release_files(historical)
    if len(rows) != 27:
        raise ValueError("Expected 27 historical figure assets")
    index = next(HERE / name for name in ("manifest-headroom.json", "manifest-tcom.json", "manifest-priced.json", "manifest.json")
                 if (HERE / name).is_file())
    edition, release_hashes = check_release_files(index)
    count = len(edition)
    tables = sum("data" in row for row in edition)
    if args.verify_only:
        print(f"Verified {count} edition PDF/PNG pairs, {tables} plotted-data tables and all 27 historical pairs.")
        return
    if args.output is None:
        parser.error("--output is required for regeneration")
    out = args.output.resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        parser.error("--output must be absent or empty")
    out.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(out / "matplotlib-cache")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    medians = compare_m_scan(out) if args.recompute_m_scan else None
    with plt.rc_context():
        redraw_historical(out)
    sys.path.insert(0, str(HERE / "sources"))
    import archived_cdl
    with plt.rc_context():
        archived_cdl.review_plots(RESEARCH, out)
    with plt.rc_context():
        archived_cdl.comparison_plot(RESEARCH, out)
    with plt.rc_context():
        redraw_native(out, rows, args.native_plots)
    priced = RESEARCH / "priced-assignment-20261111"
    for asset, script in (("priced_cdl_comparison.pdf", "plot_comparison.py"), ("priced_cdl_endpoints.pdf", "plot_endpoints.py")):
        if asset in release_hashes:
            subprocess.run([sys.executable, "-B", str(priced / script), "--analysis-dir", str(priced / "analysis"),
                            "--output-dir", str(out)], check=True)
    if "native_assignment_power_margins.pdf" in release_hashes:
        import cdl_margins
        cdl_margins.generate(out)
    if index.name == "manifest-headroom.json":
        import cdl_decisions
        cdl_decisions.generate(out, [name for name in cdl_decisions.PLOTS if name + ".pdf" in release_hashes])
    actual = {p.name: sha(p) for p in sorted(out.iterdir()) if p.suffix in (".pdf", ".png", ".csv")}
    if actual.keys() != release_hashes.keys():
        raise ValueError("Regenerated file-set mismatch: " + str(set(actual) ^ set(release_hashes)))
    for name in actual:
        if name.endswith(".csv") and actual[name] != release_hashes[name]:
            raise ValueError("Regenerated plotted values differ: " + name)
    receipt = dict(status="PASS", manifest=index.name, rendered_or_reused_assets=2 * count, plotted_data_tables=tables,
                   reused_native_plots=args.native_plots is not None,
                   m_scan_uniform_median_ratios=medians, output_sha256=actual,
                   byte_identical_to_release={k: v == release_hashes[k] for k,v in actual.items()},
                   note="Rendering metadata, fonts and installed library versions may affect bytes. Release assets have separately verified hashes.")
    (out / "figure-replay.json").write_text(json.dumps(receipt,indent=2)+"\n", encoding="utf-8")
    print(f"Produced {count} PDF/PNG pairs and {tables} plotted-data tables in", out)


if __name__ == "__main__":
    main()
