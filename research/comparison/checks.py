from pathlib import Path
import json,numpy as np,itertools
from core import *
from supervisor import run
R=Path(__file__).resolve().parent
rng=np.random.default_rng(133000)
worst_drop=0
for geometry in ['random','aligned','orthogonal']:
 h=(rng.normal(size=(4,6,2))+1j*rng.normal(size=(4,6,2)))*3
 if geometry=='aligned':h[1]=h[0]*.8;h[3]=h[2]*1.1
 if geometry=='orthogonal':
  h[:]=0
  for u in range(4):h[u,u,:]=u+1
 sc=fixed_schedule(4);a=iwmmse(h,sc,.4);b=slsqp(h,sc,.4)
 assert min(np.diff(a['history']),default=0)>=-1e-8
 for r in [a,b]:
  assert r['p'].sum()<=.4+1e-8 and min(r['p'])>=LOW-1e-8 and max(r['p'])<=HIGH+1e-8
  assert r['nominal_SE']<=upper_bound(h,.4,sc)+1e-8
 if geometry=='orthogonal':assert abs(a['nominal_SE']-upper_bound(h,.4,sc))<1e-5
 for pair,s in sc:
  u,v=pair;p=a['p'];x=p[u]*np.vdot(h[u,:,s],h[u,:,s]).real;y=p[v]*np.vdot(h[v,:,s],h[v,:,s]).real
  c=p[u]*p[v]*abs(np.vdot(h[u,:,s],h[v,:,s]))**2
  closed=np.log2(1+x-c/(1+y))+np.log2(1+y-c/(1+x))
  _,per=evaluate(h,h,p,sc);assert abs(closed-per[list(pair)].sum())<1e-8
 small=R/'check_input.npz';np.savez(small,h=h)
# Full real worker success, error, malformed output and persisted checkpoint timeout.
ok=run({'mode':'power','arm':'iwmmse','input':str(small)},5,'check_success')
bad=run({'mode':'bad_mode','input':str(small)},5,'check_failure')
invalid=run({'mode':'invalid_probe'},5,'check_invalid')
timeout=run({'mode':'watchdog_probe'},2,'check_timeout')
assert ok['status']=='COMPLETED' and bad['status']=='FAILED' and invalid['status']=='INVALID_OUTPUT'
assert timeout['status']=='WALL_TIMEOUT' and timeout['wall_seconds']<3 and timeout['result']['stage']=='loaded_job'
out={'result':'PASS','WMMSE_monotonic_and_feasible':True,'orthogonal_waterfill_reference':True,'closed_form_vs_actual_receiver':True,'SLSQP_feasible':True,'continuous_bound_valid_on_checks':True,'supervisor_statuses':[ok['status'],bad['status'],invalid['status'],timeout['status']],'timeout_wall_seconds':timeout['wall_seconds'],'checkpoint_retained':True}
(R/'checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
