from pathlib import Path
import sys,json,hashlib
R=Path(__file__).resolve().parents[2];D=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'research/gpu'))
from bounded_process import run_bounded
manifest={'files':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'CHECK_PROTOCOL.md',D/'candidate_oracle.py',D/'finite_checks.py',Path(__file__),R/'research/gpu/bounded_process.py']},'wall_seconds':45,'execution':1,'scope':'finite supporting checks; no channel/solver benchmark'}
p=D/'finite-manifest.json';assert not p.exists();p.write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps(run_bounded([sys.executable,str(D/'finite_checks.py')],45,D/'finite-execution'),indent=2))
