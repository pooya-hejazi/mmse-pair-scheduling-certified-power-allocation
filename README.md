# Reproducible code: MMSE Pair Scheduling

This repository contains **only the reproducible code and saved outputs** for the paper
*MMSE Pair Scheduling: Sharp Complexity, Certified Power Allocation, and Regime-Dependent Rate Gains*.
It does not contain the manuscript, supplement, PDFs, cover letter, or any `.tex` source.

## Environment

Python 3.12 with:

```text
pip install -r code/requirements.txt
```

The CDL generator is CPU-only. It uses the 3GPP TR 38.901 CDL-A/B/C cluster tables
included under `code/research/phase1-cdl-20261109/tables/`.

## Reproduce the headline CDL result

From this directory:

```text
cd code
python research/phase1-cdl-20261109/build_cdl.py
python research/phase1-cdl-20261109/run_cdl.py
python research/phase1-cdl-20261109/analyze_cdl.py
```

This regenerates the 53 K=16, M=2 CDL cases and the benchmark results. Expected headline values:

- median gain over the best common-model baseline: **1.31%**
- absolute median gain: **0.129 bit/s/Hz**
- 95% interval: **[1.19, 1.42]%**
- **53 wins / 0 ties / 0 losses**

Results are written to:

- `code/research/phase1-cdl-20261109/cdl_results.csv`
- `code/research/phase1-cdl-20261109/cdl_summary.json`
- `code/research/phase1-cdl-20261109/figures/`

## Reproduce the K=8 result

```text
cd code
python research/phase1-cdl-20261109/build_cdl_k8.py
python research/phase1-cdl-20261109/run_cdl_k8.py
```

The K=8 results are in `cdl_k8_results.csv`. The paper's K=8 statement is an efficiency result:
the proposed method is about 211 times faster than SLSQP by the ratio of median times, while the
absolute rate gain is negligible (about 0.0017 bit/s/Hz).

## Reproduce the attribution and 30-s baseline sensitivity

```text
cd code
python research/phase1-cdl-20261109/run_cdl_ablation.py
python research/phase1-cdl-20261109/run_long_baselines.py
python research/phase1-cdl-20261109/analyze_cdl.py
```

- `cdl_ablation.csv` — assignment-only, power-only and joint arms.
- `cdl_long_baseline.csv` — 30-s matching/SLSQP sensitivity; the proposed 10-s result remains ahead
  in all 12 tested cases, median 1.07%.

## Reproduce the receive-dimension audit

```text
cd code
python research/phase0-audit-20261109/run_audit.py
python research/phase0-audit-20261109/run_m_scan.py
```

These scripts use the stored DeepMIMO cases included under
`code/research/phase1-benchmark-20261109/`.

## Finite-box/integral certificate

The certificate code is under:

```text
code/research/manuscript-refinement-20261106/certification/
```

It includes the producer, independent checker, integer-log enclosure, protocol, frozen metadata
and the final aggregate result tables. The full archived ray-traced input archive is **not**
redistributed in this repository; the code, protocol and saved summaries are included. DeepMIMO is
retained only as the `M=8` certification and receive-dimension cross-check; it is not used for the
CDL rate claim.

## Code map

| Path | Purpose |
|---|---|
| `code/research/phase1-cdl-20261109/build_cdl.py` | Generate 3GPP CDL-A/B/C K=16/M=2 cases |
| `code/research/phase1-cdl-20261109/run_cdl.py` | Run grid, SLSQP, I-WMMSE, matching-WMMSE and the proposed exact search |
| `code/research/phase1-cdl-20261109/analyze_cdl.py` | Produce result tables and figures |
| `code/research/phase1-cdl-20261109/build_cdl_k8.py` | Generate K=8 CDL cases |
| `code/research/phase1-cdl-20261109/run_cdl_k8.py` | K=8 benchmark |
| `code/research/phase1-cdl-20261109/run_cdl_ablation.py` | Assignment/power attribution |
| `code/research/phase1-cdl-20261109/run_long_baselines.py` | 30-s baseline sensitivity |
| `code/research/phase1-benchmark-20261109/` | Stored DeepMIMO cross-check cases and phase-1 runners |
| `code/research/phase0-audit-20261109/` | M-truncation and pairing-headroom audit |
| `code/research/manuscript-refinement-20261106/certification/` | Finite-box/integral certificate code |
| `code/research/completion-20261031/confirmation/local_core.py` | Grid/SLSQP/I-WMMSE baseline |
| `code/research/dual-track-revision-20261103/baseline-code/matching_baseline.py` | Matching–WMMSE baseline |

## Notes

- No raw DeepMIMO scene archive is redistributed.
- The CDL generator, CDL tables, cases, saved results and plotting code are included.
- All scripts use paths relative to the extracted `code/` directory.
- This repository intentionally contains no manuscript or supplement files.
