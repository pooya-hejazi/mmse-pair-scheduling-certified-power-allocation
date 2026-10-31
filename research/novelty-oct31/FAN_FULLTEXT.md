# Fan 2012: full-text comparison with the current candidate

Status: bounded technical consultation, 2026-10-31; not proof acceptance or novelty clearance. No experiment or source edit. All page references below are PDF pages, with journal pages in parentheses where useful.

Source: J. Fan, G. Y. Li, Q. Yin, B. Peng, X. Zhu, *Joint User Pairing and Resource Allocation for LTE Uplink Transmission*, IEEE TWC 11(8), 2838-2847 (2012), DOI 10.1109/TWC.2012.070912.111305. Supplied PDF: `C:/Users/pooya/Downloads/f90b78900ce897573f5972891546c3fc.pdf`. Read all technical pages and appendices in the supplied page-labelled extraction; visually checked complete PDF pp. 2, 3, 4, 7. Verification images are `supplied-local/fan-verify-page-{2,3,4,7}.png`.

Compared with `research/theory/PROOF_NOTE.md` and `research/novelty-oct31/GRID_CONTINUOUS_BOUND.md` in their current form.

## Main conclusion

Fan is direct prior art for joint, frequency-dependent two-user linear-MMSE pairing/resource allocation, precomputed pair/resource scores, binary optimization, and an exact branch-and-bound benchmark. Those ingredients cannot carry a new contribution here. Its full text does **not** establish exactness of an LP relaxation, does not optimize continuous powers, and does not contain the candidate's explicit rational near-orthogonal channel construction, four-user LP gap surviving projected odd-set cuts, or restricted ideal-threshold reduction. These are distinctions from this paper only, not a finding that the candidate results are new across the literature.

## Model, CSI, power and objective

- **Network:** one cell and one BS with `N_r` receive antennas; `K` single-transmit-antenna users. A selected group shares the same adjacent RBs. The main case is `N_u=2`, although extension to larger groups is mentioned (pp. 2-3, Sections II and II.B). This is centralized uplink virtual MIMO, not a distributed-AP/fronthaul model.
- **Received signal:** `y_m=H_m sqrt(P) x_m+n_m`, Eq. (1), p. 2. `H_m` varies with subcarrier; entries are described as zero mean/unit variance. Noise covariance is `sigma_n^2 I`. `P` includes transmit power and large-scale fading and is constant across subcarriers for a given user. Perfect power control sets `P=I`.
- **Receiver:** linear MMSE frequency-domain equalization followed by SC-FDMA despreading, Eqs. (3)-(5), p. 3. The effective user SINR over the allocated `M` subcarriers is `gamma_k = [(1/M) sum_m (1+Gamma_mk)^(-1)]^(-1)-1`, where `Gamma_mk` is the per-subcarrier MMSE SINR obtained from the inverse of `sqrt(P) H_m^H H_m sqrt(P)+sigma_n^2 I`. This is not SIC or joint-decoding logdet capacity.
- **CSI:** the signal and receiver formulas use `H_m` directly. There is no distinct estimated/true channel pair or CSI-error distribution in the optimization. The low-complexity procedure replaces channels within an RB by its center-subcarrier CSI (p. 5, III.D.1; p. 9, Appendix B). That is an approximation exploiting frequency correlation, not a robust imperfect-CSI receiver model. Avoid attributing an explicit perfect-CSI theorem to the paper; the formal objective simply has no mismatch variable.
- **Power:** p. 2 expressly excludes power-control optimization. Section IV, p. 6, compares `P=I` with prescribed received-power ratios `[p2,...,p8]/p1=[0,-6,-6,-6,-6,-12,-12] dB`. These are fixed scenario inputs, not decision variables. No individual continuous power boxes or optimized total-power budget are formulated.
- **Objective:** Eq. (7), p. 3, defines `t_ij=sum_{k in P_i} rho_k log2(1+gamma_kj)` for a pair and contiguous resource pattern. The displayed expression has no additional pattern-length factor; follow the paper's bits/symbol convention rather than silently inserting bandwidth. Weights account for fairness/priority, with `rho_k=1/average_rate_k` in Eq. (8). The current candidate uses the unweighted special case, so lack of fairness weights is not a substantive separation.

## Variables, constraints and a reproduction caveat

There are `N_all=K(K-1)/2` pairs and `J=N_rb(N_rb+1)/2+1` contiguous RB patterns including the empty pattern. A binary column `x_ij` assigns pair `i` to pattern `j`; the objective is `sum x_ij t_ij` (p. 3, Eq. (9)). The accompanying explanation requires a pair to choose one pattern including empty; a nonempty pattern to be used at most once; allocated patterns to be RB-disjoint; and simultaneously active pairs to be user-disjoint. Users can remain unscheduled: p. 5 explicitly gives an example where users 1 and 7 wait for later scheduling rounds.

The proposed standard formulation is `min -t^T x`, `Cx=1`, Eqs. (10)-(12), pp. 3-4, with

    C = [ 1_(1 x N_all) tensor A ; B tensor 1_(1 x J) ],
    A = 1_(N_u x 1) tensor T.

`T` is the interval incidence matrix; `B` is user-pair incidence. Thus the printed upper block enforces exact RB coverage and the lower block exact user incidence, including empty-pattern columns. This is not transparently equivalent to the preceding optional-service/at-most description. In particular, every `B` column has exactly two ones, so the lower equality implies `2 sum_ij x_ij=K`. Binary feasibility fails for odd `K`, despite the `K=5` illustrative matrix on p. 4 and odd `K` values in Fig. 7. This equality was **visually confirmed**, not inferred from OCR. Record this narrow modeling/reproduction ambiguity; it does not invalidate the paper's general scheduling idea or establish novelty for our work. Do not silently repair its constraints and then describe the repaired program as the literal published model.

## What the B&B, LP and complexity passages actually establish

- P. 3 calls Eq. (9) NP-hard and cites generic optimization references [20]-[21]. The paper gives no instance reduction or channel-realizability hardness proof; its appendices prove a pair-index formula and assess a channel approximation (p. 9). Merely being a binary integer program is not, by itself, a hardness proof for a restricted family.
- Section III.B, p. 4, describes recursive branching, upper/lower bounding and pruning, claiming an optimal solution to the binary problem as its benchmark. It says this remains too complex for practical systems.
- The text does **not** specify an LP relaxation or LP solver used for those bounds, and contains no integrality or total-unimodularity theorem. Do not turn a generic B&B description into an explicit published LP-based method. It certainly does not claim that dropping integrality yields the exact optimum.
- Section III.E, pp. 6-7, explicitly uses a rough comparison: SINR calculation multiplications and allocation-vector dimension. Table III labels joint search complexity `N_all J` and reduced search `N_rb J`; these are the stated search dimensions, **not polynomial runtime bounds on B&B**. Its joint SINR multiplication count is `N_all N_rb N_sb N_u^3`.
- The named “optimal UP-RA” algorithm selects a reduced set of best pairs per RB and then solves that restricted binary problem (pp. 4-5, Table I). The prose acknowledges possible performance loss from two-step optimization. It is not a proof that this restriction preserves the full joint optimum.

## Exact relationship to the current candidate

| Candidate component | Comparison supported by the full text |
|---|---|
| Resource-selective pair scores and joint binary pairing/allocation | Already central to Fan. Frequency dependence is not a difference from Fan, unlike the earlier resource-independent pairing model. |
| Two-user true-channel linear-MMSE rate identity | For a flat channel within a singleton RB, the effective SINR in Eq. (5) equals its per-subcarrier SINR; after whitening it gives the same two-user scalar SINRs. The candidate's determinant-style pair identity is algebra within this established receiver model. |
| Every user once; one pair per resource; fixed `K=2S` | A natural restriction of the pair/pattern construction when only singleton patterns are admitted and full coverage is imposed. This is a conditional mathematical embedding, not a claim that all Fan's printed constraints and optional-service semantics are equivalent. Its unrestricted contiguous-pattern problem has different feasible schedules and SC-FDMA aggregation. |
| Explicit rational equal-norm, near-orthogonal realization with growing receive dimension `M=K^2` | Not supplied by Fan. Fan's generic channel matrices are related, but its LTE channel/array simulations do not establish this adversarial realization. Conversely the candidate proves nothing about fixed four-AP/eight-antenna geometry or fixed-dimensional Ped-B channels. |
| Four-user nonintegrality after projected odd-set cuts | Not analyzed by Fan. Its B&B treatment is compatible with such a gap; the witness does not refute a claim of LP exactness in this paper because no such claim is made. |
| Restricted 3DM ideal-threshold hardness, rational product encoding, small correlations | Not proved by Fan's generic NP-hardness statement. The restricted theorem may provide mathematical specificity, but must still be differentiated from earlier scheduling hardness and matching/packing literature. |
| Joint continuous-power threshold corollary | Outside Fan's optimization variables. This difference alone is not novelty evidence, and the corollary remains restricted to threshold attainment. |
| Grid/continuous error bound | Fan has neither an optimized power grid nor the relevant continuous-budget comparator, so it cannot subsume this derivation. The current note correctly labels it a standard smoothness/rounding bound rather than a new principle. Its flat-resource rate derivative is not automatically a result for Fan's multi-subcarrier SC-FDMA aggregate. |

Recommendation: cite Fan prominently for the model family and binary/B&B benchmark; do not present those as new or claim a contrast with an exact LP algorithm attributed to Fan. Keep the candidate's possible contribution narrowly focused on explicit channel-realizable restrictions and LP geometry, subject to the unresolved broader novelty and independent proof gates. Keep the power-grid bound as comparator support. Any implementation comparison needs an explicitly aligned service/contiguity convention, resource-normalization convention and clarification of Eq. (10a); none of those reconciliation issues should be used to dismiss the prior art.
