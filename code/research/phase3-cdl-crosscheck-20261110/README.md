# Phase 3 — independent CDL cross-check (Paper 2)

This folder contains the pre-registered, independent cross-check of the hand-rolled 3GPP TR 38.901 CDL generator used for the Paper-2 rate claim.

- **Protocol:** `CROSSCHECK_PROTOCOL.md` (frozen before any E2/E3 outcome).
- **Verdict:** **bucket (b)** — the advantage survives an independent Sionna 2.2.0 realisation (median **1.65%**, 95% CI **[1.57, 1.74]%**, **53/53** wins), but the hand-rolled generator is a simplified step-11 realisation and per-case ranking is not preserved (`ρ = 0.19`).
- **Primary result remains 1.31%** on the simplified generator; the Sionna number is an independent robustness check. No certified-rate claim is made at M=2.

Read `RESULTS.md` for the gates, diagnostics, E3-A ablation and reproduction commands. All frozen phase-1 inputs were read-only; their hashes are in `frozen_inputs/manifest.json`.
