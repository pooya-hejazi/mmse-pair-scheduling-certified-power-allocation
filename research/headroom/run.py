from pathlib import Path
import sys,json,time,hashlib
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'gpu'))
from bounded_process import run_bounded
sys.path.insert(0,str(R.parent/'comparison'));from supervisor import atomic
src=R.parent/'comparison/results.json';original=json.loads(src.read_text());assert original['status']=='COMPLETED'
cases=[r for r in original['rows'] if r['mode']=='info' and r['arm']=='no_probe'];assert len(cases)==32
atomic(R/'manifest.json',{'source_results_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'files':{f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['PROTOCOL.md','worker.py','run.py']},'cases':[{'context':c['context'],'sample':c['sample'],'ids':c['ids'],'input':c['input'],'sha256':hashlib.sha256(Path(c['input']).read_bytes()).hexdigest()} for c in cases]})
start=time.perf_counter();rows=[];(R/'runs').mkdir(exist_ok=True)
for c in cases:
 if time.perf_counter()-start+11>600:raise RuntimeError('10minute total budget stop')
 base=R/'runs'/f"case-{c['context']}-{c['sample']}";job=base.with_suffix('.job.json');output=base.with_suffix('.result.json')
 assert not job.exists(),'No automatic rerun'
 atomic(job,{'input':c['input'],'output':str(output),'continuous_baseline':c['result']})
 execution=run_bounded([sys.executable,str(R/'worker.py'),str(job)],10,base)
 result=json.loads(output.read_text()) if output.exists() else None
 rows.append({'context':c['context'],'sample':c['sample'],'geometry':c['geometry'],'noise':c['noise'],'execution':execution,'result':result})
 atomic(R/'results.json',{'status':'IN_PROGRESS','rows':rows,'elapsed':time.perf_counter()-start})
 if execution['status']=='FAILED':raise RuntimeError('Correctness failure: '+str(base))
 print('DONE',c['context'],c['sample'],round(time.perf_counter()-start,2),flush=True)
atomic(R/'results.json',{'status':'COMPLETED','rows':rows,'elapsed':time.perf_counter()-start})
