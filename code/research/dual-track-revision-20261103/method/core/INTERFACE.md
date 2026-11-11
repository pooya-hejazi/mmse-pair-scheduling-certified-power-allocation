# Frozen integration interface (core v1)
Import `problem.Problem` with method/core on sys.path. Vendor modules live under core/vendor; core adds that path internally. No import performs experiments or writes.

`Problem(case_dict_or_path)` exposes k,s,m,h[K,M,S], low/high/budget Fractions, pmin/pmax aliases, lookup[(u,v,s)]=(float g1,g2,r), model=certificates.Model, case.
Assignment is tuple of S sorted user-pair tuples in resource order. Powers are indexed by USER, not slot.
`value_gradient(assignment,p) -> (float Q_nats, ndarray gradient)`.
`repair(p) -> tuple[Fraction]` (exact clipping/budget repair, reject nonfinite).
`checked_candidate(assignment,p) -> dict` with schedule (JSON rational strings), assignment, powers(tuple Fractions), numeric(ndarray), lo/hi(Fraction objective enclosures), value(float). This producer check is NOT independent final publication; root uses unchanged verifier.
`improves(candidate,old) -> bool`: strict serialized interval ascent AND numerical tolerance1e-10+1e-9*max(1,abs(old.value)).

Power adapter: `refine_power(problem,assignment,p0,deadline,rng,publish) -> (numeric_power_array,diagnostics)`; deadline is absolute time.monotonic(). Check it before expensive operations. `publish(assignment,powers,diagnostics)` returns bool indicating global retention; false does NOT mean a local candidate is infeasible. Callback exceptions propagate to core wrapper, which retains anchor/best. Adapter must always retain p0 if no safe improvement; diagnostics JSON-safe and include stop reason/evaluation/iteration/cap/error counts.

Core `search.run(method,problem,anchor,deadline,seed,publish=None,refiners=None)` accepts anchor either checked-candidate dict or JSON schedule list. refiners is dict mapping FU_SCA/THU_IDE to the adapter function; T/S/W built in. Returns dict with best `candidate`, `status`, `diagnostics`. T/S/FU/THU use the same common outer. No independently checked receipt is claimed by this return.

Independent orthogonal reference: `reference_orthogonal.solve(case,deadline) -> dict(lower_nats:str,upper_nats:str,schedule:list,status,assignments_completed,gap_nats:str)`; exact-to-tolerance assertion only if status==certified and all6 assignments covered.

All imports/startup and callbacks count against owner/controller clocks. No interface permits independent hidden polishing or performance generation. Root owns controller/generator/final verifier.

`problem.common_power_starts` is populated by search.run with uniform plus eight shared SeedSequence-derived power vectors (numeric arrays). Standalone adapter fixtures may set it explicitly or use an empty list. The full remaining global deadline is passed into each refinement; no per-call time slice. IDE may use the whole cell on the anchor assignment; incomplete starts/neighborhood are logged, not misrepresented as completed search.
