# Conditional rational pricing prototype packet

Entry: report RESOLUTION-CR015-A01 technical verdict to user before executing this dependent prototype. This is supporting S03 correctness work, not a new S04 campaign or accepted manuscript model.

Goal: replace uncertified floating-point roots in the numerical prototype with exact rational-polynomial real-root isolation and outward objective bounds. Existing base Python/SymPy and standard-library Decimal only; no installs. Scope exactly Theorem 2 of CONTINUOUS_EXACT.md, unweighted true-MMSE, rational normalized correlation/prices and nonnegative rectangular powers.

Method: enumerate roots with SymPy rational isolating intervals; remove polynomial gcd with the exceptional denominator; interval-evaluate recovered coordinates; retain all potentially feasible candidates. Include every edge/corner, r=0 and zero-width boxes. Bound ln of positive rationals using directed Decimal input division and correctly rounded Decimal.ln enclosed by its adjacent representable values, then combine bounds using exact Fraction arithmetic. If denominator exclusion or requested gap cannot be certified within the finite refinement limit, return failure, never a fabricated bound. Root isolation and log-library correctness are explicit trusted dependencies.

References: https://docs.sympy.org/latest/modules/polys/reference.html#sympy.polys.polytools.intervals and https://docs.python.org/3/library/decimal.html#decimal.Decimal.ln .

Predeclared tests: deterministic rational cases covering r=0,1,intermediate correlations, positive/zero/negative prices, edges/interior maxima, degenerate boxes, exact feasible lower points and high-precision independent evaluations. External worker cap 45 seconds, no children; at most two runs for one repair, retain history. Desired oracle enclosure width <=1e-8 natural-log objective units for these cases. No throughput, GPU, solver speedup or novelty claim.

If tests pass, an additional existing-input K=8 diagnostic may be specified separately. It must preserve hashes and use an externally bounded worker. No such network run is authorized by this file alone without its specific input/method manifest. Any later validated upper bound applies to the exact declared rational input model, not automatically to propagation uncertainty or estimated receivers.

Implementation is provisional until separately reviewed. Do not promote a task or scientific stage merely because these tests pass. Original code and frozen theorem note remain unchanged.
