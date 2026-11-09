# -*- coding: utf-8 -*-
"""Generate 3GPP TR 38.901 CDL-A/B/C cases (K=16, M=2) for the paper.

The cluster delays, powers and angles are taken from the standard tables.
We use independent per-cluster phases and a ULA response at half-wavelength
spacing. The generator is seed-reproducible and CPU-only.
"""
from pathlib import Path
import json
import math
import numpy as np
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "phase1-cdl-20261109"
CASES = OUT / "cases"
CASES.mkdir(parents=True, exist_ok=True)
TABLES = OUT / "tables"


def array_response(theta_deg, m):
    theta = np.deg2rad(theta_deg)
    return np.exp(1j * np.pi * np.arange(m) * np.sin(theta)) / np.sqrt(m)


def make_case(profile, sep_deg, seed, idx):
    table = json.loads((TABLES / f"CDL-{profile}.json").read_text())
    rng = np.random.default_rng(seed)
    k, s, m = 16, 8, 2
    delays = np.asarray(table["delays"], float)
    powers = 10 ** (np.asarray(table["powers"], float) / 10)
    powers = powers / powers.sum()
    aoa = np.asarray(table["aoa"], float)
    aoa = (aoa - aoa.mean()) / (aoa.std() + 1e-12)
    c_asa = float(table["cASA"])
    # 8 pairs: users (2t,2t+1) share a resource; the pair centre is random.
    centers = rng.uniform(-60, 60, size=s)
    theta = np.empty(k)
    for t in range(s):
        theta[2 * t] = centers[t] - sep_deg / 2
        theta[2 * t + 1] = centers[t] + sep_deg / 2
    # Per-user target SNR at 0.1 W, with near-far offsets.
    base_snr = rng.uniform(5, 20, size=k)
    offsets = rng.uniform(-6, 6, size=k)
    gains = 10 ** ((base_snr + offsets) / 10) / 0.1
    # 32 tones over 50 MHz; use the first 8 tones.
    freqs = np.arange(s) * (50e6 / 32)
    delay_spread = 100e-9
    h = np.zeros((k, m, s), complex)
    for i in range(k):
        cluster_angles = theta[i] + c_asa * aoa
        cluster_phases = rng.uniform(0, 2 * np.pi, size=(len(delays), s))
        for t in range(s):
            v = np.zeros(m, complex)
            for n in range(len(delays)):
                v += np.sqrt(powers[n]) * array_response(cluster_angles[n], m) * np.exp(
                    1j * (2 * np.pi * freqs[t] * delays[n] * delay_spread + cluster_phases[n, t]))
            v = v / (np.linalg.norm(v) + 1e-15)
            h[i, :, t] = np.sqrt(gains[i]) * v
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
    name = f"cdl-{profile.lower()}-sep{sep_deg:g}-s{seed}-M{m}"
    case = dict(name=name, K=k, S=s, M=m, pmin="1/1000", pmax="1/5", budget=str(F(13, 100) * k),
                pairs=pairs, channels_re=re, channels_im=im,
                metadata=dict(scene="cdl", profile=profile, separation_deg=sep_deg, seed=seed,
                              model="3GPP TR 38.901 CDL-A/B/C; independent cluster phases; ULA M=2",
                              delay_spread_s=delay_spread, base_snr_db="U(5,20)", nearfar_db="U(-6,6)"))
    (CASES / (name + ".json")).write_text(json.dumps(case, indent=2), encoding="utf-8")
    corr = [float(F(row["r"])) for row in pairs]
    snr = [10 * math.log10(float(g) * 0.1) for g in gains]
    print(f"{name}: r median {np.median(corr):.3f} p90 {np.percentile(corr,90):.3f} "
          f"snr median {np.median(snr):.1f} dB", flush=True)


if __name__ == "__main__":
    idx = 0
    for profile in ("A", "B", "C"):
        for sep in (0.5, 2.0, 6.0, 12.0):
            for seed in (2026110901, 2026110902, 2026110903, 2026110904):
                idx += 1
                make_case(profile, sep, seed, idx)
    print("total", idx)
