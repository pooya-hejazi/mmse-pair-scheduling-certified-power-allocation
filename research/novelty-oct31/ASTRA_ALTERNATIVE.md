# Astra follow-up: continuous-power certification alternative

31 October 2026. Bounded research consultation only; no computation, training, simulation, installation, or subagents. Existing S03 gates and main sources remain unchanged.

**Verdict: YES as a mathematically sound comparator repair; NO as a sufficiently established new research contribution. Exact novelty remains UNRESOLVED.** A correlation condition can ensure joint concavity. However, ordinary differentiation already produces such a condition; standard perspective convexification then handles the continuum relaxation. The finite-grid-to-continuous certificate does not even require concavity. These observations support correcting the comparator, not declaring a new paper viable.

## 1. Model and an explicit sufficient concavity condition

Use exactly the proposed true-channel, interference-treated-as-noise, two-user linear-MMSE objective, with identity noise covariance:

    q(p1,p2) = [2 ln D − ln(1+g1 p1) − ln(1+g2 p2)] / ln 2,
    D = (1+g1 p1)(1+g2 p2) − c p1 p2,
    0 ≤ c ≤ g1 g2.

For positive channel norms define

    x=g1 p1, y=g2 p2, r=c/(g1 g2),
    A=1+x, B=1+y, d=1+x+y+(1−r)xy,
    f=q ln 2.

The exact derivatives in these normalized coordinates are

    f_xx = 1/A² − 2[1+(1−r)y]²/d²,
    f_yy = 1/B² − 2[1+(1−r)x]²/d²,
    f_xy = −2r/d².

Thus the necessary and sufficient pointwise Hessian test is f_xx≤0, f_yy≤0, and f_xx f_yy−f_xy²≥0. To certify a box, these conditions must hold throughout it; checking only sampled points or its corners has not been justified. A box can of course be intersected with the pair's feasible power-budget region.

Here is a deliberately conservative **analytical sufficient condition**, derived in this consultation rather than claimed as a novel theorem:

    r ≤ (3−sqrt(7))/2  ⇒  q is jointly concave for every p1,p2≥0.

Proof: scale the Hessian by the positive diagonal matrix diag(A,B). Its first diagonal entry is 1−2(1−r y/d)², and its second is 1−2(1−r x/d)². Since x,y≥0 and 0≤r≤1, both are at most −m, where m=2(1−r)²−1. Its off-diagonal magnitude is 2rAB/d²≤2r: indeed d≥A+B−1≥sqrt(AB). Therefore the negative scaled Hessian is positive semidefinite whenever m≥2r, which is equivalent to the displayed sufficient condition within r∈[0,1]. Positive diagonal rescaling and the positive log-base factor preserve the sign conclusion. If a channel norm is zero, its cross term is zero and the remaining scalar log-rate is concave.

This condition involves **squared normalized correlation**; it is not a threshold on the unsquared coefficient. It is sufficient, not sharp or necessary. The Hessian at x=y=0 requires r≤1/2. For concavity on the entire nonnegative quadrant, the stronger necessary condition r≤1−1/sqrt(2) follows by taking x=0 and y→∞ in f_xx. The gap between sufficient and necessary bounds is left open here. The derivation is not an independent proof acceptance and has not been checked computationally.

An equally routine box-dependent refinement is available. On [xL,xU]×[yL,yU], set

    a1 = r yU / d(xL,yU),   a2 = r xU / d(xU,yL),
    m1 = 2(1−a1)²−1,       m2 = 2(1−a2)²−1.

Monotonicity of r y/d and r x/d gives a sufficient test m1≥0, m2≥0, m1 m2≥4r². This retains the conservative global off-diagonal bound. A sharper characterization would require additional analysis, but sharpening this elementary inequality alone is not yet a substantial contribution.

## 2. What concavity buys, and what it does not

For fixed pair/resource (e,s), continuous pricing has the form

    max_p {q_es(p) − λ(p_u+p_v) − α_u − α_v − β_s},

over the declared box, where λ≥0 prices the total-power budget. Certified concavity makes this a convex optimization problem in the usual sense of maximizing a concave function over a convex feasible set. A numerical feasible pricing point gives a lower bound on the pricing maximum, not the upper bound needed to certify that no improving column exists. A valid tangent upper bound, certified solver dual bound, or globally valid error allowance is still needed.

For any candidate master dual, let vbar_es upper-bound that pricing maximum and set η_s=max(0,max_e vbar_es). Increasing β_s by η_s makes every continuum dual constraint valid. The master dual objective plus Σ_s η_s is consequently a valid upper bound. This is a standard dual-feasibility repair. It does not make the integral scheduling problem convex or remove its combinatorial gap.

There is a simpler formulation when **every eligible q_es is concave**. Let z_es be the mass assigned to a pair/resource and w_es its two accumulated powers. Jensen's inequality shows that replacing its entire distribution of power columns by its mean powers cannot decrease its rate and preserves all linear incidence and budget constraints. The continuum configuration LP therefore has the same optimum as the finite perspective problem

    maximize Σ_es z_es q_es(w_es/z_es)
    subject to the user/resource equalities,
               Σ_es (w_es,u+w_es,v) ≤ P,
               p_min,u z_es ≤ w_es,u ≤ p_max,u z_es,
               p_min,v z_es ≤ w_es,v ≤ p_max,v z_es,
               z_es ≥ 0.

At z_es=0 the closed perspective is zero and w_es=0. This has O(S K²) pair blocks when all pairs are eligible. Column generation may be an implementation choice, but an infinite power-column set does not itself create a new mathematical obstacle in this concave case. The perspective relaxation is not the integral hull of the complete scheduling problem.

This argument assumes the pair rate depends only on that pair's local powers and that the remaining coupling is exactly the stated linear incidence/budget structure. Cross-resource interference or unmodeled power-dependent constraints invalidate an automatic transfer.

## 3. The continuous comparator can be repaired without concavity

Let D_i denote differentiation of D with respect to p_i. The exact objective satisfies

    ∂q/∂p_i = [2D_i/D − g_i/(1+g_i p_i)]/ln 2,
    0 ≤ D_i/D ≤ g_i/(1+g_i p_i),

and hence

    |∂q/∂p_i| ≤ g_i / [(1+g_i p_i) ln 2].

For i=1, the upper inequality follows from

    g1 D − (1+g1 p1)D_1 = c p2 ≥ 0;

the other case is symmetric. This holds throughout the feasible power box for **every** r∈[0,1]. It uses the exact power-dependent MMSE rate, not a frozen combiner.

Choose each user's grid to include p_min and p_max and round each continuous power down to the nearest grid value. This preserves its box and a sum-power **upper** budget. For adjacent grid values a<b, integrating the derivative gives a coordinate error no larger than

    log2[(1+g_i b)/(1+g_i a)].

With g_i^max=max_s g_is, define

    E_i = max_adjacent(a,b) log2[(1+g_i^max b)/(1+g_i^max a)],
    E = Σ_i E_i.

Each user appears exactly once. Round coordinates sequentially; the derivative bound holds at the intermediate other-user powers, so the errors telescope. The rounded schedule loses at most E. Consequently

    IP_grid ≤ IP_cont ≤ IP_grid+E ≤ LP_grid+E,
    LP_grid ≤ LP_cont ≤ LP_grid+E.

The second line applies the same rounding map to each fractional power column; the incidence marginals are unchanged and total expected power decreases. These statements are for the same eligible pair family, channel realization, true-MMSE receiver, rate convention and budget. A candidate-restricted grid LP does not certify the full eligible-pair problem without a separate missing-column bound. Use a validated LP upper bound if the solver stops before optimality, and retain numerical error allowances.

**Excluded:** rate/QoS lower constraints, a required power equality, or other constraints not preserved by downward rounding. Increasing interference at one receiver is not the concern here; reducing a user's own power can violate its minimum rate. Additional constraints require a separate feasible rounding argument.

The guarantee is useful only if E is small enough. For the grid {0.05,0.1,0.2}, each doubling interval tends to one bit at high normalized gain, giving an asymptotic worst-case bound near K bits in summed spectral efficiency. For K=32 this is near 32, which can easily be too loose for a one-percent claim. This is a bound-quality observation, not a computed result on the project's channels. Geometric refinement reduces the bound but increases the number of grid combinations; that tradeoff is standard discretization analysis.

## 4. Closest primary evidence and limits

| Primary source | What was inspected and what it establishes | Why it matters here |
|---|---|---|
| [Sharma and Teneketzis, *An Externalities-Based Decentralized Optimal Power Allocation Algorithm for Wireless Networks*, 2009](https://web.eecs.umich.edu/~teneket/pubs/DecentOptPwrWireless.pdf), [DOI](https://doi.org/10.1109/TNET.2009.2020162) | Indexed passages of the author-hosted PDF, including Section IV and Appendix-B discussion; direct PDF retrieval returned an error. Two-user MMSE correlation/concavity discussion exists. Crucially, its utility is **negative MSE minus power cost**, not our log-rate sum, and the discussion uses approximate concavity. | Adjacent precedent, not a duplicate of our exact Hessian theorem. Obtain readable equations before asserting a stronger relationship. |
| [Hu and Pan, *Concavity approximation based power allocation in millimeter-wave MIMO systems*, 2017](https://anzhonghu.github.io/publication/2017-12-05-paper-title-number-3), [DOI](https://doi.org/10.1109/ACCESS.2017.2773491) | Author publication page inspected; indexed paper excerpts were discovery evidence, not a complete proof review. The work uses asymptotic channel orthogonality for a concavity-based power-allocation approximation. | Orthogonality-to-concavity motivation is already established. Its MMSE precoding model and approximation must be distinguished from exact uplink two-user detection. Full PDF remains a priority for precise comparison. |
| [Shang et al., *Noisy-interference Sum-rate Capacity of Parallel Gaussian Interference Channels*](https://arxiv.org/pdf/0903.0595) | Full-text Lemma 2 and surrounding model inspected: weighted sum **capacity** is concave in power constraints; noisy-interference conditions relate treating interference as noise to that capacity. | Capacity concavity involving permissible coding/time-sharing does not imply pointwise concavity of the fixed linear-MMSE objective. Do not import this theorem into our model. |
| [Hassan et al., *Power Control for Sum Rate Maximization on Interference Channels Under Sum Power Constraint*](https://arxiv.org/pdf/1407.4177), 2014 preprint | Full-text model and abstract inspected: analytic two-link power allocation under a sum budget, with and without QoS. | Strong adjacent comparator, but distinct receivers/interference-channel gains are not the same power-dependent common-receiver MMSE formula. No exact subsumption established. |
| [Johansson and Xiao, *Cross-layer optimization of wireless networks using nonlinear column generation*, 2006](https://ieeexplore.ieee.org/document/1611067/), [author record](https://people.kth.se/~mikaelj/content.html) | Publisher and author abstracts inspected; full proof not retrieved. Joint power, scheduling, routing and rates with nonlinear column generation and a global-convergence claim. | Continuous power plus scheduling plus column generation is not new as an architecture. Need full assumptions for an exact theorem comparison. |
| [Fu, Liew and Huang, *Fast Algorithms for Joint Power Control and Scheduling in Wireless Networks*, 2010](https://ncel.cuhk.edu.cn/sites/default/files/TW-Jun-09-0824.pdf), [DOI](https://doi.org/10.1109/TWC.2010.03.090824) | Author full-text Sections III–V inspected: master LP, continuous-power pricing under SINR constraints, Perron–Frobenius elimination, and branch-and-price for integer slots. | Certified wireless scheduling/power pricing and integral extensions are established. Different fixed-SINR airtime objective; not a duplicate of the pair-rate formula. |
| [Liu et al., *Joint Optimization of Scheduling and Power Control in Wireless Networks: Multi-Dimensional Modeling and Decomposition*](https://arxiv.org/pdf/1701.06502), v2, 2017 | Full-text model and Theorem 1 proof inspected. Powers come from a **discrete** set. The theorem transfers pricing-subproblem gap to the master gap by correcting dual feasibility. | Direct precedent for the certificate mechanism, but not itself a continuous-power guarantee. This distinction prevents repeating the comparator error. |
| [Günlük and Linderoth, *Perspective Reformulations of Mixed Integer Nonlinear Programs with Indicator Variables*](https://jlinderoth.github.io/papers/Gunluk-Linderoth-09-TR.pdf), author manuscript 2009, [published DOI](https://doi.org/10.1007/s10107-010-0360-z) | Full-text introduction/formulation inspected: indicator-driven convex sets, perspective reformulation, and tight continuous relaxations. | The finite perspective construction above is a standard application of established convexification, not a new relaxation principle. |

Search failure to identify the exact numerical correlation threshold proves nothing about its priority. This consultation does not equate the adjacent MSE, precoding, interference-capacity and uplink-MMSE objectives.

## 5. A concrete next-packet decision

**A small comparator-repair packet is justified**, if separately authorized and independently reviewed: formalize the derivative/integrated rounding bound; audit the existing grid, power normalization and constraints; calculate E on existing instances; and report whether the corrected continuous upper bound is useful. No new channel data or held-out S04 run is required for that repair. If too loose, report that outcome rather than relabeling the grid optimum as a continuous optimum.

**A new research packet is not yet justified by “concavity + pricing + grid error”.** Those three steps have routine proofs/mechanisms. Even an improved sufficient correlation threshold may be a minor technical lemma rather than the main contribution.

One precise *research target*, not an established positive alternative, would be an exact or provably near-tight concave-envelope representation for this specific q over the full physically relevant correlation/power domain, with a certified pricing algorithm and a quantitative advantage over generic spatial branch-and-bound and the standard perspective/smoothness baselines. Its value would be handling the nonconcave pairs that invalidate the convenient regime without silently discarding them. Such a target would need its own novelty search, formal statement, proof, and finite complexity/accuracy analysis before experimentation. A generic piecewise-linear envelope or ordinary Hessian-based subdivision would not meet that requirement.

Until a nonroutine theorem of that kind exists, the appropriate decision is **NO for publication progression, UNRESOLVED for exact theorem priority, and a positive recommendation only for a bounded correctness repair**. No source/gate acceptance is issued here.
