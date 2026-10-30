"""Check the installed DeepMIMO no-LPF one-path normalization directly."""
from pathlib import Path
import inspect,json,numpy as np
import DeepMIMOv3.construct_deepmimo as module
import DeepMIMOv3.consts as c
R=Path(__file__).resolve().parent
classes=[v for v in vars(module).values() if inspect.isclass(v) and hasattr(v,'no_LPF')]
assert len(classes)==1
obj=object.__new__(classes[0]);obj.total_subcarriers=32;obj.subcarriers=np.arange(32)
obj.OFDM_params={'subcarriers':32};obj.params={c.PARAMSET_DOPPLER_EN:False}
gain=2e-10
ray={c.OUT_PATH_RX_POW:np.array([gain]),c.OUT_PATH_TOA:np.array([0.]),c.OUT_PATH_PHASE:np.array([0.])}
value=obj.no_LPF(ray,1.)
assert np.allclose(abs(value)**2,gain/32,rtol=1e-12,atol=0)
assert np.allclose(abs(np.sqrt(32)*value)**2,gain,rtol=1e-12,atol=0)
(R/'unit-check.json').write_text(json.dumps({'result':'PASS','test':'actual installed no_LPF single path amplitude with 32 carriers','class':classes[0].__name__,'path_gain':gain,'stored_squared_amplitude':float(abs(value.ravel()[0])**2),'per_carrier_squared_amplitude':float(abs(np.sqrt(32)*value.ravel()[0])**2),'scope':'convention check, not radio hardware validation'},indent=2))
print('PASS: actual DeepMIMO OFDM scaling, one path')
