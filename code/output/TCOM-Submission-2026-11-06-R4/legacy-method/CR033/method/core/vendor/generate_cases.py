"""CR024 generation: CP-S09 hash gate required; no generation on import.

Python 3.9 generator uses only relative elapsed time. The Python 3.12 parent
owns the original absolute campaign clock and subprocess timeout.
"""
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations
import argparse
import hashlib
import json
import time
import numpy as np

R = Path(__file__).resolve().parents[4]
W = Path(__file__).resolve().parents[2]
C = Path(__file__).resolve().parents[1]
NFFT = 512
BANDWIDTH_HZ = 50e6
CP_SAMPLES = 512
GUARD_SECONDS = CP_SAMPLES / BANDWIDTH_HZ
TONES = np.arange(0, NFFT, 16)
NOISE_W = 10**((-174+7-30)/10)*(BANDWIDTH_HZ/NFFT)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_gate(go):
    marker = json.loads(Path(go).read_text())
    require(marker.get('checkpoint') == 'CP-S09' and marker.get('verdict') == 'PASS', 'CP-S09 PASS required')
    require(bool(marker.get('source_files')), 'missing frozen source manifest')
    require(bool(marker.get('external_readonly_inputs')), 'missing external input manifest')
    for row in marker['source_files']:
        relative = Path(row['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'source path must be project relative')
        path = R/relative
        require(digest(path) == row['sha256'], 'source hash mismatch: '+str(path))
    for row in marker['external_readonly_inputs']:
        require(digest(row['path']) == row['sha256'], 'external hash mismatch: '+row['path'])
    return digest(go)


def waveform_metadata():
    return dict(protocol='CR024', NFFT=NFFT, bandwidth_Hz=BANDWIDTH_HZ,
                retained_FFT_indices=TONES.tolist(), subcarrier_spacing_Hz=BANDWIDTH_HZ/NFFT,
                useful_symbol_seconds=NFFT/BANDWIDTH_HZ, CP_samples=CP_SAMPLES,
                guard_seconds=GUARD_SECONDS, guard_is_assumed_not_time_domain_simulated=True,
                amplitude_correction='sqrt(512)', noise_W=NOISE_W,
                synchronization='ideal symbol/frequency synchronization; zero CFO; block-static channels',
                per_user_timing_advance=False,
                SE_scope='gross useful-symbol occupied-tone SE Q/(S ln2); excludes guard and other overheads',
                payload_SE_guard_factor=NFFT/(NFFT+CP_SAMPLES),
                payload_factor_scope='0.5 before other overheads; not a new endpoint',
                air_interface_scope='generic ideal OFDM model, not standardized 6G deployment')


def configure(params, scene):
    require(scene in ('o1', 'asu'), 'scene')
    params['dataset_folder'] = str(R/'DeepMIMO_sena' if scene == 'o1' else W/'downloads/scene')
    params['scenario'] = 'O1_60' if scene == 'o1' else 'asu_campus1'
    params['active_BS'] = np.array([1]); params['num_paths'] = 10
    params['user_rows'] = np.arange(321,341) if scene == 'o1' else np.arange(21,41)
    params['enable_BS2BS'] = 0
    params['bs_antenna']['shape'] = np.array([1,8,1])
    params['ue_antenna']['shape'] = np.array([1,1,1])
    params['OFDM']['bandwidth'] = .05
    params['OFDM']['subcarriers'] = NFFT
    params['OFDM']['selected_subcarriers'] = TONES.copy()
    params['OFDM']['RX_filter'] = 0
    return params


def validate_pool(H, location, paths):
    require(H.ndim == 3 and H.shape[1:] == (8,32), 'expected user x 8 x 32 channel shape')
    require(len(H) >= 16 and np.isfinite(H).all(), 'insufficient/nonfinite channel pool')
    require(np.asarray(location).ndim == 2 and len(location) == len(H) and np.isfinite(location).all(), 'location shape/finiteness')
    require(len(paths) == len(H), 'path/user count mismatch')
    count, nonempty, minimum, maximum = 0, 0, None, None
    for path in paths:
        require(isinstance(path, dict) and 'ToA' in path, 'missing retained path ToA')
        delays = np.asarray(path['ToA'], dtype=float).reshape(-1)
        require(np.isfinite(delays).all() and np.all(delays >= 0), 'invalid retained delay')
        require(np.all(delays < GUARD_SECONDS), 'retained delay exceeds fixed guard/window')
        require(len(delays) <= 10, 'retained paths exceed declared ten-path limit')
        if len(delays):
            nonempty += 1; count += len(delays)
            minimum = float(delays.min()) if minimum is None else min(minimum,float(delays.min()))
            maximum = float(delays.max()) if maximum is None else max(maximum,float(delays.max()))
    nonzero = np.any(H != 0, axis=(1,2))
    require(bool(nonzero.any()), 'entire scene channel pool is zero')
    return dict(retained_paths=count, users_with_paths=nonempty, users_without_paths=len(H)-nonempty,
                minimum_delay_seconds=minimum, maximum_delay_seconds=maximum,
                pool_nonzero_users=int(nonzero.sum()), pool_zero_users=int((~nonzero).sum()),
                all_retained_delays_below_fixed_guard=True)


def validate_coordinates(location, prior_locations):
    now = set(map(tuple,np.asarray(location).tolist()))
    for name, old in prior_locations:
        require(not now.intersection(map(tuple,np.asarray(old).tolist())), 'coordinate overlap: '+str(name))


def selection_plan(H, scene):
    require(scene in ('o1','asu'), 'scene')
    selected, counts = [], {}
    panels = [('main',12,8,202611310 if scene=='o1' else 202611311,[0,8,16,24]),
              ('scale',4,16,202611320 if scene=='o1' else 202611321,list(range(0,32,4)))]
    for panel, n, k, seed, resources in panels:
        rng = np.random.default_rng(seed); nontrivial = 0
        for i in range(n):
            ids = rng.choice(len(H), k, replace=False)
            count = int(np.count_nonzero(H[ids][:,:,resources]))
            nontrivial += count > 0
            selected.append(dict(panel=panel,index=i,ids=ids,resources=resources,seed=seed,
                                 selected_nonzero_channel_entries=count))
        counts[panel] = dict(cases=n,nontrivial_cases=nontrivial,trivial_cases=n-nontrivial)
        require(nontrivial > 0, 'all selected '+panel+' cases are trivial; scene invalid, no resampling')
    return selected, counts


def scale_channels(H, ids, resources):
    # Convert before scaling; stored binary64 values are the exact certificate input.
    return np.asarray(H[ids],dtype=np.complex128)[:,:,resources]*np.sqrt(NFFT)/np.sqrt(NOISE_W)


def convert(h, name, metadata):
    k,m,s = h.shape; h=np.asarray(h,dtype=np.complex128)
    require(np.isfinite(h).all(), 'nonfinite scaled channels')
    gains, vectors, pairs = {}, {}, []
    for u in range(k):
        for t in range(s):
            vec=[(F(float(z.real)),F(float(z.imag))) for z in h[u,:,t]]
            vectors[u,t]=vec;gains[u,t]=sum(x*x+y*y for x,y in vec)
    for u,v in combinations(range(k),2):
        for t in range(s):
            re=sum(x*a+y*b for (x,y),(a,b) in zip(vectors[u,t],vectors[v,t]))
            im=sum(x*b-y*a for (x,y),(a,b) in zip(vectors[u,t],vectors[v,t]))
            g,hg=gains[u,t],gains[v,t];r=(re*re+im*im)/(g*hg) if g*hg else F(0)
            pairs.append(dict(users=[u,v],resource=t,gain1=str(g),gain2=str(hg),r=str(r)))
    return dict(name=name,K=k,M=m,S=s,pmin='1/20',pmax='1/5',budget=str(F(k,10)),pairs=pairs,
                channels_re=h.real.tolist(),channels_im=h.imag.tolist(),metadata=metadata)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--go',required=True)
    ap.add_argument('--scene',choices=['o1','asu'],required=True);ap.add_argument('--output',required=True)
    args=ap.parse_args();gate_hash=check_gate(args.go)
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    import DeepMIMOv3 as dm
    scene=args.scene;p=configure(dm.default_params(),scene)
    started=time.monotonic();data=dm.generate_data(p)
    require(len(data)==1, 'expected one BS')
    user=data[0]['user'];raw=np.asarray(user['channel'])
    require(raw.ndim==4 and raw.shape[1:]==(1,8,32), 'generator channel dimensions')
    H=raw[:,0,:,:];location=np.asarray(user['location'])
    validity=validate_pool(H,location,user['paths'])
    prior_paths=[W/'campaign/inputs'/scene/'pool.npz']
    if scene=='o1':
        prior_paths += [R/'research/reproduction/channels.npz',
                        R/'research/completion-20261031/csi-forward/run-01/channels.npz',
                        R/'research/completion-20261031/confirmation/run-01-inputs/channels32.npz']
    priors=[]
    for path in prior_paths:
        with np.load(path,allow_pickle=False) as z:
            priors.append((str(path),z['location'].copy()))
    validate_coordinates(location,priors)
    selections,selected_counts=selection_plan(H,scene)
    # All scene/input/selected-panel checks precede pool/case publication.
    np.savez_compressed(out/'pool.npz',H=H,location=location)
    pool_hash=digest(out/'pool.npz');rows=[]
    for item in selections:
        ids,resources=item['ids'],item['resources']
        h=scale_channels(H,ids,resources);name=f"{scene}-{item['panel']}-{item['index']:02d}"
        meta=dict(waveform_metadata(),scene=scene,scene_name=p['scenario'],
                  frequency_Hz=60e9 if scene=='o1' else 3.5e9,indices=ids.tolist(),
                  resources=resources,actual_FFT_indices=TONES[resources].tolist(),seed=item['seed'],
                  pool_sha256=pool_hash,gate_sha256=gate_hash,
                  selected_nonzero_channel_entries=item['selected_nonzero_channel_entries'],
                  scope='CR024 post-diagnosis study; all weak/zero users retained; conditional draws within fixed scene; no cross-study absolute-rate comparison')
        case=convert(h,name,meta);path=out/(name+'.json')
        with path.open('x',encoding='utf-8') as stream:
            json.dump(case,stream,indent=2)
        rows.append(dict(name=name,sha256=digest(path),indices=ids.tolist(),
                         nontrivial=item['selected_nonzero_channel_entries']>0))
    report=dict(protocol='CR024',scene=scene,cases=rows,source_pool_sha256=pool_hash,
                generator_source_sha256=digest(__file__),gate_sha256=gate_hash,
                shape=list(H.shape),seconds=time.monotonic()-started,params=p,
                waveform=waveform_metadata(),input_validity=validity,selected_case_counts=selected_counts,
                prior_pool_sha256={str(path):digest(path) for path in prior_paths},
                all_weak_zero_channels_retained=True,coordinate_disjointness=True,
                frequency_is_scene_specific=True,complete=True)
    with (out/'generation.json').open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2,default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x))
    print(json.dumps(dict(scene=scene,cases=len(rows),seconds=report['seconds'],selected_case_counts=selected_counts)))


if __name__=='__main__':
    main()
