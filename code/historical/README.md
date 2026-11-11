# Historical numerical evidence

Run from the checkout with Python, NumPy, SciPy and psutil installed. The archived analyses used NumPy 2.3.4 and SciPy 1.16.3. Allow several minutes and about 450 MB of temporary disk space.

    python -B code/historical/replay.py --output historical-replay.json

Use a new output filename. Omitting the output argument prints JSON. The command works from any directory when invoked by its absolute script path. It exits zero once all checks pass. The optional `--seconds 600` raises each bounded checker’s replay allowance on a slower machine. Replay reads the saved runs and writes temporary working copies. Generating new channels, fitting estimators or timing optimizers is a separate experiment.

## Studies and coverage

| Archive in `data/historical/` | Saved evidence and numerical checks |
| --- | --- |
| `s10-development-science.zip` | The original fixed-CSI analysis recomputes the 120 paired observations, Student-t and 10,000 paired-bootstrap intervals, and estimation-error/minimum-rate tables from 1,440 saved rows. Replay checks 54 learned-policy groups, the nine tested development settings, four acquisition contrasts, finite-grid opportunity, nine grid-MILP allocations including the 95%-throughput targets, and nine saved CPU/GPU vectors. All four initial GPU timeouts stay in the record. |
| `s10-four-ap-science.zip` | The original independent checker revisits 32 derived case inputs, 176 saved operational records and their schedules, and 10,368 channel-pair geometry rows. The original analysis recomputes the planned Full/reference comparison and its normal-process-return sensitivity. Original candidate/receipt files, timing failures and incomplete pricing are included. Historical global-upper proof trees were not retained. |
| `r1-science.zip` | Both original and corrected 128-cell studies. Each campaign is replayed against its own frozen inputs, including the corrected channel realizations and noise scaling. The original analysis regenerates its summary and cell CSV. The R4 completeness repair drives the unchanged independent R1 bound verifier on 590 original and 700 corrected timely receipts. Original PNG/SVG figure exports, source data and plotting code are retained. |
| `r2-science.zip` | 52 common starts, 260 main cells and 40 diagnostic arms on eight orthogonal reference cases. The original numerical and bootstrap routines verify retained schedules, every timely receipt chain and the registered 44-case, 11-group analysis. Reference upper bounds are checked for saved coverage and consistency. Independent reconstruction of each orthogonal assignment upper would require the missing dual witnesses. |
| `r3-science.zip` | The original diagnostics extractor regenerates the 220-row search-coverage table, per-arm summaries, input hashes and all 44 display contrasts from the R2 archive. Missing diagnostics retain the recorded missing values. |
| `r4-science.zip` | The original replay checks both endpoints of 220 matched cells, their 44 common starts, overall summaries and paired contrasts. Four six-assignment global bundles cover two physical cases and two arithmetic fixtures. The two physical cases also supply ten independently checked initial/final kernel comparisons and deficits. The incomplete matched development run is retained separately from the completed 44-case study. |

## Provenance and scope

Each ZIP contains a new `SCIENCE-MANIFEST.json` with the upstream container name and SHA-256 and the original path, size and SHA-256 of every retained member. The new public container digests are pinned in `replay.py`. The builder matched the five upstream source-container hashes and checked each retained member against its original inventory where available. The 332 R2 gzip members contain worker-diagnostics JSON. S10 NPZ members contain numeric NumPy arrays. Older manifests may record absolute original paths, omitted ancillary files or hashes of the original private distributions.

R2’s original launcher required the entire private R1 ZIP. The public entrypoint replaces that container-integrity step with the public archive digests, exact member manifests and the original pinned independent checker. The original R2 numerical routines and source-freeze checks still run.

S10 replay verifies saved statistics and encoded schedules within the coverage above. It does not regenerate estimator outputs from external propagation data or learned model checkpoints, reconstruct historical GPU wall times, or establish global bounds where proof trees are missing. The limited 95%-throughput minimum-power target permits a rate loss. Numerical comparisons refer to the indicated matched models and experimental designs.
