"""Nominal scalar uplink continuous-power baselines; no access to hidden true CSI."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
import numpy as np,time,itertools
from scipy.optimize import minimize
LOW=.05;HIGH=.2

def schedules4():
    return [[(tuple(g),0),(tuple(u for u in range(4) if u not in g),1)] for g in itertools.combinations(range(4),2)]

def fixed_schedule(n):return [((i,i+1),i//2) for i in range(0,n,2)]

def receive(h,p,schedule):
    receivers=[]
    for pair,s in schedule:
        ids=np.array(pair);H=h[ids,:,s].T;v=np.sqrt(p[ids]);Hv=H*v
        V=Hv@np.linalg.inv(np.eye(2)+Hv.conj().T@Hv)
        receivers.append((ids,s,V))
    return receivers

def evaluate(truth,estimate,p,schedule):
    per=np.zeros(len(p))
    for ids,s,V in receive(estimate,p,schedule):
        gains=abs(V.conj().T@(truth[ids,:,s].T*np.sqrt(p[ids])))**2
        sig=np.diag(gains);den=gains.sum(1)-sig+np.sum(abs(V)**2,axis=0)
        per[ids]=np.log2(1+np.maximum(sig,0)/np.maximum(den,1e-300))
    return float(per.sum()),per

def waterfill(g,budget):
    def power(lam):return np.clip(1/lam-1/np.maximum(g,1e-300),LOW,HIGH)
    lo=1e-14;hi=max(1.,float(np.max(g)))
    for _ in range(90):
        mid=(lo+hi)/2
        if power(mid).sum()>budget:lo=mid
        else:hi=mid
    return power(hi)

def upper_bound(h,budget,schedule=None):
    gains=np.sum(abs(h)**2,axis=1)
    if schedule is None:g=gains.max(1)
    else:
        g=np.zeros(len(h))
        for pair,s in schedule:g[list(pair)]=gains[list(pair),s]
    p=waterfill(g,budget)
    return float(np.log2(1+g*p).sum())

def iwmmse(h,schedule,budget,iterations=500,certificate=False,callback=None):
    p=np.full(len(h),budget/len(h));history=[evaluate(h,h,p,schedule)[0]]
    up=upper_bound(h,budget,schedule);stopped=False
    for it in range(iterations):
        if certificate and up-history[-1]<=.01*max(up,1e-12):stopped=True;break
        a=np.zeros(len(h));b=np.zeros(len(h))
        for ids,s,V in receive(h,p,schedule):
            H=h[ids,:,s].T;G=V.conj().T@H
            error=np.maximum(1-np.sqrt(p[ids])*np.real(np.diag(G)),1e-14)
            w=1/error;a[ids]=(w[:,None]*abs(G)**2).sum(0);b[ids]=w*np.real(np.diag(G))
        def update(lam):return np.clip(b/np.maximum(a+lam,1e-300),np.sqrt(LOW),np.sqrt(HIGH))**2
        candidate=update(0)
        if candidate.sum()>budget:
            lo=0.;hi=max(1.,float(np.max(b)/np.sqrt(LOW)))
            while update(hi).sum()>budget:hi*=2
            for _ in range(60):
                mid=(lo+hi)/2
                if update(mid).sum()>budget:lo=mid
                else:hi=mid
            candidate=update(hi)
        value=evaluate(h,h,candidate,schedule)[0]
        assert candidate.min()>=LOW-1e-10 and candidate.max()<=HIGH+1e-10 and candidate.sum()<=budget+1e-9
        if value<history[-1]-1e-8:raise AssertionError('WMMSE descent in sum-rate')
        improvement=value-history[-1];p=candidate;history.append(value)
        if callback:callback(p,schedule,value)
        if improvement<=1e-8*max(1.,abs(value)):break
    return {'p':p,'schedule':schedule,'nominal_SE':history[-1],'iterations':len(history)-1,'history':history,'upper_SE':up,'certificate_stopped':stopped,'scope':'fixed-schedule nominal stationary candidate; no global optimum claim'}

def slsqp(h,schedule,budget,callback=None):
    p0=np.full(len(h),budget/len(h));best=[p0,evaluate(h,h,p0,schedule)[0]]
    def retain(p):
        if p.min()<LOW-1e-8 or p.max()>HIGH+1e-8 or p.sum()>budget+1e-8:return
        val=evaluate(h,h,p,schedule)[0]
        if val>=best[1]:
            best[:]=[p.copy(),val]
            if callback:callback(p,schedule,val)
    sol=minimize(lambda p:-evaluate(h,h,p,schedule)[0],p0,method='SLSQP',bounds=[(LOW,HIGH)]*len(h),constraints=[{'type':'ineq','fun':lambda p:budget-p.sum()}],callback=retain,options={'maxiter':500,'ftol':1e-10})
    retain(sol.x)
    return {'p':best[0],'schedule':schedule,'nominal_SE':best[1],'iterations':int(sol.nit),'optimizer_success':bool(sol.success),'message':str(sol.message),'upper_SE':upper_bound(h,budget,schedule)}

def optimize_all4(h,certificate=False):
    upper=upper_bound(h,.4);best=None;stopped=False;count=0
    for schedule in schedules4():
        result=iwmmse(h,schedule,.4,iterations=100)
        count+=1
        if best is None or result['nominal_SE']>best['nominal_SE']:best=result
        if certificate and upper-best['nominal_SE']<=.01*max(upper,1e-12):stopped=True;break
    best=dict(best);best.update(upper_SE=upper,schedules_evaluated=count,certificate_stopped=stopped)
    return best

def uniform_min_power(h,schedule,target):
    lo=LOW;hi=.1
    for _ in range(70):
        mid=(lo+hi)/2
        if evaluate(h,h,np.full(len(h),mid),schedule)[0]>=target:hi=mid
        else:lo=mid
    p=np.full(len(h),hi)
    return {'p':p,'nominal_SE':evaluate(h,h,p,schedule)[0],'target_SE':target,'scope':'uniform continuous scaling on common fixed schedule; not joint minimum-power optimum'}
