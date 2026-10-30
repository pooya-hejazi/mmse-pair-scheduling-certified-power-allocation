# Research progress

This branch preserves the original code and adds separate exploratory studies:

- [Selective channel information](selective/README.md): equal communication-budget policies with a fixed estimator; mostly negative performance results retained.
- [Matching, LP strengthening and certificates](structure/README.md): full review of the two supplied papers,240 small channel instances, exact subclasses and positive LP gaps.
- [Power, throughput and GPU](gpu/README.md): a precise finite-grid model, completed8/16/32-user engineering cases, GPU/CPU comparisons and an explicitly incomplete64-user case.

S01 mathematical baseline and S02 corrected bounded reproduction were accepted locally. The power/GPU planning revision passed independent review; its implementation has not. S03 and S03G are not accepted, and S04 confirmatory experiments have not started. Current results do not establish publishable novelty, superiority over the literature, a GPU speedup, or a general polynomial-time ILP solver. The estimator remains fixed. The candidate direction is a certified choice between more channel information and more optimization within a joint scheduling/power model. Full local planning/audit history remains in the project workspace. Original main-branch files are preserved.
