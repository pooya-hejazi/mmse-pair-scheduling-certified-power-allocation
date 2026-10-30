import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from pathlib import Path
import json,hashlib,sys,importlib.metadata as md
import numpy as np
import DeepMIMOv3 as dm
R=Path(__file__).resolve().parent
SOURCE=Path(__file__).resolve().parents[2]/'DeepMIMO_sena'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
required=[SOURCE/'O1_60'/('O1_60.'+suffix+'.mat') for suffix in ['params','TX_Loc','Loc']+[str(b)+'.'+ext for b in range(1,5) for ext in ('DoD','DoA','CIR','LoS','PL')]]
assert all(p.is_file() for p in required),'Missing required real data; no synthetic fallback'
manifest=[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in required]
(R/'data-source.json').write_text(json.dumps(manifest,indent=2))
env={'python':sys.version,'executable':sys.executable,'packages':{d.metadata['Name']:d.version for d in md.distributions()},'device':'CPU; CUDA_VISIBLE_DEVICES=-1'}
(R/'environment.json').write_text(json.dumps(env,indent=2))
(R/'requirements-observed.txt').write_text('\n'.join(f'{k}=={v}' for k,v in sorted(env['packages'].items())))
p=dm.default_params();p['dataset_folder']=str(SOURCE);p['scenario']='O1_60';p['active_BS']=np.arange(1,5);p['num_paths']=10
p['user_rows']=np.arange(1,101);p['enable_BS2BS']=0;p['bs_antenna']['shape']=np.array([1,8,1]);p['ue_antenna']['shape']=np.array([1,1,1]);p['OFDM']['bandwidth']=0.05;p['OFDM']['subcarriers']=32;p['OFDM']['selected_subcarriers']=np.array([0,16])
(R/'generation-parameters.json').write_text(json.dumps(p,default=lambda v:v.tolist() if hasattr(v,'tolist') else str(v),indent=2))
d=dm.generate_data(p)
print('shapes',[(v['user']['channel'].shape,list(v['user'])) for v in d],flush=True)
H=np.stack([v['user']['channel'][:,0,:,:] for v in d],axis=1)
loc=np.asarray(d[0]['user']['location'])
assert all(np.array_equal(loc,np.asarray(v['user']['location'])) for v in d)
assert np.isfinite(H).all()
assert H.shape[1:]==(4,8,2) and len(H)>181,'API/config mismatch'
np.savez_compressed(R/'channels.npz',H=H,location=loc)
(R/'data-output.json').write_text(json.dumps({'shape':list(H.shape),'sha256':sha(R/'channels.npz'),'source':'DeepMIMO O1_60 real ray tracing','no_synthetic_fallback':True},indent=2))
