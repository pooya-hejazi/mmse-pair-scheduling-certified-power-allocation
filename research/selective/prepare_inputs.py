"""Restore pinned split/normalization after generating channels; no neural training."""
from pathlib import Path
import json,numpy as np
R=Path(__file__).resolve().parent;D=R.parent/'reproduction'
spec=json.loads((R/'input-spec.json').read_text())
d=np.load(D/'channels.npz')
assert list(d['H'].shape)==spec['channel_shape']
np.savez_compressed(D/'split-indices.npz',**{k:np.array(v,dtype=np.int64) for k,v in spec['splits'].items()})
np.savez_compressed(D/'normalization.npz',train_rms=spec['train_rms'])
print('Pinned splits and train RMS restored; no estimator trained.')
