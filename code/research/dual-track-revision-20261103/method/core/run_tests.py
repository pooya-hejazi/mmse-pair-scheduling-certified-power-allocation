"""Reserve-before-execute core test runner; counts startup, imports and failed attempts."""
import argparse,json,time,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--reserve',type=float,required=True);p.add_argument('script');a=p.parse_args()
root=Path(__file__).resolve().parent;ledger=root/'CORE_TEST_LEDGER.json';data=json.loads(ledger.read_text())
used=sum(max(x['reserved_seconds'],x.get('actual_seconds',0)) for x in data['entries'])
if used+a.reserve>data['cap_seconds']:raise SystemExit('CORE260s reservation refused')
entry=dict(index=len(data['entries']),script=a.script,reserved_seconds=a.reserve,status='reserved',started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
data['entries'].append(entry);ledger.write_text(json.dumps(data,indent=2),encoding='utf-8')
start=time.monotonic();log=root/('test-execution-%02d.log'%entry['index'])
with log.open('w',encoding='utf-8') as f:
    child=subprocess.Popen([sys.executable,'-B',str(root/a.script)],cwd=root,stdout=f,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:code=child.wait(timeout=max(.01,a.reserve-.5));status='passed' if code==0 else 'failed'
    except subprocess.TimeoutExpired:
        child.kill();child.wait();code=child.returncode;status='timeout'
entry.update(actual_seconds=time.monotonic()-start,returncode=code,status=status,log=log.name)
ledger.write_text(json.dumps(data,indent=2),encoding='utf-8');print(json.dumps(entry));print(log.read_text(encoding='utf-8')[-14000:])
raise SystemExit(0 if status=='passed' else 1)
