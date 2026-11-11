# Modern adapter source-to-code map

Implementation follows the root-authorized protocol-v2 and its hash-bound `modern-comparators/ADAPTER_SPEC.json` (SHA2569da6d49713b65a78e0dbc6cfb6baf98eef99fc7ca7f1b5b2337129dfb381cbe0). This is author implementation evidence, not independent acceptance.

## Fu-SCA (TCOM2026, adapted; exact denominator)

- `fu_sca.frozen_coefficients`: exact common-model instantaneous MMSE direction at current powers, unit normalization; b_i desired amplitude, c_ij interference coupling, n_i noise. This deliberately replaces source statistical-CSI LP-RZF architecture and recomputes receivers each outer step.
- `tangent_coefficients`, `surrogate`: Fu Eq.(25c) tangent t_i=2a_i b_i v_i-a_i²N_i(v), with analytic Jacobian/gradient and source power-block log utility. Exact common-model N_i replaces the printed Eq.(25e) extra old-denominator addition. This discrepancy is disclosed in label, docstring and prior source map.
- `solve_surrogate`: Algorithm2 power phase, maximizing the concave surrogate under positive amplitude box/shared quadratic budget and t_i>=0. SLSQP solves this convex surrogate, not the original rate objective. A smooth tangent extension of log below1e-8 exists only to define trial objective evaluations outside the feasible domain; accepted solutions satisfy the original surrogate domain.
- `refine_power`: recompute receiver, solve block, repair exactly, validate surrogate, independently enclose actual common-model rate through core Problem, accept only disjoint improving enclosures plus core numerical tolerance. Shared callback false does not reject local progress. Native status9 resumes the same convex block; caps, failures, stalls and deadline stops are distinct.
- `stationarity_residual`: scaled projected gradient in original power coordinates; stationary label requires small change AND residual<=1e-7. No global optimum, deterministic-equivalent or timed-iterate stationarity claim is inherited.

## Thu-IDE (TCOM2026 accepted manuscript, adapted power search)

- Exact source version remains arXiv2607.21860v1; primary author record verifies TCOM acceptance. Final DOI/pages were not primary verified, so no final-typeset reproduction claim is made.
- `mutation`: source Eqs.(31),(32), pbest/1 and current-to-pbest/1.
- `crossover`: Eq.(34) binomial crossover with forced coordinate.
- `sample_parameters`, `lehmer`: Eqs.(35),(36), per-operator Cauchy/normal sampling and gain-weighted Lehmer means; empty or zero-denominator success histories retain prior means.
- `operator_probability`: Eq.(33), gain per ALL invocations, resolving the source prose/Algorithm1 counting inconsistency prospectively. Untried operator retains current probability.
- `generation`: frozen old population AND archive, distinct donor identities, stable ranking, strict enclosure-validated replacement, successful displaced-parent archive, synchronous means updates. No stock differential-evolution implementation is called.
- `refine_power`: p0 then shared `problem.common_power_starts`, projected/deduplicated initialization, charged native population Q=min(4K,300),500-generation restart boundary, source means(.2,1),lambda=.2,T=10; prospective pbest10%,scale.1,archive capacityQ conventions are unchanged. All parameters are frozen; there is no pilot/holdout tuning.
- `common.project`: Euclidean common box/shared-budget projection by multiplier bisection, followed by exact rational core repair. Repaired phenotype is stored back into the normalized chromosome.

The source mixed binary satellite/AP encoding is replaced by a power-only chromosome under the same common assignment wrapper as T/S/Fu. No MRC ergodic energy-efficiency objective, satellite hardware assumptions or source convergence-in-probability claim transfers. Root explicitly retained a full remaining deadline per power call: IDE can consume that call on its initial assignment, leaving outer exchanges/restarts incomplete. This limitation must be disclosed, not silently fixed by an unapproved arm-specific time slice. Native generations, initialization, restarts and operator invocations are recorded; core records completed assignment/start coverage.

## Common safety and scope

`common.checked` brackets producer verification with absolute `time.monotonic` checks. The unchanged root final verifier remains independent. No callback receipts after root's deadline become accepted study outputs. Exact-enclosure acceptance matches core's interval and numeric monotonicity rule. Numerical invalid proposals retain the previous feasible candidate; callback exceptions propagate for core fallback handling. All imports, population creation, checks, callbacks and native work are charged by root's cell clock. These modules perform no import-time experiments, filesystem writes or network calls.

Ou Eqs.(67),(72),(74) Shannon-limit coefficients are tested against actual WMMSE coefficients/updates. No redundant Ou performance arm exists. Chen remains contextual only.
