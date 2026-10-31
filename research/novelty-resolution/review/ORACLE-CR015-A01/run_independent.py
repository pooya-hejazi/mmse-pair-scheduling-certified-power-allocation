import sys, subprocess, time, json
from pathlib import Path
D=Path(__file__).resolve().parent
start=time.perf_counter()
with (D/'independent.stdout.json').open('w',encoding='utf8') as out, (D/'independent.stderr.txt').open('w',encoding='utf8') as err:
    proc=subprocess.Popen([sys.executable,'-B',str(D/'independent_check.py')],stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    timed_out=False
    try: code=proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        timed_out=True;proc.kill();code=proc.wait(timeout=5)
result={'exit_code':code,'timed_out':timed_out,'limit_seconds':30,'elapsed_seconds':time.perf_counter()-start}
(D/'independent-execution.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
