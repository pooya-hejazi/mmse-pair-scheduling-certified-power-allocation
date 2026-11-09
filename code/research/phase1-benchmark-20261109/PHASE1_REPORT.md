# Phase-1 report: benchmark and optimizer results

## 1. What changed

The original benchmark was dominated by `M=8`, where two-user MMSE reception nearly nulls interference. The Phase-0 audit found zero fixed-power pairing gain in all 32 cases. The Phase-1 benchmark applies a deterministic `M`-truncation to the same stored channels and moves the power budget off-grid.

## 2. M-truncation restores pairing headroom

| M | Median pairing gain at uniform power | Fraction >1% | Median pairing gain at grid powers | Fraction >1% |
|---:|---:|---:|---:|---:|
| 2 | 8.87% | 93.8% | 8.34% | 93.8% |
| 4 | 2.61% | 71.9% | 2.54% | 65.6% |
| 8 | 0.00% | 3.1% | 0.00% | 0.0% |

## 3. Rate results, M=2

### K=8 (24 ray-traced cases)

| Method | Mean sum rate (nats) | Median |
|---|---:|---:|
| Grid | 34.53 | 38.38 |
| SLSQP | 36.27 | 40.70 |
| I-WMMSE | 34.07 | 39.11 |
| Matching–WMMSE | 35.60 | 39.60 |
| Proposed | 36.32 | 40.70 |

Proposed vs best baseline: median 0.000%, mean −0.047%, 95% CI [−0.241%, +0.110%]; 3 wins, 19 ties, 2 losses. Median speedup: 270× vs SLSQP, 76× vs matching–WMMSE.

### K=16 ray-traced (8 cases)

| Method | Mean sum rate (nats) | Median |
|---|---:|---:|
| Grid | 66.04 | 74.48 |
| SLSQP | 61.60 | 69.41 |
| I-WMMSE | 59.31 | 64.83 |
| Matching–WMMSE | 67.19 | 75.43 |
| Proposed | 68.11 | 76.69 |

Proposed vs best baseline: median +1.30%, mean +1.51%, 95% CI [+0.97%, +2.07%]; 8 wins, 0 ties, 0 losses. Median speedup: 4.1× vs SLSQP, 2.25× vs matching–WMMSE.

### K=16 controlled-array (12 cases)

Proposed vs best baseline: median +0.46%, mean +0.55%, 95% CI [+0.29%, +0.86%]; 11 wins, 1 tie, 0 losses.

### K=16 pooled (20 cases)

Proposed vs best baseline: median +0.80%, mean +0.94%, 95% CI [+0.61%, +1.28%]; 19 wins, 1 tie, 0 losses.

Absolute gains must be converted with the paper's gross occupied-tone SE convention, `SE = Q/(S ln 2)`, where `S=8` here. K=16 ray cases gain about 0.9 nat total at the median, i.e. about **0.16 bit/s/Hz**; controlled cases gain about 0.2 nat, i.e. about **0.034 bit/s/Hz**, which is below the 0.05 bit/s/Hz threshold. The pooled median is about 0.38 nat, i.e. about **0.069 bit/s/Hz**. The headline absolute claim therefore rests on the ray-traced K=16 pool; the controlled pool is corroborating but does not independently clear 0.05 bit/s/Hz. The 2% relative threshold is not met by the pooled median.

## 4. Attribution at M=2

Mean gain over the uniform anchor:

| Scene | Assignment only | Power only | Joint |
|---|---:|---:|---:|
| O1 | 18.9% | 0.6% | 19.4% |
| ASU | 55.4% | 62.4% | 102.0% |

In high-SNR O1, pairing dominates and power allocation is almost irrelevant. In ASU, both mechanisms contribute strongly; neither alone approaches the joint result. This explains why the original M=8 benchmark, where pairing had no headroom, could not distinguish joint algorithms.

## 5. Certification boundary

The frozen finite-box/integral producer certifies the proposed M=2 schedules to ~1e-12 on 10/32 cases (mostly ASU K=8). The remaining 22/32 retain gaps of 0.25–30 nats, concentrated in high-SNR O1 and K=16 cases. The certificate is valid but loose there; the paper must report this boundary rather than claim certified rate superiority at M=2.

The original M=8 result remains: 27/32 certificates at 0.01 nat, 97.82% median fixed-anchor gap reduction. That result is about certification, not rate superiority.

## 6. Interpretation

- The original benchmark's flat rate result is explained by `M=8`: MMSE nulls the interference, so pairing does not matter.
- At `M=2`, the proposed exact-DP + SCA method matches an exhaustive SLSQP search at K=8 at about 1/270 the runtime, and improves the best full baseline at K=16 by 1.3% median on ray-traced cases (8/8 wins) and 0.46% on controlled cases (11/12 wins).
- The rate gain is scoped: it appears at K=16 and M=2, not uniformly at K=8.
- Certification at M=2 is not uniformly tight. The paper should claim (i) certification at M=8, (ii) scoped rate superiority at K=16/M=2, and (iii) an explicit certification boundary at M=2.

## 7. Artifacts

- `BENCHMARK_PROTOCOL.md`
- `BENCHMARK_MANIFEST.json`
- `cases/` (32 M=2/M=4/M=8 variants)
- `controlled_cases/` (12 K=16 controlled cases)
- `m2_results.csv`, `controlled_results.csv`, `m2_ablation.csv`, `m2_certification.csv`
- `phase1_summary.json`
- `figures/phase1_*.pdf/png`
