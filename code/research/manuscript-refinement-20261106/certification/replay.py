"""Separate all-case archived-input replay; no producer or optimizer import."""
from fractions import Fraction as F
import importlib.util
import json
import time
import traceback
import checker
from source_data import ARCHIVE, HERE, VENDOR, save, sha


def main():
    began = time.perf_counter()
    frozen = json.loads((HERE/'FROZEN.json').read_text())
    for name, expected in frozen['source_sha256'].items():
        checker.require(sha((HERE/name).read_bytes()) == expected, 'frozen source: '+name)
    final = HERE/'final'
    outputs = json.loads((final/'OUTPUT_MANIFEST.json').read_text())
    checker.require(outputs['freeze_sha256'] == sha((HERE/'FROZEN.json').read_bytes()), 'freeze hash')
    for name, expected in outputs['files'].items():
        checker.require(sha((final/name).read_bytes()) == expected, 'saved output hash: '+name)
    archived = checker.ArchivedInputs(ARCHIVE)
    manifest = json.loads((HERE/'INPUT_MANIFEST.json').read_text())
    spec = importlib.util.spec_from_file_location('frozen_checker_replay', VENDOR/'verify_upper.py')
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    checker.require(sha((VENDOR/'verify_upper.py').read_bytes()) == frozen['vendor_sha256']['verify_upper.py'], 'baseline checker hash')
    rows = json.loads((final/'rows.json').read_text())
    checker.require(len(rows) == 32 and len({r['name'] for r in rows}) == 32, 'missing/duplicate output rows')
    checker.require({r['name'] for r in rows} == {r['name'] for r in manifest['cases']}, 'population mismatch')
    row_by_name = {r['name']: r for r in rows}
    replay = []
    for source_row in manifest['cases']:
        name = source_row['name']
        folder = final/name
        result = dict(name=name, valid=False, errors=[])
        try:
            case, anchor, dual = archived.load(source_row['binding'])
            for method in ('new', 'baseline'):
                fallback = folder/f'{method}-retained-fallback.json'
                witness_path = fallback if fallback.exists() else folder/f'{method}-witness.json'
                witness = json.loads(witness_path.read_text())
                saved = json.loads((folder/f'{method}-checked.json').read_text())
                if method == 'new':
                    receipt = checker.verify(case, witness, anchor, source_row['binding'], dual, seconds=15.)
                    extra = ('anchor_lower_nats', 'anchor_upper_nats', 'proposed_lower_nats', 'proposed_upper_nats')
                else:
                    baseline.clear_caches()
                    receipt = baseline.verify(case, witness, seconds=15.)
                    extra = ()
                for field in ('lower_nats', 'upper_nats', 'gap_nats')+extra:
                    checker.require(F(receipt[field]) == F(saved[field]), f'{method} replay endpoint: '+field)
                for field in ('lower_nats', 'upper_nats', 'gap_nats'):
                    checker.require(F(receipt[field]) == F(row_by_name[name][method+'_'+field]), 'saved-row endpoint: '+field)
                checker.require(receipt['certificate_mathematical'] == saved['certificate_mathematical'], 'certificate flag')
                result[method+'_seconds'] = receipt['seconds']
                result[method+'_fallback'] = fallback.exists()
            # Recheck every archived comparison, including saved failures/timeouts.
            model = checker.reconstruct(case)
            histories = json.loads((folder/'historical-checks.json').read_text())
            for h in histories:
                if not h['valid_schedule']:
                    result['errors'].append('saved historical error: '+h['label'])
                    continue
                archive_zip = archived.inner if h['container'] == 'nested' else None
                if archive_zip is None:
                    import zipfile
                    archive_zip = zipfile.ZipFile(ARCHIVE)
                raw = archive_zip.read(h['member'])
                checker.require(sha(raw) == h['sha256'], 'historical archived bytes')
                if 'input_member' in h:
                    other_raw = archive_zip.read(h['input_member'])
                    checker.require(sha(other_raw) == h['input_sha256'], 'historical archived input')
                    other_case = json.loads(other_raw)
                    checker.require(other_case['channels_re'] == case['channels_re'] and
                                    other_case['channels_im'] == case['channels_im'] and
                                    checker.reconstruct(other_case) == model, 'historical model replay')
                schedule = json.loads(raw)['schedule']
                lower, upper = checker.check_schedule(schedule, model)
                checker.require(lower == F(h['checked_lower_nats']) and upper == F(h['checked_upper_nats']), 'historical replay rate')
            result['valid'] = not result['errors']
        except Exception as exc:
            result['errors'].append(type(exc).__name__+': '+str(exc))
            result['traceback'] = traceback.format_exc()
        replay.append(result)
    report = dict(valid=all(r['valid'] for r in replay) and len(replay) == 32, rows=replay,
                  cases=len(replay), errors=sum(bool(r['errors']) for r in replay), seconds=time.perf_counter()-began,
                  output_manifest_sha256=sha((final/'OUTPUT_MANIFEST.json').read_bytes()),
                  archive_outer_sha256=archived.outer_sha256, archive_nested_sha256=archived.nested_sha256)
    save(HERE/'replay-result.json', report)
    print(json.dumps({k: report[k] for k in ('valid', 'cases', 'errors', 'seconds')}))
    raise SystemExit(0 if report['valid'] else 1)


if __name__ == '__main__':
    main()
