# Independent native-CDL campaign — 10 November 2026

Astra prepared this plan before implementation. Freeze this protocol and source hashes before the excluded engineering pilot; do not tune settings from solver rankings. Baseline: research/review-20261110/paper and output/Paper2-Submission-2026-11-10-Reviewed. Preserve historical evidence.

## Population and channels

Generate 20 independent root blocks, each containing fresh CDL-A/B/C channels. Reuse each profile realization at nominal reference SNR 0,10,20 dB: 180 cases but 20 independent inference blocks. Pilot uses a separate namespace and is excluded. No historical gains, angles or channels are reused.

Sionna 2.2.0, TR38.901 spec 19.2, CPU double precision; carrier 3.5GHz, 100ns delay spread, static speed zero, one time sample. K16, S8, M2, single vertically polarized omnidirectional elements; one fixed common BS orientation and fixed UT orientation. Use native profile angles, rays, coupling, phases, delays and polarization processing. No per-user BS rotation or hand-made pair separation.

Frequency indices [-14,-10,-6,-2,2,6,10,14] on a 50MHz/32-tone grid. Each user's tones come from one CIR via cir_to_ofdm_channel(normalize=False). Save native complex CIR, delays and frequency responses. Draw fresh frequency-flat user offsets Uniform[-6,6]dB. Define nominal per-antenna SNR rho at reference power 0.1W before offset and instantaneous fading: h=H_native*sqrt(10^((rho_db+offset_db)/10)/0.1). Do not normalize realized norms or individual tones. Report realized SNR distributions separately. Power box [.001,.2]W, total budget 2.08W; each user served once and two per resource, recomputed MMSE/no SIC. This is a link-profile benchmark with prescribed large-scale factors, not spatially consistent deployment/path-loss sampling.

## Streams

Record fresh SeedSequence entropy and spawn keys for pilot/main, block, profile, user channels, link factors, initialization, stochastic search and bootstrap. Record actual effective 32-bit CPU seeds. Reject duplicate seeds and intersections with recorded historical seeds before outcomes. Reset Sionna config.seed before constructing/generating every user link. Channel, large-scale, initialization and solver purposes have distinct streams. Deliberate reuse is limited to paired SNR levels and common starts across compared methods. Unique seed allocation is not a mathematical proof of PRNG independence.

## Solvers and saved evidence

Five arms: DP-SQP, DP-Fu-SCA, DP-Thu-IDE, sequential-pair Fixed-SQP, DP-uniform. The first three share exhaustive assignment DP with floating-point weights and the existing power components. Fixed-SQP keeps its sequential pairs. DP-uniform uses uniform P/K and is a deterministic ablation, not a time-matched iterative solver. Eight common feasible power starts: uniform plus seven random; DP arms share random pair starts. One initialization stream per block/profile reused across SNR; separate solver RNG stream.

Iterative allowance 10s, continuous blocks at most 5s, at most eight alternations per start. Uniform DP has a 10s cap and a checked fallback. Run serially with one numerical-library thread and cyclic arm order. Search time includes initial validation, DP, power work and candidate checks; common model/start construction and final independent replay are excluded and separately timed. Reject improvements whose validation finishes after deadline. Record overruns, completed work, unsuccessful solver returns, residuals and generations.

Predeclared sensitivity: all 20 CDL-B/10dB cases, three DP arms, 30s total and 10s power blocks, otherwise identical starts/settings. This probes budget sensitivity, not convergence. Pilot covers A/B/C at10dB and one30s control, solely for engineering checks and timing estimates. Expected full work roughly1.5–2.5hours; no outcome-based early stopping.

Save every final allocation and every accepted incumbent schedule, exact rational powers, rate enclosures, timestamps, all offered starts, diagnostics, source/case hashes and environment. A timeout keeps its last checked fallback and stays in the analysis. Missing or invalid evidence, generator/evaluator defects or changed frozen sources stop dependent work; preserve failures and explicitly document any justified affected-set restart. Never replace cases based on results.

## Gates and analysis

Before full search: unique/disjoint seed audit; fixed common arrays and native amplitudes; deterministic regeneration; independent Fourier reconstruction from CIR; finite shapes and frequency selectivity; exhaustive tiny-K4 DP/deadline guards; exact feasibility and scalar/matrix checks for all pilot arms. Independent final replay reconstructs coefficients from channels, checks incidence/boxes/budget and outward-log rate enclosures. Occupied-band SE=R/(8ln2).

Primary contrasts are DP-SQP minus Fu and minus Thu in bit/s/Hz. Average equally over nine profile/SNR cells within each block, then over 20 blocks. Use 20,000 whole-block bootstrap draws and 97.5% individual percentile intervals (1.25th,98.75th percentiles) for the two primary contrasts: Bonferroni nominal95% family, with approximate bootstrap coverage. Paired relative percentages are secondary and use the same block averaging. W/T/L tolerance1e-5bit/s/Hz. Do not infer equivalence from ties or claim significance from rounded means.

Secondary results: mean SE, per-cell pointwise95% intervals, ablation effects, runtime/completed work, all20block effects, 10/30s sensitivity and channel diagnostics. Plot profile SE versus SNR, paired differences, runtime and budget sensitivity with explicit interval/axis definitions. Retain every loss, tie, stall and timeout. Never pool this study with old archives or transfer M8 certificates to it.

Then update main paper, figures, supplement and proposal; perform line-by-line traceability and author-style review; compile/render/inspect and package all evidence. Root owns protocol/runner/integration, generator worker owns channel files, analysis worker owns analysis/plots, Astra reviews independently.
