# -*- coding: utf-8 -*-
"""Generate controlled-array K=16, M=2 cases for the Phase-1 scale check."""
from pathlib import Path
import json
import numpy as np
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "phase1-benchmark-20261109" / "controlled_cases"
OUT.mkdir(parents=True, exist_ok=True)


def make_case(seed, snr_db, nearfar_db, halfwidth_deg, name):
    rng = np.random.default_rng(seed)
    k, s, m = 16, 8, 2
    theta = np.deg2rad(halfwidth_deg) * rng.uniform(-1, 1, k)
    a = np.exp(1j * np.pi * np.arange(m)[:, None] * np.sin(theta)[None, :]) / np.sqrt(m)
    z_user = (rng.normal(size=(m, k)) + 1j * rng.normal(size=(m, k))) / np.sqrt(2 * m)
    h = np.zeros((k, m, s), complex)
    for i in range(k):
        offsets = rng.uniform(-nearfar_db, nearfar_db)
        for t in range(s):
            z_res = (rng.normal(size=m) + 1j * rng.normal(size=m)) / np.sqrt(2 * m)
            v = np.sqrt(10 / 11) * a[:, i] + np.sqrt(1 / 11) * (np.sqrt(0.8) * z_user[:, i] + np.sqrt(0.2) * z_res)
            v = v / np.linalg.norm(v)
            g = 10 ** ((snr_db + offsets) / 10) / 0.1
            h[i, :, t] = np.sqrt(g) * v
    re = h.real.tolist(); im = h.imag.tolist()
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
                pairs.append(dict(users=[u, v], resource=t, gain1=str(g1), gain2=str(g2), r=str(r)))
    case = dict(name=name, K=k, S=s, M=m, pmin="1/1000", pmax="1/5", budget=str(F(13, 100) * k),
                pairs=pairs, channels_re=re, channels_im=im,
                metadata=dict(scene="controlled", phase="phase1", source="controlled-array",
                              snr_db=snr_db, nearfar_db=nearfar_db, halfwidth_deg=halfwidth_deg, seed=seed))
    (OUT / (name + ".json")).write_text(json.dumps(case, indent=2), encoding="utf-8")
    print("wrote", name)


if __name__ == "__main__":
    idx = 0
    for seed in (2026110901, 2026110902):
        for snr_db in (0, 10, 20):
            for nearfar_db in (0, 10):
                idx += 1
                make_case(seed, snr_db, nearfar_db, 45.0, f"ctl-K16-M2-{idx:02d}")
