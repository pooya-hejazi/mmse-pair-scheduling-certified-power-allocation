"""Descriptive native-channel diagnostics; no optimizer results are used."""
from pathlib import Path
import hashlib
import json
import numpy as np

HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    receipt=json.loads((HERE/'generator_validation_main.json').read_text())
    assert receipt['status']=='PASS' and receipt['profile_count']==60
    snr={rho:[] for rho in (0,10,20)}
    gains={p:[] for p in 'ABC'}
    correlations={p:[] for p in 'ABC'}
    hashes={}
    for item in receipt['profiles']:
        path=HERE/item['native_path']
        assert sha(path)==item['native_sha256']
        hashes[item['native_path']]=sha(path)
        with np.load(path) as data:
            h=data['native_h'];offset=data['offset_db']
        assert h.shape==(16,2,8) and offset.shape==(16,)
        gain=np.sum(abs(h)**2,axis=1)
        assert np.all(gain>0)
        gains[item['profile']].extend(gain.ravel().tolist())
        for u in range(16):
            for v in range(u+1,16):
                r=abs(np.sum(h[u].conj()*h[v],axis=0))**2/(gain[u]*gain[v])
                assert np.all(r>=0) and np.all(r<=1+1e-12)
                correlations[item['profile']].extend(r.tolist())
        for rho in snr:
            values=rho+offset[:,None,None]+10*np.log10(abs(h)**2)
            assert np.isfinite(values).all()
            snr[rho].extend(values.ravel().tolist())
    def summary(values):
        q=np.quantile(values,[0,.1,.5,.9,1])
        return dict(n=len(values),minimum=float(q[0]),p10=float(q[1]),median=float(q[2]),p90=float(q[3]),maximum=float(q[4]))
    result=dict(qualification='Descriptive pooled channel entries; tones, antennas and pairs are dependent. Reference power is 0.1 W per user; SNR is per antenna.',
        per_antenna_reference_snr_db={str(k):summary(v) for k,v in snr.items()},
        native_array_power_gain={k:summary(v) for k,v in gains.items()},
        squared_pair_correlation={k:summary(v) for k,v in correlations.items()},
        provenance=dict(native_sha256=hashes,generator_receipt_sha256=sha(HERE/'generator_validation_main.json'),script_sha256=sha(Path(__file__))))
    assert all(x['n']==15360 for x in result['per_antenna_reference_snr_db'].values())
    (HERE/'channel_diagnostics.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='provenance'},indent=2))

if __name__=='__main__':main()
