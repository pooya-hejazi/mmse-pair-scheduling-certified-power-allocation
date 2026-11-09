"""Read-only frozen-archive access and byte-identical extraction into this study."""
from pathlib import Path
import hashlib
import io
import json
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARCHIVE = ROOT / 'output/TCOM-Submission-2026-11-06-R4/Supplementary_Materials.zip'
VENDOR = ROOT / 'output/TCOM-Submission-2026-11-06-R4/legacy-method/CR033/method/core/vendor'
NESTED = 'baseline_R1/Supplementary_Materials.zip'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, sort_keys=True, indent=2, allow_nan=False)+'\n', encoding='utf-8')


class FrozenArchive:
    def __init__(self, path=ARCHIVE):
        raw = Path(path).read_bytes()
        self.outer_hash = sha(raw)
        outer = zipfile.ZipFile(io.BytesIO(raw))
        self.outer = outer
        inner = outer.read(NESTED)
        self.inner_hash = sha(inner)
        self.zip = zipfile.ZipFile(io.BytesIO(inner))

    def load(self, name, population):
        scene = 'reliability' if name == 'registered-reliability-fixture' else name.split('-')[0]
        prefix = f'reproduction/studies/{population}'
        member = f'{prefix}/inputs/{scene}/{name}.json'
        grid_member = f'{prefix}/cells/{name}-grid/result.json'
        if name == 'registered-reliability-fixture':
            grid_member = f'{prefix}/cells/{name}-grid-repeat0/result.json'
        raw, grid_raw = self.zip.read(member), self.zip.read(grid_member)
        grid = json.loads(grid_raw)
        candidates = [n for n in self.zip.namelist()
                      if n.startswith(grid_member.rsplit('/', 1)[0]+'/candidate-') and n.endswith('.json')]
        dual_member, dual_raw, dual = None, None, None
        for n in sorted(candidates):
            b = self.zip.read(n)
            c = json.loads(b)
            if 'alpha' in c and 'lambda' in c:
                dual_member, dual_raw, dual = n, b, c
        binding = dict(outer_sha256=self.outer_hash, nested_sha256=self.inner_hash,
                       nested_member=NESTED, case_member=member, case_file_sha256=sha(raw),
                       grid_member=grid_member, grid_file_sha256=sha(grid_raw),
                       dual_member=dual_member, dual_file_sha256=sha(dual_raw) if dual_raw else None)
        return dict(case=json.loads(raw), grid=grid, dual=dual, binding=binding,
                    raw=raw, grid_raw=grid_raw, dual_raw=dual_raw)

    def extract(self, item, population):
        path = HERE / 'inputs' / population / item['case']['name']
        path.mkdir(parents=True, exist_ok=True)
        (path/'case.json').write_bytes(item['raw'])
        (path/'grid-result.json').write_bytes(item['grid_raw'])
        if item['dual_raw'] is not None:
            (path/'grid-duals.json').write_bytes(item['dual_raw'])
        save(path/'binding.json', item['binding'])


def population_names():
    return [f'{scene}-{panel}-{i:02d}' for scene in ('asu', 'o1')
            for panel, n in (('main', 12), ('scale', 4)) for i in range(n)]
