import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1';os.environ['CUDA_VISIBLE_DEVICES']='-1'
from pathlib import Path
import numpy as np,json,itertools,time,math,hashlib
R=Path(__file__).resolve().parent;D=R.parent/'reproduction'
TAU=np.array([4,8,16]);ALPHA=.05
A=[(g,tuple(u for u in range(4) if u not in g)) for g in itertools.combinations(range(4),2)]

def rate(h,he,g,s,noise):
 ht=h[list(g),:,s].T;hh=he[list(g),:,s].T
 v=hh@np.linalg.solve(noise*np.eye(len(g))+hh.conj().T@hh,np.eye(len(g)))
 p=np.abs(v.conj().T@ht)**2;sig=np.diag(p);den=p.sum(1)-sig+noise*np.sum(abs(v)**2,axis=0)
 return float(np.log2(1+np.divide(sig,den,out=np.zeros_like(sig),where=den>0)).sum()/2)

def rewards(h,he,noise):
 return np.array([rate(h,he,g,0,noise)+rate(h,he,g2,1,noise) for g,g2 in A])

def quantile(scores,alpha=ALPHA):
 k=math.ceil((len(scores)+1)*(1-alpha))
 return float(np.sort(scores)[k-1]) if k<=len(scores) else float('inf')

def policy(hat,q,T,method):
 # Receives observed prediction path only; future entries are accessed only after continuing.
 for t in range(2):
  v=float(hat[t].max());g=1-TAU[t]/T;gn=1-TAU[t+1]/T
  ub=(gn-g)*v+q if method=='contrast' else gn*(v+q)-g*max(0,v-q)
  if ub<=0:return t,ub
 return 2,None

def main():
 start=time.time();data=np.load(D/'channels.npz');H=data['H'].reshape(-1,64);loc=data['location'];splits=np.load(D/'split-indices.npz')
 scale=float(np.load(D/'normalization.npz')['train_rms']);H=H/scale
 train=H[splits['train']].reshape(-1,64);mean=train.mean(0);z=train-mean;cov=z.T@z.conj()/len(z)
 order=np.lexsort((loc[:,0],loc[:,1]));n=len(order)
 pool=order[int(.55*n):int(.68*n)];shiftpool=order[int(.73*n):int(.83*n)]
 assert not set(pool)&set(splits['train'].ravel()) and not set(pool)&set(splits['test'].ravel())
 x=np.exp(2j*np.pi*np.arange(4)[:,None]*np.arange(4)[None,:]/4)
 assert np.allclose(x.conj().T@x,4*np.eye(4))
 assert np.isinf(quantile(np.arange(3),.01))
 # Independent direct 32-dimensional SINR versus low-rank implementation.
 hh=H[splits['train'][0]].reshape(4,32,2);he=hh+.02j
 ht=hh[:2,:,0].T;hs=he[:2,:,0].T;v=np.linalg.solve(hs@hs.conj().T+.1*np.eye(32),hs)
 pp=abs(v.conj().T@ht)**2;diag=np.diag(pp);den=pp.sum(1)-diag+.1*np.sum(abs(v)**2,axis=0)
 assert np.allclose(rate(hh,he,(0,1),0,.1),np.log2(1+diag/den).sum()/2)
 allrows=[];summary=[]
 for context,noise in enumerate([.1,1.,10.]):
  rng=np.random.default_rng(31000+context)
  ids=np.array([rng.choice(pool if i<160 else shiftpool,4,replace=False) for i in range(200)])
  hat=np.empty((200,3,6));actual=np.empty_like(hat);oracle=np.empty((200,6))
  for i,ix in enumerate(ids):
   h=H[ix];chunks=[]
   for j in range(4):
    eps=(rng.normal(size=h.shape)+1j*rng.normal(size=h.shape))*np.sqrt(noise/2)
    chunks.append(x.conj().T@(x@h+eps)/4)
   for t,k in enumerate([1,2,4]):
    ls=np.mean(chunks[:k],axis=0);filt=np.linalg.solve(cov+noise/TAU[t]*np.eye(64),cov).T
    he=((ls-mean)@filt+mean).reshape(4,32,2);truth=h.reshape(4,32,2)
    hat[i,t]=rewards(he,he,noise);actual[i,t]=rewards(truth,he,noise)
   oracle[i]=rewards(truth,truth,noise)
  assert np.all(actual<=oracle[:,None,:]+1e-7)
  np.savez_compressed(R/f'paths-noise{context}.npz',ids=ids,hat=hat,actual=actual,oracle=oracle)
  best=hat.argmax(2);selected=np.take_along_axis(actual,best[...,None],2)[...,0]
  qa=quantile(np.maximum(abs(oracle[:80,None,:]-hat[:80]),abs(actual[:80]-hat[:80])).max((1,2)))
  for T in [50,200,1000]:
   g=1-TAU/T;V=oracle.max(1);zhat=(g[1:]-g[:-1])*hat.max(2)[:,:2]
   target=g[None,1:]*V[:,None]-g[None,:2]*selected[:,:2]
   qc=quantile((target[:80]-zhat[:80]).max(1))
   for split,indices in [('iid_development',range(80,160)),('shift_stress',range(160,200))]:
    for method,q in [('contrast',qc),('absolute',qa)]:
     rows=[]
     for i in indices:
      t,ub=policy(hat[i],q,T,method);gain=g[t]*selected[i,t]
      # saved future arrays are only used below for offline evaluation
      violate=t<2 and target[i,t]>1e-8
      row={'noise':noise,'coherence':T,'split':split,'method':method,'sample':i,'tau':int(TAU[t]),'net_se':float(gain),'certificate_upper':ub,'early':t<2,'false_certificate':bool(violate),'q':q,'nominal_regret_to_perfect_CSI_at_same_tau':float(g[t]*(V[i]-selected[i,t]))}
      for j,tau in enumerate(TAU):row[f'fixed_{tau}']=float(g[j]*selected[i,j])
      rows.append(row);allrows.append(row)
     early=sum(r['early'] for r in rows);bad=sum(r['false_certificate'] for r in rows)
     summary.append({'noise':noise,'coherence':T,'split':split,'method':method,'N':len(rows),'q':q,'mean_tau':float(np.mean([r['tau'] for r in rows])),'mean_net_se':float(np.mean([r['net_se'] for r in rows])),'early_stops':early,'false_certificates':bad,'unconditional_false_rate':bad/len(rows),'conditional_false_rate':bad/early if early else None,'fixed_means':{str(tau):float(np.mean([r[f'fixed_{tau}'] for r in rows])) for tau in TAU}})
   print('done',noise,T,flush=True)
 # Causality: if prefix1 certifies, perturbing unseen future predictions cannot change it.
 test=np.ones((3,6))*10;t,_=policy(test,0,200,'contrast');test[1:]=1e9;assert t==policy(test,0,200,'contrast')[0]==0
 result={'alpha':ALPHA,'seed_base':31000,'calibration_N':80,'stages':TAU.tolist(),'calibration_rank':math.ceil(81*.95),'seconds':time.time()-start,'checks':{'low_rank_equals_direct':True,'perfect_CSI_dominates_actual_receiver':True,'pilot_orthogonal':True,'small_n_quantile_infinite':True,'prefix_causality':True},'summary':summary,'rows':allrows,'scope':'development and shift stress only; no held-out confirmatory test; no distribution-free guarantee under shift; no conditional-on-stop guarantee'}
 (R/'pilot-results.json').write_text(json.dumps(result,indent=2))

if __name__=='__main__':main()
