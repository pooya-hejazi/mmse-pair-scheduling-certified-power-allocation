# Adaptive price-guided search on native CDL channels

The study tests whether an equal-power marginal screen can save search time while preserving mean achieved uplink spectral efficiency. It uses 20 independent blocks, each with CDL-A, B and C populations at 0, 10 and 20 dB. All five methods receive the same eight available starts, the same channel and power constraints, a ten-second search allowance and five-second local SQP limit. Each population contains 16 users, eight resources and two receive antennas. [Prospective protocol](PROTOCOL.md)

At the exact equal-power assignment the adaptive method computes each user's dimensionless marginal `(P/K) ∂R/∂p_i`. If the smallest marginal is at least 0.90, it completes one DP–SQP trajectory. Otherwise it uses up to six price trials and a second start. The full price method allows 14 trials and eight starts. Each method ran serially with one numerical thread and a generic historical warmup. The timing includes the screen, dispatch, pricing and all search work. [Implementation](method.py) · [Recorded environment and source hashes](source_manifest.json)

## Results

Relative to full Price–DP–SQP, adaptive search lost **0.000288 bit/s/Hz** on average. The 95% whole-block interval for adaptive minus full was **[−0.000863, 0]**. The geometric mean ratio of paired warm search times was **0.2148 [0.2041, 0.2236]**. The lower rate endpoint exceeded the prespecified −0.001 bit/s/Hz margin and the upper time endpoint fell below 0.5. Arithmetic mean times were 0.211 s and 0.698 s. [Primary and control contrasts](analysis/results.json)

The two methods returned identical final assignments and powers in 179 of 180 cases. In block 1 at CDL-B and 10 dB the minimum marginal was 0.9290, the screen skipped pricing, and the rate fell from 10.90051 to 10.84875 bit/s/Hz. The screen passed on 0 of 60 cases at 0 dB, 4 of 60 at 10 dB and all 60 at 20 dB. With pricing active on every case, the six-trial, two-start version reproduced all 180 full-price allocations and used a geometric 0.4025 [0.3972, 0.4074] of full search time. This direct shortened/full comparison is a descriptive post-holdout analysis. Relative to the shortened version, adding the screen used a geometric 0.5338 [0.5086, 0.5539] of its time. [Paired case values](analysis/case_values.csv) · [Shortened/full comparison and 20 block effects](analysis/short_price_vs_full.json)

All 900 reported allocations passed independent rate and feasibility checks. The audit also replayed 3,460 retained events and verified all 180 equal-power assignment optima and marginal decisions. The rate criterion concerns the mean across the tested populations. The timing evidence covers this warmed, single-thread host. [Independent replay receipt](analysis/audit.json)

## Reproduce the saved results

Run these commands from the **repository root** with Python 3.13. The optimizer used Python 3.13.5, NumPy 2.3.4, SciPy 1.16.3 and Numba 0.62.1.

```sh
python -m pip install -r code/requirements.txt
python -B reproduce.py --only adaptive --output replay-adaptive
```

The replay restores the 180 cases, checks the raw allocations, recomputes the block bootstrap and places results under `replay-adaptive/adaptive/`. The 180 files in `runs/main/*.json.gz` each contain all five arms, eight common starting allocations, retained histories, final schedules with rational per-user powers, component times and work counts. Each result identifies its warmup process. The case, block and condition tables are stored in `analysis/`.

To run the generator check alone in the solver environment, use the first command below. The second command regenerates all 960 original user links from their registered seeds and compares their impulse responses, delays and tone responses bit for bit. It uses the generation environment with Python 3.12.10, NumPy 2.5.4, CPU Torch 2.15.0 and Sionna 2.2.0. The generator specification gives the full channel-generation procedure. [Generator and compact input format](GENERATOR.md)

```sh
python -B code/research/adaptive-pricing-20261111/generate.py verify
python -B code/research/adaptive-pricing-20261111/generate.py verify --regenerate-links
```

## Repeat the timed optimization

Use a fresh output directory for a timed repeat. These commands reuse the registered channels and initialization seeds, run all 900 searches, audit the new allocations and compute both the prespecified and supplemental comparisons. The solver checkpoints after each arm, so the same command resumes an interrupted run. Wall times can vary with the numerical environment and competing host activity.

```sh
python -B code/research/adaptive-pricing-20261111/run_study.py run --output adaptive-repeat/runs
python -B code/research/adaptive-pricing-20261111/audit_analysis.py --runs adaptive-repeat/runs --output adaptive-repeat/analysis
python -B code/research/adaptive-pricing-20261111/short_price_contrast.py --runs adaptive-repeat/runs --audit adaptive-repeat/analysis/audit.json --output adaptive-repeat/analysis/short_price_vs_full.json
```

For the supplemental comparison by itself on the published evidence, run `python -B code/research/adaptive-pricing-20261111/short_price_contrast.py --output replay-short-price.json`. It checks all 180 compressed input hashes against the independent run audit, compares each final assignment and its powers, and recomputes the paired rate and time estimates with the study's 20,000 reserved whole-block resamplings.
