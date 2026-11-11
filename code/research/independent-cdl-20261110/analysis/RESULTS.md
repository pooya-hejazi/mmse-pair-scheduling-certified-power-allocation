# Independent native-CDL saved-data analysis

Complete main population: 180 cases in 20 independent root blocks; 900 allocations. Sensitivity: 20 CDL-B/10 dB cases and 60 allocations. No pilot or historical case is pooled.

Primary intervals are individual 97.5% whole-block percentile intervals (Bonferroni nominal 95% family for two absolute contrasts; approximate bootstrap coverage). All other intervals are pointwise 95%. Positive differences favour DP-SQP. Ties use an absolute 1e-5 bit/s/Hz band and do not establish equivalence.

| Comparator | Mean absolute difference (bit/s/Hz) | 97.5% interval | Case W/T/L |
|---|---:|---|---|
| DP-Fu-SCA | 0.00031903721 | [6.6101459e-05, 0.00066223701] | 6/174/0 |
| DP-Thu-IDE | 0.012243108 | [0.0083153123, 0.016826629] | 173/6/1 |

All 20 block effects, all cell values, secondary relative effects, ablations, runtime, completed work, numerical returns and 10/30-second sensitivity are retained in the machine-readable outputs. No convergence or deployment claim follows from a bounded run. DP-uniform is a deterministic ablation, not a time-matched iterative competitor.
