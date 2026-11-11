# Computational repeat of the 720 timed searches

The same 180 native-channel cases were run once in a clean Windows CPython 3.13.5 venv with 18 pinned official PyPI wheels. The original search ran in its Conda environment on the same host. Every new allocation comes from the frozen GitHub search code, with identical case hashes, cyclic arm order, eight starting allocations per case, random substreams and 10-second total and 5-second local budgets. The numerical pools used one thread. The two executions share all 20 independent channel blocks.

| Endpoint | Original mean [interval] | Repeat mean [interval] |
|---|---:|---:|
| Price minus casewise best control, bit/s/Hz (95%) | 0.0023748 [0.0011713, 0.0038442] | 0.0022377 [0.0010301, 0.0037177] |
| Same rate contrast (97.5%) | 0.0023748 [0.0010402, 0.0040654] | 0.0022377 [0.0009025, 0.0039475] |
| Log time ratio to fastest control (97.5%) | 0.4792160 [0.4676580, 0.4909749] | 0.4812066 [0.4652881, 0.4977111] |
| Geometric time ratio to fastest control (97.5%) | 1.6148079 [1.5962514, 1.6339084] | 1.6180255 [1.5924729, 1.6449518] |

Intervals use 20,000 paired whole-block percentile bootstrap draws with seed 1721630546. The primary practical threshold is a lower 95% endpoint above 0.01 bit/s/Hz. Efficiency requires a lower 97.5% rate endpoint above −0.001 bit/s/Hz and an upper geometric time-ratio endpoint below 0.5.

| Predeclared decision | Original | Repeat |
|---|---:|---:|
| Practical rate superiority | False | False |
| Efficiency rate condition | True | True |
| Efficiency time condition | False | False |
| Joint efficiency | False | False |

## Paired variation across executions

Differences are repeat minus original, with each arm evaluated on 180 cases. Wins and losses require a difference outside ±0.00001 bit/s/Hz.

| Arm | Signed mean, bit/s/Hz | Median abs. | Max abs. | Beyond band | Repeat W/T/L |
|---|---:|---:|---:|---:|---:|
| Price-DP-SQP | 1.589099e-14 | 2.797762e-14 | 2.345679e-11 | 0 | 0/180/0 |
| DP-SQP | 9.008596e-14 | 2.708944e-14 | 2.345679e-11 | 0 | 0/180/0 |
| DP-Fu-SCA | 5.51558e-07 | 2.790657e-12 | 9.927879e-05 | 1 | 1/179/0 |
| DP-Thu-IDE | 0.001006025 | 5.988343e-06 | 0.08756681 | 89 | 47/91/42 |

| Arm | Original mean / median seconds | Repeat mean / median seconds |
|---|---:|---:|
| Price-DP-SQP | 0.6322 / 0.6194 | 0.6537 / 0.6386 |
| DP-SQP | 0.3919 / 0.3859 | 0.4043 / 0.4046 |
| DP-Fu-SCA | 3.6855 / 2.1991 | 3.7364 / 2.2311 |
| DP-Thu-IDE | 10.0029 / 10.0029 | 10.0035 / 10.0030 |

| Price comparison within each execution | Original W/T/L | Repeat W/T/L |
|---|---:|---:|
| casewise_best | 23/157/0 | 23/157/0 |
| DP-SQP | 23/157/0 | 23/157/0 |
| DP-Fu-SCA | 23/157/0 | 23/157/0 |
| DP-Thu-IDE | 176/4/0 | 176/4/0 |

## Allocation checks

The independent checker accepted all 720 final allocations, 10221 retained history allocations and 1440 offered starts. It evaluated 8877 distinct schedules within their respective cases. Maximum scalar and complex-matrix sum-rate discrepancies were 1.42e-14 and 4.69e-13 nats. Every original and repeat result has a separate complete-record digest, schedule digest and history digest in the paired table.

A further timed execution can differ because the available work before a wall-clock deadline depends on numerical libraries and host timing. These paired differences describe the combined change of execution and installation on the same input population. The original confirmatory estimates remain the reference.
