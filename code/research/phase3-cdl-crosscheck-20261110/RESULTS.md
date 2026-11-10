# Independent 3GPP CDL cross-check — results

**Paper:** *MMSE Pair Scheduling: Computational Complexity and Certified Power Allocation*
**Protocol:** `CROSSCHECK_PROTOCOL.md` (SHA-256 `F1F8739774F2F185EF4CC1B179650D5BCCD6068CB6FDB3FC00D78AF5E9C1C2C8`)
**Status:** E1, E2 and E3-A complete. Bucket **(b)**: sign and magnitude robust; the hand-rolled generator is a simplified CDL realisation.

---

## 1. What was checked

Two separate questions were kept apart:

1. **Implementation fidelity (E1).** Are the TR 38.901 tables correct, and is the generator a faithful implementation of what the paper claims?
2. **Rate-conclusion robustness (E2).** Does the 1.31% CDL advantage survive when the channel directions come from an independent, full Sionna 2.2.0 CDL realisation?

The 53 frozen phase-1 cases were read-only throughout. All new files are under
`research/phase3-cdl-crosscheck-20261110/`.

## 2. T0/T1 integrity gates

- **T1 (bit-exact replay): 53/53 cases.** Re-running the paper's generator from the stored seeds reproduces all 960 pair records per case exactly (`gain1`, `gain2`, `r` strings) and every stored channel norm. The frozen cases are reproducible.
- **T0 (Sionna conventions).** The Sionna two-element ULA response matches `exp(jπm sinθ)` to `3.2e-8`; `bs_orientation=[φ,0,0]` maps GCS AoA `θ` to `θ−φ` exactly; global conjugation leaves `r` unchanged.
- The profile-mean table AoA (`A` 10.92°, `B` −6.22°, `C` 36.52°) was removed by the per-user array rotation, so each user's mean cluster angle equals its pair-centre angle.

## 3. E1 — table and semantics audit

**E1a: zero transcription errors.** Delays, powers, AoD/AoA/ZoD/ZoA, `cASD`, `cASA`, `cZSD`, `cZSA`, XPR and cluster counts in `tables/CDL-{A,B,C}.json` match the independent Sionna 2.2.0 copy of TR 38.901 V19.2 within `1e-4` (delays), `0.05` dB (powers), `0.05°` (angles) and `0.01` (scalars).

**E1b: `approximation`, not `bug`.** The generator is internally consistent, but it is a simplified step-11 realisation:

| Item | Verdict |
|---|---|
| Power normalisation | correct |
| Fixed 100 ns delay spread | disclosed simplification |
| Deterministic z-scored cluster-angle offsets | **undisclosed material simplification** |
| One ray per cluster (no 20-ray expansion) | **undisclosed simplification** |
| Polarisation/XPR ignored | undisclosed simplification |
| Half-wavelength ULA, isotropic, azimuth only | disclosed simplification |
| First 8 tones of a 50 MHz/32-tone grid | disclosed simplification |
| Unit-norm per-tone channel with fixed per-user gain | disclosed design choice |
| Independent per-cluster/per-user/per-tone phases | correct for the stated model |
| Elevation (ZoA/ZoD) unused | undisclosed minor simplification |

The key deviation is that TR 38.901 draws i.i.d. Gaussian per-cluster angular offsets per drop, whereas the generator applies one deterministic z-scored pattern, shared by all users, scaled by `cASA`.

## 4. E2 — independent Sionna benchmark

**Design (pre-registered primary):** per-user CDL links, two-element half-wavelength ULA rotated so the profile-mean AoA lands on the user's pair centre, single-polarised isotropic elements, 20 rays/cluster, i.i.d. Gaussian angular offsets, one time sample, 100 ns delay spread, Sionna 2.2.0. The frozen per-tone gains, powers, separations, tones and case seeds were reused, so only the channel directions changed. Each case was averaged over **three independent Sionna draws**; the unit of inference is the 53 case-level means.

**Results (53 cases, 159 case-realizations):**

| Statistic | Hand-rolled (primary) | Sionna 2.2.0 |
|---|---:|---:|
| Median relative gain | 1.31% | **1.65%** |
| Median 95% CI | [1.19, 1.42]% | **[1.57, 1.74]%** |
| Mean relative gain | 1.31% | 1.64% |
| Absolute median gain | 0.129 bit/s/Hz | **0.155 bit/s/Hz** |
| Wins / ties / losses | 53 / 0 / 0 | **53 / 0 / 0** |
| Median `r` | 0.504 | 0.528 |
| 90th percentile `r` | 0.921 | 0.913 |
| Runtime, proposed (median) | 5.5 s | 6.0 s |

- **Kolmogorov–Smirnov `D = 0.038`** between the two empirical `r` distributions: the correlation laws are close. (The `p`-value is tiny only because each distribution has tens of thousands of samples; `D` is the informative statistic.)
- **Spearman rank correlation of per-case gains `ρ = 0.189`.** The two models agree on the population-level advantage but not on the ordering of individual cases.
- Per-profile Sionna medians: A 1.59%, B 1.71%, C 1.62% (all positive).
- Median within-case realisation SD: 0.00165 (0.165 percentage points), small relative to the 1.65% median.

### Pre-registered gates and verdict

| Gate | Result | Pass |
|---|---|---|
| G1: zero table-transcription errors | 0 errors | yes |
| G2: median > 0 and median-CI lower > 0 | 1.65%, CI lower 1.57% | yes |
| G3: median in [0.5×, 1.5×] × 1.31% = [0.655%, 1.965%] | 1.65% | yes |
| G4: ≥48/53 positive cases | 53/53 | yes |
| G5: Spearman ρ ≥ 0.5 | 0.189 | **no** |
| E1b clean | `approximation` | **no** |

**Bucket (b).** The sign and population magnitude of the advantage survive a fuller, independent CDL realisation; per-case ranking does not. Because E1b also identifies material simplifications, the correct reading is:

> The 1.31% result is a **simplified-CDL** result. An independent Sionna 2.2.0 realisation gives **1.65% [1.57, 1.74]%** with **53/53 wins**, so the conclusion is not an artifact of the simplified generator, but the model should not be described as a faithful step-11 realisation. No certified-rate claim is made at M=2; the certified result remains M=8.

## 5. E3-A — angle-model ablation

E3-A replaces only the deterministic z-scored cluster angles with i.i.d. `N(0, cASA²)` offsets, holding the frozen gains and phases fixed. It isolates the angle construction flagged by E1b.

| Arm | Median | 95% CI | W/T/L | Abs. med. |
|---|---:|---:|---:|---:|
| Hand-rolled primary | 1.31% | [1.19, 1.42]% | 53/0/0 | 0.129 |
| Sionna 2.2.0 | 1.65% | [1.57, 1.74]% | 53/0/0 | 0.155 |
| E3-A Gaussian angles | **1.58%** | **[1.52, 1.79]%** | 53/0/0 | 0.152 |

The E3-A median is **4.6%** away from the Sionna median, inside the pre-registered 20% attribution band. Replacing the deterministic angular pattern alone therefore accounts for most of the 1.31%→1.65% magnitude shift. The residual is consistent with Sionna's 20 rays per cluster, elevation and frequency selectivity. This is the expected mechanism: the original generator applies one z-scored table pattern to every user, whereas TR 38.901 draws independent Gaussian offsets per user and drop.

## 6. Consequences for the documents

- **Paper 2:** the benchmark paragraph now discloses the simplified realisation; a new “Independent Sionna cross-check” subsection and table report 1.65% / 53 wins; the limitations paragraph reports the cross-check; the abstract adds one sentence. The primary 1.31% number is retained and the Sionna number is reported as a robustness check.
- **Proposal:** the 1.31% claim is retained, “مدل استاندارد” is softened to “مدل 3GPP CDL” where it described the realisation, and a sentence reports the independent 1.65% check. The English/LTR footnotes introduced on 10 Nov were preserved; the DOCX was edited in place, not regenerated from the old footnote script.

## 7. Artifact map

```
CROSSCHECK_PROTOCOL.md      frozen protocol
scripts/                    step0, T0, T1, E1, E2 generation/run/analysis, E3-A, merge, sums
cases/                      159 Sionna case JSONs
cases_e3a/                  53 E3-A case JSONs
output/e1_audit.json        table + semantics audit
output/e2_summary.json      gates, bucket, CIs, diagnostics
output/e2_cases.csv         53 case-level rows
output/e2_realizations.csv  159 realisation-level rows
output/e3_summary.json      E3-A result and attribution
output/figures/             scatter, r-CDF overlay, bootstrap histogram
env/                        Python/Sionna/Torch versions, pip freeze
frozen_inputs/manifest.json hashes of all frozen phase-1 inputs
SHA256SUMS                  checksums of the artifact
```

## 8. Reproduction

```powershell
$py = "C:\Users\p.hejazi\AppData\Local\Temp\opencode\cdlvenv\Scripts\python.exe"
$d  = "D:\PostDocProposal\PostDocPaper2\research\phase3-cdl-crosscheck-20261110"

& $py "$d\scripts\step0_init.py"
& $py "$d\scripts\t0_sionna_conventions.py"
& $py "$d\scripts\t1_reproducibility.py"
& $py "$d\scripts\e1_table_audit.py"
& $py "$d\scripts\e2_sionna_channels.py" --n-real 3
& $py "$d\scripts\e2_run.py" --seconds 10
& $py "$d\scripts\e2_analyze.py"
& $py "$d\scripts\e3a_gaussian_angles.py"
& $py "$d\scripts\e2_run.py" --cases-dir "$d\cases_e3a" --glob "*-e3a.json" --out e3a_results.csv
& $py "$d\scripts\e3_analyze.py"
& $py "$d\scripts\make_sums.py"
```

The optimizer run used four concurrent single-threaded workers on an 8-core CPU for the remaining cases after a sequential start; each method retained its frozen 10 s wall-clock budget. The sequential partial CSV is preserved as `output/e2_results_seq_partial.csv`.

## 9. Honest limitations

- Sionna’s CDL is a fuller model, not ground truth; it includes 20 rays/cluster, random coupling, elevation and frequency selectivity that the simplified generator omits.
- The 53 cases are a fixed, seed-reproducible population; the bootstrap intervals are descriptive, not design-based confidence guarantees.
- The per-case rank ordering is not stable across models (`ρ = 0.19`); do not use these numbers to rank individual cases.
- The CDL rate gains remain feasible and verified, not globally certified.
