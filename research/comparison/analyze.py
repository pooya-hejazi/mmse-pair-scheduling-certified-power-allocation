from pathlib import Path
import json,numpy as np,hashlib,collections
R=Path(__file__).resolve().parent;d=json.loads((R/'results.json').read_text());rows=d['rows']
manifest=json.loads((R/'run-manifest.json').read_text())
repair=json.loads((R/'storage-repair.json').read_text()) if (R/'storage-repair.json').exists() else None
for f,h in manifest['files'].items():
 if repair and f in repair['updated_hashes']:
  assert hashlib.sha256((R/f).read_bytes()).hexdigest()==repair['updated_hashes'][f]
  assert hashlib.sha256((R/'history'/f.replace('.py','-before-storage-fix.py')).read_bytes()).hexdigest()==h
 else:assert hashlib.sha256((R/f).read_bytes()).hexdigest()==h
def paired(ctx,a,b,key):
 aa={r['sample']:r for r in rows if r['mode']=='info' and r['context']==ctx and r['arm']==a}
 bb={r['sample']:r for r in rows if r['mode']=='info' and r['context']==ctx and r['arm']==b}
 valid=[i for i in aa.keys()&bb.keys() if aa[i]['status']==bb[i]['status']=='COMPLETED']
 diff=np.array([(aa[i]['wall_seconds']-bb[i]['wall_seconds']) if key=='wall_seconds' else aa[i]['result'][key]-bb[i]['result'][key] for i in sorted(valid)])
 if not len(diff):return {'N':0,'mean':None,'CI95':None}
 rng=np.random.default_rng(132000);boot=diff[rng.integers(0,len(diff),(2000,len(diff)))].mean(1)
 return {'N':len(diff),'mean':float(diff.mean()),'CI95':np.quantile(boot,[.025,.975]).tolist()}
contexts=[]
for ctx in range(4):
 rr=[r for r in rows if r['mode']=='info' and r['context']==ctx]
 if not rr:continue
 metrics={}
 for arm in ['random','weakest','joint','uniform_probe','joint_cert','no_probe']:
  a=[r for r in rr if r['arm']==arm and r['status']=='COMPLETED']
  metrics[arm]={'N':len(a),'actual_SE_mean':float(np.mean([r['result']['actual_bandwidth_SE'] for r in a])) if a else None,'power_W_mean':float(np.mean([r['result']['power_W'] for r in a])) if a else None,'wall_seconds_mean':float(np.mean([r['wall_seconds'] for r in a])) if a else None,'certificate_stop_count':sum(r['result']['certificate_stopped'] for r in a),'max_nominal_certificate_gap_fraction':max([(r['result']['upper_SE']-r['result']['nominal_SE'])/r['result']['upper_SE'] for r in a],default=None)}
 contrasts={a+'-'+b+'_'+key:paired(ctx,a,b,key) for a,b,key in [('joint','random','actual_bandwidth_SE'),('joint','weakest','actual_bandwidth_SE'),('joint_cert','joint','actual_bandwidth_SE'),('joint_cert','joint','wall_seconds'),('joint','no_probe','actual_bandwidth_SE')]}
 contexts.append({'context':ctx,'geometry':rr[0]['geometry'],'noise':rr[0]['noise'],'metrics':metrics,'paired':contrasts})
statuses=dict(collections.Counter(r['status'] for r in rows))
checks=[]
for r in rows:
 assert r['wall_seconds']<=r['limit_seconds']+1,'Parent watchdog exceeded one-second teardown margin'
 result=r['result']
 if result and 'p' in result:
  p=np.array(result['p']);n=len(p);assert min(p)>=.05-1e-8 and max(p)<=.2+1e-8 and p.sum()<=.1*n+1e-8
 if r['mode']=='info' and r['status']=='COMPLETED':
  assert result['pilot_symbols']==(4 if r['arm']=='no_probe' else 5)
  assert result['pilot_total_energy']==(16 if r['arm']=='no_probe' else 17)
  assert result['upper_SE']>=result['nominal_SE']-1e-7
  if result['certificate_stopped']:assert (result['upper_SE']-result['nominal_SE'])/result['upper_SE']<=.01+1e-8
out={'run_status':d['status'],'statuses':statuses,'contexts':contexts,'power_rows':[r for r in rows if r['mode']=='power'],'verification':'hashes, watchdog wall times, power feasibility, nominal certificate direction and information accounting passed','limits':'development networks, paired descriptive bootstrap, CSI certificates nominal only; uniform_probe is an idealized separately-observable-statistics reference, not demonstrated same-physical-pilot baseline'}
(R/'summary.json').write_text(json.dumps(out,indent=2));print(json.dumps({'run_status':d['status'],'statuses':statuses,'contrasts':[{k:c[k] for k in ['context','paired']} for c in contexts]},indent=2))
