# PDP2-CDL-2026-11-09

Final CDL-rebenchmarked release of:

**MMSE Pair Scheduling: Sharp Complexity, Certified Power Allocation, and Regime-Dependent Rate Gains**

## Files

| File | Contents |
|---|---|
| `Manuscript.pdf` | 13-page manuscript |
| `Manuscript_Source.zip` | `main.tex`, bibliography, IEEE class/style, and the figures used by the manuscript |
| `Supplementary_Material.pdf` | 47-page supplement |
| `Supplementary_Materials.zip` | `supplementary.tex`, bibliography, class/style, figures, and the complete reproducible code and saved results |
| `Cover_Letter.pdf` | cover letter to the IEEE Transactions on Communications Editor-in-Chief |
| `DELIVERY_MANIFEST.json` | sizes and SHA-256 hashes for this release |

There are exactly two `.tex` files in the release: `main.tex` and `supplementary.tex`, one in each source ZIP. No component `.tex` files are included.

## Headline result

- 53 standardized 3GPP TR 38.901 CDL-A/B/C cases, `K=16`, `M=2`.
- Median gain over the best common-model baseline: **1.31%**.
- Absolute median gain: **0.129 bit/s/Hz**.
- 95% interval: **[1.19, 1.42]%**.
- **53 wins / 0 ties / 0 losses**.

The `M=8` DeepMIMO result is retained only as a certification and receive-dimension cross-check: 27/32 certificates at 0.01 nat and a 97.82% median fixed-anchor gap reduction. DeepMIMO is not used for the rate claim.

## Reproduce

Extract `Supplementary_Materials.zip` and follow `code/README.md`. The CDL generator is CPU-only and uses the standard cluster tables under `code/research/phase1-cdl-20261109/tables/`.

## Scope

The CDL rate gains are feasible and verified but not globally certified. The certified result remains the `M=8` bound. No raw DeepMIMO scene archive is redistributed.
