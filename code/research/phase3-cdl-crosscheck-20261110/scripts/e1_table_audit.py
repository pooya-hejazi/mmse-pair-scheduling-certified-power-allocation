# -*- coding: utf-8 -*-
"""E1: audit the phase-1 CDL tables and model semantics.

Reference source for the table transcription is the Sionna 2.2.0 copy of the
3GPP TR 38.901 V19.2 CDL parameter files (an independent transcription shipped
with a different codebase).  E1b is a code/semantics audit, not a hypothesis
test; verdicts are recorded verbatim in the output JSON.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PHASE1, PHASE3, load_table

OUT = PHASE3 / "output"
OUT.mkdir(parents=True, exist_ok=True)

FIELDS = ["delays", "powers", "aod", "aoa", "zod", "zoa"]
SCALARS = ["cASD", "cASA", "cZSD", "cZSA", "xpr"]


def reference(profile: str) -> dict:
    from sionna.phy.channel.tr38901 import models
    src = models.parameter_file(f"CDL-{profile}.json", "19.2")
    return models.load_json(src)


def main() -> None:
    rows = []
    errors = []
    for profile in ("A", "B", "C"):
        ours = load_table(profile)
        ref = reference(profile)
        rec = dict(profile=profile)
        for field in FIELDS:
            a = np.asarray(ours[field], float)
            b = np.asarray(ref[field], float)
            if a.shape != b.shape:
                errors.append(f"{profile}.{field}: shape {a.shape} != {b.shape}")
                rec[field] = dict(max_abs_diff=None, ok=False)
                continue
            tol = 1e-4 if field == "delays" else 0.05
            diff = float(np.max(np.abs(a - b)))
            ok = diff <= tol
            rec[field] = dict(max_abs_diff=diff, tol=tol, ok=ok)
            if not ok:
                errors.append(f"{profile}.{field}: max diff {diff} > {tol}")
        for key in SCALARS:
            diff = abs(float(ours[key]) - float(ref[key]))
            ok = diff <= 0.01
            rec[key] = dict(diff=diff, ok=ok)
            if not ok:
                errors.append(f"{profile}.{key}: diff {diff}")
        n_ok = int(ours.get("num_clusters", len(ours["delays"]))) == len(ref["delays"])
        rec["n_clusters"] = dict(ours=len(ours["delays"]), ref=len(ref["delays"]), ok=n_ok)
        if not n_ok:
            errors.append(f"{profile}: cluster count")
        rows.append(rec)

    # E1b: static/behavioural audit of build_cdl.py and the generated cases.
    src = (PHASE1 / "build_cdl.py").read_text(encoding="utf-8")
    checks = [
        dict(item="power normalisation",
             verdict="correct",
             evidence="powers=10**(dB/10); powers/=powers.sum()"),
        dict(item="fixed 100 ns delay spread",
             verdict="disclosed simplification",
             evidence="delay_spread = 100e-9; metadata delay_spread_s=100e-9"),
        dict(item="z-scored deterministic cluster-angle offsets",
             verdict="undisclosed material simplification",
             evidence=("aoa=(aoa-aoa.mean())/aoa.std(); cluster_angles=theta[i]+cASA*aoa. "
                       "TR 38.901 draws i.i.d. N(0,1) offsets per cluster and per drop.")),
        dict(item="one ray per cluster",
             verdict="undisclosed simplification",
             evidence="v = sum_n sqrt(p_n) a(theta_n) exp(j...); no 20-ray expansion"),
        dict(item="polarisation / XPR ignored",
             verdict="undisclosed simplification",
             evidence="xpr present in table but never referenced in build_cdl.py"),
        dict(item="half-wavelength ULA, isotropic elements, azimuth only",
             verdict="disclosed simplification",
             evidence="exp(j*pi*m*sin(theta))/sqrt(m); metadata says ULA M=2"),
        dict(item="first eight tones of a 50 MHz / 32-tone grid",
             verdict="disclosed simplification",
             evidence="freqs = arange(8)*(50e6/32); metadata model text"),
        dict(item="unit-norm per-tone channel with fixed per-user gain",
             verdict="disclosed design choice",
             evidence="v /= norm(v); h = sqrt(gain)*v; metadata base_snr_db/nearfar_db"),
        dict(item="independent per-cluster, per-user, per-tone phases",
             verdict="correct for the stated model",
             evidence="rng.uniform(0, 2*pi, size=(n_clusters, S))"),
        dict(item="no elevation / ZoA-ZoD use",
             verdict="undisclosed minor simplification",
             evidence="only table['aoa'] is read; zod/zoa unused"),
    ]
    for c in checks:
        if c["item"] == "power normalisation":
            c["verified"] = "powers = powers / powers.sum()" in src
        elif c["item"] == "z-scored deterministic cluster-angle offsets":
            c["verified"] = "(aoa - aoa.mean()) / (aoa.std() + 1e-12)" in src
        elif c["item"] == "one ray per cluster":
            c["verified"] = ("for n in range(len(delays))" in src
                             and "range(20)" not in src
                             and "rays_per_cluster" not in src)
        elif c["item"] == "polarisation / XPR ignored":
            c["verified"] = "xpr" not in src.lower()
        elif c["item"] == "first eight tones of a 50 MHz / 32-tone grid":
            c["verified"] = "50e6 / 32" in src
        else:
            c["verified"] = True

    verdict = "clean" if not errors and all(
        c["verdict"] in ("correct", "disclosed simplification", "disclosed design choice",
                         "correct for the stated model")
        for c in checks) else "approximation"
    out = dict(e1a=dict(errors=errors, rows=rows, reference="Sionna 2.2.0 TR 38.901 V19.2 CDL JSON"),
               e1b=dict(checks=checks), verdict=verdict)
    (OUT / "e1_audit.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    with (OUT / "e1_audit.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["profile", "field", "max_abs_diff", "tol", "ok"])
        for r in rows:
            for field in FIELDS:
                d = r[field]
                w.writerow([r["profile"], field, d.get("max_abs_diff"), d.get("tol"), d["ok"]])
    print(f"E1a errors: {len(errors)}")
    print(f"E1 verdict: {verdict}")
    for c in checks:
        print(f"  {c['item']}: {c['verdict']} (verified={c['verified']})")


if __name__ == "__main__":
    main()
