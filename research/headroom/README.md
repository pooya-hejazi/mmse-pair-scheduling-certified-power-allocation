# Offline information opportunity and route decision

The current selective-information family did not show reliable improvement over equal-budget continuous-power baselines. Two predeclared bounded diagnostics use the same32 development inputs without retraining or new data:

1. [Perfect-information opportunity](REPORT.md), protocol [PROTOCOL.md](PROTOCOL.md): an offline oracle can improve decisions AND receivers. It is not a deployable information policy or a promise that one pilot attains the oracle value.
2. [Frozen-estimate decision-only opportunity](FROZEN_REPORT.md), protocol [FROZEN_RECEIVER_PROTOCOL.md](FROZEN_RECEIVER_PROTOCOL.md): hold the initial estimate used by each candidate's receiver mapping fixed. Exact grid opportunity0.5317%, below the declared1% engineering gate;23/32 cases cannot repay the extra symbol even with oracle action selection. Stop tuning this unchanged grid family.

These are scoped finite-grid pointwise oracle bounds, not universal wireless or continuous-power impossibility statements. `ASTRA_*.md` are research consultations, not stage acceptance.

In a fresh reproduction copy after comparison inputs/results exist, run `run.py`, `analyze.py`, `frozen_run.py`, and `frozen_analyze.py` in that order with the same environment. Existing run folders and archived outputs must be preserved; do not overwrite the evidence. Raw channel arrays stay local. Source/input hashes, per-case objectives and execution states are included. The optimization-focused alternative is in [theory](../theory/PROOF_NOTE.md).
