# Astra research decision — 2026-10-30

Consultation only; not stage acceptance. Original code and planning files were not modified. Reviewed PROTOCOL.md, METHOD.md, core.py, the comparison summary, gpu REPORT/MODEL, selective REPORT/OPTIMIZATION, and structure THEORY. Final summary rechecked: COMPLETED, 213 completed jobs and two bounded 64-user timeouts. These remain development results, not independent stage acceptance.

## Decision

There is no demonstrated publishable positive result yet. Do not add another selective-information heuristic, more posterior worlds, estimator training, GPU work, or a larger benchmark. The strongest bounded next alternative is **a perfect-information headroom audit with a proved no-acquisition certificate**, using the existing 32 development networks. Its purpose is to falsify the research premise before investing in another policy. This is one diagnostic packet, not a proposed new algorithm or a confirmatory study.

The known-CSI comparisons show essentially no fixed-schedule power headroom, while the grid arm's advantage changes the schedule. Joint minus weakest is negative in all four information contexts (-0.00766, -0.00290, -0.00297, -0.01339 bit/s/Hz), with intervals spanning zero. The certificate arm has zero early stops across all 32 networks and identical paired rates. Earlier selective evidence was also mostly negative. These observations support a stringent headroom gate; they do not establish impossibility.

Generic ingredients are not a novelty claim: joint probing/scheduling with acquisition time cost predates this work [Chaporkar–Proutiere, WiOpt 2008](https://eudl.eu/doi/10.4108/icst.wiopt2008.3189). LP-based interval minmax-regret methods also exist [2017 paper](https://doi.org/10.1016/j.cor.2016.12.010), including general binary optimization under interval uncertainty [Carvalho et al., 2022](https://www.numdam.org/item/10.1051/ro/2022198.pdf). This was a bounded primary-source check, not an exhaustive novelty clearance. A future publishable contribution needs a distinctive physical uncertainty/decision result and useful behavior; adding an LP bound to VOI is insufficient.

## Exact mathematical target

Let H be the fixed true channel within a block, tau=4, T=200, and R0(H) the raw rate of the causal no-probe decision evaluated with its actual estimated-channel receiver. All rates must share the same bandwidth normalization. Let F be the declared scheduling/power family and

    V_F(H) = max_{d in F} R_MMSE(H,d).

This oracle receives perfect CSI, chooses the best feasible schedule and power, and uses the true-channel linear MMSE receiver. It is deliberately more capable than any one-pilot policy. For every policy pi consuming at least one extra symbol, keeping the same data-power constraints and linear receiver family,

    G_pi(H) - G0(H)
      <= (1-(tau+1)/T) V_F(H) - (1-tau/T) R0(H)
      <= B(H) := (1-(tau+1)/T) U_F(H) - (1-tau/T) R0(H),

where U_F is any valid upper bound on V_F. Proof: for the realized H, the policy's chosen action lies in F, its linear receiver cannot outperform the corresponding perfect-CSI MMSE receiver, and its data fraction is at most 1-(tau+1)/T. No Bayesian posterior, calibration or independence assumption is needed for this pointwise inequality. It allows a better receiver after probing; omitting that benefit would make the audit misleading.

If B(H)<=0, no extra-pilot policy in that family can improve that block's net rate. If B(H)>0, the bound alone establishes no attainable improvement. A controller that may skip probing has improvement bounded by max(0,B(H)); an always-probe controller has the signed bound B(H). Mean positive-part bounds therefore give a conservative upper bound even for selective stopping. This theorem is elementary and is not presented as new by itself.

The test uses H only in an offline diagnostic. It is not an executable causal stopping policy. Turning it into an online rule would require a simultaneous uncertainty set covering H and maximization over that set, including uncertainty in the receiver's achieved rate. Gaussian working-prior samples do not supply that guarantee.

## One bounded packet

1. Freeze the existing 32 network IDs, four contexts, physical conventions, fixed estimator, T=200, and initial observations. Do not sample a more favorable geometry or touch the reserved test. Finish the present run before deriving inputs for this packet.
2. **Finite-grid track:** use powers {0.05,0.1,0.2} W, sum<=0.4 W, and all six schedules. Compute a causal no-probe grid optimum on the initial estimate; evaluate it on H with its estimated receiver. Independently enumerate at most 6*3^4=486 joint actions on H with true MMSE to obtain V_grid exactly within numerical tolerance. Compute the ordinary column LP on those same true-MMSE coefficients; its objective/verified dual is U_grid. Record the ordinary LP gap and the exact oracle bound separately. Grid enumeration is the reference, not a polynomial scalability result. A complete-schedule simplex is an exact small LP if desired for checking; its enumeration is not a scalable theorem.
3. **Continuous track:** reuse the existing causal continuous no-probe result. Use the already-derived global no-interference water-filling bound with per-user maximum resource gain as U_cont. Use true-CSI adapted I-WMMSE over all six schedules only as a feasible oracle lower bound. Report the resulting interval for headroom. Never use U_grid as an upper bound on continuous power. A loose U_cont means unresolved headroom, not a positive finding. Do not add solvers merely to tighten it in this packet.
4. Report receiver loss separately at the no-probe action: true-MMSE rate at its same schedule/power minus actual estimated-receiver rate. Report the further scheduling/power oracle gain separately. This identifies whether any opportunity concerns information for combining or decisions; it does not allow selecting a favorable component after inspection.
5. Equal-information performance comparators remain random and weakest one-UE probes with exactly one additional symbol/energy. No-probe is the explicit variable-cost reference. The perfect-information oracle is an unattainable ceiling, never a competing algorithm. Exclude uniform_probe from physically matched conclusions until its simultaneous observation model has a realizable pilot design.

Budget: one CPU job at a time; existing environment only; <=10 minutes total wall time, <=10 seconds per network/track including setup, <=256 MB new artifacts and <=2 GiB host memory; no GPU. Use the repaired external watchdog and retained checkpoints. No budget increases or favorable-context reruns. Save source/input hashes and every failure. Missing upper bounds make that part inconclusive; do not silently drop failed cases from aggregate claims.

Verification: enumeration versus ILP on the same finite family; LP dual upper >= enumerated optimum; direct receiver evaluation versus closed-form true-MMSE rates; current causal actual rate <= true-MMSE rate at that same action; continuous upper >= all tested continuous/grid feasible rates. Any failed inequality stops the packet. No new calibration or stochastic tuning is needed.

## Predeclared interpretation

Use equal weights across all four contexts. Report the distribution of B, fraction B<=0, and the aggregate upper opportunity sum(max(0,B))/sum(G0). Adopt 1% as an engineering relevance threshold for this diagnostic, explicitly not a statistical significance threshold.

If even the oracle upper opportunity is <=1%, stop developing selective CSI for this unchanged family. A negative result can guide the project but is not automatically a journal contribution. If the exact grid oracle shows larger opportunity, this only passes a necessary headroom gate for the grid family. If continuous lower and upper bounds straddle 1%, state that the continuous question remains unresolved. Never pick the most favorable context as the next headline.

Only a passed headroom gate justifies subsequently designing a physical, causal acquisition rule with uncertainty-valid certificates and a fresh preregistered development/confirmation split. That future rule is outside this packet. If meaningful oracle opportunity is mostly receiver recovery, the proposed scheduling/LP novelty is not supported even though better CSI could help reception. If it is mostly scheduling/power, the outstanding contribution is then sharply identified: acquire information that changes the feasible resource decision, with a proved bound on its net value. The current evidence does not establish that contribution.
