# Phase-1 benchmark protocol (pre-registered)

Status: frozen before the Phase-2 optimizer comparison.
Date: 2026-11-09
Parent: `PAPER2_FIX_PLAN.md`

## 1. Motivation

The Phase-0 audit established that the original 32-case benchmark has essentially no pairing headroom at `M=8`:

- fixed-power pairing gain = 0 in all 32 cases (p90 ≈ 1e-16);
- certified headroom over grid: O1 ≈ 0, ASU median 0.75%, max 4.14%;
- power-only gain: O1 ≈ 5e-10 relative, ASU median 0.63%.

Truncating the same stored channels to `M=2` restores pairing headroom:

- median pairing gain at uniform power: `M=2` 8.87%, `M=4` 2.61%, `M=8` 0.00%;
- fraction of cases with >1% pairing gain: `M=2` 93.8%, `M=4` 71.9%, `M=8` 3.1%.

The benchmark therefore uses `M=2` as the primary regime, `M=4` as a sensitivity regime, and `M=8` as a null control.

## 2. Cases

The 32 stored DeepMIMO cases (`asu-main-00..11`, `asu-scale-00..03`, `o1-main-00..11`, `o1-scale-00..03`) are transformed deterministically:

- truncate the same channel vectors to the first `M` receive coordinates (`M ∈ {2,4,8}`), with no case selection;
- `p_min = 0.001 W`, `p_max = 0.2 W`;
- off-grid budget `P/K = 0.13 W`;
- baseline grid `{0.05, 0.1, 0.2} W`;
- every case is retained; no case is excluded by outcome.

Primary population: 32 `M=2` cases (24 `K=8`, 8 `K=16`).
Secondary population: 12 controlled-array `K=16`, `M=2` cases (2 seeds × SNR {0,10,20} dB × near–far {0,10} dB) for the scale check.
Null control: the original 32 `M=8` cases and their archived results.

## 3. Anchor and budget

- Single common anchor for every method: sequential pairing `(2s,2s+1)` at uniform power `P/K = 0.13 W`.
- No near-optimal grid anchor for the primary endpoint.
- All methods receive the same wall-clock allowance: 12 s for `K=8`, 20 s for `K=16` (the scale check uses 10 s).
- Grid baseline uses `{0.05,0.1,0.2} W`; the off-grid budget means the grid does not contain the optimum.

## 4. Methods

| Method | Status |
|---|---|
| Sequential + uniform | anchor |
| Grid ILP/LP | baseline |
| SLSQP full assignment search | full baseline |
| Adapted I-WMMSE | full baseline |
| Matching–WMMSE | full baseline |
| Proposed exact-DP + SCA multi-start | proposed |

The proposed method:
1. fix powers, solve the resource-labelled assignment exactly by subset DP;
2. fix the assignment, refine all powers with SLSQP under the box and budget;
3. alternate until no improvement;
4. repeat from one sequential and seven randomized starts; retain the best feasible schedule.

## 5. Endpoints

Primary:
- paired relative and absolute sum-rate difference between the proposed method and the best full baseline (matching–WMMSE, SLSQP, I-WMMSE) on `M=2` cases;
- 95% whole-case bootstrap CI;
- win/tie/loss with a tie band of `1e-4` bit/s/Hz (above the numerical noise floor);
- report `K=8` and `K=16` separately.

Secondary:
- runtime and speedup;
- ablation: uniform, assignment-only, power-only, joint;
- certification gap of the proposed schedule on the M=2 cases;
- fairness/minimum-user rate (where computed).

Material effect:
- absolute ≥ 0.05 bit/s/Hz and relative ≥ 0.5% for a practical claim;
- the more demanding 2% relative threshold is reported but not required for the scoped K=16 claim.

## 6. Certification boundary

The M=2 schedules are checked with the frozen finite-box/integral producer at 10 s. A gap `U−L` is reported per case. The paper must state that:
- the certificate remains valid but can be loose at `M=2`;
- 10/32 M=2 cases certify to ~1e-12, while 22/32 retain gaps of 0.25–30 nats;
- the original M=8 certification result is reported separately.

## 7. Integrity

- All cases and results are stored under `research/phase1-benchmark-20261109/`.
- No case is selected using the proposed method's outcome.
- The original 32 R5 results remain unchanged.
- Any claim in the revised paper must be traceable to `m2_results.csv`, `controlled_results.csv`, `m2_certification.csv`, or `phase0_case_metrics.csv`.
