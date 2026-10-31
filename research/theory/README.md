# Exactness and certification limits of resource-selective pairing

**31 October novelty update:** the [attribution addendum](../novelty-oct31/ATTRIBUTION_ADDENDUM.md) identifies direct prior art for the bichromatic C4 obstruction and four-edge cut. [Current decision](../novelty-oct31/README.md): PIVOT the main contribution; the rational physical realization remains a scoped, unresolved novelty question. The frozen proof note and its technical review are unchanged. The candidate publication path below is historical and conditional, not a cleared novelty claim. A separate [standard continuous-power bound](../novelty-oct31/GRID_CONTINUOUS_BOUND.md) repairs the grid/continuous distinction; it is not a new polynomial-time ILP solver.

The candidate research question is now narrower: **when can a physically defined two-user MMSE scheduling problem be solved exactly through an LP/assignment model, and when is only a bound available?** This follows the failed selective-information performance/headroom gate; it does not restart channel-estimator development.

- [Proof note](PROOF_NOTE.md): rational channel realization,4-user LP gap surviving projected odd sets, perfect3DM ideal-threshold reduction, continuous-power corollary, and classical additive near-orthogonality bound.
- [Independent technical review](review/report.md): claims/scope PASS; mathematical correctness PASS; integration/novelty UNVERIFIED. This is not S03 acceptance. The unchanged frozen note and manifest hashes identify the reviewed version.
- [All240-case clique-cut diagnostic](CUT_REPORT.md): selective120 cases' positive gaps14→5; maximum gap halved; extra LP overhead. Standard cuts, no general integrality or novelty claim.
- [Prior-art differentiation](LITERATURE_DIFFERENTIATION.md): what has been checked and the close2014 pairing/frequency paper still requiring full-text comparison.

Important distinction: at exact orthogonality, an integral transportation assignment attains the optimal value. The original configuration-polytope constraints do not become integral merely because objective coefficients change. A fractional LP optimum can coexist with an equal-value integral optimum.

The hardness construction permits arbitrary resource-dependent channel vectors and receive dimension M=K². It is not a theorem about fixed32-antenna DeepMIMO channels or a complete6G network model. The exact rational product threshold avoids treating floating-point equality of logarithms as a complexity proof. The finite-grid and continuous-power statements have different scope.

In a fresh copy with NumPy/SciPy, `python research/theory/checks.py` runs author finite checks. `python research/theory/review/independent_checks.py` runs the independent finite checks. These write their respective checks JSON beside the script, so preserve archived outputs before any rerun. `cut_run.py` uses the previously published structure/solver-results.json and refuses to overwrite its run manifest; `cut_analyze.py` validates that archive. No raw channel dataset is needed for this cut diagnostic.

The review directory is a byte-identical export of selected files from the original local audit/reviews/THEORY-CR011-A01; original path references in its report preserve provenance. review/frozen-manifest.json identifies the authored snapshot; the current PROOF_NOTE.md/checks.py/checks.json/PROTOCOL.md match it. No independent reviewer wrote the research code or planning bundle.

## Bounded next research decision

Working article theme: *Exactness and Certification Limits of Resource-Selective Pair Scheduling with Linear-MMSE Reception*. This is a candidate, not a finished or submission-ready manuscript.

1. Complete the closest prior-art comparison, especially Ruder2014. Compare receive model, exact pair cardinality, frequency dependence, growing dimension, rational encoding and proximity to orthogonality. Stop the novelty claim if the restricted theorem is already covered.
2. If differentiation survives, formalize the theorem/proof and distinguish exact value recovery from polytope integrality. Extend power/QoS statements only with a separate proof; do not stack generic6G constraints without purpose.
3. Before a performance-paper claim, require a matched scheduling-family continuous-power comparator and practically useful certificate. The present standard-cut diagnostic is insufficient. GPU scaling remains an engineering question; native timing/feasibility defects in the prior GPU path must be fixed before reruns.
4. S03/S03G must pass independent stage review before held-out S04 studies. Preserve the32 development cases and all negative results; do not convert them into independent confirmation by relabeling them.

Current defensible contribution is a technically reviewed candidate exactness-boundary analysis and reproducible evidence. Publishable novelty and practical superiority remain open.
