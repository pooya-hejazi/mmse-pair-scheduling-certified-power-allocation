# Results: a certificate, not a universal LP solution

The bounded study uses 240 O1_60 channel instances, 4/6/8 users, four APs with two retained antennas/AP, uniform/nearby users, and normalized noise 0.1/1. Half repeat one physical channel across time slots (flat); half use different real subcarriers. Known CSI and fixed power isolate optimization structure. These are exploratory development samples, not held-out generalization evidence.

| Users | Resource model | Instances | Positive ordinary LP gap | Positive odd-set LP gap | Conflict-free optimality certificate |
|---|---|---:|---:|---:|---:|
| 4 | Flat | 40 | 0 | 0 | 40 |
| 6 | Flat | 40 | 0 | 0 | 40 |
| 8 | Flat | 40 | 1 | 0 | 40 |
| 4 | Frequency selective | 40 | 1 | 1 | 38 |
| 6 | Frequency selective | 40 | 7 | 6 | 30 |
| 8 | Frequency selective | 40 | 10 | 7 | 25 |

All 240 MILPs terminated optimally and their objective values were independently recomputed by a second author check using enumeration of matchings followed by resource assignment. This is **author verification, not independent checkpoint acceptance**. Total study time was 1.148 seconds inside the study loop, excluding channel generation, imports, and checks; it is not a large-scale timing result.

The strengthened LP is exact in the flat subclass, as classical matching theory predicts. With frequency-selective resources it still had a positive gap in 14/120 instances. The resource-price recovery produced a sufficient certificate in 93/120. A failed recovery certificate does not imply a positive integrality gap: another optimal matching may satisfy the tie conditions. Largest observed strong gap was 0.433154 in the study's rate objective; largest reported recovery residual must be read separately from LP minus IP.

The 2008 assignment argument cannot be transferred generically to disjoint pairing: an abstract symmetric weight matrix with two odd cycles gives half-assignment value 30 but perfect-matching value 20. This witness is not asserted to arise from that paper's physical channel family. The 2025 paper's printed joint objective is bilinear, and its upper-bound-only AP constraints permit the all-zero AP assignment; its printed rounding procedure is not an exactness theorem. These are bounded observations about the text, not a reproduction of the authors' code or curves.

## Research decision

Continue a narrower candidate: **certified resource and power decisions, with a rule that distinguishes spending on CSI information from spending on optimization**. Matching/duality alone is classical prior art. The open contribution would need a useful new certificate, valid uncertainty interface, and demonstrable net throughput/power improvement under equal total cost. Existing selective-information experiments were mostly negative and are retained. No publishable novelty is established yet.

Power budgets and power profiles are a new model extension; none of the exactness claims above automatically transfers to it. GPU coefficient construction and LP approximation are a separate engineering experiment. General MILP remains the reference with explicit timeout and gap.
