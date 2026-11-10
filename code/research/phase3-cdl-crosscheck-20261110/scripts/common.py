# -*- coding: utf-8 -*-
"""Shared constants and deterministic replay for the CDL cross-check.

Only reads the frozen phase-1 artifacts. Nothing here writes to phase 1.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from fractions import Fraction as F
from pathlib import Path

import numpy as np

PAPER_ROOT = Path(__file__).resolve().parents[3]
if not (PAPER_ROOT / "research").is_dir():
    PAPER_ROOT = Path(r"D:\PostDocProposal\PostDocPaper2")
PHASE1 = PAPER_ROOT / "research" / "phase1-cdl-20261109"
PHASE3 = PAPER_ROOT / "research" / "phase3-cdl-crosscheck-20261110"
TABLES = PHASE1 / "tables"
FROZEN_CASES = PHASE1 / "cases"

K, S, M = 16, 8, 2
PMIN, PMAX = "1/1000", "1/5"
BUDGET = str(F(13, 100) * K)          # 52/25
TONE_SPACING_HZ = 50e6 / 32           # 1.5625 MHz
DELAY_SPREAD_S = 100e-9
SECONDS = 10.0
MATCHING_SEED = 1101
GAIN_EPS = 1e-4
N_REAL = 3
SEED_BASE = 20_261_110

PROFILES = {
    "A": {"cASA": 11.0, "xpr": 10.0, "n_clusters": 23, "cDS_lg": -7.49,
          "cASD": 5.0, "cZSD": 3.0, "cZSA": 3.0},
    "B": {"cASA": 22.0, "xpr": 8.0, "n_clusters": 23, "cDS_lg": -6.90,
          "cASD": 10.0, "cZSD": 3.0, "cZSA": 7.0},
    "C": {"cASA": 15.0, "xpr": 7.0, "n_clusters": 24, "cDS_lg": -7.60,
          "cASD": 2.0, "cZSD": 3.0, "cZSA": 7.0},
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def load_table(profile: str) -> dict:
    return json.loads((TABLES / f"CDL-{profile}.json").read_text(encoding="utf-8"))


def array_response(theta_deg, m):
    theta = np.deg2rad(theta_deg)
    return np.exp(1j * np.pi * np.arange(m) * np.sin(theta)) / np.sqrt(m)


def recover_theta(seed: int, sep_deg: float) -> np.ndarray:
    """Replicate build_cdl.py lines 28-41 without touching the filesystem."""
    rng = np.random.default_rng(seed)
    centers = rng.uniform(-60, 60, size=S)
    theta = np.empty(K)
    for t in range(S):
        theta[2 * t] = centers[t] - sep_deg / 2
        theta[2 * t + 1] = centers[t] + sep_deg / 2
    return theta


def recover_gains(case: dict) -> dict[int, np.ndarray]:
    """Recover the exact per-user, per-tone gain from the stored channels.

    The generator normalises every tone separately, so the stored gain differs
    across tones at the 1e-16 level (and therefore so do the rational pair
    records).  The paired design reuses the per-tone value, not one scalar.
    """
    re = np.asarray(case["channels_re"], float)
    im = np.asarray(case["channels_im"], float)
    h = re + 1j * im                       # [K, M, S]
    gains = {i: (np.abs(h[i]) ** 2).sum(axis=0) for i in range(case["K"])}
    # Cross-check against the rational pair records at every resource.
    for row in case["pairs"]:
        u, v = row["users"]
        t = row["resource"]
        if abs(float(F(row["gain1"])) - float(gains[u][t])) > 1e-9:
            raise ValueError(f"{case['name']}: gain1 mismatch u={u} t={t}")
        if abs(float(F(row["gain2"])) - float(gains[v][t])) > 1e-9:
            raise ValueError(f"{case['name']}: gain2 mismatch v={v} t={t}")
    return gains


def paper_channel(profile: str, sep_deg: float, seed: int) -> dict:
    """Bit-faithful replay of phase1 build_cdl.make_case, minus disk writes.

    This is the T1 oracle. It must reproduce the frozen case exactly.
    """
    table = load_table(profile)
    rng = np.random.default_rng(seed)
    k, s, m = K, S, M
    delays = np.asarray(table["delays"], float)
    powers = 10 ** (np.asarray(table["powers"], float) / 10)
    powers = powers / powers.sum()
    aoa = np.asarray(table["aoa"], float)
    aoa = (aoa - aoa.mean()) / (aoa.std() + 1e-12)
    c_asa = float(table["cASA"])
    centers = rng.uniform(-60, 60, size=s)
    theta = np.empty(k)
    for t in range(s):
        theta[2 * t] = centers[t] - sep_deg / 2
        theta[2 * t + 1] = centers[t] + sep_deg / 2
    base_snr = rng.uniform(5, 20, size=k)
    offsets = rng.uniform(-6, 6, size=k)
    gains = 10 ** ((base_snr + offsets) / 10) / 0.1
    freqs = np.arange(s) * (50e6 / 32)
    delay_spread = DELAY_SPREAD_S
    h = np.zeros((k, m, s), complex)
    for i in range(k):
        cluster_angles = theta[i] + c_asa * aoa
        cluster_phases = rng.uniform(0, 2 * np.pi, size=(len(delays), s))
        for t in range(s):
            v = np.zeros(m, complex)
            for n in range(len(delays)):
                v += np.sqrt(powers[n]) * array_response(cluster_angles[n], m) * np.exp(
                    1j * (2 * np.pi * freqs[t] * delays[n] * delay_spread + cluster_phases[n, t])
                )
            v = v / (np.linalg.norm(v) + 1e-15)
            h[i, :, t] = np.sqrt(gains[i]) * v
    re = h.real.tolist()
    im = h.imag.tolist()
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
    return dict(name=f"cdl-{profile.lower()}-sep{sep_deg:g}-s{seed}-M{m}",
                K=k, S=s, M=m, pmin=PMIN, pmax=PMAX, budget=BUDGET,
                pairs=pairs, channels_re=re, channels_im=im,
                metadata=dict(scene="cdl", profile=profile,
                              separation_deg=sep_deg, seed=seed,
                              model=("3GPP TR 38.901 CDL-A/B/C; independent cluster phases; "
                                     "ULA M=2"),
                              delay_spread_s=delay_spread,
                              base_snr_db="U(5,20)", nearfar_db="U(-6,6)"))


def frozen_paths() -> list[Path]:
    return sorted(FROZEN_CASES.glob("*.json"))


def load_frozen(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def add_repo_to_path() -> None:
    cert = PAPER_ROOT / "research" / "manuscript-refinement-20261106" / "certification"
    for p in (
        cert,
        PAPER_ROOT / "research" / "completion-20261031" / "confirmation",
        PAPER_ROOT / "research" / "dual-track-revision-20261103" / "baseline-code",
        PAPER_ROOT / "research" / "phase1-benchmark-20261109",
    ):
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)


def bootstrap_ci(values, stat=np.median, b=10000, seed=20261109, alpha=0.05):
    rng = np.random.default_rng(seed)
    v = np.asarray(values, float)
    draws = rng.choice(v, size=(b, v.size), replace=True)
    stats = stat(draws, axis=1)
    return float(np.quantile(stats, alpha / 2)), float(np.quantile(stats, 1 - alpha / 2))


def case_gain(rec: dict) -> float:
    base = max(rec["grid_rate"], rec["slsqp_rate"], rec["iwmmse_rate"], rec["matching_rate"])
    return (rec["proposed_rate"] - base) / base


def spearman(x, y) -> float:
    def rank(a):
        a = np.asarray(a, float)
        order = np.argsort(a)
        r = np.empty_like(order, dtype=float)
        r[order] = np.arange(len(a), dtype=float)
        # average ties
        _, inv, counts = np.unique(a, return_inverse=True, return_counts=True)
        if np.any(counts > 1):
            sums = np.zeros(len(counts))
            np.add.at(sums, inv, r)
            r = (sums / counts)[inv]
        return r
    rx, ry = rank(x), rank(y)
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    den = math.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / den) if den else float("nan")
