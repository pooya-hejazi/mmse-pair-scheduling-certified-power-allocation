"""Replay the 10 November native Sionna links and their scaled case matrices."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

STUDY = Path(__file__).resolve().parent / "research/independent-cdl-20261110"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def same_bits(left, right):
    a, b = np.asarray(left), np.asarray(right)
    return a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes()


def channel_engine(ledger):
    engine_path = STUDY / "generator.py"
    require(sha(engine_path) == ledger["sources"]["generator_sha256"], "Channel implementation hash mismatch")
    spec = importlib.util.spec_from_file_location("registered_native_channel_engine", engine_path)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    phy = Path(engine.inspect.getfile(engine.CDL)).parents[2]
    expected = {}
    for name, digest in ledger["sources"]["runtime_sha256"].items():
        prefix, marker, rel = name.replace("\\", "/").rpartition("/sionna/phy/")
        require(bool(marker and rel) and rel not in expected, "Unrecognized or duplicate Sionna source key")
        expected[rel] = digest
    files = set(phy.rglob("*.py")) | set(phy.rglob("*.json"))
    require({p.relative_to(phy).as_posix(): sha(p) for p in files} == expected,
            "Installed Sionna PHY sources differ from the generation ledger")
    installed = {"sionna": engine.sionna.__version__, "torch": engine.torch.__version__, "numpy": np.__version__}
    require(all(ledger["environment"][k] == v for k,v in installed.items()), "Numerical package version mismatch")
    return engine, len(expected)


def verify(phase):
    manifest = STUDY / "seed_manifest.json"
    source_freeze = read(STUDY / "source_manifest.json")["hashes"]
    ledger_digest = sha(manifest)
    require(ledger_digest == source_freeze["research/independent-cdl-20261110/seed_manifest.json"],
            "Seed ledger hash mismatch")
    ledger = read(manifest)
    engine, source_files = channel_engine(ledger)
    phases = ("main", "pilot") if phase == "all" else (phase,)
    phases_checked = {}
    start = time.monotonic()
    for label in phases:
        generation = read(STUDY / f"generator_validation_{label}.json")
        require(generation["status"] == "PASS" and generation["seed_manifest_sha256"] == ledger_digest
                and generation["generator_sha256"] == ledger["sources"]["generator_sha256"],
                "Invalid registered generation receipt")
        records = [(r["block"], r["profile"], r) for r in ledger["profiles"] if r["phase"] == label]
        expected_ids = [(b,p) for b in range(20 if label == "main" else 1) for p in "ABC"]
        require([(b,p) for b,p,_ in records] == expected_ids, "Missing or reordered registry profile")
        require([(r["block"],r["profile"]) for r in generation["profiles"]] == expected_ids, "Generation coverage mismatch")
        link_count = case_count = 0
        for (block, profile, stream), entry in zip(records, generation["profiles"]):
            tag = f"native-b{block:02d}-{profile}" if label == "main" else f"pilot-{profile}"
            native = STUDY / "native" / (tag + ".npz")
            require(entry["native_path"] == native.relative_to(STUDY).as_posix() and sha(native) == entry["native_sha256"],
                    "Native input path/hash mismatch " + tag)
            with np.load(native, allow_pickle=False) as saved:
                channels = [s["effective_seed"] for s in stream["channels"]]
                factors = [s["effective_seed"] for s in stream["factors"]]
                require(np.array_equal(saved["channel_seeds"], channels) and np.array_equal(saved["factor_seeds"], factors),
                        "Native stream mismatch " + tag)
                offsets = np.array([np.random.default_rng(seed).uniform(-6,6) for seed in factors])
                require(np.array_equal(offsets, saved["offset_db"]), "Offset replay mismatch " + tag)
                a, tau, h = saved["cir"], saved["delays_s"], saved["native_h"]
                ut, bs = engine.arrays()
                require(len(channels) == 16 and h.shape == (16,2,8), "Link count or shape mismatch " + tag)
                for user,seed in enumerate(channels):
                    replayed = engine.link(profile,seed,ut,bs)
                    require(all(same_bits(x,y) for x,y in zip(replayed,(a[user],tau[user],h[user]))),
                            f"Link reconstruction mismatch {tag}, user {user}")
                    link_count += 1
                snrs = [0,10,20] if label == "main" else [10]
                require([c["snr_db"] for c in entry["cases"]] == snrs, "Missing SNR condition")
                for c in entry["cases"]:
                    snr = c["snr_db"]
                    path = STUDY / "cases" / f"{tag}-snr{snr:02d}.json"
                    require(c["case_path"] == path.relative_to(STUDY).as_posix() and sha(path) == c["case_sha256"],
                            "Case hash mismatch " + str(path.name))
                    case = read(path)
                    m = case["metadata"]
                    require(m["seed_manifest_sha256"] == ledger_digest and m["native_sha256"] == entry["native_sha256"]
                            and m["initialization_seed"] == stream["initialization"]["effective_seed"]
                            and m["search_seed"] == stream["search"]["effective_seed"]
                            and m["profile"] == profile and m["block"] == block and m["snr_db"] == snr
                            and m["pilot"] == (label == "pilot") and m["channel_seeds"] == channels
                            and m["factor_seeds"] == factors, "Case metadata mismatch " + path.name)
                    scale = np.sqrt(10.**((snr+offsets)/10.)/.1)
                    scaled = h * scale[:, None, None]
                    require(np.array_equal(m["nominal_perantenna_scale"],scale)
                            and same_bits(scaled.real, case["channels_re"])
                            and same_bits(scaled.imag, case["channels_im"]), "Case scaling mismatch " + path.name)
                    case_count += 1
        phases_checked[label] = {"profiles": len(records), "regenerated_native_links": link_count,
                                 "scaled_case_matrices": case_count}
    return {"status":"PASS", "phase":phase, "seed_manifest_sha256":ledger_digest,
            "generator_sha256":ledger["sources"]["generator_sha256"],"verified_sionna_phy_source_files":source_files,
            "phases":phases_checked, "bit_exact_cir_delays_tones_and_scaled_channels":True,
            "seconds_excluding_runtime_import":time.monotonic()-start}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("all","main","pilot"), default="all")
    parser.add_argument("--output", type=Path, help="Optional fresh JSON receipt file")
    args = parser.parse_args()
    receipt = verify(args.phase)
    if args.output:
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(receipt,handle,indent=2)
            handle.write("\n")
    print(json.dumps(receipt,indent=2))
