"""Fixed-estimator, one-probe joint allocation study. No estimator training/tuning."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
from pathlib import Path
import sys,json,time,itertools,argparse
import numpy as np
from scipy.optimize import linprog,milp,Bounds,LinearConstraint
R=Path(__file__).resolve().parent;D=R.parent/'reproduction'
sys.path.insert(0,str(R.parent/'innovation'));from pilot_value import rewards,rate,A as ACTIONS
GROUPS=list(itertools.combinations(range(4),2));COLS=[(g,s) for s in range(2) for g in GROUPS]
MAT=np.zeros((6,12))
for j,(g,s) in enumerate(COLS):MAT[list(g),j]=1;MAT[4+s,j]=1
VERT=np.zeros((6,12))
for a,(g,h) in enumerate(ACTIONS):VERT[a,COLS.index((g,0))]=1;VERT[a,COLS.index((h,1))]=1
def column_scores(h):return np.array([rate(h,h,g,s,NOISE) for g,s in COLS])
def solve(q):
    values=VERT@q;ix=int(values.argmax());lower=float(values[ix])
    lp=linprog(-q,A_eq=MAT,b_eq=np.ones(6),bounds=(0,1),method='highs')
    assert lp.success
    assert -lp.fun>=lower-1e-7 and np.max(abs(MAT@lp.x-1))<1e-7
    return lower,float(-lp.fun),lp.x,ix
def load_data(ant):
    raw=np.load(D/'channels.npz');H=raw['H'][:,:,:ant,:].reshape(len(raw['H']),-1)/float(np.load(D/'normalization.npz')['train_rms'])
    splits=np.load(D/'split-indices.npz');train=H[splits['train']].reshape(-1,H.shape[1]);mean=train.mean(0);z=train-mean
    C=z.T@z.conj()/len(z);w,U=np.linalg.eigh(C);w=np.maximum(w,0)
    order=np.lexsort((raw['location'][:,0],raw['location'][:,1]));pool=order[int(.55*len(H)):int(.68*len(H))]
    assert not set(pool)&set(splits['test'].ravel()) and not set(pool)&set(splits['train'].ravel())
    return H,raw['location'],pool,mean,w,U
def ids_for(pool,loc,geometry,rng):
    if geometry=='uniform':return rng.choice(pool,4,replace=False)
    center=rng.choice(pool);dist=np.sum((loc[pool]-loc[center])**2,axis=1)
    return pool[np.argsort(dist,kind='stable')[:4]]
def complex_noise(rng,shape):return (rng.normal(size=shape)+1j*rng.normal(size=shape))/np.sqrt(2)
def evaluate(h,est,noise):return rewards(h.reshape(4,-1,2),est.reshape(4,-1,2),noise)
def predictive_scores(est,Cpost,K,noise,rng,samples=8):
    # Hypothetical worlds depend only on F_4 and a fixed Gaussian working prior.
    w,U=np.linalg.eigh(Cpost);root=U*np.sqrt(np.maximum(w,0))
    a0=int(evaluate(est,est,noise).argmax());scores=np.zeros((3,4))
    for _ in range(samples):
        world=est+complex_noise(rng,est.shape)@root.T
        eps=complex_noise(rng,est.shape)*np.sqrt(noise)
        current=evaluate(world,est,noise)
        for u in range(4):
            after=est.copy();after[u]+=K@(world[u]+eps[u]-est[u])
            anew=int(evaluate(after,after,noise).argmax());actual=evaluate(world,after,noise)
            scores[0,u]+=current[anew]-current[a0] # allocation-only, receiver held fixed
            scores[1,u]+=actual[a0]-current[a0] # receiver-only, allocation held fixed
            scores[2,u]+=actual[anew]-current[a0] # joint
    return scores/samples
def main(mode):
    global NOISE
    start=time.time();rows=[];witness=None;context=0
    seed=91000 if mode=='headroom' else 92000
    if mode=='prototype':
        gate=json.loads((R/'headroom-results.json').read_text())
        assert gate['gate']['prototype_warranted'],'No headroom gate'
    for ant in [1,2,8]:
      H,loc,pool,mean,w,U=load_data(ant);f=H.shape[1]
      for geometry in ['uniform','nearby']:
       for NOISE in [.1,1.,10.]:
        rng=np.random.default_rng(seed+context);prng=np.random.default_rng(seed+10000+context);context+=1
        F=(U*(w/(w+NOISE/4)))@U.conj().T
        C4=(U*(w*NOISE/(4*w+NOISE)))@U.conj().T
        K=(U*(w/(5*w+NOISE)))@U.conj().T # C4 (C4 + noise I)^-1
        for i in range(40):
            ids=ids_for(pool,loc,geometry,rng);truth=H[ids]
            # Sufficient statistic of four unit-amplitude orthogonal pilot symbols.
            ls=truth+complex_noise(rng,truth.shape)*np.sqrt(NOISE/4)
            est=(ls-mean)@F.T+mean
            extra=truth+complex_noise(rng,truth.shape)*np.sqrt(NOISE)
            nominal=evaluate(est,est,NOISE);a0=int(nominal.argmax())
            actual=evaluate(truth,est,NOISE);perfect=evaluate(truth,truth,NOISE)
            after_rates=[];after_actions=[];estimates=[]
            for u in range(4):
                he=est.copy();he[u]+=K@(extra[u]-est[u]);estimates.append(he)
                a=int(evaluate(he,he,NOISE).argmax());after_actions.append(a)
                after_rates.append(float(evaluate(truth,he,NOISE)[a]))
            q=column_scores(est.reshape(4,-1,2));low,up,lp,idx=solve(q)
            assert idx==a0 or abs(nominal[idx]-nominal[a0])<1e-8
            closegap=up-low
            if witness is None or closegap>witness['gap']:
                witness={'ant':ant,'geometry':geometry,'noise':NOISE,'sample':i,'ids':ids.tolist(),'q':q.tolist(),'lp_x':lp.tolist(),'ILP':low,'LP':up,'gap':closegap,'H_est_real':est.real.tolist(),'H_est_imag':est.imag.tolist()}
            row={'ant':ant,'geometry':geometry,'noise':NOISE,'sample':i,'ids':ids.tolist(),'base_actual':float(actual[a0]),'base_oracle_allocation':float(actual.max()),'perfect_CSI':float(perfect.max()),'after_probe_actual':after_rates,'after_actions':after_actions,'base_action':a0,'nominal_ILP':low,'nominal_LP':up,'LP_gap':closegap,'LP_fractional':bool(np.max(abs(lp-np.rint(lp)))>1e-7)}
            if mode=='prototype':
                t0=time.perf_counter();scores=predictive_scores(est,C4,K,NOISE,prng);dt=time.perf_counter()-t0
                chosen={'round_robin':i%4,'random':int(prng.integers(4)),'weakest':int(np.sum(abs(est)**2,axis=1).argmin()),'decision_only':int(scores[0].argmax()),'receiver_only':int(scores[1].argmax()),'joint':int(scores[2].argmax())}
                row.update({'probe_selection':chosen,'policy_actual':{m:after_rates[u] for m,u in chosen.items()},'predictive_scores':scores.tolist(),'joint_score_seconds':dt})
                finalq=column_scores(estimates[chosen['joint']].reshape(4,-1,2));l,u,x,a=solve(finalq)
                row.update({'joint_post_ILP':l,'joint_post_LP':u,'joint_post_LP_gap':u-l})
            rows.append(row)
        print(mode,ant,geometry,NOISE,flush=True)
        if time.time()-start>600:raise RuntimeError('CPU budget reached')
    summary=[]
    for ant,geometry,noise in itertools.product([1,2,8],['uniform','nearby'],[.1,1.,10.]):
        rr=[r for r in rows if (r['ant'],r['geometry'],r['noise'])==(ant,geometry,noise)]
        after=np.array([r['after_probe_actual'] for r in rr]);base=np.array([r['base_actual'] for r in rr])
        s={'ant':ant,'geometry':geometry,'noise':noise,'N':len(rr),'oracle_probe_gain_over_uniform_random':float(np.mean(after.max(1)-after.mean(1))),'oracle_gain_over_best_fixed_UE':float(after.max(1).mean()-after.mean(0).max()),'allocation_regret':float(np.mean([r['base_oracle_allocation']-r['base_actual'] for r in rr])),'receiver_gap':float(np.mean([r['perfect_CSI']-r['base_oracle_allocation'] for r in rr])),'LP_gap_mean':float(np.mean([r['LP_gap'] for r in rr])),'LP_gap_max':float(max(r['LP_gap'] for r in rr)),'fractional_LP_count':sum(r['LP_fractional'] for r in rr),'positive_LP_gap_count':sum(r['LP_gap']>1e-7 for r in rr)}
        s['net_oracle_gain_vs_no_probe']={str(T):float(np.mean((1-5/T)*after.max(1)-(1-4/T)*base)) for T in [50,200,1000]}
        if mode=='prototype':
            s['policy_means']={m:float(np.mean([r['policy_actual'][m] for r in rr])) for m in rr[0]['policy_actual']}
            baseline=max(s['policy_means'][m] for m in ['round_robin','random','weakest']);s['joint_minus_best_baseline_raw']=s['policy_means']['joint']-baseline
            s['score_seconds_median']=float(np.median([r['joint_score_seconds'] for r in rr]))
        summary.append(s)
    gate={'prototype_warranted':any(s['oracle_gain_over_best_fixed_UE']>1e-7 and s['allocation_regret']>1e-7 and max(s['net_oracle_gain_vs_no_probe'].values())>0 for s in summary),'scope':'existence of physical headroom only; not evidence causal policy can attain oracle'}
    out={'mode':mode,'seed':seed,'MC_samples':8 if mode=='prototype' else 0,'seconds':time.time()-start,'gate':gate,'rows':rows,'summary':summary,'max_gap_witness':witness,'scope':'development only; one additional symbol and unit energy for every policy; fixed train-only LMMSE; no population or novelty claim'}
    (R/f'{mode}-results.json').write_text(json.dumps(out,indent=2))
    print(json.dumps({'gate':gate,'seconds':out['seconds'],'max_LP_gap':witness['gap']}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['headroom','prototype']);main(p.parse_args().mode)
