# Reproducible code and saved results

This directory contains the complete code and saved outputs for the CDL benchmark
and the finite-box/integral certificate used in the paper.

## Environment

Python 3.12 with:

```text
pip install -r requirements.txt
```

The CDL generator is CPU-only and uses the standard 3GPP TR 38.901 CDL-A/B/C
cluster tables under `research/phase1-cdl-20261109/tables/`.

## Reproduce the CDL rate benchmark

From this `code/` directory:

```text
python research/phase1-cdl-20261109/build_cdl.py
python research/phase1-cdl-20261109/run_cdl.py
python research/phase1-cdl-20261109/analyze_cdl.py
python research/phase1-cdl-20261109/run_cdl_k8.py
python research/phase1-cdl-20261109/analyze_cdl.py
```

The K=16 results are in `research/phase1-cdl-20261109/cdl_results.csv` and the
K=8 results in `cdl_k8_results.csv`. The figures are regenerated under
`research/phase1-cdl-20261109/figures/`.

## Reproduce the phase-0 receive-dimension audit

```text
python research/phase0-audit-20261109/run_audit.py
python research/phase0-audit-20261109/run_m_scan.py
```

These scripts use the stored DeepMIMO cases copied under
`research/phase1-benchmark-20261109/cases/`.

## Reproduce the CDL tables and validation

```text
python research/phase1-cdl-20261109/build_cdl.py
```

The validation table in the supplement reports the generated delay scale,
azimuth spread, XPR, squared-correlation and SNR ranges.

## Reproduce the finite-box/integral certificate

The certificate code is under
`research/manuscript-refinement-20261106/certification/`. The full archived
ray-traced input archive is not redistributed here; the code, protocol, final
summary and analysis tables are included. The original archive remains in the
prior public release. The script interface is documented in that folder's
`README.md` and `PROTOCOL.md`.

## Notes

- The CDL benchmark replaces the DeepMIMO rate claim. DeepMIMO is retained only
  as an `M=8` certification and receive-dimension cross-check.
- All scripts use paths relative to this `code/` directory.
- No raw DeepMIMO scene archive is redistributed.
