"""Wall-clock guard for future isolated solver workers; historical runner is unchanged."""
from pathlib import Path
import subprocess,time,os,json,sys

def run_bounded(command,seconds,output_prefix):
    prefix=Path(output_prefix);prefix.parent.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter()
    with prefix.with_suffix('.stdout.txt').open('w',encoding='utf8') as out, prefix.with_suffix('.stderr.txt').open('w',encoding='utf8') as err:
        proc=subprocess.Popen(command,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        expired=False
        try:code=proc.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            expired=True;proc.kill();code=proc.wait(timeout=5)
    result={'status':'WALL_TIMEOUT' if expired else ('COMPLETED' if code==0 else 'FAILED'),'exit_code':code,'wall_seconds':time.perf_counter()-start,'limit_seconds':seconds,'command':command,'scope':'kills this directly launched worker; worker must not spawn child solver processes'}
    prefix.with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    return result

if __name__=='__main__':
    root=Path(__file__).resolve().parent/'watchdog-checks'
    ok=run_bounded([sys.executable,'-c','print(7)'],3,root/'success')
    fail=run_bounded([sys.executable,'-c','raise SystemExit(3)'],3,root/'failure')
    timeout=run_bounded([sys.executable,'-c','import time; time.sleep(5)'],.2,root/'timeout')
    assert ok['status']=='COMPLETED' and fail['status']=='FAILED' and timeout['status']=='WALL_TIMEOUT'
    assert timeout['wall_seconds']<3
    print(json.dumps({'result':'PASS','success_failure_timeout_distinguished':True,'timeout_seconds':timeout['wall_seconds'],'scope':'watchdog unit behavior only; not yet integrated into a new GPU/MILP benchmark'}))
