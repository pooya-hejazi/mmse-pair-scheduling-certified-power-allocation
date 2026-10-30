# Selective information acquisition + integer resource allocation

Exploratory research, not an accepted paper or a claim to solve general NP-hard ILPs with LPs. The original repository files are preserved. Start with REPORT.md, OPTIMIZATION.md, and LITERATURE.md. The channel estimator is fixed LMMSE; the research variable is the coupled information/allocation policy and the exactness or gap of its optimization models.

## Reproduce model checks without channel data

Python 3.9, NumPy 1.26.4 and SciPy 1.13.1 were used. No TensorFlow is needed for this experiment.

```powershell
python research/selective/check_portable.py
```

This checks the stored physical witness, enumeration, MILP and the strengthened LP on 101 objectives. It does not reproduce the full wireless experiments or certify novelty.

## Reproduce the experiments in a fresh checkout

The full O1_60 ray-tracing source is external: put it under `DeepMIMO_sena/O1_60`. All AP1–AP4 files and shared metadata are required. Do not treat the older repository's partial AP data as the complete source. DeepMIMOv3 0.2.9 is the generator used; the installed package versions here are observed versions, not a cross-platform lock guarantee.

```powershell
python research/reproduction/prepare_data.py
python research/selective/prepare_inputs.py
python research/selective/experiment.py headroom
python research/selective/experiment.py prototype
```

The generator uses rows1–100, 4AP×8ant, 32OFDM carriers with selected indices0,16 and 10paths. The input specification restores the original train/development/test split and train-only RMS without neural training. Generation writes files in `research/reproduction`; experiments write new JSON/logs in `research/selective`. Preserve an earlier run in a different checkout before rerunning. The original author code is not invoked.

`summary.json` contains all 18 context summaries and the maximum-gap witnesses for both runs; `input-spec.json` fixes split indices and normalization. `RUN_MANIFEST.json` records hashes for the full local raw outputs, source and input artifacts. Raw result JSON and channel binaries are retained locally and are not included in this lightweight repository snapshot. `verify_optimization.py` is the full local verification and additionally needs those local outputs and the S02 manifest; `check_portable.py` is the self-contained published model check.

Headroom and prototype each use720 network paths, with40 per context. The prototype uses fresh seed92000, six policies and eight posterior worlds per decision. Both are development studies on the same fixed map, not a held-out scenario study. All policies use five pilot symbols and total normalized pilot energy17. Their computation costs differ; measured scoring time is reported and an end-to-end gain is not claimed.

The stage remains S03 in progress. Its independent checkpoint has not been passed. Do not change the existing reserved confirmatory test into a test of this method without a new preregistered protocol. No new estimator training or repeated tuning run is planned from these results.
