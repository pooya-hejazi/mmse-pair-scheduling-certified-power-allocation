# Scientific code and saved allocations

Run `python reproduce.py` from the repository root. The top-level command works in a temporary copy, reconstructs rates, checks the frozen summaries, and regenerates figures. Commands for individual studies and the numerical results appear in the [repository guide](../README.md).

The two primary native-CDL experiments are under [independent-cdl-20261110](research/independent-cdl-20261110/) and [priced-assignment-20261111](research/priced-assignment-20261111/). Each has its own `cases/`, `native/`, `runs/`, scientific source manifest and analysis. Preserve the relative directory layout and file bytes when moving these records. The November 11 candidate searches pair-specific transmit powers before selecting a labelled assignment at each budget price. The three controls use the same accelerated fixed-power subset DP. The two phase-1 benchmarks and phase-3 cross-check are earlier experiments.

The eight-antenna [certificate checker](m8_replay/README.md) verifies the saved bounds and feasible schedules against their original scientific member hashes. The [historical replay](historical/README.md) documents the scope of the earlier supplementary results. Native-CDL rate, timing and per-instance certificate results have separate scientific meanings and units.
