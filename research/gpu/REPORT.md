# Measured power / rate / optimization results

One development instance per size, O1_60 rows1..100, four APs × eight antennas, known CSI, all UE pairs and nine power profiles. Original S02 files and future reserved test are unchanged. Units and excluded network features are in MODEL.md. These are author-checked results, not independently accepted research conclusions.

## Throughput under the same transmit-power budget

| UEs | Columns | Occupied MHz | Power budget W | Fixed-power optimum Mbps | Joint-power IP Mbps | Joint-power LP Mbps | LP−IP Mbps |
|---:|---:|---:|---:|---:|---:|---:|---:|
|8|1008|6.25|0.80|130.280454|130.280454|130.280454|-0.000000|
|16|8640|12.50|1.60|253.663899|253.663899|253.663899|0.000000|
|32|71424|25.00|3.20|465.682013|465.682013|465.696287|0.014273|

All displayed CPU IP/LP solves terminated optimally at the recorded numerical tolerances. The power-grid method did not improve throughput over fixed power in these three instances. At 32 users, the nonzero LP gap directly refutes universal exactness for this formulation; zero gaps in smaller examples are not a general theorem. Occupied bandwidth changes with network size, so the larger aggregate rates must not be interpreted as algorithmic gain across sizes.

## Minimum power at 95% of the fixed-power incumbent's throughput

| UEs | Target Mbps | Achieved Mbps | Reference W | Minimum grid-IP W | LP lower bound W | Transmit-power reduction |
|---:|---:|---:|---:|---:|---:|---:|
|8|123.766432|124.286608|0.80|0.60|0.582646|25.00%|
|16|240.980704|242.176902|1.60|1.20|1.158364|25.00%|
|32|442.397913|443.393155|3.20|2.35|2.311486|26.56%|

This is a rate–power tradeoff against an unoptimized fixed-power reference at a **lower requested rate**, not a 25% efficiency gain at identical throughput and not superiority over a power-control paper. Continuous uniform/fixed-schedule power control, WMMSE/SCA and grid-refinement baselines are still needed to identify any added value from joint decisions. Circuit/fronthaul/compute energy is not included.

## Solver timing and GPU behavior

| UEs | CPU joint LP s | CPU joint MILP s | GPU PDHG iteration/check s | GPU status | Maximum constraint violation |
|---:|---:|---:|---:|---|---:|
|8|0.0061|0.0147|54.1172|TIME_LIMIT_NOT_CONVERGED|0.263991|
|16|0.0822|0.1929|4.7759|TOLERANCE_MET|0|
|32|2.8620|7.3344|30.0025|TIME_LIMIT_NOT_CONVERGED|0.0106641|

The 8-user first sparse GPU execution included JIT/library startup not removed by the coefficient warmup. Its 54.1s time exceeded the nominal30s check budget before the first200-iteration check. It is not a valid steady-state speed comparison. At16 users the GPU met tolerance but was slower than CPU; at32 it failed to meet feasibility tolerance in30s. Its objective at an infeasible iterate is **not a feasible rate**. The dual upper bound remains a separate numerical bound. No GPU speedup or GPU exact-MILP claim is supported.

| UEs | CPU coefficient ms | GPU kernel ms | H2D+D2H ms | Max CPU/GPU coefficient difference |
|---:|---:|---:|---:|---:|
|8|0.1249|1.5305|0.4179|1.42e-14|
|16|0.3938|1.5174|0.4516|1.08e-13|
|32|2.7434|2.5530|0.7798|6.04e-14|

CPU and GPU coefficients agreed well within1e−8. For32 users, GPU kernel time alone was slightly lower than CPU, but adding transfers removed that advantage; one timing sample is insufficient for a stable speed estimate.

## The 64-user run did not complete

The full family contains580,608 variables. The coordinator stopped its process after the aggregate run exceeded the expected per-call budget; no64-user objective was saved. Exact blocking stage is unknown because per-call logging was missing. Peak observed process working set was2,044,841,984 bytes, below the8GiB host cap; OOM was not observed. The run ended with exit1 and results.json remains an incremental artifact, not a successful full-run artifact. See interruption.json. Neither a64-user solution nor a runtime success is claimed.

The new bounded_process.py guard passes separate success, failure and wall-timeout tests, but is not yet integrated into a new solver worker. Historical benchmark code and pre-run hashes remain fixed. A future run must use isolated workers, checkpoint each call, warm sparse operations explicitly, persist LP primal/dual vectors, and compare equal tolerances. No failed size was rerun with a larger budget.

## Scientific decision

Do not write a positive performance paper from this pilot. Continue only the sharper candidate: uncertainty-aware joint scheduling/power decisions with instance-specific optimality or regret certificates and explicit information/compute costs. Matching and duality are established tools; the certificate in MODEL.md is not claimed novel by itself. The selective-information studies remain mostly negative, and the new maximum-rate power study is also negative. A defensible next experiment must test whether realistic AP/fronthaul restrictions, user geometry and QoS create useful decision uncertainty, without selecting a favorable scenario after seeing results. A traceable continuous-power baseline and independent network samples are mandatory before any publication claim.

S03 and S03G are not accepted; S04 confirmatory experiments remain locked. Planning acceptance is not scientific acceptance.
