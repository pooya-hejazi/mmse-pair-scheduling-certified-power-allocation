# Pre-registered Cross-Check Protocol — 3GPP TR 38.901 CDL Channel Generator (Paper 2)

**Document:** `CROSSCHECK_PROTOCOL.md`
**Directory:** `research/phase3-cdl-crosscheck-20261110`
**Status:** PRE-REGISTERED. This protocol is frozen BEFORE any E2/E3 outcomes are observed. The executor (DeepSeek V4.1 Flash) reads and records the SHA-256 of this file in `RESULTS.md` *before* running E2, and must not change any decision rule afterward.
**Author of protocol:** Coordinator (DeepSeek V4 Pro). **Executor:** DeepSeek V4.1 Flash.
**Date frozen:** 2026-11-10.

---

## 0. Purpose and scope

This cross-check independently audits a hand-rolled 3GPP TR 38.901 CDL-A/B/C channel generator used for the Paper-2 headline claim:

> 53 standardized CDL-A/B/C cases (K=16, M=2): the proposed method beats the strongest common-model baseline by a median 1.31% relative gain (0.129 bit/s/Hz), 95% CI [1.19%, 1.42%], 53 wins / 0 ties / 0 losses.

The cross-check answers **two distinct questions** and keeps them strictly separated:

1. **Implementation fidelity (E1).** Does `build_cdl.py` faithfully implement what the paper *claims* it implements — i.e. are the TR 38.901 table values correct, is the delay/angle/array convention internally consistent, and are the modeling simplifications *disclosed* rather than silent bugs?
2. **Rate-conclusion robustness (E2).** Does the paper's *rate conclusion* (proposed method beats the strongest common-model baseline) survive when the channel directions are produced by an independent, standard-compliant CDL model (Sionna 2.2.0) instead of the hand-rolled generator?

E1 audits the generator. E2 audits the conclusion. A generator can be a simplified but correct implementation (E1 passes as "no undisclosed bug") while the *conclusion* is or is not robust to a fuller model (E2). These are independent verdicts that are combined into three outcome buckets in §6.

**Hard constraints (binding on the executor):**
- Nothing in `research/phase1-cdl-20261109`, `research/phase2-revision-20261109`, `output/`, or the proposal may be modified. The 53 frozen case JSONs under `phase1-cdl-20261109/cases` and `cases_k8` are read-only inputs: they may be read and hashed, never written.
- Only files under `research/phase3-cdl-crosscheck-20261110` may be created.
- No certified-rate claim at M=2 is made or implied by this cross-check. The certified result stays at M=8. This protocol only tests *feasibility/robustness* of the CDL observation.

---

## 1. Definitions and notation

Frozen inputs (read-only):

| Path | Role |
|---|---|
| `research/phase1-cdl-20261109/build_cdl.py` | Generator under audit |
| `research/phase1-cdl-20261109/tables/CDL-{A,B,C}.json` | Table data under audit |
| `research/phase1-cdl-20261109/cases/*.json` | 53 frozen K=16 cases (48 = 3 profiles × 4 separations × 4 seeds, + 5 A-profile separation-sweep cases sep ∈ {10,20,40,60,90}) |
| `research/phase1-cdl-20261109/cdl_results.csv`, `cdl_summary.json` | Original results (frozen reference) |
| `research/completion-20261031/confirmation/local_core.py`, `checker.py`, `producer.py` | Optimizer core (read-only) |
| `research/dual-track-revision-20261103/baseline-code/matching_baseline.py` | Matching baseline (read-only) |
| `research/phase1-benchmark-20261109/run_benchmark_m2.py`, `run_pilot.py` | `case_rate`, `proposed` (read-only) |

Case schema (fields the cross-check must reproduce exactly):
`name, K=16, S=8, M=2, pmin="1/1000", pmax="1/5", budget="52/25", pairs[] (each {users:[u,v], resource:t, gain1:Frac, gain2:Frac, r:Frac}), channels_re, channels_im, metadata{scene, profile, separation_deg, seed, model, ...}`.

Rate definition (unchanged from `analyze_cdl.py`): for a case, `best_base = max(rate_grid, rate_slsqp, rate_iwmmse, rate_matching)`; `gain = (rate_proposed - best_base)/best_base`; `gain_bpshz = gain / (8 * ln 2)`. Win/tie/loss thresholds: `win: gain > 1e-4`, `tie: |gain| ≤ 1e-4`, `loss: gain < -1e-4`.

Optimizer interface (unchanged): `local_core.solve(case, method, seconds)` for `method ∈ {grid, slsqp, iwmmse}`; `matching_baseline.solve(case, seconds, seed=1101)`; `proposed(case, seconds)`; `case_rate(result, case)`; `local_core.GRID_LEVELS = (F(1,20), F(1,10), F(1,5))`. All read-only.

---

## 2. Validation questions, hypotheses, and outcome buckets

### 2.1 E1 — implementation fidelity

- **E1a (table transcription):** do the JSON tables reproduce TR 38.901 Table 7.7.1-1/2/3 (delays, powers, AoD/AoA/ZoD/ZoA, c_DS, c_ASD, c_ASA, c_ZSD, c_ZSA, XPR, number of clusters) to transcription tolerance?
- **E1b (model semantics):** does the generator's arithmetic implement the *stated* model ("cluster tables from TR 38.901, independent per-cluster phases, 100 ns delay spread, half-wavelength ULA, eight resources on first eight tones of a 50 MHz/32-tone grid") with no undisclosed deviation?

E1 is a deterministic audit, not a hypothesis test. Outcomes are `clean` / `approximation` / `bug` (see §3.3).

### 2.2 E2 — rate-conclusion robustness

Let `g_i` be the case-level relative gain of the proposed method over the strongest common-model baseline for case `i` under the Sionna channels (exact definition in §4.7). Let `M̂ = median_i g_i` and let `CI(M̂)` be a percentile-bootstrap 95% confidence interval (median-based). The original headline value is `M0 = 0.013104` (1.3104%).

- **H0 (not robust):** `M̂ ≤ 0`, i.e. the median case does not improve under an independent CDL realization, or the improvement is not distinguishable from zero (`CI(M̂)` lower bound ≤ 0).
- **H1 (robust in sign):** `M̂ > 0` and `CI(M̂)` lower bound > 0.

H1 is a *sign/direction* claim. H1 alone does not certify magnitude; magnitude agreement is handled by the band below.

### 2.3 Outcome buckets (combined E1 + E2 decision)

**(a) Generator validated and conclusion robust.**
E1a clean (zero transcription errors) **and** E1b finds only the already-disclosed simplifications (no undisclosed material deviation) **and** E2 satisfies ALL of §6 gates G1–G5 (positive median, CI excludes 0, magnitude within the band, ≥90% sign agreement, rank preserved).

**(b) Result robust in sign but the generator approximation is material.**
E2 satisfies the *sign* gates (M̂ > 0 and CI lower > 0) but fails at least one magnitude/rank/fidelity gate — e.g. M̂ outside the band, or E1b documents an undisclosed material deviation (such as the deterministic z-scored angle construction or single-ray-per-cluster), or the r distribution is materially different. The paper must reword the CDL claim as an *illustrative/simplified* CDL model and report the Sionna number alongside.

**(c) Result not robust.**
E2 fails a sign gate: `M̂ ≤ 0` or `CI(M̂)` lower bound ≤ 0. The CDL quantitative claim is withdrawn and the certified claim reverts to M=8 only.

The most likely honest landing zone is (b): the generator is openly a *simplified* CDL (single ray/cluster, no polarization/XPR, deterministic angular offsets), so E1b will flag deviations even if E2 shows the sign is robust.

---

## 3. E1 — table and implementation audit

### 3.1 E1a — table transcription

Compare each of `tables/CDL-{A,B,C}.json` against an authoritative transcription of TR 38.901 Tables 7.7.1-1 (CDL-A), 7.7.1-2 (CDL-B), 7.7.1-3 (CDL-C), plus the per-profile scalar parameters (c_DS, c_ASD, c_ASA, c_ZSD, c_ZSA, XPR, number of clusters) from the same table rows.

Reference values to hard-code in the audit script (these are the 3GPP-published numbers):

| Param | CDL-A | CDL-B | CDL-C |
|---|---|---|---|
| N clusters | 23 | 23 | 24 |
| c_DS (log10[s] mean) | -7.49 | -6.90 | -7.60 |
| c_ASD (deg) | 5 | 10 | 2 |
| c_ASA (deg) | 11 | 22 | 15 |
| c_ZSD (deg) | 3 | 3 | 3 |
| c_ZSA (deg) | 3 | 7 | 7 |
| XPR (dB) | 10 | 8 | 7 |

The delays, powers, and four angle vectors (AoD, AoA, ZoD, ZoA) for each profile must be transcribed from the 3GPP tables and hard-coded in `scripts/e1_table_audit.py` (the executor must source these from a second, independently obtained copy of the tables — e.g. the 3GPP spec PDF or the Sionna `tr38901` source constants — and note the provenance in `output/e1_audit.json`).

**Tolerances (E1a):** delays exact to `1e-4` absolute (table precision is 0.0001); powers exact to `0.05` dB absolute (table precision 0.1 dB); angles exact to `0.05` deg absolute (table precision 0.1 deg); c_ASD/c_ASA/c_ZSD/c_ZSA/XPR exact to `0.01`; number of clusters exact. Any mismatch above tolerance is a **transcription error** → E1a not clean.

### 3.2 E1b — model semantics (the important part)

Audit each step of `build_cdl.py` against the *stated* model and against the full TR 38.901 step-11 CDL procedure. Record, for each item, whether it is (i) correct, (ii) a disclosed simplification, (iii) an undisclosed simplification, or (iv) a bug. The items to audit:

1. **Power normalization** (line 32): `powers = 10^(dB/10); powers /= sum`. Correct (per-cluster powers normalized to unit total).
2. **Delay scaling** (line 47–48, 57): `freq = arange(S)*(50e6/32)`, `phase += 2π·freq·delay·100e-9`. This applies a *fixed* 100 ns delay spread (`delay_spread=100e-9`) rather than drawing DS ~ lognormal(c_DS). **Disclosed** ("100 ns delay spread"). Note: 100 ns is a fixed value, not the profile-specific c_DS; flag as a fixed-vs-drawn simplification. Also note the first-cluster delay is 0 for all profiles, so the phase reference is cluster 0.
3. **Angle construction** (lines 33–35, 51): `aoa = (aoa - mean)/std` (z-score of the *table AoA vector*), then `cluster_angles = theta[i] + cASA·aoa`. **This is a material, undisclosed deviation.** The TR 38.901 procedure draws, per cluster *n* and per user/drop, an i.i.d. Gaussian angular offset: `φ_n,AoA = φ_n,AoA,table + cASA·Z_n`, `Z_n ~ N(0,1)`. The generator instead uses a **deterministic**, **user-shared** z-scored table-angle pattern scaled by cASA. Consequences to record: (a) the angular offsets are identical for every user (only the rigid shift `theta[i]` differs), so the differential angular structure between two users' clusters is exactly zero beyond the pair separation — this mechanically ties `r` to the separation and the fixed `aoa` pattern; (b) cASA multiplies a unit-variance vector, which is dimensionally the same scale as a Gaussian std, but the *distribution* (fixed pattern vs random Gaussian) is different. **Verdict: undisclosed simplification (material), not a bug** — the generator is self-consistent, but it does not implement the TR 38.901 angle draw.
4. **Single ray per cluster** (lines 55–57): one ray per cluster (`sum over n of sqrt(p_n) a(θ_n) exp(...)`), no 20-ray/cluster expansion, no per-ray offsets (TR 38.901 Table 7.5-3). **Undisclosed simplification** (the paper's "cluster tables" disclosure does not state "one ray per cluster").
5. **Polarization/XPR ignored**: no 2×2 polarization matrix, no XPR (the `xpr` field is present in the JSON but never used). **Undisclosed simplification** (material only if dual-polarized arrays are claimed; the paper's ULA is single-polarization, so this is defensible but must be stated).
6. **Array response** (lines 21–23): `exp(jπ m sinθ)/sqrt(M)`, m=0..M-1, half-wavelength ULA, isotropic elements, no elevation. Correct for a half-wavelength scalar ULA. **Disclosed** ("half-wavelength ULA").
7. **Azimuth-only**: ZoA/ZoD are ignored (only `aoa` is used); the ULA is horizontal so elevation enters only via an element pattern, which is isotropic here. **Undisclosed simplification**, minor for M=2.
8. **Tone mapping** (line 47): 8 tones at spacing 50e6/32 = 1.5625 MHz, first tone at 0. **Disclosed** ("first eight tones of a 50 MHz/32-tone grid"). Note the first tone has zero frequency → no delay phase on tone 0.
9. **Unit-norm per tone** (line 58): each user's per-tone vector is normalized to unit norm, then scaled by `sqrt(gain)`. This discards the channel's natural path loss and imposes a fixed per-user gain. **Disclosed implicitly** via "per-user target SNR"; record as a fixed-SNR design choice.
10. **Independent phases** (line 52): `cluster_phases` uniform on [0,2π), independent per cluster, per user, per tone. **Disclosed** ("independent per-cluster phases"). Correct relative to the stated model (the full model couples phases across rays and polarizations; single-ray here).

### 3.3 E1 verdict mapping

- `clean`: E1a zero errors **and** every E1b item is either "correct" or "disclosed simplification".
- `approximation`: E1a zero errors but ≥1 E1b item is "undisclosed simplification" (expected: items 3, 4, and possibly 5, 7).
- `bug`: any E1a transcription error, or any E1b item classified "bug" (an internal inconsistency, wrong sign, wrong scaling, wrong cASA applied, wrong table column used, etc.).

E1 does not modify anything; it only reports. If a bug is found, the executor records it in `output/e1_audit.json` and flags the paper for a corrective note (but does **not** edit the paper — that is out of scope for this cross-check).

---

## 4. E2 — independent Sionna-generated CDL benchmark

### 4.1 Objective

For each of the 53 frozen cases, produce a new case that is **identical in every respect except the channel directions (and hence the pair correlations `r`)**, where the directions come from Sionna 2.2.0's TR 38.901 CDL model. Feed each new case through the **same** optimizer/baselines with the **same** settings, and compare the resulting rate conclusion to the frozen original.

### 4.2 Design decisions (pre-registered)

**(i) Per-user CDL instances with rotated receive array — PRIMARY.**
For each user `i`, generate an independent Sionna CDL link with:
- a **2-element half-wavelength ULA** as the receive array, oriented (rotated in azimuth) so that the user's cluster AoAs are shifted by `theta[i]` (the paper's per-user pair-centre angle);
- a **single-antenna** transmit array;
- `direction="uplink"` (UT→BS, so the 2-element ULA is the receiver and the paper's `aoa` = arrival angle at that array).

This reproduces the paper's `cluster_angles = theta[i] + cASA·aoa` structure (each user's clusters rigidly shifted by `theta[i]`), while Sionna supplies the TR 38.901 angle draw, 20 rays/cluster, and polarization machinery. A "one batch of independent realizations" without per-user angular positioning is **rejected as primary** because it would erase the pair-separation structure that the paper's design (and its `r` statistics) depend on; it is retained only as sensitivity E3-D (§5).

**Justification of the rotation sign:** the exact sign of the rotation that reproduces `+theta[i]` depends on Sionna's Euler/array-orientation convention. It is pinned by test T0b (§4.5) **before** E2 runs; the executor records the sign and the API used.

**(ii) Per-user SNR/gain matching — paired design, reuse exact target gains.**
The paper sets `gain_i = 10^((base_snr_i + offset_i)/10)/0.1` and then `h_i = sqrt(gain_i)·v_unit`. The cross-check **reuses the exact same `gain_i`** for every user (recovered from the frozen case), so the only quantity that changes between the frozen case and the Sionna case is `r`. This isolates the channel-*direction* effect from any gain/SNR effect.

**(iii) Reuse exact gains (paired) — PRIMARY; fresh draws — sensitivity.**
Primary is the paired design above. A fresh-draw sensitivity (E3-E) re-draws `base_snr` and offsets from the same distributions with a new seed, to bound how much the specific gain draws matter; it is labelled sensitivity and never substituted for the primary.

**(iv) Number of realizations per case: `N_real = 3` (PRIMARY), fallback `N_real = 1`.**
Sionna's CDL is stochastic (random per-cluster angle jitter, random coupling/phases). To average this Monte-Carlo noise, each case is realized `N_real = 3` times with independent Sionna draws; the case-level gain `g_i` is the **mean** of the 3 realization-level gains. `N_real = 3` is chosen to give a stable median while keeping wall-clock ≈ 1.5–2.2 h at the original 10 s/method budget. **Pre-registered fallback:** if wall-clock at the 50% mark (26 cases done) exceeds 1.5 h, the executor reduces `N_real` to 1 for the remaining cases and records the change in `RESULTS.md`; this is a *pre-registered* budget rule, not a post-hoc choice. The within-case realization SD is always reported so the reader can judge stability.

**(v) Intra-cluster rays, polarization/XPR, time variation.**
- **Intra-cluster rays:** keep Sionna's default 20 rays/cluster. This is the *point* of an independent check — it is a fuller model than the generator's single ray. No attempt to force Sionna to 1 ray/cluster.
- **Polarization/XPR:** use **single-polarization (vertical, "V") antennas on both arrays**, so Sionna produces a scalar per-antenna channel and XPR is structurally absent — matching the paper's polarization-free scalar model. A dual-polarized (cross-pol) Sionna run is sensitivity E3-F (isolates the XPR effect). This choice neutralizes XPR in the *primary* rather than introducing a feature the paper lacks.
- **Element pattern:** isotropic (`pattern="iso"`) to match the paper's isotropic ULA elements.
- **Time variation:** `num_time_steps = 1`, `min_speed = 0.0` (or the minimum Sionna permits). The paper's model is static; no Doppler.
- **Delay spread / carrier frequency:** `delay_spread = 100e-9` (matches the paper's fixed 100 ns); `carrier_frequency = 3.5e9` (arbitrary — path loss is discarded and we normalize per tone).
- **Normalization:** call `cir_to_ofdm_channel(frequencies, a, tau, normalize=False)`, then explicitly normalize each per-tone 2-element vector to unit norm and scale by `sqrt(gain_i)` (§4.6 step 4), mirroring `build_cdl.py` lines 58–59 exactly. This makes Sionna's `normalize` flag irrelevant (we re-normalize per tone) and removes any ambiguity.

### 4.3 Reference API (Sionna 2.2.0, CPU)

```
import sionna as sn
from sionna.phy.channel.tr38901 import CDL
from sionna.phy.channel import cir_to_ofdm_channel
from sionna.phy.channel import Antenna, AntennaArray, Array   # exact module path verified in T0

cdl = CDL(model="A", delay_spread=100e-9, carrier_frequency=3.5e9,
          ut_array=<1-elem V antenna/array>,
          bs_array=<2-elem ULA V, rotated by theta[i]>,
          direction="uplink", min_speed=0.0)
a, tau = cdl(batch_size=1, num_time_steps=1, sampling_frequency=50e6)
H = cir_to_ofdm_channel(frequencies=np.arange(8)*1.5625e6, a=a, tau=tau, normalize=False)
# H: complex [1, num_rx=2, num_tx=1, num_ofdm=8]  (squeeze to [2, 8])
```
The executor must verify the exact class/attribute names (e.g. `AntennaArray` vs `Array`, the `orientation` argument, and whether `cir_to_ofdm_channel` lives in `sionna.phy.channel` vs `sionna.channel`) against the installed Sionna in T0, and record them.

### 4.4 Case-geometry recovery (deterministic, no modification of frozen cases)

The frozen cases store `channels_re/im` and `pairs`, but not `theta` or the raw `gains`. The executor recovers them deterministically:

- **`recover_theta(profile, sep, seed) -> ndarray[16]`** replicates `build_cdl.py` lines 28–41: `rng = np.random.default_rng(seed)`; `centers = rng.uniform(-60, 60, size=8)`; `theta[2t] = centers[t] - sep/2`; `theta[2t+1] = centers[t] + sep/2`. (The RNG draws `centers` first, so this is exact.)
- **`recover_gains(case) -> dict[int, Fraction]`** reads any `pairs` record mentioning user `i`: `gain1` if `i == users[0]`, `gain2` if `i == users[1]` (gains are constant across resources).

**T1 (reproducibility self-check, MANDATORY before E2):** re-run the *paper's own* channel construction (import `build_cdl` logic as a function `paper_channel(profile, sep, seed)`) and confirm the resulting `pairs` (`gain1`, `gain2`, `r` strings) are **bit-identical** to the frozen case's `pairs` for all 53 cases (all 120 pairs × 8 resources = 960 records per case). This simultaneously proves the frozen cases are reproducible from the disclosed seed and that `recover_theta`/`recover_gains` are exactly correct. If T1 fails for any case, E2 for that case is blocked and the discrepancy is reported.

### 4.5 T0 — Sionna convention self-consistency (MANDATORY before E2)

- **T0a (array response):** evaluate Sionna's 2-element ULA response to a single plane wave at azimuth θ and confirm it equals the paper's `array_response(θ) = exp(jπ m sinθ)/sqrt(2)` (m=0,1) — or its complex conjugate — to `1e-6` per element. If it is the conjugate, record that `r` is invariant to a global conjugation (both users conjugated → `|<h_u,h_v>|²` unchanged) and proceed. Any *per-element* or *per-angle* mismatch beyond `1e-6` is a blocking convention error to resolve and document.
- **T0b (rotation sign):** with the ULA rotated by azimuth φ, confirm the effective AoA shift equals `±φ` and record the sign, so that the Sionna cluster AoAs are shifted by **`+theta[i]`** (matching the paper's `theta[i] + cASA·aoa`). The executor uses the sign that makes `effective_AoA = table_AoA + theta[i]`; the test records which orientation direction achieves this.
- **T0c (r invariance to conjugation/delay sign):** verify numerically on one Sionna link that `r` is unchanged when the frequency-response phase is conjugated and when the delay phase sign is flipped, confirming the paper's `+j2πfτ` vs Sionna's `−j2πfτ` is immaterial to `r`.

### 4.6 E2 case construction (per case, per realization)

```
def sionna_case(profile, sep, seed, gains, theta, realization, sionna_cfg) -> dict:
    tf.random.set_seed(SEED_BASE + case_ordinal*1000 + realization*10)   # see §4.9
    h = np.zeros((16, 2, 8), complex)
    for i in range(16):
        # 1. generate one link: 2-elem ULA rotated to theta[i] (receiver), 1-elem V TX
        a, tau = cdl_i(batch_size=1, num_time_steps=1, sampling_frequency=50e6)
        H = cir_to_ofdm_channel(frequencies, a, tau, normalize=False)      # [2, 8]
        # 2. normalize each tone to unit norm, scale by sqrt(gain)
        for t in range(8):
            v = H[:, t] / (norm(H[:, t]) + 1e-15)
            h[i, :, t] = sqrt(float(gains[i])) * v
    # 3. build pairs EXACTLY as build_cdl.py lines 60-83 (Fraction gain1/gain2/r),
    #    with channels_re = h.real.tolist(), channels_im = h.imag.tolist()
    return case_dict
```
Key: only the `h` source changes; the pair/gain/r construction (and its exact-rational `Fraction` arithmetic) is copied verbatim from `build_cdl.py`, so `gain1`/`gain2` are the exact `||h||²` of the stored channel and `r = Fraction.from_float(r_float)` with `r_float = |⟨h_u,h_v⟩|²/(||h_u||²||h_v||²)`. This keeps the stored vectors, pair gains, and `r` mutually consistent, which `matching_baseline`'s physical checks require.

### 4.7 E2 rate computation

For each Sionna case (53 cases × N_real realizations), run the optimizer exactly as `run_cdl.py` does: `seconds = 10`, `matching seed = 1101`, `GRID_LEVELS` override, methods `[grid, slsqp, iwmmse, matching, proposed]`. Compute `best_base` and `gain` per §1. Aggregate:

- realization-level `gain_{i,r}`;
- **case-level `g_i = mean_r gain_{i,r}`** (the unit of inference);
- **`M̂ = median_i g_i`** (primary statistic, analogous to the paper's median 1.31%);
- **median-bootstrap 95% CI** over the 53 `g_i` (percentile-of-medians, B=10000, seed 20261109), plus the mean-bootstrap CI for comparability with the paper's CI;
- **win count `Ŵ`** = # cases with `g_i > 1e-4`; ties/losses likewise;
- **`ρ`** = Spearman rank correlation between the 53 frozen original gains and the 53 Sionna `g_i`;
- **r-distribution diagnostics:** median `r` (original vs Sionna) over all pair/resource records, and the Kolmogorov–Smirnov `D` between the two empirical r CDFs (reported, not a hard gate).

### 4.8 Comparison anchor

The frozen reference (from `cdl_summary.json`, do not recompute):
`M0 = 0.013104`, mean `0.013068`, mean-CI `[0.011870, 0.014242]`, abs median `0.12918` bit/s/Hz, `wins=53, ties=0, losses=0`. Per profile: A `1.2118%`, B `1.3212%`, C `1.5187%`.

### 4.9 Seed hygiene

- Frozen case geometry: `recover_theta` uses the case's stored `seed` (no new randomness).
- Sionna RNG: reset the TensorFlow seed before each (case, realization) to a deterministic value `SEED_BASE + case_ordinal*1000 + realization*10`, where `case_ordinal` is the 1-based sorted index of the case (stable ordering by `name`). Within a case+realization the 16 user links are generated sequentially (the RNG advances naturally). Record the exact formula and `SEED_BASE = 20_261_110` in `output/env.json`.
- Optimizer: reuse the paper's fixed `proposed` internal seed `20261109` and `matching` seed `1101` — **unchanged** — so any optimizer stochasticity is identical to the original run.
- Do not reseed between the 5 methods within a case (same as `run_cdl.py`).

---

## 5. E3 — diagnostic ablation (isolates any E2 discrepancy)

E3 runs **only if** E2 lands outside bucket (a) (i.e. any magnitude/rank/fidelity gate fails while sign gates pass). Its purpose is to attribute the discrepancy to a *specific* model feature rather than leaving a bare mismatch. Each ablation produces its own case set through the same schema and optimizer, and its result is labelled `E3-<letter>`, reported separately, never substituted for E2.

- **E3-A (angle model) — FIRST:** run the *paper's own* generator but replace line 51 with an i.i.d. Gaussian draw: `cluster_angles = theta[i] + cASA * rng.standard_normal(len(delays))` (per cluster per user). This isolates the deterministic-z-score-vs-random-Gaussian angle effect. If E3-A's median gain ≈ E2's (within 20% relative of each other), attribute the discrepancy to the angle construction → "approximation material (angle model)".
- **E3-B (intra-cluster rays):** paper's generator expanded to 20 rays/cluster using TR 38.901 Table 7.5-3 per-ray offsets and per-ray phases (averaged over rays per cluster). Optional; run if E3-A does not explain the discrepancy.
- **E3-C (delay spread):** paper's generator with DS drawn from the profile's lognormal c_DS (or a few fixed DS values {33, 100, 126, 250} ns) to test sensitivity of `r` to the fixed-100 ns choice.
- **E3-D (angular positioning):** Sionna links without per-user array rotation (all arrays identically oriented) — bounds how much the rotation assumption matters.
- **E3-E (gain draws):** fresh `base_snr`/offset draws (new seed) with the paper's generator — bounds gain-draw dependence.
- **E3-F (polarization/XPR):** Sionna dual-polarized (cross-pol) arrays — isolates the XPR effect.

**Decision rule for E3:** report the ablation that best matches E2 (pre-registered criterion: smallest median-gain distance to E2's `M̂`, evaluated over E3-A/B/C). That single ablation is declared the attributed cause in `RESULTS.md`; all others remain listed as evidence. No ablation is used to *replace* the E2 verdict.

---

## 6. Acceptance criteria (pre-registered, binding)

### 6.1 Hard gates

| Gate | Definition | Threshold |
|---|---|---|
| G1 (E1a) | transcription errors | 0 (zero) |
| G2 (sign) | `M̂` | `> 0` **and** median-CI lower bound `> 0` |
| G3 (magnitude) | `M̂` in band | `0.00655 ≤ M̂ ≤ 0.01965` (i.e. [0.5×, 1.5×] of `M0=0.013104`) |
| G4 (sign agreement) | `Ŵ` | `≥ 48/53` |
| G5 (rank preservation) | Spearman `ρ` | `≥ 0.5` |

### 6.2 Decision tree

- **Bucket (a):** G1 ∧ G2 ∧ G3 ∧ G4 ∧ G5 all hold **and** E1b = `clean`.
- **Bucket (c):** G2 fails (`M̂ ≤ 0` **or** median-CI lower ≤ 0), regardless of everything else.
- **Bucket (b):** G2 holds but any of G1/G3/G4/G5 fails, or E1b = `approximation`.

### 6.3 Diagnostics (reported, affect wording/interpretation, not the bucket)

- Median `r` original vs Sionna, and KS `D` between the r CDFs. Flag `D > 0.35` as "r distributions materially differ" (supports a (b) interpretation and a "simplified model" reword).
- Per-profile median gains (A/B/C), within-case realization SD, and runtime.
- Any E1b "undisclosed simplification" list (feeds the wording change in §8).

### 6.4 No-silent-retune rule (binding)

- The primary configuration (per-user rotated receive array, single-polarization, `N_real=3`, paired gains, 10 s/method, Sionna 2.2.0) is **frozen**. If E2 disagrees with the paper, the executor reports **both** the original and the Sionna results and states the required wording change (§8). It must **not** go back and switch polarization, `N_real`, rotation, or any other knob to improve the outcome.
- If any *additional* configuration is run for diagnostic purposes, it is labelled `E3-*` or `sensitivity-*` and reported separately; it never replaces the primary E2 result in the bucket decision.
- If a pre-registered fallback is exercised (Sionna install failure, `N_real` reduction), it is recorded explicitly with the reason and the fact that independence may be reduced (see §7).

---

## 7. Run order, runtime, and failure fallbacks

Run in this order. Each step writes only under `phase3-cdl-crosscheck-20261110/`.

| Step | What | Est. runtime | Fallback / notes |
|---|---|---|---|
| 0 | Create dir; write `env/` capture (Python 3.12, numpy, Sionna 2.2.0, TF version, `pip freeze`); compute and record SHA-256 of this protocol file and of all frozen phase1 inputs into `SHA256SUMS` | <1 min | none |
| T0 | Sionna import + a/b/c convention tests | ~5 min | If Sionna import fails → E2 impossible; see fallback below |
| T1 | Reproducibility self-check (replay `build_cdl` against 53 frozen cases) | ~2 min | If any case fails, block its E2 row and report |
| E1 | Table + semantics audit (`scripts/e1_table_audit.py`) | ~5 min | needs only numpy + the hard-coded reference tables |
| E2-gen | Generate Sionna channels → cross-check cases (`scripts/e2_sionna_channels.py`) | ~10–20 min (53×3×16 links, tiny) | negligible; CPU |
| E2-run | Optimizer over Sionna cases (`scripts/e2_run.py`) | ~44 min (N_real=1) up to ~2.2 h (N_real=3) | pre-registered: drop `N_real`→1 at the 50% wall-clock guard (§4.2 iv) |
| E2-analyze | `scripts/e2_analyze.py` → `output/e2_summary.json` | ~1 min | none |
| E3 | Ablation (only if E2 ∉ (a)) | ~20–40 min | E3-A first; E3-B/C/F optional |
| Final | Write `RESULTS.md`, figures, final `SHA256SUMS` | ~5 min | none |

**If Sionna install fails or is too slow (CPU), the independent fallback is:**
- **Primary fallback:** a **from-scratch numpy reimplementation of the TR 38.901 step-11 CDL** written *independently of `build_cdl.py`* (fresh code, 20 rays/cluster, i.i.d. Gaussian angular offsets, per-ray phases, single-polarization), fed through the same case schema and optimizer. This preserves independence of *implementation* but is authored by the same team — so the result is reported as **"independent reimplementation (same-author), reduced independence"**, and the bucket decision is downgraded: bucket (a) is not reachable via this fallback (cap at (b)).
- **Absolute minimum fallback:** E3-A alone (internal angle-model ablation), reported as **"internal ablation only — not an independent cross-check"**. This does **not** satisfy the independence requirement and the CDL conclusion is reported as *not cross-checked* (the paper keeps its current disclosure, and the Sionna cross-check remains "pending").
- These fallbacks are pre-registered; they **do not silently weaken** the independence requirement — they re-label the evidence accordingly.

---

## 8. Documentation text (methods + results templates)

### 8.1 Methods paragraph (supplement; placeholders `{...}`)

> *Independent CDL cross-check.* To test whether the CDL observation is an artifact of the simplified generator, we re-derived the 53 K=16, M=2 cases with an independent 3GPP TR 38.901 CDL-A/B/C realization using Sionna v2.2.0 (CPU), keeping K, M, the eight resources, `p_min`/`p_max`, the sum-power budget, the pairing separations, the case seeds, and the per-user target SNRs identical. For each user we generated a single-polarization CDL link with a two-element half-wavelength ULA whose azimuth orientation reproduces the user's pair-centre angle, one time sample (no Doppler), and a 100 ns delay spread, then normalized each tone to unit norm and reapplied the same per-user gain. For every case, `{N_real}` independent realizations were averaged. Each resulting case was fed through the same solver and baselines as the main experiment. The Sionna model differs from the hand-rolled generator in that it includes twenty rays per cluster, i.i.d. Gaussian per-cluster angular offsets, and (in a sensitivity) polarization/XPR.

### 8.2 Results sentence templates

- **Outcome (a) — validated/robust:**
  > Under the independent Sionna CDL realization, the proposed method still beats the strongest common-model baseline on all 53 cases, with median relative gain `{M̂*100:.2f}%` (95% CI `[{lo*100:.2f}%, {hi*100:.2f}%]`; `{Ŵ}` wins / `{ties}` ties / `{losses}` losses), consistent with the hand-rolled generator's `1.31%`. Rank correlation between the two realizations is `{ρ:.2f}`.

- **Outcome (b) — robust in sign, approximation material:**
  > An independent Sionna CDL realization preserves the *sign* of the advantage — median relative gain `{M̂*100:.2f}%` (95% CI `[{lo*100:.2f}%, {hi*100:.2f}%]`, `{Ŵ}/53` positive) — but the magnitude `{relation to 1.31%: higher/lower}` differs from the hand-rolled generator. We attribute this to `{E3-attributed cause: the generator's deterministic z-scored cluster-angle construction / single-ray-per-cluster / fixed 100 ns delay spread}`. Accordingly, the CDL model in this paper is best regarded as a simplified, illustrative CDL-A/B/C model rather than a faithful realization of the full step-11 procedure; both numbers are reported, and no certified-rate claim is made at M=2.

- **Outcome (c) — not robust:**
  > Under an independent, standard-compliant CDL realization the median advantage is `{M̂*100:.2f}%` with a 95% CI whose lower bound is `{lo*100:.2f}%` (non-positive), so the CDL-based advantage does not survive an independent channel model. We therefore withdraw the quantitative CDL claim and restrict the certified result to the M=8 case. The CDL numbers remain available as an illustrative exercise in the artifact, clearly labelled as not reproduced.

In all outcomes, append the boundary sentence (already true in the paper and not to be weakened):
> No certified-rate claim is made at M=2; the certified result remains at M=8.

---

## 9. Artifact layout (all under `phase3-cdl-crosscheck-20261110/`)

```
CROSSCHECK_PROTOCOL.md        <- this file (frozen)
README.md                     <- 1-paragraph pointer + status
env/
  pip-freeze.txt, python-version.txt, sionna-version.txt, tf-version.txt, machine.txt
scripts/
  common.py                   <- constants, recover_theta, recover_gains, Fraction helpers
  t0_sionna_conventions.py    <- T0a/b/c
  t1_reproducibility.py       <- T1
  e1_table_audit.py           <- E1a/E1b (hard-coded reference tables + provenance)
  e2_sionna_channels.py       <- E2 channel generation -> cases/
  e2_run.py                   <- optimizer over cross-check cases (mirrors run_cdl.py)
  e2_analyze.py               <- M̂, CI, Ŵ, ρ, KS, figures
  e3_ablation.py              <- E3-A/B/C/D/E/F
tables/                       <- authoritative reference tables used by E1 (provenance-tagged)
cases/                        <- generated Sionna cross-check case JSONs (read-only after gen)
output/
  e1_audit.json, e1_audit.csv
  e2_summary.json             <- primary statistics + bucket verdict
  e2_cases.csv                <- 53 rows: name, profile, sep, seed, orig_gain, g_i, SD
  e2_realizations.csv         <- 53*N_real rows: realization-level gains
  e3_summary.json
  figures/
    gain_scatter_orig_vs_sionna.{png,pdf}
    r_cdf_overlay.{png,pdf}
    bootstrap_histogram.{png,pdf}
  logs/                       <- stdout/stderr per step
frozen_inputs/manifest.json   <- list of phase1 paths hashed + their SHA-256 (provenance)
SHA256SUMS                    <- checksums of this protocol, frozen inputs, and all outputs
RESULTS.md                    <- executor-written summary + bucket + wording change (if any)
```

The 53 original cases remain frozen and read-only: they are only read and hashed into `frozen_inputs/manifest.json`.

---

## 10. Scientific risks and threats to validity

1. **Sionna CDL ≠ the generator (by design).** Sionna includes 20 rays/cluster and random per-cluster per-user Gaussian angle offsets and coupling, so its `r` distribution will differ from the generator's (`r` median 0.46–0.56 reported for the generator). This is the quantity being tested, not a bug — but it means bucket (a) is genuinely hard to reach.
2. **Per-user orientation implementation.** The rotation sign/convention is the most error-prone step; mitigated by T0a/T0b and by requiring bit-exact reproduction in T1.
3. **Polarization/XPR.** Neutralized in the primary by single-polarized arrays; cross-pol kept as sensitivity E3-F. The generator ignores XPR entirely; if the paper were ever read as dual-polarized, this is an undisclosed gap (E1b item 5).
4. **`normalize=True` ambiguity.** Neutralized by using `normalize=False` and explicit per-tone normalization that mirrors the generator.
5. **OFDM vs continuous tone phase reference / delay sign.** Both use first tone at 0 Hz and a `+j2πfτ` vs `−j2πfτ` sign; verified immaterial to `r` in T0c (conjugation invariance). The first cluster delay is 0 in all profiles, so the phase reference is well-defined.
6. **Fixed 100 ns delay spread.** Overstates the profile-specific c_DS for A (~33 ns) and C (~25 ns), raising frequency selectivity and lowering `r`; E3-C tests sensitivity. This is a disclosed simplification but a potential magnitude driver.
7. **Finite-sample noise (53 cases; N_real=3).** Reported via bootstrap CI and within-case SD. The CI is the primary guard against sampling noise; the 53-case sample is fixed (not resampled from a superpopulation), so the CI is a descriptive uncertainty, not a design-based inferential guarantee.
8. **Selection / multiple-comparison risk.** Mitigated by pre-registration: the primary configuration, `N_real`, seeds, band, and gates are frozen before E2. Any alternative configuration is labelled sensitivity and never substituted. The decision tree (§6.2) is applied once.
9. **Stochastic optimizer.** The baselines and `proposed` are themselves stochastic (multistart, `matching` seed 1101). Reusing the identical seeds/seconds as the original run makes the original-vs-Sionna comparison matched on optimizer stochasticity; residual optimizer noise is shared across both.
10. **Data-dependent "strongest baseline" selection.** Both the original and E2 select the max over 4 baselines per case; this identical, mildly optimistic procedure is applied to both, so the *contrast* is unbiased.
11. **Sionna version dependence.** Pin `sionna==2.2.0`; record exact version and RNG seeds. A different minor version may change internal defaults; do not upgrade mid-run.

---

## 11. Reference API (concrete signatures and field names)

```python
# common.py
PROFILES = {"A": {"cASA": 11.0, "xpr": 10.0, "n_clusters": 23, "cDS_lg": -7.49},
            "B": {"cASA": 22.0, "xpr":  8.0, "n_clusters": 23, "cDS_lg": -6.90},
            "C": {"cASA": 15.0, "xpr":  7.0, "n_clusters": 24, "cDS_lg": -7.60}}
K, S, M = 16, 8, 2
PMIN, PMAX, BUDGET = "1/1000", "1/5", "52/25"       # budget = 13/100 * 16
TONE_SPACING_HZ = 50e6 / 32                          # 1.5625e6
DELAY_SPREAD_S  = 100e-9
N_REAL          = 3                                  # primary (fallback 1)
SEED_BASE       = 20_261_110
SECONDS         = 10.0                               # per method
MATCHING_SEED   = 1101
GAIN_EPS        = 1e-4                               # win/tie/loss threshold (same as paper)

def recover_theta(seed: int, sep_deg: float) -> np.ndarray: ...   # shape (16,)
def recover_gains(case: dict) -> dict[int, Fraction]: ...          # user -> exact gain
def paper_channel(profile: str, sep_deg: float, seed: int) -> dict: ...  # returns full case dict (T1)
def sionna_link(profile: str, theta_deg: float, cfg: dict): ...    # -> complex[2,8] frequency response
def sionna_case(profile: str, sep_deg: float, seed: int, case_ordinal: int,
                gains: dict[int, Fraction], theta: np.ndarray,
                realization: int) -> dict: ...                      # same schema as frozen cases
def run_optimizer(case: dict, seconds: float = SECONDS) -> dict:   # {method_rate, method_status, method_time}
def case_gain(result: dict) -> float: ...                           # (proposed - best_base)/best_base

# e2_analyze.py
def summarize(cases_gains: dict[str, list[float]]) -> dict:         # M̂, CI_mean, CI_median, Ŵ, ρ, KS_D
def bootstrap_median(v, B=10000, seed=20261109) -> tuple[float, float]: ...
def spearman(orig: list[float], sionna: list[float]) -> float: ...
```

Field names in `e2_cases.csv`: `name, profile, separation, seed, orig_gain, sionna_gain_case_mean, sionna_gain_sd, n_real`. In `e2_summary.json`: `n_cases, n_real, M_hat, M0, ci_mean, ci_median, wins, ties, losses, spearman_rho, ks_D, r_median_orig, r_median_sionna, bucket, gates{G1..G5}, e1_verdict`.

---

## 12. Pre-registration statement

This protocol was finalized **before** any E2/E3 result was produced. The executor must, at Step 0, write the SHA-256 of this file into `RESULTS.md` and then execute the run order verbatim. Any deviation (including exercising a pre-registered fallback) is recorded with a reason; no decision threshold in §6 may be edited after the fact. If the protocol and results diverge, the protocol text governs the interpretation.
