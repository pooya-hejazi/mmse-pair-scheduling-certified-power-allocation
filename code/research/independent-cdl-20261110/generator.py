"""Native Sionna CDL generation; frozen design in PROTOCOL.md, no optimization."""
import os,sys
sys.dont_write_bytecode=True
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='1'
import argparse,hashlib,importlib.metadata,inspect,json,re,secrets,time
from fractions import Fraction as F
from pathlib import Path
import numpy as np
import torch
import sionna
from sionna.phy import config
from sionna.phy.channel.tr38901 import CDL,Antenna,AntennaArray
from sionna.phy.channel import cir_to_ofdm_channel
BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[1]
WORKSPACE=PROJECT.parent
K,S,M=16,8,2
FREQUENCIES=np.array([-14,-10,-6,-2,2,6,10,14],dtype=np.float64)*(50e6/32)
BS_ORIENTATION=[0.,0.,0.]
UT_ORIENTATION=[float(np.pi),0.,0.]
config.precision='double';config.device='cpu'
torch.set_num_threads(1)

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save_json(path,obj):
    with Path(path).open('x',encoding='utf-8') as stream: json.dump(obj,stream,indent=2,allow_nan=False)
def historical_seed_audit():
    """Scan actual relevant Paper2 populations, not duplicated package archives."""
    case_roots=[PROJECT/'research/phase1-cdl-20261109/cases',
        PROJECT/'research/phase1-cdl-20261109/cases_k8',
        PROJECT/'research/phase1-benchmark-20261109/cases',
        PROJECT/'research/phase3-cdl-crosscheck-20261110/cases',
        PROJECT/'research/phase3-cdl-crosscheck-20261110/cases_e3a']
    paths=set()
    for root in case_roots:
        if root.exists(): paths.update(root.rglob('*.json'))
    paths.update((PROJECT/'research/phase1-cdl-20261109').glob('*.py'))
    paths.update((PROJECT/'research/phase3-cdl-crosscheck-20261110/scripts').glob('*.py'))
    for relative in ('research/dual-track-revision-20261103/method/core/vendor/generate_cases.py',
                     'research/review-20261110/comparison/run_comparison.py',
                     'research/review-20261110/comparison/PROTOCOL.md'):
        path=PROJECT/relative
        if path.exists(): paths.add(path)
    seeds={419812991,20261109,20261110,1101}
    entries=[];bytes_scanned=0
    seed_value=re.compile(rb'"[^"\r\n]*seed[^"\r\n]*"\s*:\s*(\[[^\]]*\]|"[^"\r\n]*"|-?\d+)',re.I)
    seed_assignment=re.compile(rb'\b(?:[a-z0-9_]*seed[a-z0-9_]*|random_state)\s*[=:]\s*([0-9][0-9_]*)',re.I)
    for path in sorted(paths):
        data=path.read_bytes();bytes_scanned+=len(data);found=set()
        for match in seed_value.finditer(data):found.update(int(x) for x in re.findall(rb'\d+',match.group(1)))
        for match in seed_assignment.finditer(data):found.add(int(match.group(1).replace(b'_',b'')))
        found={x % (2**32) for x in found if x>=0}
        seeds.update(found)
        entries.append(dict(path=str(path),sha256=hashlib.sha256(data).hexdigest(),seeds=sorted(found)))
    return dict(scope='Relevant expanded Paper2 channel cases, their Python generators and prior comparison initialization/search constants; duplicated archives and zip-only metadata are excluded. Nonnegative historical seed tokens are reduced modulo 2**32 before exclusion. Disjoint seed identifiers are not proof of disjoint PRNG trajectories.',
        case_roots=[str(x) for x in case_roots],engineering_smoke_seed=419812991,
        explicit_prior_initialization_search_seeds=[20261109,20261110,1101],files_scanned=len(paths),bytes_scanned=bytes_scanned,
        seed_count=len(seeds),seeds=sorted(seeds),records=entries,unreadable=[])
def lineage(ss,purpose):
    return dict(purpose=purpose,entropy=str(ss.entropy),spawn_key=list(ss.spawn_key),effective_seed=int(ss.generate_state(1,dtype=np.uint32)[0]))
def prepare(entropy=None):
    history=historical_seed_audit()
    entropy=secrets.randbits(128) if entropy is None else int(entropy)
    root=np.random.SeedSequence(entropy)
    pilot,main,bootstrap=root.spawn(3)
    records=[];profiles=[]
    for phase,namespace,count in [('pilot',pilot,1),('main',main,20)]:
        for block,block_ss in enumerate(namespace.spawn(count)):
            for profile,profile_ss in zip('ABC',block_ss.spawn(3)):
                channel_ss,factor_ss,init_ss,search_ss=profile_ss.spawn(4)
                channels=[lineage(x,'channel') for x in channel_ss.spawn(K)]
                factors=[lineage(x,'large_scale_offset') for x in factor_ss.spawn(K)]
                init=lineage(init_ss,'initialization');search=lineage(search_ss,'stochastic_search')
                item=dict(phase=phase,block=block,profile=profile,spawn_key=list(profile_ss.spawn_key),
                          channels=channels,factors=factors,initialization=init,search=search)
                profiles.append(item);records.extend(channels+factors+[init,search])
    boot=lineage(bootstrap,'bootstrap');records.append(boot)
    effective=[r['effective_seed'] for r in records]
    assert len(effective)==len(set(effective)), 'fresh effective seed collision: stop before generation'
    assert not (set(effective)&set(history['seeds'])), 'historical effective seed collision: stop'
    phy=Path(inspect.getfile(CDL)).parents[2]
    runtime_files=sorted(set(phy.rglob('*.py'))|set(phy.rglob('*.json')))
    manifest=dict(schema='NATIVE_CDL_SEEDS_V1',created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        root_entropy=str(entropy),namespace_spawn_keys=dict(pilot=list(pilot.spawn_key),main=list(main.spawn_key),bootstrap=list(bootstrap.spawn_key)),
        bootstrap=boot,profiles=profiles,effective_seed_count=len(effective),historical_audit=history,
        sources=dict(generator_sha256=digest(__file__),protocol_sha256=digest(BASE/'PROTOCOL.md'),
                     runtime_sha256={str(p):digest(p) for p in runtime_files}),
        environment=dict(python=sys.version,sionna=sionna.__version__,torch=torch.__version__,numpy=np.__version__,device='cpu',precision='double',torch_threads=torch.get_num_threads()),
        design=dict(K=K,S=S,M=M,carrier_hz=3.5e9,delay_spread_s=100e-9,frequency_hz=FREQUENCIES.tolist(),
                    bs_orientation_rad=BS_ORIENTATION,ut_orientation_rad=UT_ORIENTATION,spec_version='19.2',normalize=False,
                    nominal_scale='h = native_h * sqrt(10**((snr_db + offset_db)/10) / 0.1)',
                    offset_distribution='independent per-user uniform[-6,6] dB; frequency flat',
                    sharing='native CIR, offset, initialization and search streams deliberately reused only across paired SNR levels; initialization shared across methods'))
    save_json(BASE/'seed_manifest.json',manifest)
    print(f'PREPARED {len(profiles)} profiles, {len(effective)} unique seeds; excluded {history["seed_count"]} historical tokens',flush=True)

def arrays():
    common=dict(polarization='single',polarization_type='V',antenna_pattern='omni',carrier_frequency=3.5e9,precision='double',device='cpu')
    return Antenna(**common),AntennaArray(num_rows=1,num_cols=2,**common)

def link(profile,seed,ut,bs):
    # All random construction (including CDL ray coupling) follows the reset.
    config.seed=int(seed)
    cdl=CDL(model=profile,delay_spread=100e-9,carrier_frequency=3.5e9,ut_array=ut,bs_array=bs,
            direction='uplink',min_speed=0.,max_speed=0.,
            ut_orientation=torch.tensor(UT_ORIENTATION,dtype=torch.float64),
            bs_orientation=torch.tensor(BS_ORIENTATION,dtype=torch.float64),
            precision='double',device='cpu',spec_version='19.2')
    a,tau=cdl(batch_size=1,num_time_steps=1,sampling_frequency=50e6)
    h=cir_to_ofdm_channel(torch.tensor(FREQUENCIES,dtype=torch.float64),a,tau,normalize=False)
    assert a.dtype==torch.complex128 and h.dtype==torch.complex128 and tau.dtype==torch.float64
    a=a[0,0,:,0,0,:,0].detach().numpy().copy()
    tau=tau[0,0,0,:].detach().numpy().copy()
    h=h[0,0,:,0,0,0,:].detach().numpy().copy()
    assert a.shape==(M,len(tau)) and h.shape==(M,S)
    assert all(np.all(np.isfinite(x)) for x in (a,tau,h))
    return a,tau,h

def coefficients(h):
    re,im=h.real.tolist(),h.imag.tolist()
    vectors={(u,t):[(F(re[u][m][t]),F(im[u][m][t])) for m in range(M)] for u in range(K) for t in range(S)}
    gains={key:sum(x*x+y*y for x,y in vec) for key,vec in vectors.items()}
    pairs=[]
    for u in range(K):
        for v in range(u+1,K):
            for t in range(S):
                g1,g2=gains[u,t],gains[v,t]
                real=sum(x*z+y*w for (x,y),(z,w) in zip(vectors[u,t],vectors[v,t]))
                imag=sum(x*w-y*z for (x,y),(z,w) in zip(vectors[u,t],vectors[v,t]))
                r=(real*real+imag*imag)/(g1*g2) if g1*g2 else F(0)
                assert 0<=r<=1 and g1>0 and g2>0
                pairs.append(dict(users=[u,v],resource=t,gain1=str(g1),gain2=str(g2),r=str(r)))
    return re,im,pairs

def make_profile(item,manifest):
    phase,block,profile=item['phase'],item['block'],item['profile']
    tag=f'pilot-{profile}' if phase=='pilot' else f'native-b{block:02d}-{profile}'
    ut,bs=arrays()
    cs=[x['effective_seed'] for x in item['channels']]
    fs=[x['effective_seed'] for x in item['factors']]
    rows=[link(profile,seed,ut,bs) for seed in cs]
    cir,delays,native=map(np.stack,zip(*rows))
    offsets=np.array([np.random.default_rng(seed).uniform(-6,6) for seed in fs])
    regen=link(profile,cs[0],ut,bs)
    assert all(np.array_equal(x,y) for x,y in zip(rows[0],regen)), 'deterministic regeneration failed'
    fourier=np.einsum('kmp,kps->kms',cir,np.exp(-2j*np.pi*delays[:,:,None]*FREQUENCIES[None,None,:]))
    error=float(np.max(abs(fourier-native)))
    assert error<1e-11*max(1.,float(np.max(abs(native)))), 'independent Fourier reconstruction failed'
    gains=np.sum(abs(native)**2,axis=1)
    variation=np.ptp(gains,axis=1)
    assert np.min(variation)>1e-8, 'unexpected tone-flat/normalized realization'
    assert np.std(gains)>1e-4 and np.max(abs(gains-1))>1e-3, 'unexpected imposed unit gains'
    bspos=bs.ant_pos.detach().numpy();utpos=ut.ant_pos.detach().numpy()
    assert bspos.shape==(2,3) and utpos.shape==(1,3)
    assert abs(np.linalg.norm(bspos[1]-bspos[0])-299792458/3.5e9/2)<1e-12
    native_path=BASE/'native'/f'{tag}.npz'
    with native_path.open('xb') as stream:
        np.savez_compressed(stream,cir=cir,delays_s=delays,native_h=native,frequency_hz=FREQUENCIES,
            offset_db=offsets,channel_seeds=np.array(cs,dtype=np.uint32),factor_seeds=np.array(fs,dtype=np.uint32),
            bs_orientation_rad=np.array(BS_ORIENTATION),ut_orientation_rad=np.array(UT_ORIENTATION),
            bs_ant_pos_m=bspos,ut_ant_pos_m=utpos)
    record=dict(phase=phase,block=block,profile=profile,native_path=native_path.relative_to(BASE).as_posix(),
        native_sha256=digest(native_path),regeneration_bit_exact=True,max_fourier_abs_error=error,
        min_tone_gain_range=float(np.min(variation)),native_gain_quantiles=np.quantile(gains,[0,.1,.5,.9,1]).tolist(),
        native_cir_shape=list(cir.shape),native_delay_shape=list(delays.shape),cases=[])
    for snr in ([10] if phase=='pilot' else [0,10,20]):
        scale=np.sqrt(10.**((snr+offsets)/10)/.1)
        h=native*scale[:,None,None]
        assert np.allclose(h/scale[:,None,None],native,rtol=1e-15,atol=1e-15)
        re,im,pairs=coefficients(h)
        name=f'{tag}-snr{snr:02d}'
        metadata=dict(scene='native-cdl-independent',pilot=phase=='pilot',block=block,profile=profile,snr_db=snr,
            initialization_seed=item['initialization']['effective_seed'],search_seed=item['search']['effective_seed'],
            channel_seeds=cs,factor_seeds=fs,native_path=record['native_path'],native_sha256=record['native_sha256'],
            seed_manifest_sha256=digest(BASE/'seed_manifest.json'),generator_sha256=digest(__file__),
            protocol_sha256=manifest['sources']['protocol_sha256'],offset_db=offsets.tolist(),nominal_perantenna_scale=scale.tolist(),
            frequency_hz=FREQUENCIES.tolist(),bs_orientation_rad=BS_ORIENTATION,ut_orientation_rad=UT_ORIENTATION,
            precision='double',sionna_version=sionna.__version__,spec_version='19.2',normalize=False,
            model='native CDL links, fixed common arrays, raw frequency-selective amplitudes; prescribed large-scale offsets, not spatially consistent deployment')
        case=dict(name=name,K=K,S=S,M=M,pmin='1/1000',pmax='1/5',budget='52/25',pairs=pairs,channels_re=re,channels_im=im,metadata=metadata)
        path=BASE/'cases'/f'{name}.json';save_json(path,case)
        realized=10*np.log10(.1*abs(h)**2)
        record['cases'].append(dict(case_path=path.relative_to(BASE).as_posix(),case_sha256=digest(path),
            snr_db=snr,realized_perantenna_reference_snr_db_quantiles=np.quantile(realized,[0,.1,.5,.9,1]).tolist()))
    return record

def generate(phase):
    manifest=json.loads((BASE/'seed_manifest.json').read_text())
    assert digest(__file__)==manifest['sources']['generator_sha256'], 'generator changed after seed freeze'
    assert digest(BASE/'PROTOCOL.md')==manifest['sources']['protocol_sha256'], 'protocol changed after seed freeze'
    for path,expected in manifest['sources']['runtime_sha256'].items():assert digest(path)==expected, 'runtime source changed'
    if phase=='main':
        pilot=json.loads((BASE/'generator_validation_pilot.json').read_text())
        assert pilot['status']=='PASS' and pilot['generator_sha256']==digest(__file__)
    (BASE/'native').mkdir(exist_ok=True);(BASE/'cases').mkdir(exist_ok=True)
    results=[];begun=time.monotonic()
    for item in manifest['profiles']:
        if item['phase']!=phase:continue
        record=make_profile(item,manifest);results.append(record)
        print(f'{phase} b{item["block"]:02d} {item["profile"]}: Fourier error {record["max_fourier_abs_error"]:.3g}; {len(record["cases"])} cases; {time.monotonic()-begun:.1f}s',flush=True)
    assert len(results)==(3 if phase=='pilot' else 60)
    receipt=dict(status='PASS',phase=phase,generator_sha256=digest(__file__),protocol_sha256=digest(BASE/'PROTOCOL.md'),
        seed_manifest_sha256=digest(BASE/'seed_manifest.json'),seconds=time.monotonic()-begun,
        profile_count=len(results),case_count=sum(len(x['cases']) for x in results),profiles=results,
        gates=dict(unique_disjoint_effective_seeds=True,deterministic_regeneration=True,independent_fourier=True,
                   finite_double_shapes=True,frequency_selective_raw_gains=True,fixed_common_arrays=True,exact_binary64_pair_coefficients=True))
    save_json(BASE/f'generator_validation_{phase}.json',receipt)
    print(f'GENERATION {phase} PASS',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('prepare','pilot','main'))
    parser.add_argument('--entropy',type=int,default=None)
    args=parser.parse_args()
    if args.mode=='prepare':prepare(args.entropy)
    else:generate(args.mode)


