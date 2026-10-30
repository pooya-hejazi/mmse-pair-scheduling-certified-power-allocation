from pathlib import Path
import sys,json,time,hashlib
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'comparison'));from supervisor import atomic
sys.path.insert(0,str(R.parent/'gpu'));from bounded_process import run_bounded
prior=json.loads((R/'manifest.json').read_text());cases=prior['cases'];assert len(cases)==32
atomic(R/'frozen-manifest.json',{'files':{f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['FROZEN_RECEIVER_PROTOCOL.md','frozen_worker.py','frozen_run.py']},'cases':cases})
start=time.perf_counter();rows=[];(R/'frozen-runs').mkdir(exist_ok=True)
for c in cases:
 assert time.perf_counter()-start+11<300
 assert hashlib.sha256(Path(c['input']).read_bytes()).hexdigest()==c['sha256']
 base=R/'frozen-runs'/f"case-{c['context']}-{c['sample']}";job=base.with_suffix('.job.json');output=base.with_suffix('.result.json');assert not job.exists()
 atomic(job,{'input':c['input'],'output':str(output)})
 execution=run_bounded([sys.executable,str(R/'frozen_worker.py'),str(job)],5,base)
 result=json.loads(output.read_text()) if output.exists() else None
 rows.append({'context':c['context'],'sample':c['sample'],'execution':execution,'result':result});atomic(R/'frozen-results.json',{'status':'IN_PROGRESS','rows':rows,'elapsed':time.perf_counter()-start})
 if execution['status']=='FAILED':raise RuntimeError('Correctness failure')
 print('DONE',c['context'],c['sample'],flush=True)
atomic(R/'frozen-results.json',{'status':'COMPLETED','rows':rows,'elapsed':time.perf_counter()-start})
