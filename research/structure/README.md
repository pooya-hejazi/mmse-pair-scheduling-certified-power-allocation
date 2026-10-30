# Resource-priced pairing: exactness and its limits

This is a small **solver study**, not an end-to-end wireless policy or a new polynomial algorithm for general ILP. The two supplied papers were read in full; the source files and extracted text stay local. See [paper review](PAPERS_REVIEW.md), [model/proofs](THEORY.md), and [results](REPORT.md).

Reproduce locally with the existing `6g_project` environment:

```powershell
python research/structure/generate.py
python research/structure/solver_study.py
python research/structure/checks.py
```

Requires the local O1_60 scenario and previously prepared S02 normalization/splits. Original data and code are not overwritten. `generate.py` uses rows 1..100 and new real subcarriers [0,8,16,24]. Reserved future rows 101..200 are untouched. Full input lineage is in `generation.json`; output objectives and certificates are in `solver-results.json`.

The matching oracle enumerates at most 105 perfect matchings (8 users). This implementation is explicitly small-scale. Enumerating all odd-set constraints is exponential. Polynomial matching theory does not make this implementation scalable. A future implementation needs blossom/separation or another controlled relaxation. Independent S03 acceptance is still pending.
