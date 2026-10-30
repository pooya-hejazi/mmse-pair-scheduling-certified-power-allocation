"""Persisted, externally enforced wall-clock jobs; at most one worker at a time."""
from pathlib import Path
import sys,json,time,subprocess,os
R=Path(__file__).resolve().parent
def atomic(p,d):
    q=p.with_suffix('.tmp');q.write_text(json.dumps(d,indent=2));q.replace(p)
def run(job,limit,name):
    base=R/'runs'/name;base.parent.mkdir(parents=True,exist_ok=True)
    output=base.with_suffix('.result.json');jobpath=base.with_suffix('.job.json')
    if jobpath.exists():raise FileExistsError('Refuse to overwrite prior run: '+str(jobpath))
    job={**job,'output':str(output)};atomic(jobpath,job)
    start=time.perf_counter()
    with base.with_suffix('.log').open('w') as stream:
        process=subprocess.Popen([sys.executable,str(R/'worker.py'),str(jobpath)],stdout=stream,stderr=stream,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        atomic(base.with_suffix('.status.json'),{'status':'RUNNING','pid':process.pid,'limit_seconds':limit})
        try:code=process.wait(timeout=limit);status='COMPLETED' if code==0 else 'FAILED'
        except subprocess.TimeoutExpired:process.kill();code=process.wait(timeout=5);status='WALL_TIMEOUT'
    elapsed=time.perf_counter()-start
    result=None
    if output.exists():
        try:result=json.loads(output.read_text())
        except (ValueError,OSError):status='INVALID_OUTPUT'
    if status=='COMPLETED' and (not result or not result.get('completed')):status='INVALID_OUTPUT'
    record={'status':status,'exit_code':code,'wall_seconds':elapsed,'limit_seconds':limit,'result':result,'pid':process.pid}
    atomic(base.with_suffix('.status.json'),record)
    return record
