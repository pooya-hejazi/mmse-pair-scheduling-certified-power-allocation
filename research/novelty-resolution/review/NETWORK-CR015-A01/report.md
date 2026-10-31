# NETWORK-CR015-A01 independent integration audit

31 October 2026. Initial attempt under the separate two-attempt network integration contract. I did not author the network integration. I previously reviewed the isolated pair oracle and reuse that acceptance only within its stated rational rectangular scope. Three reflections were completed within the six-minute budget; one independent computation ran under an external 30-second limit. No agents, installations, broader runs, or source edits were used.

**Scoped verdict: PASS for this one stored-input K=8 development certificate integration.** The exact feasible schedule and repaired continuous-configuration dual bound are valid for the declared model. S03/S04 acceptance, novelty, algorithm superiority, practical throughput, GPU scaling, and general network implementation acceptance remain **UNVERIFIED**. No blocking integration defect was found.

## R1 — Feasible set, normalization, and coverage: PASS

The frozen NPZ contains only h, a complex128 array of shape (8,32,4). Every real and imaginary binary64 component is converted exactly to a rational; converting those components through Python float loses no bits for this dtype. Independent reconstruction using as_integer_ratio reproduced every stored gain and squared normalized inner product. Positive channel gains and correlations in [0,1] hold. The input digest matches both the pinned comparison manifest and the result, and the execution manifest's seven source/input hashes match the frozen files.

The certified model uses identity-noise normalization implicit in the stored h, true-channel recomputed linear MMSE, no unequal rate weights, all 28 unordered user pairs on each of four resources, one pair per resource, and each of eight users served exactly once. Every served user's physical power is in [1/20,1/5] W and total radiated power is at most 4/5 W. The normalization x=g_u p_u and y=g_v p_v is correct. The price conversion lambda/g_u makes the oracle's normalized penalty exactly lambda p_u. Independent exact Sherman-Morrison SINRs and 100-digit logarithms confirmed the schedule rates. The certificate concerns these stored channels; the input archive alone does not establish upstream noise calibration, channel-generation correctness, or physical-model fidelity.

There are exactly 112 unique pair/resource pricing entries, with their key set equal to all 28 pairs times four resources. Each continuous pricing rectangle covers the full power box. The grid has all nine ordered power-level assignments per pair/resource, hence 1,008 columns. Using an unordered user pair loses nothing because the two associated powers remain independently selectable.

Let Z_GI and Z_GL denote the exact-objective grid integer and grid LP optima, Z_CI the continuous integral optimum, and Z_CL the infinite-configuration LP optimum. The valid relations are Z_GI <= Z_GL <= Z_CL and Z_GI <= Z_CI <= Z_CL. There is no general ordering asserted between Z_GL and Z_CI. The stored numerical LP/MILP values are proposal evidence, not exact optimality certificates for those grid problems. Their near equality is unnecessary to the valid network bounds below.

## R2 — Dual repair, exact primal, and reported arithmetic: PASS

For any pair (u,v) on resource t and any feasible local powers, the accepted pair oracle certifies

    q_uvt(p_u,p_v) - lambda (p_u+p_v) <= U_uvt.

Setting beta_t=max_{u<v}(U_uvt-alpha_u-alpha_v) makes every infinite-column dual constraint valid. User prices alpha and resource prices beta are free because their constraints are equalities; lambda must be nonnegative for the upper-bounded power budget, as it is here. Summing these inequalities over any integral schedule, or integrating them against any nonnegative feasible configuration-LP solution, gives

    objective <= sum_u alpha_u + sum_t beta_t + lambda * (4/5).

Thus numerical LP marginal signs, residuals, and grid approximation cannot invalidate the repaired bound: the extracted numbers serve only as exact rational candidate prices. Each stored pricing upper bound already includes its enclosure error; no separate sum over all 112 pricing tolerances is needed.

The independent check recomputed all 112 accepted-oracle calls from the stored channels and exact recorded prices. Every pricing upper bound, enclosure width, and root-refinement count matched exactly. Every repaired dual constraint held, all four beta values equalled their exact per-resource maxima, and the exact summed dual value matched upper_nats. The largest pair-pricing width was approximately 8.35495e-9 nats, below the declared 1e-8 tolerance.

The selected schedule pairs users (0,2), (3,4), (5,7), and (1,6) on resources 0,1,2,3 respectively, with power 1/10 W for each user. Exact integer incidence checks confirm each user and resource occurs once. Exact rational power checks give 4/5 W, and every power belongs to the permitted box and grid. The selected schedule therefore remains feasible independently of MILP status or integrality tolerances. All four interval rate lower bounds and their sum were reproduced exactly; independent MMSE rate evaluations lie inside the corresponding intervals.

The exact rational nat bounds correspond approximately to 60.202353115471205 and 60.67830317764084. Dividing the positive lower bound by the upper ln(2) bound, and the positive upper bound by the lower ln(2) bound, preserves enclosure direction. The JSON decimal fields are explicitly displays and use ordinary float rounding. For a rigorously outward-rounded eight-decimal statement, the audit establishes

    86.85363628 <= Z_CI / ln(2) <= Z_CL / ln(2) <= 87.54028709.

The attained schedule is at least the left endpoint. The relative certificate width (U-L)/L is approximately 0.790583818637%, hence less than 0.790584%. This is an upper bound on the incumbent's relative shortfall to the continuous integral optimum; it does not decompose discretization, scheduling integrality, or dual-price suboptimality, and does not prove exact optimality. These are sums of spectral-efficiency terms over resources, not a demonstrated network throughput in bits per second.

## R3 — Provenance, execution, and claim limits

**Frozen evidence integrity and bounded execution: PASS.** All 15 snapshot entries matched SHA-256 before analysis and after the independent computation. Initial and final hash records are retained here. The supplied boundary record reports an ACL-denied negative write probe; I did not attempt a new write against the protected snapshot. The accepted pair-oracle source hash is unchanged. The original network run reports completion, exit code zero, empty stderr, 7.789 seconds externally against a 45-second limit, and 4.945 seconds inside the diagnostic. The source sets five-second LP/MILP limits and fails before publishing a result on unsuccessful LP, missing feasible integer incumbent, unresolved pricing, or failed checks.

The single independent worker completed in 5.578 seconds under its 30-second external cap; its internal verification took 4.948 seconds. It did not re-solve the numerical LP/MILP or rerun the integration script. It reconstructed channels, audited all 112 pricing certificates, repaired-dual arithmetic, exact primal feasibility, independent MMSE rates, numerical displays, and provenance. Evidence is retained in independent_check.py, run_independent.py, independent.stdout.json, independent.stderr.txt, and independent-execution.json. Python bytecode writes were disabled.

**Broader scientific and performance claims: UNVERIFIED.** This single existing development instance establishes a useful narrow certificate, not matched-baseline superiority, general runtime performance, CPU/GPU scaling, throughput gain, novelty, manuscript sufficiency, or stage acceptance. Reuse of the oracle is conditional on its accepted SymPy root-isolation and Decimal log dependencies. No whole-pipeline or upstream physical-input audit is implied. No task, plan, checkpoint, live source, frozen artifact, or original result was changed; all new files are confined to this review directory.
