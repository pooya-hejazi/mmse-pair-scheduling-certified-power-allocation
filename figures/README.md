# Article and supplementary figures

The [current figure index](manifest-tcom.json) maps each asset to its placement in the article or supplement. The [preceding 29-asset index](manifest-priced.json) describes the earlier edition.

Run `python reproduce.py --only figures --output rebuilt-figures` from the repository root to redraw the edition. The original 27 assets, the [three-profile price-guided comparison](priced_cdl_comparison.pdf), the [prespecified rate and time endpoints](priced_cdl_endpoints.pdf), and the three comparisons below have matching high-resolution PNGs.

## Additional main-article CDL comparisons

Rebuild the three comparison figures and their adjacent plotted-data CSVs with
`python -I -B figures/sources/cdl_margins.py --output rebuilt-comparisons` from the repository root.
The full edition command above also calls this generator. It reads the final JSON run records and checks their audit hashes.

| Figure | Inputs and interpretation |
| --- | --- |
| [Assignment and power restrictions](native_assignment_power_margins.pdf) · [18 plotted means and intervals](native_assignment_power_margins.csv) | In the first independent sample, DP–SQP minus Fixed–SQP and DP–uniform uses the same block, profile and SNR. Each point averages 20 paired differences. Both intervals and means are checked against the archived cell estimates. |
| [Price-guided margins across SNR](priced_snr_margins.pdf) · [12 plotted means and intervals](priced_snr_margins.csv) | In the fresh sample, each block averages three paired profile differences at a given SNR. The 20 blocks receive equal weight. DP–SQP was the unique strongest control on every fresh case under the archived exact objective comparison. Panel (b) resolves the separation between the two near-coincident price-guided margins in panel (a). Averaging the three SNR means reproduces each published overall comparator mean. |
| [Certified gap coverage](native_certified_coverage.pdf) · [80 checked allocations and empirical counts](native_certified_coverage.csv) | Each of the 20 prespecified CDL-B/10 dB cases supplies one common upper bound from its hash-checked passing replay witness. The original rational checker reconstructs the case, verifies the final schedule and powers for each arm, and evaluates that arm’s own feasible lower bound. The gap uses a lower enclosure of 8 ln 2. The table includes exact rational endpoints and an upward-rounded decimal tolerance (12 decimal places) for each step. All 20 price-guided endpoints must equal the archived rational values. |

SE differences and gap tolerances use occupied-band bit/s/Hz. The first two figures use pointwise 95% percentile intervals from 20,000 draws of the 20 paired blocks and the original study-specific bootstrap seeds. The coverage curves count the specified cases exactly; they do not estimate a population distribution.

## November 10 independent-CDL release

The 27 PDFs are the vector files placed in the main article and supplement. The adjacent PNGs are the original plotting-program exports. `manifest.json` records the SHA-256 digest of both formats, the release figure number, the source group and the LaTeX labels present in that figure. The main article uses two images in Figure 1 and two in Figure 5. Supplementary Figure S15 also uses two images.

From the repository root, verify the released PDF and PNG files with

```sh
python -I -B figures/reproduce.py --verify-only
```

Regenerate the scientific figures and repeat the receive-dimension calculation with

```sh
python -I -B figures/reproduce.py --output replayed-figures --recompute-m-scan
```

Choose a new or empty output directory. The command writes PDFs, PNGs, a figure-replay receipt and an M-scan subdirectory. The receive-dimension replay reconstructs channel gains and correlations after truncation, then runs resource-labelled assignment DP using the archived floating-point rate weights. It checks all 96 rows against the retained table and every archived summary. The main M-scan plot connects all 32 cases at 2, 4 and 8 receive coordinates. Omit `--recompute-m-scan` to make the plots directly from the saved numerical evidence.

| Source group | Number of assets | Data and drawing routines |
| --- | ---: | --- |
| r5 | 15 | Historical corrective, matched and controlled-array evidence in `sources/inputs/figure-inputs.zip`, including saved receipt histories. `sources/historical_panels.py` also draws the two model diagrams. |
| r5-bounds | 2 | Exact certificate endpoints, timing and verification records in `sources/inputs/bound-inputs.zip`. `sources/historical_bounds.py` reads the snapshots and draws both bound figures. |
| review | 3 | `code/research/phase0-audit-20261109/phase0_m_scan.csv` and the result/ablation CSVs in `code/research/phase1-cdl-20261109/`. The drawing routines are in `sources/archived_cdl.py`. |
| comparison | 1 | The 72 saved arm results in `code/research/review-20261110/comparison/campaign/raw.csv` produce the three-profile figure through `sources/archived_cdl.py`. |
| native | 6 | The frozen `code/research/independent-cdl-20261110/analysis.py` plots the saved block summaries and individual recorded search times. |

The two historical input bundles contain only scientific records and their protocol or scientific bound-study note. Their adjacent provenance tables list hash-checked members. Drawing and data-reading functions for the R5 groups come from the original R5 generator scripts identified in `sources/historical-source-hashes.json`. The historical drawing environment used the versions in `sources/historical-requirements.txt`. The November 10 native study used its own recorded analysis environment.

The default command redraws the six native figures using the archived summary and per-run search times. To reuse the products of a recently completed independent native analysis, pass `--native-plots PATH` with the directory containing those six new PDF and PNG pairs. The `reused_native_plots` field in the receipt records that choice. The released assets have fixed hashes. Re-rendered PDF metadata, fonts and the plotting-library version can affect output hashes, so the receipt reports each individual hash comparison.

## Recorded fresh-checkout preparation check

In the November 11 Windows replay with Matplotlib 3.10.0, all 27 PDF/PNG pairs were regenerated from the scientific inputs. The 96-row M-scan CSV was byte-identical to the archive. The median uniform-power reassignment gains were 8.8730015228%, 2.6118998773% and 0% at 2, 4 and 8 receive coordinates.

All 27 PDFs retained the same extracted text in the same order and all 27 PNGs had their original dimensions. The replay matched 23 PNGs byte for byte and 25 PDF page rasters pixel for pixel when rendered with PyMuPDF at 1.7 pixels per point. The remaining small differences affected glyph placement, lines, markers or antialiasing. All PDF byte hashes changed under this rendering environment.
