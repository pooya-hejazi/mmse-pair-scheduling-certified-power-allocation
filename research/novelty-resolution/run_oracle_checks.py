from pathlib import Path
import sys,json,hashlib
R=Path(__file__).resolve().parents[2];D=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'research/gpu'));from bounded_process import run_bounded
files=[D/'ORACLE_PROTOCOL.md',D/'rational_oracle.py',D/'oracle_checks.py',Path(__file__),R/'research/gpu/bounded_process.py']
manifest={'files':{p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'wall_seconds':45,'executable':sys.executable,'scope':'rational isolated pair oracle only'}
p=D/'oracle-manifest.json';assert not p.exists();p.write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps(run_bounded([sys.executable,str(D/'oracle_checks.py')],45,D/'oracle-execution'),indent=2))
