# Numeric and statistical audit — 2026-11-10

Scope: current primary CDL, K8, long-baseline, ablation, independent-generator cross-check, phase0 M-scan, phase1 ray/controlled tables, and central M8 certification claims. Read-only analysis of retained data, no optimizer reruns or manuscript changes. All calculations and exact values are in `audit_statistics.py`, `corrected_statistics.json` and `paired_contrasts.csv`. `audit_run.log` records successful assertions. Legacy supplementary S5–S10 campaign tables were not exhaustively recomputed; current main M8 summary arithmetic was recomputed from its retained final CSV.

## Corrections that change the interpretation

1. **The 53 CDL cases are not 53 independent random networks.** Four seeds are reused across profiles and separations; the balanced design has 48 cells, and five extra CDL-A sweep cells all use seed 2026110901. Cluster sizes are 17/12/12/12. Gains, centres and some phase streams are shared within seed. Whole-case resampling understates the design dependence and cannot justify “statistically resolved” or “population-level advantage.” The 24 K8 cases likewise use only four shared seeds. These are fixed-design descriptive results.

2. **Sionna's three realizations are not fully independent.** The stored metadata confirms 48 per-user realization RNG seeds but only 36 unique seeds in every case. The generator uses `SEED_BASE + case_ordinal*1000 + realization*10 + i`, with 16 users. Adjacent realizations share six streams. Different orientations and gains do not make identical underlying random streams independent. Use “three realizations,” document dependence, and do not claim independent draws. A repaired independent campaign would require new runs, outside this audit.

3. **The primary interval is a mean interval, not a median interval.** For 53 primary cases, median gain is 1.310391%, mean 1.306828%; the archived [1.19,1.42]% comes from a bootstrap of the mean. Recomputing 10,000 resamples with seed 20261109 gives mean [1.187007,1.424238]%, median [1.164774,1.562209]%. Cross-generator tables mix this mean interval with Sionna/E3 median intervals. Label the estimand or use consistently computed median intervals. All case-bootstrap intervals remain descriptive because of shared seeds.

4. **Four-seed sensitivity, not reliable population confidence.** Exact enumeration of 4^4=256 ordered cluster resamples preserves all cells inside each selected seed. For primary pooled53, mean interval is [1.139826,1.508622]%, median [1.109676,1.690327]%. For balanced48: median 1.321199%, mean 1.302216%, 48/0/0; cluster mean interval [1.095811,1.508622]%, median [1.070479,1.690327]%. With only four groups these are sensitivity ranges; positive endpoints are not strong inferential evidence. Sionna pooled53 median cluster interval [1.543030,1.790588]%, E3-A [1.162589,1.889034]%. Full values and seed-level effects are in JSON.

5. **Historic CDL schedules were not retained or independently feasibility checked by the runner.** `run_cdl.py`, `run_cdl_k8.py` and `e2_run.py` retain rates, statuses and times only. Proposed rates are read directly from `res['rate_nats']`. `case_rate` returns a supplied rate or reconstructs the objective from a returned schedule, but does not enforce coverage, boxes or budget. Thus objective reconstruction is not an independent retained-allocation audit. Remove “feasible and verified” for historical CDL results; describe stored solver-reported rates. `run_pilot.proposed` additionally initializes random powers as `low + raw*scale` although raw already includes low; a start can exceed pmax before refinement, and its initial rate may be retained. A code audit should repair this for new experiments; the historic CSV cannot show whether it occurred.

## Numeric corrections

| Item | Correct retained-data value |
|---|---|
| S13 K16 matching mean / mean CI | 1.475383%; [1.279294,1.691189]% (not 1.31%; [1.19,1.42]%) |
| M2 fraction above 5% | 25/32 = 78.125% (not 68.8%) |
| M4 fraction above 5% | 9/32 = 28.125% (not 0%) |
| K8 median absolute gain vs SLSQP | 0.003746866 bit/s/Hz (0.001731644 is vs best-per-case) |
| K8 matching W/T/L at stated absolute band | 24/0/0 (historical relative band gives 22/2/0) |
| Ray K8 matching W/T/L at stated absolute band | 22/2/0 (historical relative band gives 21/3/0) |
| K16 absolute gain range vs best | [0.006833017,0.192139113] bit/s/Hz; do not imply all lie in 0.05–0.27 |
| CDL-A per-case r90 range | [0.906681779,0.971531883], rounds to 0.91–0.97 (not 0.91–0.94) |
| K8 matching mean percent | 0.730458538%, rounds to 0.730 at three decimals (not 0.731) |

The audit uses one explicit bootstrap implementation and seed for every contrast. Several printed minor interval endpoints cannot be reproduced with this rule: e.g. K8/SLSQP mean interval is [0.100803,0.478632]% instead of [0.106,0.485]%; K16/SLSQP [13.602182,16.889386]% instead of [13.63,16.87]%; long-baseline matching mean [0.876161,1.441946]% instead of [0.87,1.45]%. These are small Monte Carlo/provenance differences, distinct from the mean-versus-median error. Use the machine values consistently after choosing the reporting convention.

Main and supplementary rate means/medians agree with retained CDL and phase1 CSVs to displayed precision (apart from the matching contrast duplication above). CDL ablation means verify: assignment 54.776649%, power 17.286927%, joint 54.924520%. Sionna case-average median 1.654016%, mean 1.644612%, median case-bootstrap interval [1.569310,1.735837]%, absolute median 0.155355709. E3-A median 1.577999%, interval [1.517636,1.790321]%, absolute median 0.151996978; its relative distance from the Sionna median is 4.595896%. These are correct descriptive statistics, not proof the angle change causally explains most differences. Sionna all159 individual realization gains are also positive (minimum 0.609603%), but their streams overlap as above.

## Runtime and figures

- `analyze_cdl.py` reads only cdl_results.csv (K16), so cdl_runtime.pdf does not display K8. Caption must specify K16 or figure must be regenerated with both datasets.
- “Fastest arm at both sizes” is false. K16 median times: grid 1.960193 s; proposed 5.502729 s; SLSQP 10.061984 s; I-WMMSE 10.062949 s; matching 10.001174 s. Proposed is fastest in only 3/53 K16 cases. It has the lowest median among continuous-power arms.
- K8 median times: proposed 0.0567873 s; grid 0.0718154 s; matching 3.9034254 s; SLSQP 12.0078819 s. Ratios of medians 211.45365 and 68.73765 are arithmetically correct. They compare single recorded callable times and capped baseline runs, not matched stopping tolerance or latency distributions.
- All K16 SLSQP/I-WMMSE/matching rows stop at the time cap. Two grid rows have GRID_NO_TIME_FOR_LP; GRID_SOLVES_RETURNED does not itself retain an IP optimality proof. Avoid asserting globally solved baseline IPs from these summary statuses.
- cdl_rate_by_method's “tightest upper tail” is unsupported: grid p90-minus-median 3.54808 nat vs proposed 3.80502; max-minus-median 3.65175 vs 3.90996. State only the verified highest median/mean.
- cdl_profile_gain shows mean/median bars, not interval bars. All three profile means and medians are positive, but a visual claim about intervals is not displayed by that figure.
- cdl_absolute_gain is data-backed for 53 K16 cases and the 0.05 dashed reference, but the text's 0.05–0.27 description is inaccurate; one case reaches only 0.00683.
- Current M-truncation figure is backed by phase0_m_scan.csv. The calculation holds p=0.1 W for all users and compares the best assignment with the archived grid assignment evaluated at that same power. It is not the sequential anchor at P/K=0.13 W used in phase1 rates.

## M-scan and M8 certificate scope

The M-scan medians/p90s are correct: M2 8.873002%/21.563252%; M4 2.611900%/8.065409%; M8 0%/0.250924%. Above1% counts are 30/23/1 of32. All32 per-case M2→M4→M8 gains are nonincreasing. However, truncation changes gain/SNR as well as correlation, so it does not isolate dimension from those consequences. “Zero in all32 at M8” is valid only at archived grid powers; the uniform0.1W audit has one case above1%. Specify the power anchor everywhere, including abstract/conclusion.

M8 certification arithmetic verifies: 27/32 new vs0/32 generic target count, 16 O1+11 ASU; median fixed-anchor gap reduction97.816237%; remaining gaps0.010182356–1.431924614 nat; median final gap9.345618e-10 nat; median construction/check times1.429080/0.597005 vs1.236720/0.463112 s. Grid-relative median achieved gain0.04034843%,3/32 above1%; old-Full-relative median0.03555243%,2/32 above1%. Curvature counts verify O1 combined5184/5184, quadrant51; ASU combined1663/5184, quadrant471. This audit checked retained arithmetic, not replayed every certificate tree.

M2 certification CSV has10/32 gaps<=0.01 nat; tight range1.002e-12–2.454e-12, remaining0.249168440–29.248867938. Its runner checks a separately rerun proposed schedule lower against the producer upper, but does not call a full independent certificate-tree checker or save that full witness. Do not conflate that procedure with the complete archived M8 certificate check.

Pooled channel correlation values verify: primary median0.503976570/p900.921078430; Sionna0.528207171/0.912720142; KS distance0.038358229; per-case gain Spearman0.189001774. Correlations share users/resources/seed groups, so use KS D descriptively, not the nominal iid KS p-value. Low cross-generator gain rank correlation and changed construction support a sensitivity check, not proof that no generator artifact can exist.

Suggested conservative headline wording: “Across the 53 stored design cells, the proposed solver-reported rate exceeded the best recorded common-model baseline in every cell, with median relative gain1.31% and median occupied-tone gain0.129 bit/s/Hz. The balanced48-cell subset gives a1.32% median. Cells reuse four channel seeds; case-bootstrap and four-seed cluster ranges are reported descriptively and do not establish a population-level guarantee.”

Skipped: optimizer reruns, certificate-tree replay, legacy S5–S10 campaign reanalysis, and new charts. Material risks: historical CDL feasibility cannot be recovered from scalar CSVs; dependence and Sionna stream overlap preclude the current independence/significance wording.
