"""Generate separate 32-carrier data; never modifies accepted S02 or reserved test."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import numpy as np,json,time,hashlib
import DeepMIMOv3 as dm
R=Path(__file__).resolve().parent
p=dm.default_params();p['dataset_folder']=str(R.parents[1]/'DeepMIMO_sena');p['scenario']='O1_60'
p['active_BS']=np.arange(1,5);p['num_paths']=10;p['user_rows']=np.arange(1,101);p['enable_BS2BS']=0
p['bs_antenna']['shape']=np.array([1,8,1]);p['ue_antenna']['shape']=np.array([1,1,1])
p['OFDM']['bandwidth']=.05;p['OFDM']['subcarriers']=32;p['OFDM']['selected_subcarriers']=np.arange(32)
start=time.perf_counter();data=dm.generate_data(p)
H=np.stack([v['user']['channel'][:,0,:,:] for v in data],axis=1);loc=data[0]['user']['location']
assert H.shape[1:]==(4,8,32) and np.isfinite(H).all()
assert all(np.array_equal(loc,v['user']['location']) for v in data)
np.savez_compressed(R/'channels32.npz',H=H,location=loc)
src=Path(dm.__file__).parent
files={n:hashlib.sha256((src/n).read_bytes()).hexdigest() for n in ['construct_deepmimo.py','raytracing_v2.py','utils.py']}
out={'parameters':p,'shape':H.shape,'seconds':time.perf_counter()-start,'sha256':hashlib.sha256((R/'channels32.npz').read_bytes()).hexdigest(),'source_manifest':'../reproduction/data-source.json','generator_source_hashes':files,'convention':'stored raw DeepMIMO channel; benchmark uses sqrt(32)*H as per-carrier physical response','scope':'development rows1..100; reserved rows101..200 untouched'}
(R/'generation.json').write_text(json.dumps(out,default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x),indent=2))
assert out['seconds']<600
print(json.dumps({'shape':H.shape,'seconds':out['seconds'],'bytes':(R/'channels32.npz').stat().st_size}))
