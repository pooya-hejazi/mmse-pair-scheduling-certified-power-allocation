# Model reconciliation after reading the supplied papers

31 October 2026. Supporting derivation, not a new model claimed as original, not an independently accepted theorem, and not a new solver run. The frozen proof note remains unchanged.

## 1. A clean common integer scheduling model

Let U be the users, B the elementary resource blocks, and R the family of allowed **nonempty** contiguous resource patterns. Each column a=(e,r) assigns a two-user subset e of U to pattern r. Its coefficient w_a is computed from the declared receiver, CSI, fixed powers and fairness weights. Define user incidence H_ua=1[u in e] and resource incidence A_ba=1[b in r]. For optional service and optional unused spectrum, a faithful packing model is

    maximize w^T x
    subject to Hx <= 1, Ax <= 1, x in {0,1}.

If every RB must be occupied, impose Ax=1 explicitly. If every user must be served exactly once, impose Hx=1 explicitly, accepting the resulting feasibility requirements. These are distinct contracts; none may be silently substituted for another. With pure two-user columns, Hx=1 requires even |U|. Empty patterns are unnecessary for optional service: an unserved user is represented by no selected column. A silent/dummy-variable construction would need its own stated incidence and meaning.

This is a standard set-packing/partitioning formulation of the existing allocation concept. It does not constitute a new contribution. The elementary RB rows linearize the integer non-overlap condition in Ruder 2014 eq.(28d). They also specify a particular LP relaxation: replacing binary x with x>=0 yields a maximization upper bound. Pairwise conflict inequalities alone can produce a weaker fractional relaxation even when their binary feasible set is the same. One must identify the actual LP matrix before asserting exactness.

For the project's narrower full-service model, take K even, S=K/2 fixed disjoint equal-sized resources, one pair per resource, and every user once. The rows become the equalities in PROOF_NOTE.md. This is a restricted scheduling family, not the same feasible set as optional service on arbitrary contiguous patterns. Generic NP-hardness of the larger family does not prove hardness of this subfamily. The project's separate explicit physical reduction addresses its own assumptions only.

## 2. The Fan printed equality requires care

Fan 2012 PDF p.4 / printed p.2841, eqs.(10a)–(14), gives Cx=1 with a user-incidence block having two ones in every column, including columns for the empty resource pattern. Summing its user rows yields

    2 sum_a x_a = K.

Thus the literal binary equality model cannot be feasible for odd K, whereas its displayed example uses K=5 and the paper discusses scheduling subsets. This is a specific inconsistency between the printed formulation and the service interpretation. It does not establish what the unavailable simulation code actually solved or invalidate every result. Reproduction must state the intended packing/full-coverage model and disclose any repair. Merely changing all equalities to inequalities without identifying the intended service contract is not a faithful literal reproduction.

## 3. Capacity and linear-MMSE rate are different coefficients

For a noise-whitened, flat pair define x=g1 p1, y=g2 p2 and

    D=(1+x)(1+y)-c p1 p2,   c=|h1^H h2|^2.

Joint-decoding Gaussian sum capacity is C=log2 D. The sum of the two separate linear-MMSE rates is

    q=2 log2 D-log2(1+x)-log2(1+y).

Consequently

    C-q=log2((1+x)(1+y)/D) >= 0.

It vanishes for orthogonal channels or a zero-power user. This standard identity explains why the capacity-based pairing weights of Ruder 2011/2013 cannot simply be substituted for the project's MMSE-rate weights. Their separate BER/detection experiments do not make the objectives identical. Likewise, the existence of an exact Hungarian step with fixed pairs does not imply joint-pairing optimality or integrality of the configuration LP.

Ruder 2014 eqs.(3)–(6) and Fan 2012 eq.(5) use SC-FDMA effective SINR: inverse averaging of inverse (1+SINR) over the assigned subcarriers. This is generally different from summing independent OFDM tone rates. Under **flat channels within each resource**, equal resource bandwidth, equal fairness weights and matching noise/power normalization, their fixed-power pair utility reduces, up to a common factor, to q. That establishes direct physical-objective overlap under stated specialization, not equivalence of all their constraints or evaluation settings.

## 4. Power and CSI contracts for future comparisons

Fan's equal/unequal received-power cases are fixed inputs; Ruder's cited pairing cases use fixed power. None supplies a global continuous-power optimizer for our problem. If a finite set of pair-power choices is enumerated, add those choices to column a and their power costs to a budget row; the resulting finite problem is an ILP. Relaxing column integrality gives an LP for that grid. Allowing genuinely continuous power leaves nonlinear rate coefficients and is not the same finite LP. GRID_CONTINUOUS_BOUND.md gives a separate, scoped discretization allowance.

Ruder 2014 PDF p.9 / printed p.96 explicitly uses imperfect CSI for scheduling but perfect CSI for payload detection, and counts sounding overhead. This is prior art for isolating scheduling-information effects. To compare with it, declare whether both schedules and receivers see the same information; do not mix receiver improvements into a decision-only gain. No new estimator development follows from this observation.
