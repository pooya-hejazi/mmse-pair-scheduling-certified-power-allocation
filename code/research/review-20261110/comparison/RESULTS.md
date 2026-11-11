# New common-model comparison results

All 24 predeclared CDL-inspired cases completed, with three arms (72 allocations). These compare local/power-search components under a shared exact fixed-power DP assignment wrapper. They do not reproduce the source papers end to end. The current method is DP + local SQP, not a globally exact continuous optimizer.

Occupied-band SE is R/(8 ln 2); aggregate_bits in raw.csv preserves R/ln 2. A first pilot used aggregate reporting; pilot_normalized repeats the normalized checks. No search parameter was selected from those rankings.

| Arm | Mean SE (bit/s/Hz) | Mean search time (s) | Deadline cases | Completed starts |
|---|---:|---:|---:|---:|
| DP-SQP | 10.00296767 | 6.376 | 0/24 | 192/192 |
| DP-Fu-SCA | 10.00296767 | 7.801 | 0/24 | 192/192 |
| DP-Thu-IDE | 9.99566843 | 10.003 | 24/24 | 40/192 |

Paired outcomes for the current method; ties use absolute SE tolerance 1e-5 bit/s/Hz.

| Comparator | Wins / ties / losses | Mean paired relative difference | Relative range |
|---|---:|---:|---:|
| DP-Fu-SCA | 0 / 24 / 0 | +0.000000% | +0.000000% to +0.000000% |
| DP-Thu-IDE | 24 / 0 / 0 | +0.075362% | +0.022572% to +0.131003% |

Power-block termination diagnostics (feasibility is checked even when the optimizer does not declare success):
- DP-SQP: {'Positive directional derivative for linesearch': 76, 'Optimization terminated successfully': 361}; complete IDE generations=0; caught adapter exceptions/validation failures=0.
- DP-Fu-SCA: {'numerical_stall': 437}; complete IDE generations=0; caught adapter exceptions/validation failures=0.
- DP-Thu-IDE: {'deadline': 120}; complete IDE generations=379; caught adapter exceptions/validation failures=0.

Fu subproblem diagnostics: 267 success statuses and 170 status-8 line-search terminations; stationarity residuals 5.63e-5 to 3.12e-4 exceed the 1e-7 threshold. The DP searches the assignment family exhaustively using floating-point weights; it does not certify an outward-rounded fixed-power optimum.

All final exact-rational schedules passed user-incidence, resource, box and budget checks. Maximum matrix/scalar discrepancy: 3.55e-14 nats; maximum observed deadline overrun: 0.005789 s. Retained search improvements were checked to precede the global deadline.

Interpretation limits: two fixed seeds per profile, four separations, M=2 and K=16 only. Means are descriptive; there is no confidence or full-population superiority claim. A 2 s local block can truncate IDE initialization/generations, and the 10 s result is not a converged-algorithm comparison. Fu and Thu retain their documented component modifications; original satellite/cell-free/energy-efficiency objectives are not transferred. No upper-bound gap or global exactness is inferred.

Figures: comparison_se.pdf/png (mean over six paired cases per separation); comparison_by_profile.pdf/png (two seeds per profile); comparison_difference_runtime.pdf/png (signed paired differences and actual times). Raw allocations and per-power-call status diagnostics are in campaign/*.json; every aggregate can be reconstructed from campaign/raw.csv and summary.csv.

Wrapper repairs: box/budget-feasible random starts; guarded DP deadlines; reject K>20 before exponential allocation; retain only pre-deadline improvements; count completed rather than offered starts. The 2 s block cap is shared by all arms and differs from the historical 5 s proposed cap. Original source modules and frozen historical data were not edited.

Not checked: source-paper full-system reproduction, convergence at larger time budgets, additional seeds, K32, M>2, and physical calibration/standards conformance of the archived CDL-inspired generator.
