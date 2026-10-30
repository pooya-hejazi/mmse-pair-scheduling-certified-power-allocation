# Astra decision on the physical LP-gap and hardness construction

2026-10-30. Bounded consultation; not checkpoint acceptance or independent publication review. No other files changed. The proposed mathematical constructions were checked directly against the pair-MMSE identity and the existing THEORY.md. A targeted primary-source literature check was performed using the academic-research method already invoked in this consultation.

## Decision

**Pursue one precise technical note and proof-check packet.** The constructions appear sound and close a real logical gap between arbitrary combinatorial rewards and realizable Gaussian multiple-access channel coefficients. The strongest limited statement is that arbitrarily near-orthogonal physical channel vectors can retain both a positive resource-coupled LP gap and exact optimization hardness. This does not establish novelty or a publishable performance contribution. Keep selective-CSI development stopped for the failed finite-grid/frozen-receiver family.

## Four-user witness: checked

Use unit powers, identity noise covariance, single-antenna users and true-channel linear MMSE without SIC. Let A0={12,34}, A1={13,24}. On resource s, F_s is the zero-diagonal adjacency matrix of pairs outside A_s, and G_s=I+epsilon F_s, with 0<epsilon<1/2.

Each F_s is the adjacency matrix of K2,2, with spectrum {2,0,0,-2}. Thus G_s is positive definite and is a valid Gram matrix of four channel vectors in four receive dimensions. All norms are one; allowed inner products are zero; forbidden inner products are epsilon.

Writing a=2log2(2)=2 and delta=-2log2(1-epsilon^2/4)>0, the pair-MMSE formula gives q=a on allowed columns and q=a-delta otherwise. The fractional point placing 1/2 on (12,0),(34,0),(13,1),(24,1) meets every UE and resource equality. Its projected edge vector is a four-cycle with weights 1/2. Every three-vertex odd-set contains two of those cycle edges, so its odd-set inequality holds at equality; singleton inequalities are trivial. Hence the witness survives **all projected perfect-matching odd-set cuts**.

Every feasible LP point has total column mass two and coefficient at most a, so 2a is an upper bound attained by that point. Every integer schedule uses at most one allowed column, because the complement of an allowed pair on one resource is forbidden on the other. One allowed plus one forbidden is feasible. Therefore

    LP = LP_odd = 2a,
    IP = 2a-delta,
    gap = delta.

The normalized squared coherence is at most epsilon^2 and tends to zero with epsilon. Near-orthogonality therefore does not imply exactness of either relaxation. At epsilon=0 the objective becomes additive and exactness returns; there is no contradiction with the existing orthogonal-subclass result or its approximate bounds. The gap vanishes as epsilon^2/(2 ln 2); this is an exactness obstruction, not evidence of a large practical rate loss. Four-user complement cuts still remove it.

## Rational physical realization: checked with precise scope

For U users, allocate two coordinates for every unordered pair and one private coordinate per user: M=2 binom(U,2)+U=U^2. Use the same coordinate labels on every resource. For a pair {u,v}, place amplitude t for both users in its first coordinate if the pair is forbidden; if it is allowed, place u's amplitude t in the first and v's in the second. All other users are zero in this block. User u additionally has amplitude one on its private coordinate. This is an explicit rational channel matrix when t is rational.

Every user has norm squared

    g = 1+(U-1)t^2,

and every pair inner product is exactly t^2 if forbidden and zero if allowed. Other pair blocks create no cross-inner-product contribution. Thus all allowed pair rates equal

    a_t = 2log2(1+g),

and every forbidden pair has rate a_t-delta_t, where

    delta_t = -2log2(1-t^4/(1+g)^2)>0.

This construction avoids relying on an irrational Cholesky factor in a Turing-model reduction. Equal norms hold within and across all resources. Unit norm is not needed for this second construction and should not be claimed.

For a 3-dimensional-matching instance X,Y,Z, each of size n, use users X union Y, U=2n, and n resources indexed by Z. A cross-pair (x,y) is allowed on z exactly when (x,y,z) is an input triple; all other pairs are forbidden. Every schedule serves each user once and uses one pair on every resource. Its rate is

    U log2(1+g) - k delta_t,

where k is its number of forbidden pairs. A schedule reaches U log2(1+g) if and only if the original instance has a perfect 3-dimensional matching. Both directions follow directly from disjoint user coverage and unique resource use. The reduction direction is 3DM -> physical scheduling.

Set t=1/U. Channel entries are in {0,1,1/U}, have O(log U) bits, and the explicit output contains O(U^4) entries across users, resources and receive coordinates. The maximum normalized squared coherence is t^4/g^2=O(U^-4). Moreover g<=5/4 for U>=2, so

    delta_t >= 32/(81 ln 2) * U^-4.

This gives an inverse-polynomial **raw sum-rate additive** separation. Dividing by the number of resources changes its order by another factor U; state the chosen normalization.

Define the decision problem using a rational product threshold Q, asking whether a feasible schedule satisfies product_u(1+SINR_u)>=Q. In this reduction Q=(1+g)^U is rational with polynomial encoding length. For rational channels, fixed rational powers and positive rational noise, pair SINRs are rational and a proposed schedule's product can be verified by polynomial-bit rational arithmetic. Thus this carefully defined decision version is in NP and the construction proves NP-hardness, yielding NP-completeness. The associated exact sum-log-rate optimizer is NP-hard through monotonicity of log. Do not silently substitute a conventional rational *log-rate* threshold without discussing representation.

## Joint-power ideal-threshold corollary: also valid

The proposed follow-up extension repairs the otherwise missing link to joint power control. For these same channels, norm squared g is equal for every user and resource. Set noise to one, choose a common budget-average power p0>0 inside the declared power box, and impose sum_u p_u<=U p0. For every schedule and power vector,

    sum_u log2(1+SINR_u)
      <= sum_u log2(1+g p_u)
      <= U log2(1+g p0).

Equality in the second inequality requires full budget and, by strict concavity, p_u=p0 for every user. Because these powers are positive, equality in the first inequality requires every selected pair to be orthogonal. Thus the ideal threshold is attainable if and only if the 3DM instance has a perfect matching. The power set is compact and rates continuous, so absence of such a matching implies a strictly smaller optimum, not merely an unattained supremum.

This works for continuous powers in [0.5,2] with p0=1, for the original numeric box [0.05,0.2] with p0=0.1, and for any grid containing p0 and obeying the same budget. The rational product threshold is Q=(1+g p0)^U. It establishes hardness of exact joint scheduling/power optimization and of the constructed ideal-threshold existence problem. The yes certificate in this restricted construction is a discrete schedule with every power p0. It does **not** establish NP membership for general continuous-power decision instances with arbitrary thresholds. The fixed-power formula k delta_t and its inverse-polynomial gap must not be transferred to continuously optimized powers without another proof.

## Claims to exclude

- This proves worst-case hardness for a deterministic channel-input family with additive Gaussian noise and receive dimension growing as U^2. It proves neither fixed-four-AP/fixed-32-antenna hardness nor hardness for DeepMIMO's geometric/channel manifold. It is not an average-case result for i.i.d. Gaussian fading.
- Channels may vary arbitrarily across resources. Flat/resource-invariant pairing is a different problem with matching structure.
- Distinguish the fixed-power reduction from the joint-power ideal-threshold corollary just proved. The exact four-user LP-gap value delta is a fixed-power result; no continuous-power LP formulation or identical optimized gap follows from it.
- Keep this theorem separate from the empirical pilot prelog 1-U/200, which becomes invalid as an asymptotic positive factor for U>=200. Use raw rates, or a specified positive common scaling, in the complexity model.
- Do not infer constant-factor inapproximability, a substantial integrality gap, exponential runtime on typical instances, or the absence of useful LP certificates. Exact optimization can remain hard while a cheap approximation is excellent because the gap shrinks.
- Avoid claiming strong NP-hardness without a separately specified rational-data/encoding convention. NP-hardness is sufficient here.

## Prior-art assessment

The close pairing paper is now partly accessible through indexed full text: [Hottinen and Viterbo, Optimal User Pairing for Multiuser MIMO, 2008](https://engit.monash.edu/profiles/wp-content/uploads/2017/09/isssta08b.pdf). Section II-A assumes each user's channel is constant across the entire frame. That restriction distinguishes it from the resource-dependent construction. Do not describe the proposed hardness as contradicting its polynomial pairing claim, and do not rely on its Hungarian recovery argument without a separate audit of that formulation.

[Prasad et al., Multi-User MIMO Scheduling in the Fourth Generation Cellular Uplink, arXiv:1108.0013v3](https://arxiv.org/pdf/1108.0013) already proves uplink scheduling hardness. Its Appendix B uses one resource, variable scheduled-set cardinality, an optimal-decoding log-determinant objective and a maximum-principal-subdeterminant/clique argument. That proof does not directly establish this restricted exactly-two-users/resource, all-users-served-once, linear-MMSE model. Its existence nevertheless rules out any broad claim that discovering MIMO scheduling hardness is new.

[Ruder, Moldovan and Gerstacker, 2014](https://doi.org/10.1016/j.phycom.2014.10.001) explicitly identifies joint V-MIMO user pairing/frequency allocation as NP-hard and cites preceding LTE work. [Fan et al., Joint User Pairing and Resource Allocation for LTE Uplink Transmission, 2012](https://doi.org/10.1109/TWC.2012.070912.111305) is a mandatory closest-predecessor comparison. The complete Fan proof was not obtained in this bounded check; no claim that its reduction lacks physical realization is justified. These models involve SC-FDMA allocation restrictions, whose exact role must be compared before stating that the present restricted hardness theorem is new.

Current novelty status: **unresolved, with a plausible narrower distinction** in explicit rational physical realization, vanishing coherence, and an odd-set-resistant physical LP witness. No exhaustive search or equivalence audit has been completed.

## One bounded next packet

Prepare a short self-contained theorem note containing the two propositions above, the explicit reduction, bit-complexity argument, scope table and closest-source comparison. Use at most 30 minutes of computation/review, no new data, estimator, GPU work, installation or environment expansion. Preserve all original artifacts.

Verification should use exact rational arithmetic for the constructed channel norms, inner products, SINR products and 3DM equivalence. Exhaust all n=2 triple subsets (256 instances), plus a fixed seed list of at most 100 n=3 instances; compare 3DM enumeration to schedule enumeration. Verify the four-user witness symbolically, with a few rational epsilon values for direct-matrix cross-checks. Numerical LP objectives may corroborate but cannot replace the symbolic inequalities, especially as delta approaches solver tolerance. Stop on the first mismatch rather than changing the construction to fit outputs.

The deliverable is a verified scoped technical result and an explicit novelty comparison. If the closest prior work already contains the same restricted construction or equivalent theorem, keep this as a correctness appendix and do not promote it to the paper's central innovation. That negative novelty outcome does not invalidate the proof or justify restarting the failed selective-information route.

A useful companion statement already in the project is the fixed-power transportation bound: with all pairs allowed, solve the integral UE-to-resource transportation LP for interference-free scores and evaluate the resulting schedule. Its regret and the configuration-LP integrality gap are at most sum_s max_e delta_es, with delta_es=-2log2(1-kappa_es) under unit resource weights. This is a classical perturbation bound, not independent novelty. Together the statements explain how exact optimization can be hard arbitrarily near orthogonality while an LP-derived schedule has a small additive error. Keep the transportation exactness/approximation statement fixed-power; introducing a coupled continuous-power budget does not preserve its TU argument automatically.
