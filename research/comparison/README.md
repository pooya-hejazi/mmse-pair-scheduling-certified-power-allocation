# Continuous power and equal-information-budget comparison

Start with [REPORT.md](REPORT.md), [METHOD.md](METHOD.md), and the pre-run [PROTOCOL.md](PROTOCOL.md). This is a development comparison with negative main performance findings, not a reproduction of every assumption in the I-WMMSE paper. The adaptation and scheduling-family differences are explicit.

Run environment: existing Python3.10.19 / NumPy2.1.3 / SciPy1.15.3 on Windows, CPU solver arms. The parent enforces bounded worker lifetimes and preserves feasible checkpoints. It allows process teardown/storage overhead; observed wall times and states are retained. The original source and incomplete GPU study were not overwritten. No new GPU speedup is asserted.

For local reproduction in a fresh copy, with the prior DeepMIMO channel and train-only normalization artifacts available:

```powershell
python research/comparison/checks.py
python research/comparison/check_storage.py
python research/comparison/prepare.py
python research/comparison/run.py
python research/comparison/analyze.py
python research/comparison/report.py
```

Do not rerun against the archived runs folder: the supervisor intentionally refuses to overwrite existing jobs. `resume.py` is a one-off repair of the documented original Windows sharing violation, not a general fresh-run command. Historical source hashes differ only for the documented storage repair; pre-repair code is in history/. Paths in the original manifests are evidence of that local run and are not a portable dataset distribution. Raw input arrays are deliberately excluded from GitHub; generator, IDs and hashes are included. Re-created archives can differ in ZIP metadata even when numerical arrays agree.

Results:215 jobs,213 completed,2 timed out at64users. Selective-information primary comparisons use all six schedules and common continuous power constraints. `uniform_probe` is an idealized auxiliary observation reference, not a demonstrated physical pilot-multiplexing baseline. Grid MILP at larger sizes can reschedule while continuous arms there use a fixed schedule, so their objective difference cannot establish power-control superiority. See [headroom](../headroom/README.md) for the bounded route-selection decision.
