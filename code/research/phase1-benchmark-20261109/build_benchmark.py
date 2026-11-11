# -*- coding: utf-8 -*-
"""Build the pre-registered Phase-1 benchmark variants.

The 32 stored DeepMIMO cases are transformed deterministically:
- receive dimension M in {2,4,8} by truncating the same channel vectors;
- p_min = 0.001 W, p_max = 0.2 W;
- off-grid budget P/K = 0.13 W;
- grid {0.05,0.1,0.2} W.
No case is selected by outcome.
"""
from pathlib import Path
import hashlib
import json
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "research" / "manuscript-refinement-20261106" / "certification"
OUT = ROOT / "research" / "phase1-benchmark-20261109"
CASES = OUT / "cases"
CASES.mkdir(parents=True, exist_ok=True)


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def truncate(case, m_eff):
    k, s = case["K"], case["S"]
    re, im = case["channels_re"], case["channels_im"]
    pairs = []
    for u in range(k):
        for v in range(u + 1, k):
            for t in range(s):
                vec_u = [(F(re[u][j][t]), F(im[u][j][t])) for j in range(m_eff)]
                vec_v = [(F(re[v][j][t]), F(im[v][j][t])) for j in range(m_eff)]
                g1 = sum(x * x + y * y for x, y in vec_u)
                g2 = sum(x * x + y * y for x, y in vec_v)
                real = sum(x * z + y * w for (x, y), (z, w) in zip(vec_u, vec_v))
                imag = sum(x * w - y * z for (x, y), (z, w) in zip(vec_u, vec_v))
                r = (real * real + imag * imag) / (g1 * g2) if g1 * g2 else F(0)
                pairs.append(dict(users=[u, v], resource=t,
                                  gain1=str(g1), gain2=str(g2), r=str(r)))
    out = dict(case)
    out["name"] = f'{case["name"]}-M{m_eff}'
    out["M"] = m_eff
    out["pmin"] = "1/1000"
    out["pmax"] = "1/5"
    out["budget"] = str(F(13, 100) * k)
    out["channels_re"] = [user[:m_eff] for user in re]
    out["channels_im"] = [user[:m_eff] for user in im]
    out["pairs"] = pairs
    out["metadata"] = dict(out.get("metadata", {}),
                           phase="phase1",
                           source_case=case["name"],
                           m_eff=m_eff,
                           protocol="M-truncated stored channels; pmin=0.001; pmax=0.2; P/K=0.13; grid=0.05,0.1,0.2")
    return out


def main():
    manifest = []
    for path in sorted((CERT / "inputs" / "corrected").glob("*/case.json")):
        source = json.loads(path.read_text(encoding="utf-8"))
        for m_eff in (2, 4, 8):
            if m_eff > source["M"]:
                continue
            case = truncate(source, m_eff)
            out_path = CASES / (case["name"] + ".json")
            out_path.write_text(json.dumps(case, sort_keys=True, indent=2), encoding="utf-8")
            manifest.append(dict(name=case["name"], source=source["name"], scene=source["metadata"].get("scene", source["name"].split("-")[0]),
                                 K=case["K"], S=case["S"], M=m_eff, pmin=case["pmin"], pmax=case["pmax"],
                                 budget=case["budget"], sha256=hashlib.sha256(out_path.read_bytes()).hexdigest(),
                                 challenge=dict(pairing_gain=None)))
            print("wrote", out_path.name)
    doc = dict(
        schema="PHASE1_BENCHMARK_V1",
        description="Deterministic M-truncation of all 32 stored DeepMIMO cases; no outcome-based selection.",
        factors=dict(M=[2, 4, 8], K=[8, 16], pmin="1/1000", pmax="1/5", budget_over_K="13/100",
                     grid=["1/20", "1/10", "1/5"], anchor="sequential pairing + uniform P/K"),
        cases=manifest,
        n=len(manifest),
    )
    (OUT / "BENCHMARK_MANIFEST.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print("total", len(manifest))


if __name__ == "__main__":
    main()
