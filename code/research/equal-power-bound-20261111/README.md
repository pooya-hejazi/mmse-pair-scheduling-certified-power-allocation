# How much does adapting power improve the best equal-power assignment?

These 180 cases are the original November 11 price-guided study, with 20 channel blocks, three CDL profiles and three SNRs. Each case has 16 users, eight resources, a budget of 2.08 W and equal power of 0.13 W per user. The reported quantity is the continuous joint optimum minus the best full-service assignment with every user at equal power. Rates are averaged over the occupied band.

| SNR (dB) | Cases | Mean feasible gain lower bound | Mean analytic upper bound | Mean of the tighter analytic or grid upper bounds | Analytic upper bound ≤ 0.01 | Tighter upper bound ≤ 0.01 |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 60 | 0.25436224 | 1.01482147 | 0.25510638 | 0 | 0 |
| 10 | 60 | 0.01648678 | 0.16115512 | 0.01758206 | 4 | 38 |
| 20 | 60 | 0.00006944 | 0.00013213 | 0.00013213 | 60 | 60 |

Entries are directed outward in bit/s/Hz. At 20 dB the analytic upper bound is tighter than the earlier grid certificate on all 60 channels and its largest value is 0.000471531874 bit/s/Hz. The grid certificate is tighter on all 120 remaining channels. At 0 dB even the smallest achieved gain exceeds 0.08874 bit/s/Hz. At 10 dB 21 cases have achieved gains above 0.01, and one case still straddles that threshold after using both certificates. The largest analytic upper bound is 1.410028768401 bit/s/Hz on native-b01-C-snr00.

## Checking the scalar bound

Let `b=min(P/K,pmax)`, so every feasible allocation has total power at most `K b`. The zero-budget or zero-upper-rail case has rate zero. At positive `b`, write `z=p/b`, `G=g b`, `H=h b`, and `C=G[1+(1−r)H]/(1+H)`. Each one-sided correction maximizes

    ln{[(1+C z)/(1+C)]² (1+G)/(1+G z)} + 1−z

over `pmin/b ≤ z ≤ 1`. For `G=0` the left endpoint attains the maximum. Otherwise the derivative has the sign of the quadratic

    −CG z² + (CG−C−G)z + (2C−G−1).

The checker evaluates both endpoints and encloses the larger root if it intersects the interval. A repeated root cannot produce a strict interior maximum. With vertex `m=(CG−C−G)/(2CG)`, the larger root is `m+sqrt(R)`, where `R=m²+(2C−G−1)/(CG)`. Integer square root encloses `sqrt(R)` between consecutive multiples of `2⁻⁶⁴`. The implementation evaluates the increasing numerator of the log ratio at the right end, the denominator at the left end, and the price correction at the left end. The other user's correction exchanges the gains.

The fixed-power log rate and both coordinate corrections are evaluated on the exact rational gains and correlation reconstructed from the stored binary64 channel coefficients. The pinned integer logarithm encloses each log. The checker rounds each edge weight upward at scale `2⁴⁴` and runs the existing integer subset assignment recurrence twice, once for equal power and once with both corrections. The resulting scalars are global upper bounds on the corresponding continuous-rate objectives.

The archived DP–SQP history supplies an equal-power assignment. A separate checker verifies its user incidence, resource incidence, power rails, total power and rate interval. On all 180 cases, the largest difference between the upper bound on optimal equal-power rate and this checked schedule's lower endpoint is below `3.59 × 10⁻¹³` aggregate nats. Saved DP–SQP and price-guided allocations supply feasible lower endpoints for the joint optimum. The earlier grid certificates supply independent joint upper bounds. The checker matches each input and allocation to its archived hash.

## Replay

From the repository root, the commands below use only the Python standard library. The full calculation runs offline. The pilot is one earlier November 10 CDL-A channel at 10 dB and does not enter the table.

    python -I -B code/research/equal-power-bound-20261111/tests.py
    python -I -B code/research/equal-power-bound-20261111/validate.py pilot
    python -I -B code/research/equal-power-bound-20261111/validate.py check --workers 4

Use `run` in place of `check` to write the CSV and JSON from the original inputs. The adjacent `../cdl-headroom-20261111/diagnose.py` rechecks the earlier grid witnesses and their endpoints.

The per-case CSV gives exact rational aggregate rates, case hashes, and the selected equal-power pair on each resource in increasing resource order. Let `L_eq` be the feasible equal-power lower endpoint, `U_eq` its assignment upper bound, `L_joint` the larger checked feasible lower endpoint, and `U` the analytic, grid, or smaller of the two global upper bounds. The benefit interval in bit/s/Hz runs from `max(0,L_joint−U_eq)/(S × upper(ln 2))` to `(U−L_eq)/(S × lower(ln 2))`. The optional DP–SQP columns use its own feasible lower endpoint in the upper-gap calculation. Counts and statistics use the exact fractions before the CSV's directed twelve-decimal rounding.
