# -*- coding: utf-8 -*-
"""E2 generation: independent Sionna 2.2.0 CDL realisations in the frozen schema.

Primary configuration (protocol §4.2): one CDL link per user, a two-element
half-wavelength ULA rotated so that the profile-mean table AoA lands on the
user's pair-centre angle, single polarisation, 20 rays/cluster, one time
sample, 100 ns delay spread.  Per-tone gains are reused from the frozen case
(paired design), so only the channel directions change.
"""
from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction as F
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (DELAY_SPREAD_S, K, M, N_REAL, PAPER_ROOT, PHASE3, PMAX, PMIN,
                    BUDGET, SEED_BASE, TONE_SPACING_HZ, frozen_paths, load_frozen,
                    load_table, recover_gains, recover_theta, sha256)

CASES_OUT = PHASE3 / "cases"
CASES_OUT.mkdir(parents=True, exist_ok=True)


def build_links(profile: str, theta_deg: np.ndarray, seeds: list[int]):
    """Return Sionna frequency responses [K, M, S] for one case/realisation."""
    from sionna.phy.channel.tr38901 import CDL, Antenna, AntennaArray
    from sionna.phy.channel import cir_to_ofdm_channel

    f = 3.5e9
    spec = "19.2"
    ut = Antenna(polarization="single", polarization_type="V",
                 antenna_pattern="omni", carrier_frequency=f)
    bs = AntennaArray(num_rows=1, num_cols=2, polarization="single",
                      polarization_type="V", antenna_pattern="omni",
                      carrier_frequency=f)
    mu = float(np.mean(load_table(profile)["aoa"]))
    freqs = torch.arange(8, dtype=torch.float32) * TONE_SPACING_HZ
    h = np.zeros((K, M, 8), complex)
    phis = []
    for i in range(K):
        # aoa_lcs = aoa_gcs - phi  =>  phi = mu - theta_i
        phi = np.deg2rad(mu - theta_deg[i])
        phis.append(float(phi))
        cdl = CDL(model=profile, delay_spread=DELAY_SPREAD_S,
                  carrier_frequency=f, ut_array=ut, bs_array=bs,
                  direction="uplink", min_speed=0.0, max_speed=0.0,
                  spec_version=spec,
                  bs_orientation=torch.tensor([phi, 0.0, 0.0], dtype=torch.float32))
        cdl.torch_rng.manual_seed(int(seeds[i]))
        a, tau = cdl(batch_size=1, num_time_steps=1, sampling_frequency=50e6)
        H = cir_to_ofdm_channel(freqs, a, tau, normalize=False)
        H = H.squeeze().detach().cpu().numpy()          # [M, 8]
        if H.shape != (M, 8):
            raise RuntimeError(f"unexpected Sionna shape {H.shape}")
        h[i] = H
    return h, phis


def make_case(orig: dict, realization: int, case_ordinal: int, n_real: int) -> dict:
    meta = orig["metadata"]
    profile = meta["profile"]
    sep = float(meta["separation_deg"])
    seed = int(meta["seed"])
    theta = recover_theta(seed, sep)
    gains = recover_gains(orig)

    seeds = [SEED_BASE + case_ordinal * 1000 + realization * 10 + i for i in range(K)]
    h, phis = build_links(profile, theta, seeds)

    # Mirror build_cdl.py exactly: unit norm per tone, then sqrt(gain).
    for i in range(K):
        for t in range(8):
            v = h[i, :, t]
            h[i, :, t] = np.sqrt(float(gains[i][t])) * v / (np.linalg.norm(v) + 1e-15)

    re = h.real.tolist()
    im = h.imag.tolist()
    pairs = []
    for u in range(K):
        for v in range(u + 1, K):
            for t in range(8):
                vec_u = [(F(re[u][j][t]), F(im[u][j][t])) for j in range(M)]
                vec_v = [(F(re[v][j][t]), F(im[v][j][t])) for j in range(M)]
                g1 = sum(x * x + y * y for x, y in vec_u)
                g2 = sum(x * x + y * y for x, y in vec_v)
                real = sum(x * z + y * w for (x, y), (z, w) in zip(vec_u, vec_v))
                imag = sum(x * w - y * z for (x, y), (z, w) in zip(vec_u, vec_v))
                r = (real * real + imag * imag) / (g1 * g2) if g1 * g2 else F(0)
                pairs.append(dict(users=[u, v], resource=t, gain1=str(g1),
                                  gain2=str(g2), r=str(r)))

    name = f"{orig['name']}-sionna-r{realization}"
    return dict(name=name, K=K, S=8, M=M, pmin=PMIN, pmax=PMAX, budget=BUDGET,
                pairs=pairs, channels_re=re, channels_im=im,
                metadata=dict(scene="cdl-sionna", profile=profile,
                              separation_deg=sep, seed=seed,
                              model=("3GPP TR 38.901 CDL Sionna 2.2.0, per-user rotated "
                                     "half-wavelength ULA, 20 rays/cluster, single pol"),
                              delay_spread_s=DELAY_SPREAD_S,
                              realization=realization, n_real=n_real,
                              case_ordinal=case_ordinal,
                              sionna_seeds=seeds,
                              bs_orientation_rad=phis,
                              theta_deg=theta.tolist(),
                              base_case=orig["name"],
                              sionna_version=__import__("sionna").__version__,
                              spec_version="19.2"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-real", type=int, default=N_REAL)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    paths = frozen_paths()
    if args.limit:
        paths = paths[:args.limit]
    manifest = []
    for ord_, path in enumerate(frozen_paths(), start=1):
        if path not in paths:
            continue
        orig = load_frozen(path)
        for r in range(args.n_real):
            case = make_case(orig, r, ord_, args.n_real)
            out = CASES_OUT / f"{case['name']}.json"
            out.write_text(json.dumps(case, indent=2), encoding="utf-8")
            manifest.append(dict(name=case["name"], file=out.name,
                                 bytes=out.stat().st_size, sha256=sha256(out)))
            print(f"[{ord_}/{len(frozen_paths())}] r{r} {case['name']}", flush=True)
    (CASES_OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(manifest)} cases")


if __name__ == "__main__":
    main()
