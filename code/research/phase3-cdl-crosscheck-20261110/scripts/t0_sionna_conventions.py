# -*- coding: utf-8 -*-
"""T0: pin Sionna array/orientation conventions before any E2 generation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DELAY_SPREAD_S, PHASE3, PROFILES, array_response, load_table

OUT = PHASE3 / "output"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    from sionna.phy.channel.tr38901 import CDL, Antenna, AntennaArray

    f = 3.5e9
    lam = 299_792_458.0 / f
    ut = Antenna(polarization="single", polarization_type="V",
                 antenna_pattern="omni", carrier_frequency=f)
    bs = AntennaArray(num_rows=1, num_cols=2, polarization="single",
                      polarization_type="V", antenna_pattern="omni",
                      carrier_frequency=f)
    pos = bs.ant_pos.numpy()
    theta = np.deg2rad(np.linspace(-80, 80, 33))
    r_hat = np.stack([np.cos(theta), np.sin(theta), np.zeros_like(theta)], axis=1)
    phase = 2 * np.pi / lam * (r_hat @ pos.T)
    resp = np.exp(1j * phase)                      # [angles, 2]
    paper = np.stack([array_response(t, 2) for t in np.rad2deg(theta)])
    ratio_err = np.max(np.abs(resp[:, 1] / resp[:, 0]
                              - np.exp(1j * np.pi * np.sin(theta))))
    global_phase = np.exp(-1j * np.pi / 2 * np.sin(theta))
    full_err = np.max(np.abs(resp - global_phase[:, None] * paper))

    # T0b: orientation -> effective LCS azimuth
    cdl = CDL(model="A", delay_spread=DELAY_SPREAD_S, carrier_frequency=f,
              ut_array=ut, bs_array=bs, direction="uplink", min_speed=0.0)
    cc = cdl._cir_gen
    zoa = torch.tensor([[[[[np.pi / 2]]]]], dtype=torch.float32)
    maps = []
    for phi in (-0.6, -0.3, 0.0, 0.3, 0.6):
        aoa = torch.tensor([[[[[0.7]]]]], dtype=torch.float32)
        o = torch.tensor([[phi, 0.0, 0.0]], dtype=torch.float32)
        _, aoa_out = cc._gcs_to_lcs(o, zoa, aoa)
        maps.append(dict(phi=phi, aoa_in=0.7, aoa_out=float(aoa_out)))

    # Centre offsets so that the profile-mean table AoA lands on theta_i.
    centre = {p: float(np.mean(load_table(p)["aoa"])) for p in PROFILES}

    # T0c: r invariance under global conjugation (exact) and delay-sign law.
    rng = np.random.default_rng(7)
    r_vals, r_conj = [], []
    for _ in range(200):
        h = rng.standard_normal((2, 8)) + 1j * rng.standard_normal((2, 8))
        ru = h[0] / np.linalg.norm(h[0])
        rv = h[1] / np.linalg.norm(h[1])
        r = abs(np.vdot(ru, rv)) ** 2
        r_vals.append(float(r))
        r_conj.append(float(abs(np.vdot(ru.conj(), rv.conj())) ** 2))

    out = dict(
        sionna_version=__import__("sionna").__version__,
        array_positions_m=pos.tolist(),
        wavelength_m=lam,
        t0a=dict(max_ratio_error=float(ratio_err), max_full_error=float(full_err),
                 note="resp = exp(-j*pi/2*sin(theta)) * paper_array_response"),
        t0b=dict(mapping=maps, profile_mean_aoa_deg=centre,
                 note="aoa_lcs = aoa_gcs - phi; set phi_deg = mean_aoa - theta_i"),
        t0c=dict(max_conj_r_difference=float(np.max(np.abs(np.array(r_vals) - np.array(r_conj))))),
    )
    (OUT / "t0_conventions.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
