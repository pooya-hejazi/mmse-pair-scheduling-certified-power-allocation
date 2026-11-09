# -*- coding: utf-8 -*-
"""Generate 3GPP CDL K=8, S=4, M=2 cases."""
from pathlib import Path
import json
import math
import numpy as np
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "phase1-cdl-20261109"
CASES = OUT / "cases_k8"
CASES.mkdir(parents=True, exist_ok=True)
TABLES = OUT / "tables"


def aresp(theta_deg, m):
    theta = np.deg2rad(theta_deg)
    return np.exp(1j * np.pi * np.arange(m) * np.sin(theta)) / np.sqrt(m)


def make_case(profile, sep, seed):
    table = json.loads((TABLES / f"CDL-{profile}.json").read_text())
    rng = np.random.default_rng(seed)
    k, s, m = 8, 4, 2
    delays = np.asarray(table["delays"], float)
    powers = 10 ** (np.asarray(table["powers"], float) / 10); powers /= powers.sum()
    aoa = np.asarray(table["aoa"], float); aoa = (aoa - aoa.mean()) / (aoa.std() + 1e-12)
    c_asa = float(table["cASA"])
    centers = rng.uniform(-60, 60, size=s)
    theta = np.empty(k)
    for t in range(s):
        theta[2*t] = centers[t] - sep/2
        theta[2*t+1] = centers[t] + sep/2
    gains = 10 ** ((rng.uniform(5, 20, size=k) + rng.uniform(-6, 6, size=k)) / 10) / 0.1
    freqs = np.arange(s) * (50e6 / 32)
    ds = 100e-9
    h = np.zeros((k, m, s), complex)
    for i in range(k):
        angles = theta[i] + c_asa * aoa
        phases = rng.uniform(0, 2*np.pi, size=(len(delays), s))
        for t in range(s):
            v = np.zeros(m, complex)
            for n in range(len(delays)):
                v += np.sqrt(powers[n]) * aresp(angles[n], m) * np.exp(1j*(2*np.pi*freqs[t]*delays[n]*ds + phases[n, t]))
            v /= (np.linalg.norm(v) + 1e-15)
            h[i, :, t] = np.sqrt(gains[i]) * v
    re, im = h.real.tolist(), h.imag.tolist()
    pairs = []
    for u in range(k):
        for v in range(u+1, k):
            for t in range(s):
                vu = [(F(re[u][j][t]), F(im[u][j][t])) for j in range(m)]
                vv = [(F(re[v][j][t]), F(im[v][j][t])) for j in range(m)]
                g1 = sum(x*x+y*y for x, y in vu); g2 = sum(x*x+y*y for x, y in vv)
                real = sum(x*z+y*w for (x, y), (z, w) in zip(vu, vv))
                imag = sum(x*w-y*z for (x, y), (z, w) in zip(vu, vv))
                r = (real*real+imag*imag)/(g1*g2) if g1*g2 else F(0)
                pairs.append(dict(users=[u, v], resource=t, gain1=str(g1), gain2=str(g2), r=str(r)))
    name = f"cdl-k8-{profile.lower()}-sep{sep:g}-s{seed}"
    case = dict(name=name, K=k, S=s, M=m, pmin="1/1000", pmax="1/5", budget=str(F(13, 100)*k),
                pairs=pairs, channels_re=re, channels_im=im,
                metadata=dict(scene="cdl", profile=profile, separation_deg=sep, seed=seed, model="3GPP CDL K8"))
    (CASES / (name + ".json")).write_text(json.dumps(case, indent=2), encoding="utf-8")
    print(name, flush=True)


if __name__ == "__main__":
    for p in "ABC":
        for sep in (2.0, 12.0):
            for seed in (2026110901, 2026110902, 2026110903, 2026110904):
                make_case(p, sep, seed)
