from pathlib import Path
import sys,json,hashlib
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'gpu'));from bounded_process import run_bounded
assert not (R/'cut-manifest.json').exists()
files=[R/'CUT_PROTOCOL.md',R/'cut_worker.py',R/'cut_run.py',R.parent/'comparison/supervisor.py',R.parent/'gpu/bounded_process.py',R.parent/'structure/solver-results.json']
(R/'cut-manifest.json').write_text(json.dumps({'files':{str(p.relative_to(R.parent.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'executable':sys.executable,'wall_limit_seconds':180},indent=2))
print(json.dumps(run_bounded([sys.executable,str(R/'cut_worker.py')],180,R/'cut-execution'),indent=2))
