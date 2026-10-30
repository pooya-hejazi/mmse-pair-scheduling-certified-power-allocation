"""Resource-priced matching certificates. Small oracle is exhaustive, explicitly not a scalable implementation."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
from pathlib import Path
import itertools,json,time,sys
import numpy as np
from scipy.optimize import linprog,milp,Bounds,LinearConstraint,linear_sum_assignment
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'innovation'))
from pilot_value import rate
def matchings(nodes):
    if not nodes:yield [];return
    u=nodes[0]
    for v in nodes[1:]:
        for rest in matchings([x for x in nodes[1:] if x!=v]):yield [(u,v)]+rest
def structure(n):
    edges=list(itertools.combinations(range(n),2));s=n//2;E=len(edges)
    A=np.zeros((n+s,E*s))
    for j,(u,v) in enumerate(edges):
        for k in range(s):A[[u,v,n+k],j*s+k]=1
    odd=[];rhs=[]
    for k in range(3,n,2):
        for subset in itertools.combinations(range(n),k):
            row=np.zeros(E*s)
            for j,(u,v) in enumerate(edges):
                if u in subset and v in subset:row[j*s:(j+1)*s]=1
            odd.append(row);rhs.append((k-1)/2)
    mats=[[edges.index(e) for e in m] for m in matchings(list(range(n)))]
    return edges,A,np.array(odd),np.array(rhs),mats
def matching_oracle(weight,mats):
    ix=max(range(len(mats)),key=lambda j:sum(weight[e] for e in mats[j]))
    return mats[ix]
def assignment(q,matching):
    rr,cc=linear_sum_assignment(-q[matching]);value=float(q[np.array(matching)[rr],cc].sum())
    return value,cc.tolist()
def solve(q,st):
    edges,A,C,b,mats=st;n=A.shape[0]-q.shape[1];s=q.shape[1];c=-q.ravel();start=time.perf_counter()
    weak=linprog(c,A_eq=A,b_eq=np.ones(n+s),bounds=(0,None),method='highs');assert weak.success
    strong=linprog(c,A_eq=A,b_eq=np.ones(n+s),A_ub=C,b_ub=b,bounds=(0,None),method='highs');assert strong.success
    lp_time=time.perf_counter()-start
    price=-strong.eqlin.marginals[n:];weights=(q-price).max(1);chosen=matching_oracle(weights,mats)
    upper=float(price.sum()+sum(weights[e] for e in chosen));lower,res=assignment(q,chosen)
    # A resource matching using only per-edge maximizers certifies equality.
    allowed=np.isclose(q[chosen]-price,weights[chosen,None],atol=1e-8,rtol=0)
    rr,cc=linear_sum_assignment((~allowed).astype(float));conflictfree=bool(allowed[rr,cc].all())
    if conflictfree:
        certvalue=float(q[np.array(chosen)[rr],cc].sum());assert abs(certvalue-upper)<1e-6
        lower=max(lower,certvalue)
    plain=matching_oracle(q.mean(1),mats);plainvalue,_=assignment(q,plain)
    lower=max(lower,plainvalue)
    before=time.perf_counter();ip=milp(c,integrality=np.ones(c.size),bounds=Bounds(0,1),constraints=LinearConstraint(A,np.ones(n+s),np.ones(n+s)),options={'time_limit':10,'mip_rel_gap':0});iptime=time.perf_counter()-before
    if ip.status!=0 or ip.x is None:return {'status':'MILP_UNRESOLVED','solver_status':int(ip.status),'message':str(ip.message),'lower':lower,'upper':upper}
    opt=float(-ip.fun)
    assert np.max(abs(A@ip.x-1))<1e-7 and np.max(abs(ip.x-np.rint(ip.x)))<1e-7
    assert lower<=opt+1e-6 and opt<=upper+1e-6 and upper<=-weak.fun+1e-6
    assert abs(upper+strong.fun)<1e-6
    if conflictfree:assert abs(lower-opt)<1e-6
    return {'status':'OPTIMAL','MILP':opt,'LP_weak':float(-weak.fun),'LP_odd':float(-strong.fun),'upper_priced':upper,'lower':lower,'plain_matching_assignment':plainvalue,'conflictfree_certificate':conflictfree,'weak_gap':float(-weak.fun-opt),'odd_gap':float(-strong.fun-opt),'certified_residual':upper-lower,'price':price.tolist(),'LP_seconds':lp_time,'MILP_seconds':iptime,'matching_edges':[edges[j] for j in chosen]}
def main():
    start=time.time();data=np.load(R/'channels-four.npz');H=data['H'][:,:,:2,:]/float(np.load(R.parent/'reproduction/normalization.npz')['train_rms']);loc=data['location'];order=np.lexsort((loc[:,0],loc[:,1]));pool=order[int(.55*len(H)):int(.68*len(H))]
    old=np.load(R.parent/'reproduction/split-indices.npz');assert not set(pool)&set(old['test'].ravel())
    rows=[];context=0
    for n,geometry,mode,noise in itertools.product([4,6,8],['uniform','nearby'],['flat','selective'],[.1,1.]):
        rng=np.random.default_rng(101000+context);context+=1;st=structure(n);s=n//2
        for i in range(10):
            if geometry=='uniform':ids=rng.choice(pool,n,replace=False)
            else:
                center=rng.choice(pool);dist=np.sum((loc[pool]-loc[center])**2,axis=1);ids=pool[np.argsort(dist,kind='stable')[:n]]
            ht=H[ids].reshape(n,8,4)[:,:,:s]
            if mode=='flat':ht=np.repeat(ht[:,:,:1],s,axis=2)
            q=np.array([[rate(ht,ht,e,k,noise)*2/s for k in range(s)] for e in st[0]])
            result=solve(q,st)
            if mode=='flat' and result['status']=='OPTIMAL':assert result['odd_gap']<1e-6 and abs(result['plain_matching_assignment']-result['MILP'])<1e-6
            rows.append({'users':n,'geometry':geometry,'mode':mode,'noise':noise,'sample':i,'ids':ids.tolist(),'q':q.tolist(),**result})
        print(n,geometry,mode,noise,flush=True)
        if time.time()-start>600:raise RuntimeError('10 minute budget exceeded')
    summary=[]
    for n,mode in itertools.product([4,6,8],['flat','selective']):
        rr=[x for x in rows if x['users']==n and x['mode']==mode];ok=[x for x in rr if x['status']=='OPTIMAL']
        summary.append({'users':n,'mode':mode,'N':len(rr),'resolved':len(ok),'weak_positive_gap':sum(x['weak_gap']>1e-7 for x in ok),'odd_positive_gap':sum(x['odd_gap']>1e-7 for x in ok),'conflictfree':sum(x['conflictfree_certificate'] for x in ok),'max_weak_gap':max(x['weak_gap'] for x in ok),'max_odd_gap':max(x['odd_gap'] for x in ok),'max_certified_residual':max(x['certified_residual'] for x in ok)})
    (R/'solver-results.json').write_text(json.dumps({'seconds':time.time()-start,'summary':summary,'rows':rows,'scope':'fixed known-CSI optimization benchmark; exhaustive matching oracle for <=8 users; full odd sets explicitly enumerated; no runtime scalability or novelty claim'},indent=2))
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
