"""Stdlib lease wrapper: reserve before launching scientific child imports."""
import time
START = time.monotonic()
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
LEDGER=ROOT/'MODERN_TEST_LEDGER.json'
lease=json.loads(LEDGER.read_text())
reservation=float(sys.argv[1]) if len(sys.argv)>1 else 35.0
used=sum(max(x['reserved_seconds'],x.get('actual_seconds',0)) for x in lease['executions'])
if used+reservation>lease['total_lease_seconds']:
    raise SystemExit('test lease exceeded; no child started')
number=len(lease['executions'])+1
entry=dict(id=number,stage='deterministic_correctness',reserved_seconds=reservation,status='RUNNING',
           started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           command=[sys.executable,'-B',str(ROOT/'test_modern.py')])
lease['executions'].append(entry)
LEDGER.write_text(json.dumps(lease,indent=2))
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
try:
    child=subprocess.run(entry['command'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=max(.1,reservation-(time.monotonic()-START)-1))
    entry.update(status='PASS' if child.returncode==0 else 'FAIL',returncode=child.returncode)
    (ROOT/f'test-results-{number:02d}.json').write_text(child.stdout)
    (ROOT/f'test-stderr-{number:02d}.txt').write_text(child.stderr)
except subprocess.TimeoutExpired as exc:
    entry.update(status='TIMEOUT',returncode=None)
    (ROOT/f'test-results-{number:02d}.json').write_text(json.dumps(dict(timeout=True,stdout=str(exc.stdout),stderr=str(exc.stderr))))
finally:
    entry['actual_seconds']=time.monotonic()-START
    entry['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    lease['accounted_seconds']=sum(max(x['reserved_seconds'],x.get('actual_seconds',0)) for x in lease['executions'])
    LEDGER.write_text(json.dumps(lease,indent=2))
print(json.dumps(entry))
sys.exit(0 if entry['status']=='PASS' else 1)
