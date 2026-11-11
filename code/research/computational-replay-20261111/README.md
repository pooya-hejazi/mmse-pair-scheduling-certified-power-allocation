# Replaying the computational timing sensitivity study

We repeated the 720 searches on the original 180 input cases in an isolated installation of the recorded official PyPI wheels. NumPy 2.3.4, SciPy 1.16.3 and Numba 0.62.1 agree across installations. The original used MKL and psutil 5.9.0. The repeat used OpenBLAS and psutil 6.1.1. Each arm used its original starts, seeds and deadline. The 20 channel blocks are the same in both executions. The estimates describe sensitivity to this execution and environment. See `RESULTS.md` for the paired outcomes and `SURVEY/PROTOCOL.md` for the plan committed before timing.

## Recheck the released data

From the repository root, with the numerical dependencies listed in the root README installed, run

```text
python -I -B code/research/computational-replay-20261111/replay.py --output path/to/empty-directory
```

The script verifies the archive and all member hashes, assembles a disposable copy of the frozen scientific code and inputs, and imports only the recorded starts, process evidence and search histories into it. The original independent checker recalculates feasibility, rational enclosures and scalar/matrix rates. The original analyzer regenerates the block bootstrap and decisions. The reader then compares all 720 records against the published search, writes both paired CSVs under `comparison/` and writes `report.json` with the estimates, decisions and arm-level differences. The independent audit and analysis logs are retained. The numerical comparisons allow absolute or relative roundoff of 1e-12 for floating-point replay. Identifiers, counts, hashes and rational final enclosures must match exactly. Search time in the analysis is the time recorded during the fresh search.

## Archived evidence

`data/rerun-priced-20261111.zip` contains the 720 fresh, complete arm records, their histories, 180 shared start files, the stage manifest, warmup and single-thread process evidence, the independent audit and individual certificates, and the numerical analysis tables. `comparison/allocation_pairs.csv` records per-arm measurements, statuses and separate schedule, history and result digests. `comparison/case_endpoints.csv` records the 180 paired rate and log-time endpoints. `members.json` binds every payload by byte count and SHA-256. `archive.json` binds the ZIP itself. The original input files and the published reference schedules live in the repository's preceding priced-assignment study.

The pre-run receipt `meta/prerun.json` records the source commit, baseline hashes, common seeds, exact wheel URLs and checksums, interpreter and numerical binary digests. `meta/environment.json` summarizes host and build information. The original frozen process receipts identify the numerical library files actually loaded. `meta/requirements-lock.txt` and `meta/wheel-provenance.json` describe the Windows CPython 3.13 wheelhouse. On a freshly created isolated Windows venv, these exact wheels can be installed with pip's `--no-index --find-links WHEELHOUSE --require-hashes -r WHEELHOUSE/requirements-lock.txt` options after downloading them to `WHEELHOUSE` using the recorded URLs and verifying their hashes.

## Run new searches

For a further timed sensitivity check, use a separate clean checkout of source commit `2a9b228cdba68abf6620725dc9850b30f3374d29`, the recorded Windows wheel environment, and an unused workspace. Copy the two wheel metadata files above into the directory containing the wheels. Stop other substantial compute jobs. Invoke the launcher distributed here with the isolated venv interpreter

```text
python -I -B code/research/computational-replay-20261111/repeat.py --checkout PATH_TO_SOURCE_COMMIT --commit 2a9b228cdba68abf6620725dc9850b30f3374d29 --work NEW_WORK_DIRECTORY --wheels WHEELHOUSE
```

This command validates the original checkout, stage and all input hashes before invoking its unmodified serial runner. Once all 720 arm records exist, run `verify_study.py` and then `analyze_study.py` from `NEW_WORK_DIRECTORY/code/research/priced-assignment-20261111` using the same venv. Additional timed runs may return different incumbents under a fixed wall-clock allowance. Keep each execution in its own workspace.
