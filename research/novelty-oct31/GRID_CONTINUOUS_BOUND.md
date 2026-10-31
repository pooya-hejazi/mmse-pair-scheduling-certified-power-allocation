# A standard power-grid error bound for the existing comparison

Status: supporting derivation and comparator correction, **not a novelty claim**. This note does not replace the frozen CR011 theorem or its review. The objective remains the existing unweighted sum of two-user linear-MMSE rates, with noise-whitened known channels, each user scheduled exactly once, a fixed family of pair/resource choices, individual power boxes and a total-power upper bound. Power does not alter channel information. There are no minimum-rate constraints in this statement.

## Pair identity and a derivative envelope

For one pair let g_i=||h_i||², c=|h_1ᴴh_2|², so 0≤c≤g_1g_2. Set

    D=(1+g_1p_1)(1+g_2p_2)−c p_1p_2,
    q=2 log₂ D−log₂(1+g_1p_1)−log₂(1+g_2p_2).

D≥1 for nonnegative powers. With j≠i,

    D_i=g_i+(g_1g_2−c)p_j,
    0≤D_i/D≤g_i/(1+g_i p_i),
    ∂q/∂p_i=[2D_i/D−g_i/(1+g_i p_i)]/ln2.

The middle upper inequality follows by multiplying positive denominators: D_i(1+g_i p_i)−g_i D=−c p_j≤0. Hence

    |∂q/∂p_i|≤g_i/[(1+g_i p_i)ln2].

This does not assert q is monotone in each power: interference can make the derivative negative. It also does not need joint concavity.

## Feasibility-preserving rounding and exact implication

Give user i an increasing finite grid containing both box endpoints. For any feasible continuous power p_i, let p_i^- be its largest grid value not exceeding p_i. The same schedule with p^- remains feasible because the power lower bound is a grid point and the total-power constraint is an upper bound. Change coordinates one at a time and integrate the absolute derivative bound. For its selected resource s,

    |Q(p)−Q(p^-)|≤Σ_i log₂[(1+g_is p_i)/(1+g_is p_i^-)].

Let g_i^max=max_s g_is, and let the adjacent grid intervals be [a,b]. Define

    E_i=max_[a,b] log₂[(1+g_i^max b)/(1+g_i^max a)],
    E=Σ_i E_i.

The log ratio is increasing in g when b≥a, so E is schedule-independent. Writing V_c for the continuous-power mixed-integer optimum and V_g for its exact grid optimum,

    V_g≤V_c≤V_g+E≤U_g+E,

where U_g is ANY valid upper bound for the full grid problem, including a valid LP dual bound. For any feasible continuous candidate L, max(0,U_g+E−L) is an absolute optimality-gap upper bound. It may be loose. A global interference-free upper bound, when separately valid for the same model, can be intersected with U_g+E by taking their minimum.

The implication does not make the continuous mixed-integer problem an LP. It relates optima of different feasible sets through an explicit error allowance. An archived floating-point LP primal value alone is not a rigorous upper certificate; dual feasibility/residual correction or a solver guarantee must be retained for numerical certification. The diagnostic accompanying this note computes E only and does not manufacture missing archived dual vectors.

For a positive geometric grid with adjacent ratio≤r, E≤K log₂ r. To make this worst-case allowance≤ε in sum-SE units, r≤2^(ε/K) suffices. Smaller spacing increases the number of pair-power columns quadratically in the number of levels. This is a familiar discretization trade-off, not a polynomial exact algorithm independent of precision. For a fixed positive box the finite-grid ILP still has integer scheduling decisions.

## Exclusions and relation to the article gate

Rounding down need not preserve minimum-user-rate, exact total-power, or other lower-performance constraints. Channel-estimation uncertainty is not covered. A receiver recomputed from a mismatched estimate has a different true-rate function and needs a separate derivative proof. Bandwidth and pilot prelog must be identical across comparators; a common factor scales Q and E together. The min-power-at-target-rate problem is not certified by this argument because rounding can violate the target.

This standard smoothness argument closes one comparator gap in the current engineering study. Continuous column generation and perspective relaxations have substantial prior art (see ASTRA_ALTERNATIVE.md). None of this establishes the substantive new contribution required before drafting a positive article or starting its performance study.
