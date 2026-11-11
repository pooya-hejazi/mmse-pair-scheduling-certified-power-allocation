"""Development only: original O1-main-00, legacy reliability, nonorthogonal fixtures."""
from fractions import Fraction as F
import importlib.util
import sys
import time
import checker
import producer
from source_data import FrozenArchive, HERE, VENDOR, save
from tests import synthetic


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    archive = FrozenArchive()
    baseline = load_module('frozen_certificates_smoke', VENDOR/'certificates.py')
    baseline_checker = load_module('frozen_verify_smoke', VENDOR/'verify_upper.py')
    rows = []
    for name in ('o1-main-00', 'registered-reliability-fixture'):
        item = archive.load(name, 'original')
        archive.extract(item, 'original')
        candidate = producer.run(item['case'], item['grid']['schedule'], item['binding'], item['dual'], seconds=5.)
        checked = checker.verify(item['case'], candidate, item['grid']['schedule'], item['binding'], item['dual'], seconds=15.)
        save(HERE/'development'/name/'witness.json', candidate)
        save(HERE/'development'/name/'checked.json', checked)
        baseline.clear_caches()
        b = baseline.run(item['case'], 'grid_repair', initial=item['grid']['schedule'],
                         grid_duals=item['dual'], seconds=5.)
        baseline_checker.clear_caches()
        bc = baseline_checker.verify(item['case'], b, seconds=15.)
        save(HERE/'development'/name/'baseline-witness.json', b)
        save(HERE/'development'/name/'baseline-checked.json', bc)
        row = dict(name=name, new_gap=float(F(checked['gap_nats'])),
                   baseline_gap=float(F(bc['gap_nats'])), producer_seconds=candidate['metrics']['seconds'],
                   checker_seconds=checked['seconds'], status=candidate['metrics']['status'],
                   price_rows=checked['metrics']['price_rows'], splits=checked['metrics']['splits'])
        rows.append(row)
        print(row, flush=True)
    for k in (4, 8, 16):
        case, anchor = synthetic(k=k, seed=41)
        c = producer.run(case, anchor, {'synthetic': True}, seconds=5.)
        v = checker.verify(case, c, anchor, {'synthetic': True}, seconds=15.)
        save(HERE/'development'/case['name']/'witness.json', c)
        save(HERE/'development'/case['name']/'checked.json', v)
        row = dict(name=case['name'], gap=float(F(v['gap_nats'])), producer_seconds=c['metrics']['seconds'],
                   checker_seconds=v['seconds'], status=c['metrics']['status'], splits=v['metrics']['splits'])
        rows.append(row)
        print(row, flush=True)
    save(HERE/'development'/'smoke-summary.json', rows)


if __name__ == '__main__':
    main()
