# -*- coding: utf-8 -*-
"""E3-A: isolate the deterministic z-scored cluster-angle construction.

Same frozen seeds, gains and per-cluster phases as the paper generator; only
the per-user cluster angles are replaced by the TR 38.901 i.i.d. Gaussian
offset law with std cASA.  This is a sensitivity arm, never a substitute for E2.
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction as F
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (BUDGET, DELAY_SPREAD_S, K, M, PMAX, PMIN, PHASE3,
                    array_response, frozen_paths, load_frozen, load_table,
                    recover_gains, recover_theta)

OUTDIR = PHASE3 / "cases_e3a"
OUTDIR.mkdir(parents=True, exist_ok=True)


def gaussian_channel(profile: str, sep: float, seed: int) -> dict:
    table = load_table(profile)
    rng = np.random.default_rng(seed)
    arng = np.random.default_rng(seed * 10 + 3)
    k, s, m = K, 8, M
    delays = np.asarray(table["delays"], float)
    powers = 10 ** (np.asarray(table["powers"], float) / 10)
    powers = powers / powers.sum()
    c_asa = float(table["cASA"])
    n_cl = len(delays)

    centers = rng.uniform(-60, 60, size=s)
    theta = np.empty(k)
    for t in range(s):
        theta[2 * t] = centers[t] - sep / 2
        theta[2 * t + 1] = centers[t] + sep / 2
    base_snr = rng.uniform(5, 20, size=k)
    offsets = rng.uniform(-6, 6, size=k)
    gains = 10 ** ((base_snr + offsets) / 10) / 0.1
    freqs = np.arange(s) * (50e6 / 32)
    h = np.zeros((k, m, s), complex)
    for i in range(k):
        # identical draw order to build_cdl.py: phases are consumed after the
        # (rng-free) angle computation, so the phase sequence is unchanged.
        cluster_phases = rng.uniform(0, 2 * np.pi, size=(n_cl, s))
        cluster_angles = theta[i] + c_asa * arng.standard_normal(n_cl)
        for t in range(s):
            v = np.zeros(m, complex)
            for n in range(n_cl):
                v += np.sqrt(powers[n]) * array_response(cluster_angles[n], m) * np.exp(
                    1j * (2 * np.pi * freqs[t] * delays[n] * DELAY_SPREAD_S
                          + cluster_phases[n, t]))
            h[i, :, t] = np.sqrt(gains[i]) * v / (np.linalg.norm(v) + 1e-15)

    re, im = h.real.tolist(), h.imag.tolist()
    pairs = []
    for u in range(k):
        for v in range(u + 1, k):
            for t in range(s):
                vec_u = [(F(re[u][j][t]), F(im[u][j][t])) for j in range(m)]
                vec_v = [(F(re[v][j][t]), F(im[v][j][t])) for j in range(m)]
                g1 = sum(x * x + y * y for x, y in vec_u)
                g2 = sum(x * x + y * y for x, y in vec_v)
                real = sum(x * z + y * w for (x, y), (z, w) in zip(vec_u, vec_v))
                imag = sum(x * w - y * z for (x, y), (z, w) in zip(vec_u, vec_v))
                r = (real * real + imag * imag) / (g1 * g2) if g1 * g2 else F(0)
                pairs.append(dict(users=[u, v], resource=t, gain1=str(g1),
                                  gain2=str(g2), r=str(r)))
    return dict(name=f"cdl-{profile.lower()}-sep{sep:g}-s{seed}-M{m}-e3a",
                K=k, S=s, M=m, pmin=PMIN, pmax=PMAX, budget=BUDGET,
                pairs=pairs, channels_re=re, channels_im=im,
                metadata=dict(scene="cdl-e3a", profile=profile,
                              separation_deg=sep, seed=seed,
                              model=("paper generator with i.i.d. N(0,cASA^2) cluster "
                                     "angles; same gains and phases"),
                              delay_spread_s=DELAY_SPREAD_S,
                              angle_model="iid_gaussian", angle_std_deg=c_asa,
                              base_case=f"cdl-{profile.lower()}-sep{sep:g}-s{seed}-M{m}"))


def main() -> None:
    for path in frozen_paths():
        orig = load_frozen(path)
        meta = orig["metadata"]
        case = gaussian_channel(meta["profile"], float(meta["separation_deg"]),
                                int(meta["seed"]))
        out = OUTDIR / f"{case['name']}.json"
        out.write_text(json.dumps(case, indent=2), encoding="utf-8")
        print(case["name"], flush=True)
    print("done", len(frozen_paths()))


if __name__ == "__main__":
    main()
