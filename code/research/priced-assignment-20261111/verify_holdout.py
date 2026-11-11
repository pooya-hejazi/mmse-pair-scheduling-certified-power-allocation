"""Independently verify saved native-CDL holdout inputs; optional link regeneration."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from fractions import Fraction
from pathlib import Path

sys.dont_write_bytecode = True
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import numpy as np

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parents[1]
FREQ = np.array([-14, -10, -6, -2, 2, 6, 10, 14], dtype=np.float64) * (50e6 / 32)
PREVIOUS = PROJECT / "research/independent-cdl-20261110"
PAIRS_PER_CASE = 960


def check(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keys_for(ledger):
    keys = [ledger["bootstrap"]]
    for profile in ledger["profiles"]:
        keys.extend(profile["channels"] + profile["factors"])
        keys.extend([profile["initialization"], profile["search"]])
    return keys


def check_ledger(ledger):
    sources = ledger["sources"]
    for name, digest in {**sources["project_sha256"], **ledger["historical_audit"]["sources"]}.items():
        check(sha(PROJECT / name) == digest, f"Source mismatch {name}")

    # Reconstruct the two prior registries and all actual draft pilot-invocation IDs.
    excluded = set()
    for name in ("seed_manifest.json", "generator_validation_draft_seed_manifest.json"):
        old = read(PREVIOUS / name)
        excluded.update(int(i) % 2**32 for i in old["historical_audit"]["seeds"])
        excluded.update(int(record["effective_seed"]) for record in keys_for(old))
    for profile in "ABC":
        with np.load(PREVIOUS / "native/draft-before-lowbits" / f"pilot-{profile}.npz",
                     allow_pickle=False) as old_raw:
            for name in ["channel_seeds", "factor_seeds"]:
                excluded.update(map(int, old_raw[name]))
    check(sorted(excluded) == ledger["historical_audit"]["seeds"], "Prior identifier set mismatch")
    records = keys_for(ledger)
    ids = set()
    for row in records:
        word = np.random.SeedSequence(int(ledger["root_entropy"]), spawn_key=tuple(row["spawn_key"])).generate_state(1)
        check(str(row["entropy"]) == ledger["root_entropy"] and int(word[0]) == row["effective_seed"],
              "Stream lineage mismatch")
        ids.add(int(word[0]))
    check(len(ids) == len(records) == 2041 and not (excluded & ids), "Seed identifier overlap")
    return len(excluded)


def exact_vector(vector):
    components = [float(x).as_integer_ratio() for z in vector for x in (z.real, z.imag)]
    unit = max(d for _, d in components)
    integers = [n * (unit // d) for n, d in components]
    sqnorm = sum(i * i for i in integers)
    return integers, sqnorm, str(Fraction(sqnorm, unit * unit))


def check_pair_rows(case, h):
    integer_vectors = [[exact_vector(h[u, :, s]) for s in range(8)] for u in range(16)]
    check(len(case["pairs"]) == PAIRS_PER_CASE, "Missing or duplicate pair row")
    combinations = ((u, v, s) for u in range(16) for v in range(u + 1, 16) for s in range(8))
    for row, (u, v, s) in zip(case["pairs"], combinations):
        a, na, ga = integer_vectors[u][s]
        b, nb, gb = integer_vectors[v][s]
        dot = sum(x * y for x, y in zip(a, b))
        cross = a[0] * b[1] - a[1] * b[0] + a[2] * b[3] - a[3] * b[2]
        correlation = str(Fraction(dot * dot + cross * cross, na * nb))
        check(row == dict(users=[u, v], resource=s, gain1=ga, gain2=gb, r=correlation),
              f"Exact coefficient mismatch {case['name']} {u} {v} {s}")


def original_link_module(ledger):
    source_path = PREVIOUS / "generator.py"
    spec = importlib.util.spec_from_file_location("frozen_link_engine", source_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    phy = Path(module.inspect.getfile(module.CDL)).parents[2]
    runtime = {p.relative_to(phy).as_posix(): sha(p) for p in
               sorted(set(phy.rglob("*.py")) | set(phy.rglob("*.json")))}
    check(runtime == ledger["sources"]["runtime_sha256"], "Runtime mismatch")
    return module


def verify(rebuild_links):
    ledger_path = BASE / "seed_manifest.json"
    ledger = read(ledger_path)
    prior_count = check_ledger(ledger)
    gen_path = BASE / "generator_validation_main.json"
    gen = read(gen_path)
    check(gen["status"] == "PASS" and gen["seed_manifest_sha256"] == sha(ledger_path),
          "Generation receipt binding")
    identity = [(b, p) for b in range(20) for p in "ABC"]
    check([(p["block"], p["profile"]) for p in ledger["profiles"]] == identity, "Missing seed registry rows")
    check([(p["block"], p["profile"]) for p in gen["profiles"]] == identity, "Missing generation rows")
    check({p.name for p in (BASE / "native").iterdir()} ==
          {f"native-b{b:02d}-{p}.npz" for b, p in identity}, "Native file inventory")
    check({p.name for p in (BASE / "cases").iterdir()} ==
          {f"native-b{b:02d}-{p}-snr{snr:02d}.json" for b, p in identity for snr in (0, 10, 20)},
          "Case file inventory")
    module = original_link_module(ledger) if rebuild_links else None
    user_links = 0
    case_count = 0
    maximum_error = 0.
    tic = time.monotonic()
    for seeds, profile in zip(ledger["profiles"], gen["profiles"]):
        b, p = seeds["block"], seeds["profile"]
        tag = f"native-b{b:02d}-{p}"
        raw_path = BASE / "native" / (tag + ".npz")
        native_digest = sha(raw_path)
        check(profile["native_sha256"] == native_digest and profile["native_path"] == f"native/{tag}.npz", tag)
        with np.load(raw_path, allow_pickle=False) as record:
            raw = {name: record[name] for name in record.files}
        cir, tau, native = raw["cir"], raw["delays_s"], raw["native_h"]
        paths = {"A": 23, "B": 23, "C": 24}[p]
        check(native.shape == (16, 2, 8) and cir.shape == (16, 2, paths) and tau.shape == (16, paths), tag)
        check(native.dtype == cir.dtype == np.complex128 and tau.dtype == np.float64, "Precision")
        check(np.array_equal(raw["frequency_hz"], FREQ) and np.all(np.isfinite(cir))
              and np.all(np.isfinite(tau)) and np.all(np.isfinite(native)), "Nonfinite channel or bad frequencies")
        check(np.array_equal(raw["bs_orientation_rad"], [0., 0., 0.])
              and np.array_equal(raw["ut_orientation_rad"], [math.pi, 0., 0.]), "Array orientations")
        check(np.array_equal(raw["ut_ant_pos_m"], np.zeros((1, 3))), "UT geometry")
        expected_bs = np.zeros((2, 3))
        expected_bs[:, 1] = np.array([-.25, .25]) * (299792458 / 3.5e9)
        check(np.allclose(raw["bs_ant_pos_m"], expected_bs, rtol=0, atol=1e-14), "BS geometry")
        cs = [x["effective_seed"] for x in seeds["channels"]]
        fs = [x["effective_seed"] for x in seeds["factors"]]
        check(np.array_equal(raw["channel_seeds"], cs) and np.array_equal(raw["factor_seeds"], fs), "Seed mapping")
        check(np.array_equal(raw["offset_db"], [np.random.default_rng(i).uniform(-6, 6) for i in fs]), "Offset replay")
        # Compute each tone by a direct path sum, separately from the generator's einsum.
        rebuilt = np.stack([(cir * np.exp((-2j * np.pi * f) * tau[:, None, :])).sum(axis=2)
                            for f in FREQ], axis=-1)
        fourier_error = float(np.max(abs(rebuilt - native)))
        check(fourier_error < 1e-11, "Independent Fourier mismatch")
        maximum_error = max(fourier_error, maximum_error)
        check(np.all(np.ptp(np.sum(abs(native)**2, axis=1), axis=1) > 1e-8), "Unexpected flat gains")
        if rebuild_links:
            ut, bs = module.arrays()
            for u in range(16):
                replay = module.link(p, cs[u], ut, bs)
                check(all(np.array_equal(expected, got) for expected, got in
                          zip([cir[u], tau[u], native[u]], replay)), f"Link replay mismatch {tag} {u}")
                user_links += 1
        check([v["snr_db"] for v in profile["cases"]] == [0, 10, 20], "Case coverage")
        for case_info in profile["cases"]:
            snr = case_info["snr_db"]
            name = f"{tag}-snr{snr:02d}"
            case_path = BASE / "cases" / (name + ".json")
            check(case_info["case_path"] == f"cases/{name}.json" and sha(case_path) == case_info["case_sha256"],
                  "Case path/hash mismatch")
            case = read(case_path)
            m = case["metadata"]
            check((case["name"], case["K"], case["S"], case["M"], case["pmin"], case["pmax"], case["budget"])
                  == (name, 16, 8, 2, "1/1000", "1/5", "52/25"), "Case header")
            check((m["block"], m["profile"], m["snr_db"], m["pilot"]) == (b, p, snr, False), "Case identity")
            check(m["initialization_seed"] == seeds["initialization"]["effective_seed"] and
                  m["search_seed"] == seeds["search"]["effective_seed"] and
                  m["channel_seeds"] == cs and m["factor_seeds"] == fs, "Case stream metadata")
            check(m["native_sha256"] == native_digest and m["native_path"] == profile["native_path"] and
                  m["seed_manifest_sha256"] == gen["seed_manifest_sha256"] and
                  m["generator_sha256"] == ledger["sources"]["generator_sha256"] and
                  m["protocol_sha256"] == ledger["sources"]["protocol_sha256"], "Case binding")
            check(np.array_equal(m["frequency_hz"], FREQ) and np.array_equal(m["offset_db"], raw["offset_db"])
                  and not m["normalize"], "Case metadata")
            h = np.asarray(case["channels_re"]) + 1j * np.asarray(case["channels_im"])
            # NumPy vector pow preserves the binary64 scaling recipe across builds of the frozen runtime.
            scales = np.sqrt(np.power(10., (snr + raw["offset_db"]) / 10.) / .1)
            check(np.array_equal(scales, np.asarray(m["nominal_perantenna_scale"])), "Scale-factor mismatch")
            check(np.array_equal(native * scales[:, None, None], h), "Scaled channel mismatch")
            check_pair_rows(case, h)
            case_count += 1
    check(case_count == 180 and user_links == (960 if rebuild_links else 0), "Replay count")
    return dict(status="PASS", mode="full-link-replay" if rebuild_links else "stored-input-replay",
                seed_manifest_sha256=sha(ledger_path), generation_receipt_sha256=sha(gen_path),
                verifier_sha256=sha(Path(__file__)), profile_count=60, case_count=case_count,
                native_links=960, regenerated_links_bitwise_equal=user_links, coefficients_checked=case_count*PAIRS_PER_CASE,
                exact_scaled_cases=case_count, max_fourier_abs_error=maximum_error, effective_seed_count=2041,
                excluded_historical_id_count=prior_count, historical_collisions=0, seconds=time.monotonic() - tic)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerate-links", action="store_true")
    parser.add_argument("--output", type=Path, help="Write a new receipt. Existing files are never replaced.")
    args = parser.parse_args()
    receipt = verify(args.regenerate_links)
    if args.output:
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(receipt, handle, indent=2, allow_nan=False)
            handle.write("\n")
    print(json.dumps(receipt, indent=2))

