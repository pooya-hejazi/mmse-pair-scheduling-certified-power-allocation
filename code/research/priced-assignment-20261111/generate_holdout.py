"""Register fresh native-CDL holdout streams and generate inputs without optimization."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import secrets
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
for thread_variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[thread_variable] = "1"

import numpy as np

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parents[1]
PREVIOUS = PROJECT / "research/independent-cdl-20261110"
DEPENDENCY = PREVIOUS / "generator.py"
OLD_GENERATOR = "4a915941b440dae9f20adf802d7a5abc39cd34a5153ee17f8a19e9591dfb056c"
REGISTRY = BASE / "seed_manifest.json"
PROTOCOL = BASE / "GENERATOR_PROTOCOL.md"
VERIFIER = BASE / "verify_holdout.py"
MODULUS = 2**32


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(path, data):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, allow_nan=False)
        handle.write("\n")


def project_path(path):
    return Path(path).relative_to(PROJECT).as_posix()


def registered_seeds(ledger):
    result = [ledger["bootstrap"]["effective_seed"]]
    for row in ledger["profiles"]:
        result.extend(entry["effective_seed"] for entry in row["channels"] + row["factors"])
        result.extend(row[key]["effective_seed"] for key in ("initialization", "search"))
    return result


def exclusions():
    prior_files = {}
    prior_sets = {}
    prescribed = {
        "seed_manifest.json": "1c15391815480d681dc48ee2fb792cafb14aa15293f31d53289a8f9c768967c3",
        "generator_validation_draft_seed_manifest.json": "750dc681ecb906c497986ebd0316ada2a32bbf63304070295d683df6e3958a94"
    }
    for name, expected in prescribed.items():
        path = PREVIOUS / name
        require(sha(path) == expected, "Unexpected prior seed registry: " + name)
        prior_files[project_path(path)] = expected
        previous = load(path)
        seeds = registered_seeds(previous)
        require(len(seeds) == len(set(seeds)) == 2143, "Prior stream count mismatch")
        prior_sets[name + "/purpose"] = set(seeds)
        prior_sets[name + "/historical"] = {int(s) % MODULUS for s in previous["historical_audit"]["seeds"]}
    for profile in "ABC":
        path = PREVIOUS / "native/draft-before-lowbits" / f"pilot-{profile}.npz"
        with np.load(path, allow_pickle=False) as saved:
            seeds = set(map(int, saved["channel_seeds"])) | set(map(int, saved["factor_seeds"]))
        require(len(seeds) == 32, "Unexpected draft identifiers")
        prior_sets["draft-pilot-" + profile] = seeds
        prior_files[project_path(path)] = sha(path)
    union = set().union(*prior_sets.values())
    return {
        "scope": "Historical identifiers in the two hash-checked prior seed registries, all registered purpose streams, and archived draft pilot channel/offset identifiers. Prior historical audit scope is inherited. Duplicate identifiers are counted once. Identifier disjointness is not proof of disjoint pseudorandom trajectories.",
        "sources": prior_files,
        "counts_before_union": {name: len(values) for name, values in prior_sets.items()},
        "seeds": sorted(union),
        "seed_count": len(union)
    }


def stream(node, purpose):
    return dict(purpose=purpose, entropy=str(node.entropy), spawn_key=list(node.spawn_key),
                effective_seed=int(node.generate_state(1, dtype=np.uint32)[0]))


def make_streams(entropy):
    main, bootstrap = np.random.SeedSequence(entropy).spawn(2)
    profiles = []
    for block, block_node in enumerate(main.spawn(20)):
        for profile, node in zip("ABC", block_node.spawn(3)):
            channel, factor, init, search = node.spawn(4)
            profiles.append(dict(
                phase="main", block=block, profile=profile, spawn_key=list(node.spawn_key),
                channels=[stream(user, "channel") for user in channel.spawn(16)],
                factors=[stream(user, "large_scale_offset") for user in factor.spawn(16)],
                initialization=stream(init, "initialization"), search=stream(search, "stochastic_search")
            ))
    return dict(root_entropy=str(entropy), namespace_spawn_keys={"main": [0], "bootstrap": [1]},
                bootstrap=stream(bootstrap, "bootstrap"), profiles=profiles)


def channel_module():
    require(sha(DEPENDENCY) == OLD_GENERATOR, "Native channel source mismatch")
    spec = importlib.util.spec_from_file_location("frozen_native_cdl_channels", DEPENDENCY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BASE = BASE
    return module


def runtime_hashes(module):
    phy = Path(module.inspect.getfile(module.CDL)).parents[2]
    files = sorted(set(phy.rglob("*.py")) | set(phy.rglob("*.json")))
    return {p.relative_to(phy).as_posix(): sha(p) for p in files}


def bind_sources(module):
    return dict(generator_sha256=sha(DEPENDENCY), wrapper_sha256=sha(__file__),
                verifier_sha256=sha(VERIFIER), protocol_sha256=sha(PROTOCOL),
                project_sha256={project_path(p): sha(p) for p in (DEPENDENCY, Path(__file__), VERIFIER, PROTOCOL)},
                runtime_root="sionna.phy", runtime_sha256=runtime_hashes(module))


def prepare():
    require(not REGISTRY.exists(), "Seed ledger exists")
    assert_pristine_outputs()
    prior = exclusions()
    module = channel_module()
    streams = make_streams(secrets.randbits(128))
    effective = registered_seeds(streams)
    require(len(effective) == len(set(effective)) == 2041, "Fresh stream collision")
    require(not set(effective).intersection(prior["seeds"]), "Historical seed collision")
    previous = load(PREVIOUS / "seed_manifest.json")
    recorded_runtime = {p.replace("\\", "/").split("/sionna/phy/")[-1]: h
                        for p, h in previous["sources"]["runtime_sha256"].items()}
    sources = bind_sources(module)
    require(sources["runtime_sha256"] == recorded_runtime, "Runtime mismatch against frozen channel model")
    ledger = dict(schema="PRICED_HOLDOUT_NATIVE_CDL_SEEDS_V1",
                  created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **streams,
                  effective_seed_count=len(effective), historical_audit=prior, sources=sources,
                  environment=dict(python=sys.version, sionna=module.sionna.__version__, torch=module.torch.__version__,
                                   numpy=np.__version__, device="cpu", precision="double",
                                   torch_threads=module.torch.get_num_threads()), design=previous["design"])
    save(REGISTRY, ledger)
    print(f"Registered {len(effective)} unique identifiers, excluding {prior['seed_count']} prior identifiers", flush=True)


def assert_pristine_outputs():
    for name in ("native", "cases"):
        directory = BASE / name
        require(not directory.exists() or (directory.is_dir() and not any(directory.iterdir())),
                f"{name} must be absent or empty before generation")
    require(not (BASE / "generator_validation_main.json").exists(), "Generation receipt exists")


def generate():
    ledger = load(REGISTRY)
    assert_pristine_outputs()
    module = channel_module()
    require(bind_sources(module) == ledger["sources"], "Generator, verifier, protocol or runtime changed")
    for name in ("native", "cases"):
        (BASE / name).mkdir(exist_ok=True)
    start = time.monotonic()
    profiles = []
    for item in ledger["profiles"]:
        profiles.append(module.make_profile(item, ledger))
        print(f"b{item['block']:02d} CDL-{item['profile']} saved", flush=True)
    require(len(profiles) == 60 and sum(len(p["cases"]) for p in profiles) == 180, "Holdout coverage")
    save(BASE / "generator_validation_main.json",
         dict(status="PASS", phase="main", profile_count=60, case_count=180, profiles=profiles,
              generator_sha256=sha(DEPENDENCY), wrapper_sha256=sha(__file__), protocol_sha256=sha(PROTOCOL),
              seed_manifest_sha256=sha(REGISTRY), seconds=time.monotonic() - start))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "main"))
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    else:
        generate()
