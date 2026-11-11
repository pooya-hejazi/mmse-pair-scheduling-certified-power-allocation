# Independent native-CDL scientific records

`PROTOCOL.md`, `source_manifest.json` and `seed_manifest.json` freeze the study design, implementation and streams. `cases/` contains 180 main cases and 3 excluded pilot cases; raw native CIRs, delays, frequency responses and link factors are in `native/`. `native/draft-before-lowbits/` preserves the superseded channel-only engineering pilot provenance, not additional inference cases.

`runs/main/` contains 900 final five-arm records, `runs/sensitivity/` contains 60 three-arm sensitivity records, and pilot folders contain excluded engineering runs. Offered starts, exact rational allocations, accepted-incumbent histories, diagnostics and timing are preserved. `audit_campaign.json` and `audit_receipts.json` record independent saved-data verification; `analysis/` contains the prespecified statistics and figures. Generator validation reports include all-960-link deterministic native replay and all-180-case scaling/hash checks. `PREFLIGHT.json` records the engineering gate.

Run saved-evidence verification and analysis using the root README_REPRODUCTION.md. Those operations need no Sionna runtime and are distinct from regenerating channels or rerunning deadline-limited solvers. Twenty base blocks are the inference units; 180 cases are not 180 independent blocks. No source-system superiority or global-rate certificate is implied.
