# How much rate gain remained after DP–SQP?

On the original 180 native-CDL cases, a global optimizer could have gained at most **0.003545 bit/s/Hz on average** over the saved DP–SQP allocation. Price–DP–SQP achieved a mean gain of **0.002375 bit/s/Hz**. The original allocation audit ranked DP–SQP above both other controls on every case. The target was a mean gain of 0.01 bit/s/Hz. [Original study and design](../priced-assignment-20261111/PROTOCOL.md)

| Nominal SNR | Cases | Mean gain achieved by pricing | Upper bound on mean possible gain over DP–SQP | Upper bound on mean remaining gain over pricing | 0.01 gain impossible | Pricing exceeded 0.01 |
|---|---:|---:|---:|---:|---:|---:|
| 0 dB | 60 | 0.004948 | 0.005692 | 0.000745 | 48 | 12 |
| 10 dB | 60 | 0.002177 | 0.003273 | 0.001096 | 57 | 3 |
| 20 dB | 60 | 0 | 0.001670 | 0.001670 | 60 | 0 |
| **All** | **180** | **0.002375** | **0.003545** | **0.001170** | **165** | **15** |

Rates are in bit/s/Hz across the occupied band. Upper bounds are rounded upward to six decimal places. The largest remaining gap bound for pricing was **0.002734 bit/s/Hz** on block 17, CDL-A, 20 dB. The largest gap bound for DP–SQP was **0.060247 bit/s/Hz** on block 0, CDL-B, 10 dB. The exact rational summaries include the 15 case IDs where the saved priced allocation demonstrably exceeded the target. [Exact group bounds and case IDs](paired_bounds.json) · [Per-case rate intervals and hashes](cases.csv)

The experiment used 20 independent channel blocks, each evaluated for three CDL profiles at three nominal SNRs. The 20 CDL-B cases at 10 dB were the prespecified certificate subset. The other 160 witnesses extend that analysis retrospectively. All comparisons refer to the original ten-second searches. Witness construction and replay were offline. [Original 20 witnesses](../priced-assignment-20261111/native_certificate/witnesses) · [Additional 160 witnesses](additional-witnesses) · [Scientific input revision](https://github.com/pooya-hejazi/mmse-pair-scheduling-certified-power-allocation/commit/3b9b35d305a7f779122df32d289bc13e591f93ce)

## Replay

From the repository root, install the scientific dependencies and run the checker.

```sh
python -m pip install -r code/requirements.txt
python -B code/research/cdl-headroom-20261111/diagnose.py --output reproduced/headroom
```

The default replay reads all 180 stored witnesses, binds them to the exact case and saved run, checks every grid row on all 960 pair–resource edges per case, recomputes the integer assignment maximum, and evaluates both feasible schedules. It compares every row with the archived table and regenerates the paired bounds and threshold counts. The output directory receives `paired_bounds.json`. The command runs serially by default and accepts `--workers N` for parallel replay. [Certificate proof](../priced-assignment-20261111/native_certificate/PROOF.md) · [Frozen checker](../priced-assignment-20261111/native_certificate/certificate.py)

For a faster arithmetic check, add `--endpoints-only`. This uses the stored integer assignment values, verifies the case and run bindings, checks the saved feasible intervals against the original independent allocation audit, and repeats the paired comparisons. The default replay also verifies the grid and assignment computations underlying each global upper bound. [Original independent rate audit](../priced-assignment-20261111/audit_study.json)

For each case, let `U` be the global upper bound and `[Ld, Ud]` and `[Lp, Up]` the feasible aggregate-rate intervals for DP–SQP and pricing in nats. The possible gain over DP–SQP is bounded above by `(U − Ld)/(8 ln 2)`. A lower bound on the gain attained by pricing is `(Lp − Ud)/(8 ln 2)`. The checker uses rational bounds on ln 2 and rounds both comparisons outward. Equal assignments and powers give an exact zero difference. A case is marked impossible when its global gap ceiling is strictly below 1/100 and attained when its feasible gain floor is strictly above 1/100. All 180 cases meet one of those strict conditions. [Exact summaries from the original analysis](results.json)

## Channel and allocation diagnostics

At 20 dB, both methods chose identical assignments and powers on all 60 cases. DP–SQP powers differed from the equal-power allocation of 0.13 W by a mean of 0.000616 W per user, compared with 0.058318 W at 0 dB. The 10th and 90th percentiles of the normalized marginal rate reward at equal power were 0.986 and 0.999 at 20 dB, and 0.204 and 0.920 at 0 dB. Recompute these descriptive quantities with `python -B code/research/cdl-headroom-20261111/mechanism.py --output reproduced/headroom/mechanism.json`. [Archived channel diagnostics](mechanism.json)
