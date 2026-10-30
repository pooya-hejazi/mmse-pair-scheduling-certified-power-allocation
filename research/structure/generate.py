"""Separate solver-study channels; never modifies S02 inputs or uses reserved rows."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import numpy as np,json,time,hashlib
import DeepMIMOv3 as dm
R=Path(__file__).resolve().parent;source=R.parents[1]/'DeepMIMO_sena'
p=dm.default_params();p['dataset_folder']=str(source);p['scenario']='O1_60';p['active_BS']=np.arange(1,5);p['num_paths']=10
p['user_rows']=np.arange(1,101);p['enable_BS2BS']=0;p['bs_antenna']['shape']=np.array([1,8,1]);p['ue_antenna']['shape']=np.array([1,1,1]);p['OFDM']['bandwidth']=.05;p['OFDM']['subcarriers']=32;p['OFDM']['selected_subcarriers']=np.array([0,8,16,24])
start=time.time();data=dm.generate_data(p)
H=np.stack([v['user']['channel'][:,0,:,:] for v in data],axis=1);loc=data[0]['user']['location']
assert H.shape[1:]==(4,8,4) and np.isfinite(H).all()
assert all(np.array_equal(loc,v['user']['location']) for v in data)
np.savez_compressed(R/'channels-four.npz',H=H,location=loc)
(R/'generation.json').write_text(json.dumps({'parameters':p,'shape':H.shape,'seconds':time.time()-start,'sha256':hashlib.sha256((R/'channels-four.npz').read_bytes()).hexdigest(),'source_manifest':'../reproduction/data-source.json','scope':'same rows1..100, new real carriers, no test use'},default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x),indent=2))
print(H.shape,time.time()-start)
