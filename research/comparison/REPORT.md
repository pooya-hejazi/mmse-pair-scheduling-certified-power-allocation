# Equal-cap comparison: measured outcomes and research decision

The completed development run contains215 jobs:213 completed,2 externally timed out. The two64-user solver workers were killed after20.071/20.046s; their feasible initial schedules survived as checkpoints, not solver optima or LP bounds. There were no repeated completed trials. A Windows sharing error interrupted one status-file rename; its completed result was recovered unchanged, and only unexecuted jobs resumed. Original20min wall budget was retained; total elapsed including repair was322.47s. See storage-repair.json and original/history hashes.

## Known-CSI continuous power

All continuous arms use the same deterministic schedule, power box[.05,.2]W and sum budget. Rates below are sumSE; no changing-bandwidth comparisons are inferred.

| UEs | Uniform sumSE | SLSQP sumSE | Adapted I-WMMSE sumSE | Uniform power W | Uniform continuous power W at95% rate |
|---:|---:|---:|---:|---:|---:|
|8|81.881116|81.881118|81.881116|0.800|0.560795|
|16|164.135717|164.135724|164.135717|1.600|1.120640|
|32|319.589230|319.589248|319.589230|3.200|2.262241|

The continuous optimizers provided negligible sum-rate improvements over equal power in these instances. Even simple uniform continuous scaling saves substantial transmit power when a5% rate loss is allowed. Thus the earlier savings against an unoptimized fixed-power reference are not a defensible innovation claim. Targets/schedules differ from the earlier globally rescheduled grid study; their exact percentage savings cannot be subtracted as a matched comparison.

The full grid MILP can reschedule and obtains higher rates than these fixed-schedule continuous arms. That difference is **not evidence that grid power outperforms I-WMMSE**. The models' scheduling families differ. A joint alternating scheduling/I-WMMSE comparator or all-schedule small benchmark is required for a joint-method superiority claim. The information experiment below uses all six schedules for every method, avoiding this particular mismatch.

## Selective information with continuous power

Each context contains8 paired development networks. All primary acquisition arms spend5 pilot symbols/17 total normalized pilot energy and use the same all-six-schedule adapted I-WMMSE, common power budget0.4W and5s external runtime cap. All192 information jobs completed. Values are net bandwidth-normalized bit/s/Hz including the stated pilot prelog, but not physical compute airtime.

| Geometry | Noise | Joint−random mean [descriptive95% CI] | Joint−weakest mean [descriptive95% CI] |
|---|---:|---|---|
|uniform|0.1|-0.022050 [-0.059435, +0.001975]|-0.007660 [-0.031605, +0.015987]|
|uniform|1.0|+0.039351 [-0.053686, +0.168140]|-0.002897 [-0.049399, +0.045508]|
|nearby|0.1|+0.008837 [-0.031740, +0.051078]|-0.002970 [-0.036133, +0.032290]|
|nearby|1.0|+0.006285 [-0.024990, +0.035534]|-0.013387 [-0.059055, +0.025706]|

Every joint-vs-random and joint-vs-weakest interval spans zero. Joint-vs-weakest means are negative in all four contexts. These small development results do not prove equality or impossibility, but do not establish a reliable improvement. The Gaussian working prior and fixed-power lookahead used to select the probe may be mismatched to the final continuous optimizer; no post-hoc tuning was used to conceal this limitation.

Uniform_probe remains an auxiliary idealized reference: its separately observable per-UE statistics have not been implemented with the same physical pilot multiplexing resources. Its scalar energy count alone does not prove a physically equal-budget baseline. The primary causal comparisons above probe only one UE and share the same observation contract. No_probe has lower information cost and is reported only as a cost reference.

## What the certificate actually did

Certificate early stopping activated0/32 times. Joint_cert and joint produced identical achieved rates for every network. Both evaluated all six schedules. Therefore runtime differences, including a negative paired timing interval in one context, cannot be interpreted as certificate-induced speedup; there was no skipped optimization work. Scheduling order was fixed and process/OS variation remains. The upper bound is valid for nominal continuous power, but too loose for the1% threshold in these cases. It is not a CSI-error guarantee.

The finite-grid LP and the continuous interference-free bound are distinct. No continuous solution is certified by the finite-grid LP. Feasible checkpoint preservation fixes runtime reliability, not mathematical complexity or novelty.

## Decision

Do not claim a positive paper result from this route. Keep the code/results and consult Astra on a bounded alternative: measure perfect-information headroom before designing another acquisition policy. The next gate should distinguish no physical room for improvement from a weak policy or loose certificate. New selector tuning, estimator training, or favorable-scenario selection is not justified by the current evidence.

Checks passed: WMMSE monotonicity/feasibility, orthogonal water-filling limit, direct MMSE rate, SLSQP feasibility, forced timeout with retained checkpoint, malformed output/nonzero exit, transient and permanent storage failures, post-run hashes, budget/power accounting and certificate orientation. These are author checks; independent scientific stage acceptance is still pending. The primary-source adaptation and exact comparator limits are documented in METHOD.md.
