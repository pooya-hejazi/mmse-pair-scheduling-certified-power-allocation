# Power, throughput and GPU feasibility

Start with [the precise model](MODEL.md), [measured results](REPORT.md), [related work](RELATED_WORK.md), and the preregistered [protocol](MODEL_PROTOCOL.md)/[run configuration](RUN_CONFIG.json). This is an exploratory engineering study, not a completed SOTA comparison or proof that general ILP is polynomial.

Original project code is preserved. The study uses separate DeepMIMO data and existing environments. No estimator is trained. Native Windows CuPy runs on the RTX5060 Laptop GPU using a process-local DLL loader. CPU HiGHS solves the reference LP/MILP; the GPU PDHG experiment solves only a relaxation of throughput maximization.

Portable CPU check (NumPy/SciPy only):

```powershell
python research/gpu/check_portable.py
```

This checks closed-form MMSE rates against matrix solves and both objective directions against exhaustive scheduling/power enumeration on four synthetic users. It does not reproduce the real data.

Historical local experiment commands used the existing `6g_project` environment for `generate.py` and `check_units.py`, then `tf-gpu` for `benchmark.py`. Full O1_60 data and S02 splits are required and are not included in this branch. Real-data coefficient arrays, GPU caches and full PDF texts remain local. `pre-run-manifest.json` and `generation.json` record their lineage.

**Do not treat the historical benchmark launcher as a production solver.** The 64-user run was stopped without a completed result, and first-run GPU timing included unseparated compilation. See `interruption.json`. A supervised-process launcher and a fresh recorded timing packet are needed before another large run. No large rerun was performed to improve the reported results. S03G independent acceptance is pending.
