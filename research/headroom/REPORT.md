# Perfect-information headroom audit

All32 frozen development networks completed in22.12s under individual10s external caps. No estimator, observation, scenario, seed or original source was changed. Astra's predeclared1% engineering gate is a diagnostic, not statistical significance.

| Quantity | Result |
|---|---:|
| Exact finite-grid positive-part oracle opportunity / no-probe rate |6.2240%|
| Same grid, ordinary LP upper opportunity |6.2710%|
| Continuous oracle feasible lower opportunity |6.1538%|
| Continuous oracle upper opportunity |18.0749%|
| Positive finite-grid LP gaps |2/32|
| Receiver-first share of raw grid oracle uplift |88.99%|

The perfect-information headroom exceeds the1% gate, so an absolute lack of room is not established. This ceiling grants perfect CSI and a perfect-channel MMSE receiver after paying just one symbol: it is deliberately unattainable by a real one-pilot method. It neither predicts an achievable6% gain nor validates the previously negative selector.

The pointwise proof is: any feasible one-extra-symbol policy has net gain<=.975U(H)−.98R0(H), where U is a valid upper bound on perfect-CSI optimum in the same power/schedule family. Optional probing has improvement<=max(0,that bound). These statements use true H only offline. They are elementary bounding results, not a new online uncertainty guarantee.

The89% receiver-first fraction depends on decomposition order. It does not upper-bound the benefit of changing actions while retaining the original channel estimate; action changes can avoid bad combining directions. Consequently it cannot justify declaring the optimization path exhausted. Astra recommends a final, separate finite-grid oracle that freezes the estimated-channel receiver **mapping** for every candidate action and changes only schedule/power choice. No more selector tuning is authorized by these results.

Enumeration, MILP and reconstructed LP dual bounds agree within tolerance. Direct receiver evaluation is checked against the true-MMSE formula, and continuous bounds dominate all tested feasible actions. The finite-grid LP is never used as an upper bound for continuous power. All contexts have equal sample counts and weight. Results are provisional development evidence; independent stage acceptance remains open.
