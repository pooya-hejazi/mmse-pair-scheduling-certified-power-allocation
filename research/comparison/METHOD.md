# What this comparison can establish

The scope and budgets were recorded in PROTOCOL.md before execution. It is a development comparison, not a reproduction of a paper's figures or a held-out publication result. Primary reference: [Wang et al., Algorithm1 and equations16–18](https://arxiv.org/abs/2301.02417). The scalar implementation specializes the centralized receiver/weight/precoder cycle and adds a shared sum-power constraint. It omits that paper's conditional channel-error covariance terms; this is explicitly a nominal plug-in comparator. Numerical receiver evaluation uses the true channel only after decisions.

## Adapted I-WMMSE derivation

Noise-whitened channel vectors have noise covariance I. Write v_j=sqrt(p_j), H_g the two-user channel matrix on one resource, and U=(I+H_g diag(p) H_g^H)^−1 H_g diag(v). Implementation uses an equivalent2x2 inverse. The scalar MSE is e_i=1−v_i Re(u_i^H h_i), at the MMSE receiver. Set w_i=1/e_i. With U,w fixed, the amplitude update minimizes

    Σ_j [a_j v_j² −2 b_j v_j],
    a_j=Σ_i w_i |u_i^H h_j|², b_j=w_j Re(u_j^H h_j),
    sqrt(.05)≤v_j≤sqrt(.2), Σ_j v_j²≤.1K.

The solution is v_j=clip(b_j/(a_j+λ),sqrt(.05),sqrt(.2)); λ≥0 is selected by bisection when the shared constraint is active. Receivers and weights give exact block optima and this convex amplitude block cannot worsen the nominal sum-rate beyond numerical tolerance. Stopping after finite iterations does not establish stationarity; no global continuous optimum is asserted. Orthogonal channels supply a water-filling reference test. SLSQP is a separate direct power optimizer with feasible incumbent retention.

## Continuous certificate and its comparator

Interference can only decrease an MMSE user's SINR relative to p_u||h_us||². Therefore maximizing Σ_u log2(1+g_u p_u), under the same box/sum constraints, bounds every feasible rate from above. For a fixed schedule g_u uses its assigned resource. For a global scheduling bound use g_u=max_s||h_us||², relaxing resource conflicts as well. Water-filling solves this concave maximization. A feasible result L satisfying U−L≤.01U has a numerical1% approximation certificate for the **declared nominal comparator family**. This does not imply that the optimizer is globally optimal, nor cover CSI estimation error.

Early stopping does not inherently improve rate; it can save compute while accepting a bounded nominal loss. Measure runtime including bound computation and parent startup. The old finite-grid LP cannot upper-bound a feasible continuous method lying outside the grid. The grid MILP and continuous certificate are different objects and are reported separately.

## Equal budgets and necessary distinctions

Known-CSI continuous arms share one deterministic schedule and common initial power, while full grid MILP may reschedule. A grid-rate gain here cannot be attributed to the power optimizer or certificate; scheduling family differs. This arm is a solver reference, not evidence of superiority over I-WMMSE. The information experiment instead enumerates the same six schedules for all policies, uses the same continuous update and same5s external wall cap. Certificate stopping is the only optimization change between joint and joint_cert.

Information policies all spend5 pilot symbols and17 total normalized pilot energy, except the explicitly unequal-cost no_probe reference. Uniform_probe puts0.25 of the extra energy on eachUE in a wideband sufficient-statistic abstraction. It is not a claim that four arbitrary channels can be orthogonally sounded in one scalar physical dimension; this abstraction assumes separately observable per-UE statistics, like the previous selective study. A practical pilot multiplexing design is still missing. Consequently absolute field throughput and deployable PHY feasibility are not established by this comparison.

The working Gaussian posterior supports the selector only; it is not a calibrated guarantee for the chosen decision. True-channel performance can worsen while the nominal certificate tightens. Certifying a real system requires simultaneous valid rate uncertainty bounds over the candidate family, and incorporating the selection event and measurement cost. None of those guarantees is manufactured from these simulations.

## Novelty decision boundary

Watchdogs, I-WMMSE, water-filling upper bounds, LP relaxation and bounded early stopping are established mechanisms. A positive engineering result for their combination does not alone establish novelty. A viable scientific contribution must show a distinct decision certificate tied to CSI uncertainty, a causal allocation policy that exploits it, and an equal-cost benefit over continuous-power and simple information policies on independent networks. Negative comparisons are preserved and cannot be repaired by selecting a favorable context after observing outcomes.
