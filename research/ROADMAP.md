# Research progress

This branch preserves the original code and adds separate exploratory studies:

- [Selective channel information](selective/README.md): equal communication-budget policies with a fixed estimator; mostly negative performance results retained.
- [Matching, LP strengthening and certificates](structure/README.md): full review of the two supplied papers,240 small channel instances, exact subclasses and positive LP gaps.
- [Power, throughput and GPU](gpu/README.md): a precise finite-grid model, completed8/16/32-user engineering cases, GPU/CPU comparisons and an explicitly incomplete64-user case.
- [Continuous power and equal-budget information](comparison/README.md): external worker deadlines,215 jobs, adapted I-WMMSE/SLSQP, and negative selective-information/certificate-speedup findings.
- [Information opportunity audit](headroom/README.md): exact offline grid checks on32 fixed development networks; the frozen-estimate decision-only route fails its predeclared1% gate and is stopped.
- [Physical exactness boundary](theory/README.md): rational near-orthogonal channel counterexample, restricted hardness argument, independent technical review, and a240-case diagnostic of classical clique cuts.

S01 mathematical baseline and S02 corrected bounded reproduction were accepted locally. The power/GPU planning revision passed independent review; its implementation has not. S03 and S03G are not accepted, and S04 confirmatory experiments have not started. Current results do not establish publishable novelty, superiority over the literature, a GPU speedup, or a general polynomial-time ILP solver. The estimator remains fixed. Following the negative information-policy and opportunity gates, the current candidate is the precise boundary between exact assignment, near-orthogonal approximation and genuinely fractional resource-selective pairing. The independent mathematical review found no blocking proof error but did not clear novelty or stage integration. Full local planning/audit history remains in the project workspace. Original main-branch files are preserved.
