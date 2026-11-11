# CR033 core method implementation handoff

Status: implementation author handoff, **not independent acceptance**. Author stage began2026-11-03 04:29:25UTC with60-wall-minute cap. Core algorithm sources stabilized by04:36:43UTC; documentation/manifest handoff before04:39UTC. No performance input, pilot, holdout, or registered reference seed was generated or executed by this owner. Root owns those stages and final independent receipt acceptance.

## Files and scientific behavior

- `vendor/`: all13 delivered modules copied byte-for-byte, independently checked against original BASELINE_CODE_MANIFEST. `VENDOR_MANIFEST.json` records provenance. No original file changed.
- `problem.py`: common exact rational feasibility/serialization, stable scalar rate and analytic gradient, physical coefficient validation, matrix/scalar check and producer interval objective. `checked_candidate` is not an independent final certificate; root's unchanged verifier remains authoritative.
- `transfer.py`: same/different-pair transfer log-argument polynomial construction in normalized coordinate; degree-at-most3 numerator; unpriced slack-coordinate numerator degree<=1. Numerical roots, endpoints andzero proposed; degree trimming/repeated/near-real/exception branches logged. No exact-root/global-optimum claim. All accepted changes require rationally serialized lower_new>upper_old and the fixed numerical improvement tolerance.
- `slsqp_power.py`: common-box/shared-budget analytic-gradient SLSQP;500-iteration cap resumes same start while deadline allows. Intermediate feasible interval improvements retained. A numerical solver success flag is not a global certificate.
- `wmmse.py`: actual delivered receiver/matching/amplitude operations reused; common anchor; original uniform/eight seeded starts preserved in the outer;10000 emergency iteration cap and convergence/deadline exchange power refinement, replacing arbitrary short caps. Matrix/scalar check accompanies retained global improvement.
- `search.py`: one deterministic multistart/four-user assignment exchange wrapper for T/S/FU_SCA/THU_IDE. Five method names are supported through registered refiner mapping; modern owner supplies Fu/Thu. W retains matching multistart before exchange. Common start digest and explicit started/completed/exchange counts are logged. Callback exceptions keep the previous retained candidate and return error diagnostics.
- `reference_line.py`: independent SymPy derivative construction from rational MMSE logarithms, root isolation and outward objective bounds; does not reuse T numerator builder. Mathematical scalar fixtures deliberately specify exact gain/r pairs and do not claim arbitrary all-pair coefficient collections form network channels.
- `reference_orthogonal.py`: separate exhaustive6-assignment K4 reference, rational water-filling multiplier bracketing, feasible lower and concave dual upper. Certified only for orthogonal data with gap<=1e-6nat. Unfinished coverage retains conservative universal ceiling. Nonorthogonal input is rejected. Root performs full physical-input/final schedule validation.
- `test_core.py`, `test_guards.py`: deterministic correctness fixtures; `run_tests.py` reserves cost before subprocess execution and logs startup/import/failure/cleanup in CORE_TEST_LEDGER.json.

## Interface and accounting

Exact integration contract is INTERFACE.md. Assignment is resource-ordered tuple of sorted user pairs; powers indexed by user. `search.run` returns producer `candidate`, status and JSON-safe diagnostics. Candidate contains Fraction/ndarray objects and should be serialized through its `schedule` field. Root's worker matches this interface. Root was notified that a returned core status='error' must not be marked operationally normal merely because the wrapper returned without raising.

The frozen policy passes the **full remaining global deadline to each power call**. No unregistered0.5s slicing was added. Consequently Thu-IDE can spend its allowance on the anchor assignment, with zero completed neighborhood/restarts; this is explicit adapter behavior, not evidence against the source's entire architecture. Equal permitted starts/neighborhood do not imply equal completed work or evaluations. All process startup/import/callback and independent final checking costs remain root-controlled within the20s contract.

Producer acceptance uses cached outward Decimal/rational interval evaluation from the unchanged certificate producer. Final root publication uses the separate integer-log verifier. Failed root generation retains endpoints/zero, and every method retains a feasible anchor under deadline/numerical failure. Native linear algebra/root/SLSQP operations are cooperatively bounded between calls; root's external watchdog is required for hard enforcement.

## Executed correctness evidence

Two logged executions only:

1. `test_core.py`: PASS,60s reserved,4.657s actual including import/startup.22 evidence records: twelve generic rational restricted-line comparisons across r=0,1/2,1, equal/unequal gains and same/different scheduled pairs; edge branches; four physically constructed orthogonal/collinear/unequal/near-collinear scalar-vs-matrix/gradient comparisons; independent orthogonal6-assignment reference; short T/S/W deterministic fixture runs; expired-deadline fallback.
2. `test_guards.py`: PASS,25s reserved,1.078s actual. Publication exception rolls back unpublished retention; planned starts identical across T/S/W; strict serialized interval-monotone accepted transfer trace; root exception endpoint fallback; expired line; reference nonorthogonality/timeout guards; illegal incidence/nonfinite rejection and exact power repair.

Total conservative test reservation85/260s, actual5.735s; unused175s is not permission for unlogged work. No test failed and no repeated full test run was needed. Registered eight reference cells are not included in these fixture records and remain root-owned under their separate480s allocation. Modern identity/equivalence fixtures remain modern-owner responsibility. Core tests prove listed obligations only, not practical rate efficacy or general global-optimum correctness.

## Remaining limitations and acceptance

Numerical polynomial coefficient trimming can lose a stationary point; hence numerical heuristic wording is mandatory. Exact orthogonal reference is a restricted subclass, while generic line reference certifies only a one-dimensional restriction. The finite deadline may leave initial starts/exchanges incomplete. All claimed empirical advantage waits for independent method, pilot and study checkpoints. Root must confirm modern adapter integration, registered development references, timeout/publication receipts and source hashes before method acceptance. No self-PASS is issued by this implementation author.
