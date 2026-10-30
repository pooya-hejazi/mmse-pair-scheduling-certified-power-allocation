# CR009: Astra-directed perfect-information headroom audit

Authorized by the user's request to continue autonomously and consult Astra on alternatives. Decision and proof: ../comparison/ASTRA_DECISION.md. This is one bounded diagnostic within S03/T-A02..04, not a new selector, estimator or confirmatory S04 trial.

Freeze the same32 networks, initial observations, four contexts and completed no-probe decisions from CR008. Finite-grid track uses exact enumeration of all six schedules and3^4 power vectors with total<=.4W; causal grid decision from initial estimate; actual estimated-receiver rate evaluated separately. Oracle uses true CSI and MMSE. LP and MILP share precisely that family and grid. Verify the numerical LP dual bound independently via the box Lagrangian. No claim of polynomial scaling from enumeration.

Continuous track reuses the causal no-probe continuous decision, bounds oracle optimum above by global no-interference water-filling and below by all-six-schedule true-CSI adapted I-WMMSE (also include perfect-MMSE value at the existing action). The grid LP never bounds continuous powers. Report receiver loss at unchanged action separately from scheduling/power opportunity.

Raw bandwidth-normalized rates R0,V,U give net no-probe G0=.98R0 and post-probe oracle bound .975U. Every one-extra-symbol policy in the same family has gain<=B=.975U−.98R0. Optional probing gain<=max(0,B). H enters only this offline diagnostic; no deployable online certificate is asserted.

Report all contexts with equal weight. Engineering relevance gate is aggregate positive-part oracle opportunity / aggregate no-probe rate >1%, predeclared before audit outputs. This is not a significance threshold. For exact grid oracle it is only a necessary opportunity gate; for continuous, lower/upper straddling1% is inconclusive. If upper opportunity<=1%, stop selector development in this unchanged family. No favorable subset/geometry selection.

Budget: existing CPU environment, serial<=10s external wall cap per network including both tracks, <=10min total, <=256MB new output, <=2GiB worker memory. No GPU/install/new channel generation. Stop on mathematical inequality failure; preserve all timeouts and never drop them from aggregate denominator. Checks: grid enumeration vs MILP, reconstructed LP dual>=IP, actual receiver<=perfectMMSE at same action, continuousupper>=gridopt/continuousfeasible, sources/inputs hashed. Previously completed comparisons and original code are preserved.
