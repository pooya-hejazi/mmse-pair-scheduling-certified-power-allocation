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
