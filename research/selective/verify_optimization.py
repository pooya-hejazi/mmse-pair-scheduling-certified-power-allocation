"""Independent formulations for the small exact hull, numerical physical witness, and budget replay."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import json,itertools,hashlib
import numpy as np
from scipy.optimize import linprog,milp,Bounds,LinearConstraint
import experiment as e
R=Path(__file__).resolve().parent
def strengthened(q):
    cuts=np.zeros((6,12))
    for j,g in enumerate(e.GROUPS):
        comp=tuple(u for u in range(4) if u not in g)
        cuts[j,e.COLS.index((g,0))]=1;cuts[j,e.COLS.index((comp,1))]=-1
    A=np.vstack([e.MAT,cuts]);b=np.r_[np.ones(6),np.zeros(6)]
    lp=linprog(-q,A_eq=A,b_eq=b,bounds=(0,1),method='highs');assert lp.success
    return float(-lp.fun),lp.x
def check(q):
    enum=float((e.VERT@q).max())
    ip=milp(-q,integrality=np.ones(12),bounds=Bounds(0,1),constraints=LinearConstraint(e.MAT,np.ones(6),np.ones(6)),options={'mip_rel_gap':0,'time_limit':5})
    assert ip.status==0 and ip.x is not None
    strong,x= strengthened(q)
    assert np.allclose([-ip.fun,strong],enum,atol=1e-7)
    assert np.max(abs(x-np.rint(x)))<1e-7
    return enum,strong
report={'random_objectives_checked':100,'scope':'author checks, not independent stage audit'}
rng=np.random.default_rng(4321)
for _ in range(100):check(rng.normal(size=12))
head=json.loads((R/'headroom-results.json').read_text());w=head['max_gap_witness']
h=np.array(w['H_est_real'])+1j*np.array(w['H_est_imag']);e.NOISE=w['noise'];q=e.column_scores(h.reshape(4,-1,2))
assert np.allclose(q,w['q'])
ip,strong=check(q);fraction=np.array(w['lp_x']);assert np.max(abs(e.MAT@fraction-1))<1e-8
assert q@fraction-ip>0.4
report['physical_witness']={'noise':w['noise'],'ant':w['ant'],'geometry':w['geometry'],'ids':w['ids'],'ILP':ip,'ordinary_LP':w['LP'],'strengthened_LP':strong,'gap':w['gap'],'fractional_x':w['lp_x']}
proto=json.loads((R/'prototype-results.json').read_text())
for r in proto['rows']:
    for method,u in r['probe_selection'].items():
        assert 0<=u<4
        assert r['policy_actual'][method]==r['after_probe_actual'][u]
    assert r['nominal_LP']>=r['nominal_ILP']-1e-7
    assert r['joint_post_LP']>=r['joint_post_ILP']-1e-7
    for j,m in enumerate(['decision_only','receiver_only','joint']):assert r['probe_selection'][m]==int(np.argmax(r['predictive_scores'][j]))
report['prototype_rows_replayed']=len(proto['rows']);report['policy_outcomes_replayed']=6*len(proto['rows'])
manifest=json.loads((R.parent/'reproduction/run-manifest.json').read_text())
for f in manifest['files']:assert hashlib.sha256((R.parents[1]/f['path']).read_bytes()).hexdigest()==f['sha256']
report['S02_unchanged']=True
# Verify the fixed estimator's update from both sufficient statistics and covariance form.
_,_,_,mean,ev,U=e.load_data(2);noise=1.;C=(U*ev)@U.conj().T
F4=(U*(ev/(ev+noise/4)))@U.conj().T;F5=(U*(ev/(ev+noise/5)))@U.conj().T
K=(U*(ev/(5*ev+noise)))@U.conj().T
ls=e.complex_noise(rng,(4,len(ev)));y=e.complex_noise(rng,ls.shape);m=(ls-mean)@F4.T+mean
update=m+(y-m)@K.T;direct=((4*ls+y)/5-mean)@F5.T+mean
assert np.allclose(update,direct,atol=1e-8)
report['LMMSE_update_equals_five_energy_sufficient_statistic']=True
def additive_check(h,noise):
    e.NOISE=noise;q=e.column_scores(h);single=.5*np.log2(1+np.sum(abs(h)**2,axis=1)/noise)
    loss=[]
    for (u,v),s in e.COLS:
        aa=np.vdot(h[u,:,s],h[u,:,s]).real;bb=np.vdot(h[v,:,s],h[v,:,s]).real
        k=abs(np.vdot(h[u,:,s],h[v,:,s]))**2/((noise+aa)*(noise+bb))
        loss.append(-np.log2(1-k))
    additive=np.array([single[list(g),s].sum() for g,s in e.COLS]);loss=np.array(loss)
    assert np.allclose(additive-q,loss,atol=1e-8)
    score=e.VERT@q;add=e.VERT@additive;chosen=int(add.argmax());B=max(loss[:6])+max(loss[6:])
    low,up,_,_=e.solve(q)
    assert up-low<=B+1e-8 and low-score[chosen]<=B+1e-8
    return float(B),float(up-low)
for _ in range(100):additive_check(e.complex_noise(rng,(4,8,2)),.3)
orth=np.zeros((4,4,2),complex)
for u in range(4):orth[u,u,:]=u+1
B,gap=additive_check(orth,.3);assert B<1e-10 and abs(gap)<1e-8
report['pair_loss_identity_and_additive_bound_checks']=100
report['orthogonal_channels_exact_objective']=True
(R/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
