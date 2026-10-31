from pathlib import Path
import sys,json,hashlib
R=Path(__file__).resolve().parent;root=R.parents[1];sys.path.insert(0,str(root/'research/gpu'));from bounded_process import run_bounded
assert not (R/'bound-manifest.json').exists()
names=['research/novelty-oct31/'+n for n in ['BOUND_PROTOCOL.md','GRID_CONTINUOUS_BOUND.md','bound_check.py','run_bound_check.py']]+['research/comparison/results.json','research/comparison/inputs.json','research/gpu/bounded_process.py']+['research/comparison/inputs/power-'+str(n)+'.npz' for n in [8,16,32]]
(R/'bound-manifest.json').write_text(json.dumps({'files':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},'wall_seconds':30,'executable':sys.executable,'scope':'no optimizer runs'},indent=2))
print(json.dumps(run_bounded([sys.executable,str(R/'bound_check.py')],30,R/'bound-execution'),indent=2))
