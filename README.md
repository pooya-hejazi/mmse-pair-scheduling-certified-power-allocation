# MMSE Pair Scheduling: current release PDP2-CDL-2026-11-09

The current release is **PDP2-CDL-2026-11-09**, synchronized on 9 November 2026. It replaces the DeepMIMO rate claim with a standardized 3GPP TR 38.901 CDL-A/B/C benchmark and adds the exact-assignment plus SQP power search.

- [Manuscript PDF (13 pages)](releases/PDP2-CDL-2026-11-09/Manuscript.pdf)
- [Manuscript source ZIP](releases/PDP2-CDL-2026-11-09/Manuscript_Source.zip)
- [Supplementary material (47 pages)](releases/PDP2-CDL-2026-11-09/Supplementary_Material.pdf)
- [Supplementary source and complete reproducible code](releases/PDP2-CDL-2026-11-09/Supplementary_Materials.zip)
- [Cover letter](releases/PDP2-CDL-2026-11-09/Cover_Letter.pdf)
- [Release notes and scope](releases/PDP2-CDL-2026-11-09/README.md)
- [Delivery manifest](releases/PDP2-CDL-2026-11-09/DELIVERY_MANIFEST.json)

Headline result: 53 CDL-A/B/C cases at `K=16`, `M=2`; median gain over the best common-model baseline **1.31%**, absolute **0.129 bit/s/Hz**, 95% interval **[1.19,1.42]%**, **53 wins / 0 ties / 0 losses**. The `M=8` DeepMIMO result remains only as a certification and receive-dimension cross-check (27/32 certificates at 0.01 nat, 97.82% median gap reduction). CDL rate gains are feasible and verified but not globally certified.

---

# Earlier release: reviewed revision R1

The R1 version is **PDP2-CR030-R1**, synchronized on 3 November 2026. Its previously reviewed scientific results are unchanged.

- [Article PDF (13 pages)](releases/PDP2-CR030-R1/Manuscript.pdf)
- [Article LaTeX source ZIP](releases/PDP2-CR030-R1/Manuscript_Source.zip)
- [Technical supplement (32 pages)](releases/PDP2-CR030-R1/Supplementary_Material.pdf)
- [Response to all 58 review comments (9 pages)](releases/PDP2-CR030-R1/Response_to_Review.pdf)
- [Independent Astra review](releases/PDP2-CR030-R1/ASTRA_REVIEW.md)
- [Exact delivery manifest](releases/PDP2-CR030-R1/DELIVERY_MANIFEST.json) and [validation](releases/PDP2-CR030-R1/VALIDATION.json)
- [Complete R1 directory, cover letter and reference exports](releases/PDP2-CR030-R1/)

## Reassemble the supplementary archive

Download this repository as a ZIP and extract it, or download all seven `Supplementary_Materials.zip.partNN` files together with `ARCHIVE_PARTS.json` and `reassemble.py` from the R1 directory. Run:

```text
python releases/PDP2-CR030-R1/reassemble.py
```

For files downloaded into one folder, run `python reassemble.py` there. The script verifies every part and reconstructs the exact reviewed `Supplementary_Materials.zip` (10,052,799 bytes; SHA-256 `6dc52e28c6d1352029c2f6b8f23afa77a4e5440cc3239655d4bb806ca0636639`). Extract it and follow its README for source builds, saved-statistics and certificate replay. All 3,627 scientific reproduction files are unchanged. No new optimization, training or channel generation was performed.

The split is a connector transport workaround. The original R1 PDFs, source ZIP, manifests and review files retain their exact audited bytes. Statements about local preparation/public release in those immutable documents describe their preparation state. Synchronization does not change repository visibility or constitute journal submission; the repository remains private. Raw DeepMIMO datasets and third-party full texts are not included in R1.

## Earlier version (historical)

The older root-level files and instructions below are retained as historical material. Use the R1 links above for the current manuscript and supplement.

# MMSE Pair Scheduling: Computational Complexity and Certified Power Allocation

This companion material contains the manuscript sources, a separate technical supplement, figures, saved computational outcomes, proof receipts and programs for checking or plotting those outcomes. It contains no raw DeepMIMO scenario archive or channel-pool NPZ file. The original and corrective studies remain separate; original input-window failures and the disclosed recovery allocation are preserved.

## Contents and environment

The three PDFs are the initial-submission manuscript, IEEE layout preview and technical supplement. `source/` contains editable LaTeX/BibTeX, referenced figures and the unmodified IEEEtran class from the supplied template (LPPL notice retained). `reproduction/` in the supporting ZIP contains project Python programs and saved JSON/CSV inputs/results/receipts. The file manifest lists exact sizes and SHA-256 hashes.

Use an existing Python3.12 environment with NumPy, SciPy, Matplotlib and psutil. The mathematical verifier uses standard-library arithmetic; its wrapper imports psutil. Compilation requires an existing IEEEtran-compatible TeX environment; the tested compiler is Tectonic with tlextras-2022.0r0 and an existing cache. No raw dataset, compiler, installed third-party package, external paper or author sample is redistributed.

## Checking saved results

Extract `supporting-materials.zip` to a short new path. Run these commands from its root, choosing output directories that do not already exist:

```text
python reproduction/plot_figures.py --output replay-figures
python reproduction/reproduce.py --study original --mode statistics --output original-statistics
python reproduction/reproduce.py --study corrected --mode statistics --output corrected-statistics
python reproduction/reproduce.py --study original --mode certificates --output original-proofs --seconds 120
python reproduction/reproduce.py --study corrected --mode certificates --output corrected-proofs --seconds 120
python reproduction/historical-figure-replay/draw_system.py --output model-figures
```

Expected outcomes:8performancefigures; original128cells/590receipts; corrective128cells/700receipts, with417identical verified-input reuses in the latter. The primary success difference is zero. These commands check saved evidence and do not regenerate optimization experiments or historical timings. Exact PDF figure bytes can match the tested environment; PNG encoding may vary while pixels remain identical.

Compile in `source/`: `tectonic submission.tex`, `tectonic manuscript.tex`, `tectonic supplement.tex`. Local page counts do not guarantee publisher pagination. Author names, affiliation and contacts follow the author-confirmed manuscript metadata; funding, conflicts and final submission approval remain author-controlled declarations.

## Raw data and attribution

Raw ray-tracing scenarios must be obtained from DeepMIMO. Original O1_60 download: https://www.dropbox.com/scl/fi/w5s9tjo3cvijo052hmeua/O1_60.zip?rlkey=nlqe3a9q63jh1ktmnyh30u7rq&e=1&dl=0

Credit A.Alkhateeb, “DeepMIMO: A Generic Deep Learning Dataset for Millimeter Wave and Massive MIMO Applications,” ITA2019, and Remcom Wireless InSite (https://www.remcom.com/wireless-insite). The O1_60 and ASU Campus1 scenarios and installed generator retain their applicable terms. This package supplies recorded reduced mathematical cases and research results for saved-evidence checking, not raw scenario or pool datasets. Full scene regeneration requires the separate scenario files, declared generator version/settings and a separately configured environment; it is not performed by the commands above.

## Interpretation and availability

Valid nominal bounds, finite-grid optima and physical deployment guarantees are distinct. The recorded experiment demonstrates tighter bounds in selected cases; it does not establish primary target-certification superiority or a pricing-specific rate gain. AI assistance is disclosed in the manuscript. Third-party ownership and license notices are preserved; no blanket license over third-party material is asserted. Corresponding author: Masoud Sabaei (sabaei@aut.ac.ir).

Public release verification is recorded separately; a local archive is not evidence of a public GitHub release.

## Obtain the complete reviewed archive

Download this repository as a ZIP and extract it, or download all seven supporting-materials.zip.partNN files, ARCHIVE_PARTS.json and reassemble.py into one folder. Run: `python reassemble.py`. The standard-library script checks every part and creates supporting-materials.zip only when its exact size and SHA-256 match the reviewed archive. Then extract that archive and follow the commands above. The complete archive is 10,178,262 bytes; SHA-256: 690b48938445200eeac3c55cce00d8c1ede978c6cc3ef697662d6e739f622fa0. Splitting is solely a transport workaround.

This revision replaces the current main-branch file tree. Earlier Git commits and other branches remain recoverable; removing current Dataset files does not purge historical raw data. The repository owner controls public visibility.
