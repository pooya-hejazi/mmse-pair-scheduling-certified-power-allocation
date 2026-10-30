# Targeted prior-art check, 30 October 2026

This is a bounded targeted check, not an exhaustive review or a novelty certificate. Negative search results do not establish originality. Generic scheduling hardness, WMMSE, matching duality, and conflict-clique inequalities are known.

| Primary source | Evidence inspected | Consequence for the candidate |
|---|---|---|
| [Prasad et al., Multi-User MIMO Scheduling in the Fourth Generation Cellular Uplink](https://arxiv.org/abs/1108.0013) | Full-text model and Appendix B, pp.22–23: hardness reduction uses one RB, variable-cardinality selection, log-determinant MAC utility and receive dimension growing with users. | Establishes broad uplink hardness. It does not directly prove the narrower exactly-two-user, linear-MMSE, resource-selective statement in our note. This distinction alone is not sufficient novelty. |
| [Ruder et al., SC-FDMA user pairing and frequency allocation with imperfect channel state information](https://doi.org/10.1016/j.phycom.2014.10.001) | Publisher abstract; full proof not obtained. Two single-antenna users per frequency/time resource is a close model. | Highest-priority missing full text. Do not claim a new hardness theorem until its receiver, pairing/frequency restrictions and hardness argument are checked. |
| [Zhang et al., ProxySelect](https://arxiv.org/abs/2510.15452), 2025 | Full-text formulation inspected: downlink ZF, frequency-selective group/RU ILP, sampled near-orthogonal candidate groups and proxy rates. | Near-orthogonality plus a group-resource ILP is already an active combination. Our exactness-boundary claim concerns uplink linear-MMSE, full pair family and rational realization; no performance superiority over ProxySelect has been tested. |
| [Gerstacker and Ruder, Beamforming for Energy Efficient Multiuser MIMO SC-FDMA Transmission with QoS Requirements](https://cris.fau.de/publications/230113824/) | Institutional abstract: power minimization under user-rate requirements, ZF analytic treatment and MMSE numerical optimization. | Power reduction relative to fixed allocation is established background, not a sufficient contribution. |
| [Karp, Reducibility Among Combinatorial Problems](https://www.cs.umd.edu/~gasarch/BLOGPAPERS/Karp.pdf) | Original-paper reprint identified; standard perfect3DM NP-completeness is the input theorem. | Our computational enumeration checks instances, not the general NP-completeness theorem. |

The supplied2008 frame-constant pairing paper and2025 joint-learning paper have a separate [local review](../structure/PAPERS_REVIEW.md); our unpublished third draft is background content only, not a prior submission or publication.

## Decision

Keep the exactness/approximation boundary as a candidate mathematical contribution. Do not market NP-hardness itself, a standard clique cut, or the CPU timing as novel. The remaining differentiator would need to be a provably new restricted channel realization/boundary and a useful, precisely scoped certification method. The full Ruder2014 paper is an outstanding dependency for that judgment. Its DOI above is the download link to use when access becomes available; accessible mathematical and reproducibility work can proceed meanwhile.
