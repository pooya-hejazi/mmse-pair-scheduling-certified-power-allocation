"""Resume only unexecuted jobs; recover a fully persisted status without rerunning it."""
from pathlib import Path
import json,time,hashlib
from supervisor import atomic,run
R=Path(__file__).resolve().parent;manifest=R/'run-manifest.json';started=manifest.stat().st_mtime
old=json.loads(manifest.read_text())
for f,h in old['files'].items():
 if f not in ['worker.py','supervisor.py']:assert hashlib.sha256((R/f).read_bytes()).hexdigest()==h
 else:assert hashlib.sha256((R/'history'/f.replace('.py','-before-storage-fix.py')).read_bytes()).hexdigest()==h
atomic(R/'storage-repair.json',{'reason':'Windows transient PermissionError replacing status file; completed solve preserved','no_decision_algorithm_changes':True,'prior_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'updated_hashes':{f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['supervisor.py','worker.py','resume.py']},'budget':'original20min elapsed wall since manifest creation; no restarted budget; no completed job repeated'})
rows=[]
for item in json.loads((R/'inputs.json').read_text()):
 arms=['uniform','uniform_min','slsqp','iwmmse','cert_iwmmse','grid','lp'] if item['mode']=='power' else ['random','weakest','joint','uniform_probe','joint_cert','no_probe']
 if item.get('users')==64:arms=['grid','lp']
 for arm in arms:
  name=f"power-{item['users']}-{arm}" if item['mode']=='power' else f"info-{item['context']}-{item['sample']}-{arm}"
  base=R/'runs'/name;status=base.with_suffix('.status.json');temp=base.with_suffix('.status.tmp')
  record=json.loads(status.read_text()) if status.exists() else None
  if record and record['status']=='RUNNING':
   assert temp.exists(),'Ambiguous worker outcome; refuse automatic repeat'
   recovered=json.loads(temp.read_text());assert recovered['status']=='COMPLETED' and recovered['result']['completed']
   assert recovered['pid']==record['pid'];atomic(status,recovered);record=recovered
  if record is None:
   limit=20 if item['mode']=='power' else 5
   if time.time()-started+limit+5>1200:
    atomic(R/'results.json',{'status':'TOTAL_BUDGET_STOP','rows':rows,'elapsed':time.time()-started});raise SystemExit('Original total budget exhausted')
   record=run({'mode':item['mode'],'arm':arm,'input':item['input']},limit,name)
  assert record['status'] not in ['FAILED','INVALID_OUTPUT','RUNNING']
  rows.append({**item,'arm':arm,**record});atomic(R/'results.json',{'status':'IN_PROGRESS','rows':rows,'elapsed':time.time()-started,'storage_recovery':True})
 print('RECONCILED',item['mode'],item.get('users',str(item.get('context'))+'-'+str(item.get('sample'))),round(time.time()-started,2),flush=True)
atomic(R/'results.json',{'status':'COMPLETED','rows':rows,'elapsed':time.time()-started,'storage_recovery':True})
