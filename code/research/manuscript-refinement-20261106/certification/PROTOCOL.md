# Frozen finite-box / integral-schedule study

## Population, purpose, and prospective targets

Evaluate **all 32 unchanged corrected physical cases** in the nested frozen
`baseline_R1/Supplementary_Materials.zip`: ASU and O1 each have 12 main K8
and 4 scale K16 cases. No replacement, reseeding, exclusion, normalization,
noise change, or power-domain change is permitted. `INPUT_MANIFEST.json`
binds the complete population and common-grid schedules to archive bytes.
Only original O1-main-00, the original reliability fixture, and explicitly
synthetic nonorthogonal fixtures were used for algorithm development.

The prospective scientific target is **certification**, requiring all 32
new records to verify, at least 16/32 gaps `U-L <= 0.01` nat, and at least
50% median paired reduction in `U-L_grid` against the matched new run of
the frozen generic scalar-price repair. The common-grid lower in this last
comparison prevents improvements in feasible power from masquerading as
an upper-bound improvement. Invalid or timed-out rows remain in the
population and prevent the all-verified target. A failed target is reported.

Achieved sum rate is a separate endpoint. Report every paired gain from
the common grid and from the archived Full/pricing schedules. Count gains
of at least 1% as a predeclared **descriptive material-gain threshold**;
this is not a significance test or a superiority acceptance rule. No
statistical rate-superiority hypothesis is tested. Small attainable
headroom is a legitimate outcome, not a reason to replace physical data.

## Frozen algorithm

1. Start from the **archived grid result's exact schedule**. SLSQP proposes
   continuous power on that assignment, with a one-second internal limit.
   Repair feasibility exactly and retain only a larger enclosed lower.
2. Propose one nonnegative common **physical-power** multiplier from median
   interior derivatives (or `K/P`; zero for visible slack). Represent it
   as a rational with denominator `2^30`. Proposals are not certificates.
3. Cover every original pair/resource power box. L-BFGS-B proposes leaf
   tangent points. Decide quadrant/finite-box concavity by exact rationals,
   using cancellation-safe W2. Bound with a whole-rate tangent when
   certified, otherwise a tangent to `2 log d` plus upper convex secants;
   also use the mixed bound. Complete bisections refine the largest
   numerical pricing-gap proposal, at most 1,200 splits per price table.
   Search stops at numerical row gap `1e-7` only as a heuristic; all bounds
   still require the independent rational reconstruction.
4. Round each certified price upper upward to `2^-40`, preserving signs.
   Bottom-up exact integer subset DP considers **all pairs** for each
   labelled resource. Keep `lambda*P` exact. Refine the DP schedule's
   physical powers and retain a better lower if obtained.
5. Up to three complete price evaluations are allowed, updating the price
   from the proposed DP schedule. Stop if the exact producer upper/lower
   difference is at most `0.001` nat, the next price differs by at most
   `1e-6`, or the cap is reached. Keep the smallest complete upper and
   best feasible lower. No claim of guaranteed duality-gap closure follows.
   An incomplete later round cannot erase a complete earlier bound.
6. Emit the selected complete price, every tangent point and partition
   split, all upward integer weights, the exact DP sum and maximizing
   schedule, a feasible lower witness, input hashes, and round diagnostics.

The independent standard-library checker imports no producer/optimizer.
It reconstructs scalars from binary64 channel vectors, replays complete
partitions, rebuilds all rational bounds, and uses its own top-down DP.
Only the frozen integer log enclosure primitive is shared. Neither
nearest-rounded derivatives nor a final ceiling of an unverified number
can certify anything. The integral upper is for `V_C`, not necessarily
`V_CLP`. Its dominance over a repaired configuration dual is asserted only
for matched `lambda,H`; the saved fixed-alpha diagnostic has that scope.

## Comparator, timing, fallbacks, and failures

Primary comparator: unmodified frozen `certificates.run(mode='grid_repair')`
and its unmodified independent `verify_upper.verify`, supplied the same
archived grid schedule and archived grid dual proposals. This is the
generic rectangular scalar-price repair; no new grid solve is charged.
Both methods receive **10 seconds producer computation**; independent
checking receives **15 seconds separately**, with actual time reported.
The new algorithm reserves 1.6 seconds for K16 DP (0.15 for K8); timings
include construction/refinement inside the callable, excluding imports,
archive loading, initial verified fallback setup, and output I/O. Small
atomic-operation overruns are recorded and fail the timely flag. There is
one trial per case/method. Order alternates by case index. Caches clear
before each charged producer/checker call. The run is sequential.

A separately checked universal/grid fallback is prepared per case. On
producer/checker error or timeout, retain that fallback and the error in
the row; do not count the row as a successful new bound. Integral-DP or
price-family incompleteness is explicit. A 1,000-second campaign guard
leaves every remaining planned case as an explicit incomplete row. Total
new execution (development, campaign, replay) is intended below 20 minutes.

The original archived Full (K8) / pricing (K16) and joint outcomes are
context, with their reported timing scopes retained. Their **schedules**
are independently rechecked under the unchanged current case. The four
matching physical cases with recorded CR033 T/S/W/Fu-SCA/Thu-IDE outcomes
are also rechecked, after exact model equality. Their common anchors are
recorded where available. Equal initial schedules do **not** imply equal
timing or preprocessing scope; no matched-time claim is made against
these historical rows. No new modern-comparator optimization is run.

## Analysis and reporting

- Publish all-case exact outputs and a flattened CSV, including failures.
- Report certificate counts, fixed-anchor and delivered gaps, paired gap
  reductions, actual producer/checker times and cap flags by scene/K.
- Report achieved and archived feasible rates separately, plus the upper
  bound on remaining improvement over each checked old Full/pricing lower.
- At nominal 0.1 W, report all user/resource received SNR distributions
  and median-of-case-medians (zero links explicitly counted). Report
  squared-correlation distributions and exact full-box curvature counts.
  Scene and case dependence are retained; no deployment-throughput claim.
- Check all newly saved rows in a separate replay, loading bound archive
  inputs and exact witnesses and comparing all claimed rational endpoints.
  Missing/duplicated rows, altered files, replay errors and timeouts appear
  in the replay ledger. Numerical summaries are descriptive; exact JSON
  fractions, not display floats, determine certificate success.
- Freeze source/protocol/input hashes after passing mathematical,
  coverage, signed-rounding, labelled-DP, power-duality-gap, zero-gain,
  archived-binding, and output-replay tests. The all32 campaign may only
  start after `FROZEN.json` exists and its hashes still match.

The proof is documented in `PROOF_NOTE.md`; the separately authored parent
`PROOF_AUDIT.md` is incorporated by hash. Its PASS is mathematical and
does not constitute acceptance of unobserved empirical outcomes.
