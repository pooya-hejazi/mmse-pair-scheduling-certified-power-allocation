# PDP2-CR030-R1: local revised submission package

The article is Manuscript.pdf (13 pages). Upload Manuscript_Source.zip as its editable source: main.tex is the self-contained entry point, with references.bib, main.bbl, IEEEtran.cls, IEEEtran.bst and images/. The technical supplement is Supplementary_Material.pdf (32 pages), also inside Supplementary_Materials.zip. Response_to_Review.pdf/md/tex records dispositions for all 58 detailed comments and the additional acceptance checklist.

Build the extracted article using an existing TeX environment: `latexmk -pdf main.tex`, or `pdflatex main; bibtex main; pdflatex main; pdflatex main`. The tested alternative is Tectonic with tlextras-2022.0r0. Build the supplement from source/supplement.tex. Standard amsmath, amssymb, array, booktabs, longtable, graphicx, cite, geometry, fontenc and hyperref packages are required. Class/style license notices are retained. No absolute input paths, runtime binaries or raw DeepMIMO datasets are required for these builds.

The supplementary archive preserves all 3,627 scientific reproduction payloads byte for byte. revision/ contains the new provenance/configuration/case manifests, inference references, current plot inputs, review dispositions and figure metadata. The complete original and corrected studies remain separate. Original zero-channel ASU outcomes, the corrective protocol and postprocessing recovery are retained. No channel generation, optimization campaign or training was run for this revision.

Extract the supplement to a short new directory. In an existing Python environment with NumPy, SciPy, Matplotlib and psutil, run from its root:

```text
python reproduction/reproduce.py --study corrected --mode statistics --output replay-statistics
python reproduction/reproduce.py --study corrected --mode certificates --output replay-certificates --seconds 120
python reproduction/reproduce.py --study original --mode statistics --output original-statistics
python reproduction/reproduce.py --study original --mode certificates --output original-certificates --seconds 120
python plot_figures.py --output current-figures
python draw_system.py --output current-model-figures
python checks/theory_regression.py
```

Choose new output directories. The last command additionally requires SymPy and writes checks/theory-regression.json. It checks analytic identities/boundary cases; it is not an independent proof review. The plot scripts use saved scalars only. The historical reproduction/plot_figures.py remains unchanged and reproduces the historical figure style; use the root plot_figures.py for this revision's main performance figures. Rendering metadata may vary across environments without changing figure content. Saved-data replay checks scientific outcomes and receipt integrity, not historical execution times.

The corrected statistics have 128 cells (96 main, 24 scale, 8 analytic reliability); 700 timely receipts include 417 cached mathematical reconstructions after receipt-specific integrity checks. The primary difference is zero with conservative 95% interval [-0.3449,0.3449]. Pricing adds no achieved-rate gain over corresponding unpriced search or main/scale 0.01-nat target success.

revision/PROVENANCE.json and GENERATOR_CONFIGS.json preserve the recorded generator, installed-source/input hashes and full historical parameter arrays. Absolute dataset locations in those historical configuration records are provenance values, not executable source dependencies; replace dataset_folder when independently obtaining the raw scenarios. Unrecorded generator VCS/scenario tags, original O1 archive digest, historical BLAS build and separate HiGHS version remain explicitly unknown. See HISTORICAL_README.md for dataset acquisition/attribution and unchanged older replay instructions.

our_papers.bib contains two published author papers; closest_other_papers.bib contains three selected external papers. All five are cited in the article. Cover_Letter.pdf/tex retains the existing author-confirmed identity and factual scope. Final coauthor approval, exclusivity and submission-form declarations remain author-controlled. No message, journal submission or public upload has been made.

PDP2-CR030-R1 is a fixed local artifact identifier. revision/REPRODUCTION_MANIFEST.json hashes the scientific payload; FILES.json in each archive hashes every archive payload except itself; DELIVERY_MANIFEST.json hashes the delivered files except itself and the subsequent independent review. A local digest is not a public DOI. Public repository visibility/release verification is outstanding, based on the last observed private state; it was not reprobed here.
