# Computational repeat of the published 720 timed searches

Freeze this plan before starting any search in the repeat. The original 180-case study is the confirmatory experiment. This repeat uses the same channels and streams to measure computational sensitivity of the four timed implementations on the recorded host. It provides no additional independent channel replicates. The earlier one-case installation smoke check is excluded from this repeat.

## Inputs, implementation and execution

Use a fresh checkout of the published engineering-fix commit, recording its exact Git SHA before launch. Verify the complete frozen scientific source manifest and all 180 original case hashes. Copy the required scientific inputs to a new working directory with no prior runs, audits or analysis products. Preserve the original release as the reference. Retain the same 20 blocks, three profiles, three paired SNRs, case enumeration, eight offered start IDs, initialization/search seeds, cyclic arm order and source files.

Use the clean CPython 3.13.5 verification environment and its 18 SHA-256-verified official PyPI wheels. Record the wheel lock, software versions, active numerical-library paths and thread pools. Reuse the frozen run_study.py runner, including its synthetic JIT and historical-pilot warmup, serial calls, single-thread limits, 10-second total and 5-second continuous-block allowances. Run Price-DP-SQP, DP-SQP, DP-Fu-SCA and DP-Thu-IDE once per case. Preserve every completed search, deadline, stall, loss, tie, retained schedule, accepted history, start record and process receipt. A genuine interruption is reported; preserving a completed prefix and resuming only the unexecuted suffix is allowed if necessary and disclosed. No reroll or performance-based omission is permitted. Known concurrent computation should finish before launch.

## Preregistered comparisons

The frozen analysis uses occupied-band spectral efficiency R/(8 ln 2) in bit/s/Hz. Recompute the original endpoints independently on the new allocations using the same 20,000 whole-block bootstrap resamples and seed. Compare both estimates, interval ends and decisions between the original run and this repeat.

- The primary endpoint is the mean of Price-DP-SQP minus the best achieved control for each case, with equal weighting within each of the 20 blocks. Practical superiority requires the lower two-sided 95% percentile endpoint to exceed 0.01 bit/s/Hz.
- The secondary efficiency decision requires the lower 97.5% rate endpoint to exceed -0.001 bit/s/Hz and the upper 97.5% endpoint for mean log search time relative to the fastest control to be below log(0.5). Report the two component decisions and exponentiated geometric time-ratio interval.
- For each arm, record all 180 paired fresh-minus-original spectral efficiencies, the signed mean, median absolute difference, maximum absolute difference, count exceeding absolute 0.00001 bit/s/Hz, and fresh wins/ties/losses using that absolute tolerance. Compare original and repeat Price-versus-control and Price-versus-best W/T/L summaries. Report original/repeat mean and median search seconds and per-case elapsed differences for each arm.
- Preserve all 720 rows, including case, arm, case hash, start binding, seed, cyclic order, original and new SE and elapsed seconds, arm result status, process identifier, complete run digest, and separate allocation and history digests. These 720 pairs belong to the same cases in both environments.

## Evidence gates and distribution

Check every fresh case binding and offered-start hash against the published run, verify all 720 new process bindings, and require the original independent verify_study.py audit of feasibility, incidence, paired channels, rate enclosures, accepted histories and relevant timing guards. Archive the 720 new complete arm records, 180 starts, manifest, process data, independent audit/receipts/intervals, analysis and baseline-versus-repeat results. Bind each member by SHA-256. The archive reader must re-run the frozen independent checker and analysis on the new records, then reproduce the before/after comparisons against the published records, without requiring a further timed search. Distribute the exact source Git SHA, environment and protocol digest. Summarize the outcomes even if a previous practical decision changes.
