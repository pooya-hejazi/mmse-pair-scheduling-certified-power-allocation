from pathlib import Path
import sys,json,hashlib
R=Path(__file__).resolve().parents[2];D=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'research/gpu'));from bounded_process import run_bounded
files=[D/'NETWORK_PROTOCOL.md',D/'network_diagnostic.py',D/'rational_oracle.py',Path(__file__),R/'research/gpu/bounded_process.py',R/'research/comparison/inputs/power-8.npz',R/'research/comparison/inputs.json']
manifest={'files':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'wall_seconds':45,'executable':sys.executable,'scope':'one predeclared K8 development diagnostic'}
p=D/'network-manifest.json';assert not p.exists();p.write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps(run_bounded([sys.executable,str(D/'network_diagnostic.py')],45,D/'network-execution'),indent=2))
