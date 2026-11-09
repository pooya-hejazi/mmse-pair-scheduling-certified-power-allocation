# Finite-box integral-schedule certification study

The prospective protocol is `PROTOCOL.md`; `FROZEN.json` binds its source,
input manifest, successful test record, and the independent mathematical
audit. `PROOF_NOTE.md` gives the self-contained mathematics and arithmetic
qualifications. The parent `BOUND_STUDY_REPORT.md` gives measured conclusions.

## Reproduce/check

From this directory in the original project layout, with Python 3.12:

```powershell
python -B replay.py
python -B analyze.py
```

Replay needs only the standard library, this code, and the immutable
`output/TCOM-Submission-2026-11-06-R4/Supplementary_Materials.zip`. It opens
the nested baseline archive and compares archive, source, and output
hashes before rebuilding every new and matched-baseline bound. All lower
and upper endpoints in the JSON witnesses are exact fractions; decimal
CSV values are display/analysis values, not outward-rounded certificates.
For a relocated copy, the archive must remain at the same project-relative
path, or a caller can use `checker.ArchivedInputs(explicit_archive_path)`
and `checker.verify` directly.

Development tests additionally need SymPy; production additionally needs
NumPy/SciPy. `python -B tests.py` writes the development test record, so run
it on a separate copy if retaining the exact frozen evidence. The original
sequence was `tests.py`, `campaign.py freeze`, `campaign.py run`, `replay.py`,
then descriptive analysis. `campaign.py run` refuses to overwrite `final/`.
No optimizer is invoked by replay or analysis.

## Evidence layout

- `inputs/corrected/`: byte-identical all32 cases, archived grid result/dual
  proposals, and historical comparison records; all bound by the manifest.
- `final/<case>/new-witness.json`: rational price and tangent points,
  complete split trees, integer weights, DP maximum/schedule, feasible lower.
- `final/<case>/new-checked.json`: independent reconstructed endpoints and
  curvature/DP diagnostics. Baseline analogues contain the frozen method's
  full witnesses and independent checks. `row.json` contains errors/caps.
- `final/<case>/historical-checks.json`: independently checked old schedules,
  their original status/errors/timeouts, and their distinct timing scopes.
- `final/summary.json`, `final/results.csv`, `final/rows.json`: all-case
  primary results. `final/OUTPUT_MANIFEST.json` protects saved outputs.
- `replay-result.json`: separate all-case replay and error ledger.
- `analysis/descriptive.json`, `analysis/*.csv`: diagnostic distributions,
  achieved rates, attainable headroom, and historical comparisons.
- `development/`: pre-campaign smoke/tests. The weaker initial single-price
  variant is retained in `development-v1-single-price/`; the nonclosing K16
  synthetic result is not discarded. These are not population evidence.

## Scope of the measured improvement

The mechanism uses finite-box Hessian certificates, numeric tangent/price
proposals, generic complete partitions, and exact integral subset DP. It
does **not** integrate the finite-candidate algebraic oracle. It supplies an
upper on the integral continuous-power problem, not necessarily on the
fractional configuration LP. Its price relaxation can retain a duality gap.

The timed comparison has a common archived grid anchor and a common
10-second producer allowance, with separate 15-second checking. Historical
Full and modern-refiner records have different charged scopes. Reported
producer-plus-checker time is time to the **final independently checked
receipt**, not an instrumented earliest-certificate publication time.
Sum-rate gains and certification-gap gains must be quoted separately.
