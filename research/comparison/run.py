from pathlib import Path
import json,time,hashlib
from supervisor import run,atomic
R=Path(__file__).resolve().parent
assert json.loads((R/'checks.json').read_text())['result']=='PASS'
meta=json.loads((R/'inputs.json').read_text());start=time.perf_counter();rows=[]
files=['core.py','worker.py','supervisor.py','prepare.py','PROTOCOL.md','checks.py','inputs.json','run.py']
atomic(R/'run-manifest.json',{'files':{f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in files},'limit_total_seconds':1200,'scope':'prospective development run, no S04 confirmation'})
for item in meta:
 arms=['uniform','uniform_min','slsqp','iwmmse','cert_iwmmse','grid','lp'] if item['mode']=='power' else ['random','weakest','joint','uniform_probe','joint_cert','no_probe']
 if item.get('users')==64:arms=['grid','lp']
 for arm in arms:
  limit=20 if item['mode']=='power' else 5
  if time.perf_counter()-start+limit+5>1200:
   atomic(R/'results.json',{'status':'TOTAL_BUDGET_STOP','rows':rows,'elapsed':time.perf_counter()-start});raise SystemExit('Total packet budget reached; no extension')
  name=f"power-{item['users']}-{arm}" if item['mode']=='power' else f"info-{item['context']}-{item['sample']}-{arm}"
  record=run({'mode':item['mode'],'arm':arm,'input':item['input']},limit,name)
  rows.append({**item,'arm':arm,**record});atomic(R/'results.json',{'status':'IN_PROGRESS','rows':rows,'elapsed':time.perf_counter()-start})
  if record['status'] in ['FAILED','INVALID_OUTPUT']:raise RuntimeError('Implementation failure: '+name)
 print('DONE',item['mode'],item.get('users',str(item.get('context'))+'-'+str(item.get('sample'))),round(time.perf_counter()-start,2),flush=True)
atomic(R/'results.json',{'status':'COMPLETED','rows':rows,'elapsed':time.perf_counter()-start})
