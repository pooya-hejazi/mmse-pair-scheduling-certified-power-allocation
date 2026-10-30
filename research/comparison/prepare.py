from pathlib import Path
import sys,json,hashlib,itertools,numpy as np
R=Path(__file__).resolve().parent;inputs=R/'inputs';inputs.mkdir(exist_ok=True)
sys.path.insert(0,str(R.parent/'gpu'));import benchmark as old
d=np.load(R.parent/'gpu/channels32.npz');H=d['H'];loc=d['location'];prev=json.loads((R.parent/'gpu/results.json').read_text())
meta=[]
for n in [8,16,32,64]:
 if n<64:ids=np.array(next(x['ids'] for x in prev['rows'] if x['users']==n))
 else:
  order=np.lexsort((loc[:,0],loc[:,1]));pool=order[int(.55*len(H)):int(.68*len(H))];ids=np.random.default_rng(125064).choice(pool,n,replace=False)
 h=(np.sqrt(32)*H[ids]).reshape(n,32,32)[:,:,:n//2]/np.sqrt(old.NOISE)
 path=inputs/f'power-{n}.npz';np.savez(path,h=h)
 meta.append({'mode':'power','users':n,'ids':ids.tolist(),'input':str(path)})
del H,d
sys.path.insert(0,str(R.parent/'selective'));import experiment as ex
H,loc,pool,mean,w,U=ex.load_data(2)
for ctx,(geometry,noise) in enumerate(itertools.product(['uniform','nearby'],[.1,1.])):
 rng=np.random.default_rng(131000+ctx)
 F=(U*(w/(w+noise/4)))@U.conj().T;C4=(U*(w*noise/(4*w+noise)))@U.conj().T
 K=(U*(w/(5*w+noise)))@U.conj().T;Ku=(U*(w/(17*w+4*noise)))@U.conj().T
 # Ku=C4/(C4+4noise I)=w/(17w+4noise).
 assert np.allclose(K,C4@np.linalg.inv(C4+noise*np.eye(len(w))))
 assert np.allclose(Ku,C4@np.linalg.inv(C4+4*noise*np.eye(len(w))))
 for i in range(8):
  ids=ex.ids_for(pool,loc,geometry,rng);truth=H[ids]
  ls=truth+ex.complex_noise(rng,truth.shape)*np.sqrt(noise/4);estimate=(ls-mean)@F.T+mean
  base_noise=ex.complex_noise(rng,truth.shape)
  extra=truth+base_noise*np.sqrt(noise);uniform=truth+base_noise*np.sqrt(4*noise)
  path=inputs/f'info-{ctx}-{i}.npz'
  np.savez(path,truth=truth,estimate=estimate,extra=extra,uniform_observation=uniform,noise=noise,K=K,Ku=Ku,C4=C4,random_ue=rng.integers(4),policy_seed=141000+ctx*100+i)
  meta.append({'mode':'info','context':ctx,'sample':i,'geometry':geometry,'noise':noise,'ids':ids.tolist(),'input':str(path)})
for m in meta:m['sha256']=hashlib.sha256(Path(m['input']).read_bytes()).hexdigest()
(R/'inputs.json').write_text(json.dumps(meta,indent=2));print('Prepared',len(meta),'pinned inputs; original data unchanged')
