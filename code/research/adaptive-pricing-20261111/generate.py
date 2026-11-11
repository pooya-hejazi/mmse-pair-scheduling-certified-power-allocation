"""Generate or verify the adaptive-pricing holdout; reconstruct its compact cases."""
import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import secrets
import shutil
import sys
import tempfile
import time
from functools import cache
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
PRICED = HERE.parent / 'priced-assignment-20261111'
REGISTRY = HERE / 'seed_manifest.json'
RECEIPT = HERE / 'input_check.json'
INPUTS = HERE / 'inputs'
CONVERTER = HERE.parent / 'dual-track-revision-20261103/method/core/vendor/generate_cases.py'
PRICED_LEDGER_HASH = '62cfeb039830058910dc35b7727c0229c0a77a20283984fb4919a505ed14dc45'
CONVERTER_HASH = '5fdca9e84b1a27f49b065a18004c74fabb6c24f4f61c93933c6bd1cda880ae9b'
SNRS = (0, 10, 20)


def require(test, message):
    if not test:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    with path.open('xb') as out:
        out.write(case_bytes(value) + b'\n')


def case_bytes(case):
    return json.dumps(case, indent=2, allow_nan=False).encode('utf-8')


@cache
def module(path):
    spec = importlib.util.spec_from_file_location('adaptive_inputs_' + path.stem, path)
    imported = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported)
    return imported


def sources_and_exclusions():
    old_path = PRICED / 'seed_manifest.json'
    require(sha(old_path) == PRICED_LEDGER_HASH, 'Previous priced seed ledger changed')
    previous = read(old_path)
    sources = {**previous['sources']['project_sha256'],
               old_path.relative_to(PROJECT).as_posix(): PRICED_LEDGER_HASH,
               CONVERTER.relative_to(PROJECT).as_posix(): CONVERTER_HASH}
    for path, expected in sources.items():
        require(sha(PROJECT / path) == expected, 'Frozen source mismatch: ' + path)
    for path in (Path(__file__).resolve(), HERE / 'GENERATOR.md'):
        sources[path.relative_to(PROJECT).as_posix()] = sha(path)
    old = module(PRICED / 'generate_holdout.py')
    historical = old.exclusions()
    require(historical == previous['historical_audit'] and historical['seed_count'] == 4063,
            'Previous historical and pilot exclusions changed')
    priced = set(old.registered_seeds(previous))
    excluded = priced.union(historical['seeds'])
    require(len(priced) == 2041 and len(excluded) == 6104, 'Unexpected priced seed overlap')
    return previous, old, sources, dict(seed_count=len(excluded), seeds=sorted(excluded),
        inherited_historical_count=4063, previous_priced_count=2041, new_pilot_count=0,
        sources={**historical['sources'], old_path.relative_to(PROJECT).as_posix(): PRICED_LEDGER_HASH})


def channel_engine(previous):
    engine = module(PRICED / 'verify_holdout.py').original_link_module(previous)
    actual = dict(python=sys.version, numpy=np.__version__, sionna=engine.sionna.__version__,
                  torch=engine.torch.__version__, device=engine.config.device,
                  precision=engine.config.precision, torch_threads=engine.torch.get_num_threads())
    require(actual == previous['environment'], 'Pinned generation environment mismatch: ' + str(actual))
    return engine


def check_streams(ledger, old, excluded):
    reconstructed = old.make_streams(int(ledger['root_entropy']))
    require(all(ledger[k] == value for k, value in reconstructed.items()), 'Seed lineage changed')
    seeds = old.registered_seeds(ledger)
    require(len(seeds) == len(set(seeds)) == 2041, 'Effective seed collision')
    require(set(seeds).isdisjoint(excluded['seeds']), 'Effective seed is already registered')


def prepare():
    require(not any(p.exists() for p in (REGISTRY, INPUTS, RECEIPT)), 'Holdout inputs already registered')
    previous, old, sources, excluded = sources_and_exclusions()
    channel_engine(previous)
    streams = old.make_streams(secrets.randbits(128))
    check_streams(streams, old, excluded)
    ledger = dict(schema='ADAPTIVE_PRICING_NATIVE_CDL_SEEDS_V1',
        created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **streams,
        effective_seed_count=2041, historical_audit=excluded, design=previous['design'],
        environment=previous['environment'], sources=dict(project_sha256=sources,
            generator_sha256=previous['sources']['generator_sha256'], protocol_sha256=sha(HERE / 'GENERATOR.md'),
            runtime_root='sionna.phy', runtime_sha256=previous['sources']['runtime_sha256']))
    save(REGISTRY, ledger)
    print(f'Registered 2,041 effective identifiers after excluding 6,104. Ledger SHA-256 {sha(REGISTRY)}')


def verified_ledger():
    ledger = read(REGISTRY)
    previous, old, sources, excluded = sources_and_exclusions()
    check_streams(ledger, old, excluded)
    require(ledger['effective_seed_count'] == 2041 and ledger['historical_audit'] == excluded and
            ledger['sources']['project_sha256'] == sources and ledger['design'] == previous['design'] and
            ledger['environment'] == previous['environment'] and
            ledger['sources']['runtime_sha256'] == previous['sources']['runtime_sha256'] and
            ledger['sources']['generator_sha256'] == previous['sources']['generator_sha256'] and
            ledger['sources']['protocol_sha256'] == sha(HERE / 'GENERATOR.md'), 'Ledger source or design mismatch')
    return ledger


@cache
def catalog(inputs):
    return json.loads(gzip.decompress((inputs / 'catalog.json.gz').read_bytes()))


def restore_case(descriptor, native):
    case = copy.deepcopy(descriptor)
    meta = case.pop('metadata')
    scaled = native * np.asarray(meta['nominal_perantenna_scale'])[:, None, None]
    converted = module(CONVERTER).convert(scaled, case['name'], meta)
    for field in ('pairs', 'channels_re', 'channels_im', 'metadata'):
        case[field] = converted[field]
    return case


def load_case(name):
    """Load a complete case by its registered name using NumPy and the archived project."""
    descriptor = catalog(INPUTS)[name]
    with np.load(INPUTS / (name.rsplit('-snr', 1)[0] + '.npz'), allow_pickle=False) as raw:
        return restore_case(descriptor, raw['native_h'])


def same_bits(left, right):
    return left.dtype == right.dtype and left.shape == right.shape and left.tobytes() == right.tobytes()


def audit(ledger, inputs, profiles, case_hashes, regenerate):
    verifier = module(PRICED / 'verify_holdout.py')
    engine = channel_engine(ledger) if regenerate else None
    data = catalog(inputs)
    require(set(data) == set(case_hashes), 'Unexpected case catalog entries')
    require({p.name for p in inputs.iterdir()} == {'catalog.json.gz', *(Path(p).name for p in profiles)},
            'Unexpected native input inventory')
    cases = links = coefficient_rows = native_populations = 0
    max_fourier = 0.
    manifest_hash = sha(REGISTRY)
    for item in ledger['profiles']:
        b, profile = item['block'], item['profile']
        tag = f'native-b{b:02d}-{profile}'
        path = inputs / (tag + '.npz')
        relative = 'inputs/' + path.name
        native_hash = sha(path)
        require(profiles.get(relative) == native_hash, 'Native archive hash mismatch: ' + tag)
        with np.load(path, allow_pickle=False) as record:
            raw = {key: record[key] for key in record.files}
        cs = [r['effective_seed'] for r in item['channels']]
        fs = [r['effective_seed'] for r in item['factors']]
        a, tau, h = raw['cir'], raw['delays_s'], raw['native_h']
        paths = {'A': 23, 'B': 23, 'C': 24}[profile]
        require(a.shape == (16, 2, paths) and tau.shape == (16, paths) and h.shape == (16, 2, 8) and
                a.dtype == h.dtype == np.complex128 and tau.dtype == np.float64 and
                all(np.isfinite(v).all() for v in (a, tau, h)), 'Native shape, precision or finiteness: ' + tag)
        offsets = np.array([np.random.default_rng(seed).uniform(-6., 6.) for seed in fs])
        require(np.array_equal(raw['channel_seeds'], cs) and np.array_equal(raw['factor_seeds'], fs) and
                same_bits(raw['offset_db'], offsets), 'Native streams or offsets mismatch: ' + tag)
        expected_bs = np.zeros((2, 3))
        expected_bs[:, 1] = np.array([-.25, .25]) * (299792458 / 3.5e9)
        require(np.array_equal(raw['bs_orientation_rad'], [0., 0., 0.]) and
                np.array_equal(raw['ut_orientation_rad'], [np.pi, 0., 0.]) and
                np.array_equal(raw['ut_ant_pos_m'], np.zeros((1, 3))) and
                np.allclose(raw['bs_ant_pos_m'], expected_bs, rtol=0, atol=1e-14) and
                np.array_equal(raw['frequency_hz'], verifier.FREQ), 'Array geometry or tone grid mismatch: ' + tag)
        direct = np.stack([(a * np.exp((-2j * np.pi * f) * tau[:, None, :])).sum(axis=2)
                           for f in verifier.FREQ], axis=-1)
        error = float(np.max(abs(direct - h)))
        require(error < 1e-11 and np.all(np.ptp(np.sum(abs(h)**2, axis=1), axis=1) > 1e-8),
                'Native Fourier or frequency variation mismatch: ' + tag)
        max_fourier = max(max_fourier, error)
        if engine is not None:
            ut, bs = engine.arrays()
            for u, seed in enumerate(cs):
                replay = engine.link(profile, seed, ut, bs)
                require(all(same_bits(x, y) for x, y in zip(replay, (a[u], tau[u], h[u]))),
                        f'Native user link differs: {tag} {u}')
                links += 1
        for snr in SNRS:
            name = f'{tag}-snr{snr:02d}'
            case = restore_case(data[name], h)
            meta = case['metadata']
            require(digest(case_bytes(case)) == case_hashes[name], 'Expanded case SHA-256 mismatch: ' + name)
            require((case['name'], case['K'], case['S'], case['M'], case['pmin'], case['pmax'], case['budget'])
                    == (name, 16, 8, 2, '1/1000', '1/5', '52/25'), 'Case header mismatch: ' + name)
            require((meta['block'], meta['profile'], meta['snr_db'], meta['pilot'], meta['normalize'])
                    == (b, profile, snr, False, False) and meta['native_path'] == relative and
                    meta['native_sha256'] == native_hash and meta['seed_manifest_sha256'] == manifest_hash and
                    meta['protocol_sha256'] == ledger['sources']['protocol_sha256'] and
                    meta['generator_sha256'] == ledger['sources']['generator_sha256'] and
                    meta['initialization_seed'] == item['initialization']['effective_seed'] and
                    meta['search_seed'] == item['search']['effective_seed'] and
                    meta['channel_seeds'] == cs and meta['factor_seeds'] == fs and
                    np.array_equal(meta['offset_db'], offsets) and np.array_equal(meta['frequency_hz'], verifier.FREQ),
                    'Case metadata mismatch: ' + name)
            scale = np.asarray(meta['nominal_perantenna_scale'])
            expected = np.sqrt(np.power(10., (snr + offsets) / 10.) / .1)
            require(np.allclose(scale, expected, rtol=1e-15, atol=0) and
                    (engine is None or same_bits(scale, expected)), 'Case scaling mismatch: ' + name)
            scaled = h * scale[:, None, None]
            require(same_bits(scaled.real, np.asarray(case['channels_re'])) and
                    same_bits(scaled.imag, np.asarray(case['channels_im'])), 'Scaled channel mismatch: ' + name)
            verifier.check_pair_rows(case, scaled)
            cases += 1
            coefficient_rows += len(case['pairs'])
        native_populations += 1
    require(cases == len(case_hashes) == 180 and native_populations == len(profiles) == 60 and
            coefficient_rows == 172800 and links == (960 if regenerate else 0), 'Incomplete input verification')
    return dict(status='PASS', profile_count=native_populations, case_count=cases, native_links=960,
                regenerated_links_bitwise_equal=links, coefficients_checked=coefficient_rows,
                exact_scaled_cases=cases, max_fourier_abs_error=max_fourier, effective_seed_count=2041,
                excluded_historical_id_count=6104, historical_collisions=0, new_pilot_count=0)


def generate():
    ledger = verified_ledger()
    if RECEIPT.exists():
        return verify(True)
    engine = channel_engine(ledger)
    with tempfile.TemporaryDirectory(dir=HERE, prefix='.generating-') as scratch:
        stage = Path(scratch)
        packed = stage / 'inputs'
        for path in (stage / 'native', stage / 'cases', packed):
            path.mkdir()
        shutil.copyfile(REGISTRY, stage / REGISTRY.name)
        engine.BASE = stage
        descriptors, cases, profiles = {}, {}, {}
        for item in ledger['profiles']:
            row = engine.make_profile(item, ledger)
            original = stage / row['native_path']
            relative = 'inputs/' + original.name
            profiles[relative] = row['native_sha256']
            original.rename(packed / original.name)
            for entry in row['cases']:
                expanded = stage / entry['case_path']
                require(sha(expanded) == entry['case_sha256'], 'Direct generator case changed')
                case = read(expanded)
                case['metadata']['native_path'] = relative
                name = case['name']
                cases[name] = digest(case_bytes(case))
                descriptors[name] = {k: v for k, v in case.items() if k not in ('pairs', 'channels_re', 'channels_im')}
        packed_catalog = packed / 'catalog.json.gz'
        packed_catalog.write_bytes(gzip.compress(case_bytes(descriptors), mtime=0))
        checks = audit(ledger, packed, profiles, cases, regenerate=True)
        receipt = dict(**checks, seed_manifest_sha256=sha(REGISTRY), generator_sha256=sha(Path(__file__)),
                       catalog_sha256=sha(packed_catalog), profiles=profiles, cases=cases)
        if INPUTS.exists():
            require({p.name: sha(p) for p in INPUTS.iterdir()} == {p.name: sha(p) for p in packed.iterdir()},
                    'Interrupted output differs from regenerated inputs')
        else:
            packed.rename(INPUTS)
        save(RECEIPT, receipt)
        return checks


def verify(regenerate):
    ledger, receipt = verified_ledger(), read(RECEIPT)
    require(receipt['status'] == 'PASS' and receipt['seed_manifest_sha256'] == sha(REGISTRY) and
            receipt['generator_sha256'] == sha(Path(__file__)) and receipt['catalog_sha256'] == sha(INPUTS / 'catalog.json.gz'),
            'Input receipt provenance mismatch')
    checks = audit(ledger, INPUTS, receipt['profiles'], receipt['cases'], regenerate)
    require(all(receipt[k] == v for k, v in checks.items() if k not in ('regenerated_links_bitwise_equal', 'max_fourier_abs_error'))
            and receipt['regenerated_links_bitwise_equal'] == 960 and receipt['max_fourier_abs_error'] < 1e-11,
            'Input receipt coverage mismatch')
    return checks


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'generate', 'verify'))
    parser.add_argument('--regenerate-links', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    else:
        result = generate() if args.action == 'generate' else verify(args.regenerate_links)
        print(json.dumps(result, indent=2))
