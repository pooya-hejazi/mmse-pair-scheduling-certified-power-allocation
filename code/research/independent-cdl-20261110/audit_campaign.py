"""Independent saved-allocation and native-channel audit; never imports a runner.

--pilot checks the 15 engineering arms plus three sensitivity arms. Default checks
all 900 main and 60 sensitivity records. --self-test writes no outcome evidence.
"""
from pathlib import Path
import argparse
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING
from fractions import Fraction as F
import hashlib
import importlib.util
import json
import math
import sys
import time

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
CERT = PROJECT/'research/manuscript-refinement-20261106/certification'
sys.path.insert(0, str(CERT))
spec = importlib.util.spec_from_file_location('independent_schedule_checker', CERT/'checker.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
ARMS = ('DP-SQP', 'DP-Fu-SCA', 'DP-Thu-IDE', 'Fixed-SQP', 'DP-uniform')
FREQUENCIES = np.array([-14,-10,-6,-2,2,6,10,14])*(50e6/32)


def require(test, message):
    if not test:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def local_path(base, relative):
    require(isinstance(relative,str) and not Path(relative).is_absolute(), 'Expected a relative evidence path')
    path = (base/relative).resolve()
    require(path.is_relative_to(base.resolve()), 'Evidence path escapes its root')
    return path


def scalar_decimal_interval(schedule, model):
    # Independent 100-digit outward arithmetic also checks the runner's tighter saved interval.
    data = model[5]
    total_low = total_high = F(0)
    with localcontext() as context:
        context.prec = 100
        def log_bounds(value):
            context.rounding = ROUND_FLOOR
            low = Decimal(value.numerator)/Decimal(value.denominator)
            context.rounding = ROUND_CEILING
            high = Decimal(value.numerator)/Decimal(value.denominator)
            return F(low.ln().next_minus()), F(high.ln().next_plus())
        for row in schedule:
            u,v = row['users']; resource = row['resource']
            p,q = map(F,row['powers']);g,h,r = data[u,v,resource]
            x,y = g*p,h*q
            dl,du = log_bounds(1+x+y+(1-r)*x*y)
            al,au = log_bounds(1+x);bl,bu = log_bounds(1+y)
            total_low += 2*dl-au-bu
            total_high += 2*du-al-bl
    return total_low,total_high


def evaluate(schedule, model, channels):
    lower,upper = checker.check_schedule(schedule,model)
    dl,du = scalar_decimal_interval(schedule,model)
    require(lower <= dl <= du <= upper, 'Independent integer and Decimal rate bounds disagree')
    matrix = 0.
    for row in schedule:
        pair = row['users']; powers = list(map(F,row['powers'])); resource = row['resource']
        for j,user in enumerate(pair):
            channel = channels[user,:,resource]
            other = channels[pair[1-j],:,resource]
            covariance = np.eye(channels.shape[1],dtype=complex)+float(powers[1-j])*np.outer(other,other.conj())
            sinr = float(powers[j])*np.vdot(channel,np.linalg.solve(covariance,channel)).real
            require(math.isfinite(sinr) and sinr>=0, 'Invalid independently reconstructed SINR')
            matrix += math.log1p(sinr)
    return dict(lower=lower,upper=upper,decimal_lower=dl,decimal_upper=du,matrix=matrix)


def check_reported(record, evaluated):
    low,high = F(record['lower_nats']),F(record['upper_nats'])
    require(low <= evaluated['decimal_lower'] <= evaluated['decimal_upper'] <= high,
            'Saved rate enclosure does not contain independent high-precision enclosure')
    value,se = record['rate_nats'],record['se_bits']
    require(all(isinstance(x,(int,float)) and math.isfinite(x) for x in (value,se)), 'Nonfinite reported rate')
    error = abs(value-float((evaluated['lower']+evaluated['upper'])/2))
    require(error < 1e-9 and abs(value-evaluated['matrix']) < 1e-8,
            'Reported scalar rate differs from independent evaluation')
    require(abs(se-value/(8*math.log(2))) < 1e-11, 'Occupied-band SE normalization')
    return error,abs(value-evaluated['matrix'])


def seed_audit(manifest):
    profiles = manifest['profiles']
    expected = {('pilot',0,p) for p in 'ABC'}|{('main',b,p) for b in range(20) for p in 'ABC'}
    mapping = {(r['phase'],r['block'],r['profile']):r for r in profiles}
    require(len(mapping)==len(profiles) and set(mapping)==expected, 'Seed-profile population mismatch')
    records = [manifest['bootstrap']]
    for profile in profiles:
        require(len(profile['channels'])==len(profile['factors'])==16, 'User seed count')
        records += profile['channels']+profile['factors']+[profile['initialization'],profile['search']]
    used=[]
    for row in records:
        seed = row['effective_seed']
        require(type(seed) is int and 0<=seed<2**32, 'Effective seed is not uint32')
        require(int(row['entropy'])==int(manifest['root_entropy']), 'Seed entropy mismatch')
        rebuilt=int(np.random.SeedSequence(int(row['entropy']),spawn_key=tuple(row['spawn_key']))
                    .generate_state(1,dtype=np.uint32)[0])
        require(seed==rebuilt, 'SeedSequence lineage reconstruction failed')
        used.append(seed)
    require(len(used)==len(set(used))==manifest['effective_seed_count'], 'Duplicate effective purpose seed')
    historical=set(manifest['historical_audit']['seeds'])
    require(not set(used)&historical, 'Fresh/historical seed identifiers intersect')
    return mapping,dict(effective_seed_count=len(used),historical_identifiers=len(historical),
        seedsequence_lineage_reconstructed=True,duplicates=0,historical_intersections=0,
        limitation='Disjoint identifiers and SeedSequence lineage are not mathematical proof of independent PRNG trajectories; historical exclusion is scoped to the frozen recorded audit.')


def native_audit(case, profile, native_cache):
    metadata=case['metadata']
    path=local_path(HERE,metadata['native_path'])
    require(sha(path)==metadata['native_sha256'], 'Native NPZ hash mismatch')
    if path not in native_cache:
        with np.load(path,allow_pickle=False) as archive:
            arrays={key:archive[key] for key in archive.files}
        cir,delays,h=arrays['cir'],arrays['delays_s'],arrays['native_h']
        require(cir.ndim==3 and cir.shape[:2]==(16,2) and delays.shape==(16,cir.shape[2])
                and h.shape==(16,2,8), 'Native CIR/delay/frequency shape')
        require(all(np.isfinite(x).all() for x in (cir,delays,h,arrays['offset_db'])), 'Nonfinite native values')
        require(cir.dtype==np.complex128 and h.dtype==np.complex128 and delays.dtype==np.float64,
                'Native channel precision is not binary64')
        require(np.array_equal(arrays['frequency_hz'],FREQUENCIES), 'Unexpected frequency sample grid')
        require(np.array_equal(arrays['bs_orientation_rad'],np.zeros(3)) and
                np.allclose(arrays['ut_orientation_rad'],[np.pi,0,0],rtol=0,atol=1e-15), 'Noncommon array orientations')
        require(arrays['bs_ant_pos_m'].shape==(2,3) and arrays['ut_ant_pos_m'].shape==(1,3), 'Antenna positions')
        require(abs(np.linalg.norm(np.diff(arrays['bs_ant_pos_m'],axis=0))-299792458/3.5e9/2)<1e-12,
                'BS array is not half-wavelength')
        fourier=np.einsum('kmp,kps->kms',cir,np.exp(-2j*np.pi*delays[:,:,None]*FREQUENCIES[None,None,:]))
        error=float(np.max(abs(fourier-h)))
        require(error<1e-11*max(1.,float(np.max(abs(h)))), 'Independent CIR Fourier reconstruction')
        gain=np.sum(abs(h)**2,axis=1)
        require(np.all(np.ptp(gain,axis=1)>1e-8), 'Unexpected normalized or tone-flat native channel')
        arrays['_fourier_error']=error
        native_cache[path]=arrays
    arrays=native_cache[path]
    channel_seeds=[x['effective_seed'] for x in profile['channels']]
    factor_seeds=[x['effective_seed'] for x in profile['factors']]
    require(np.array_equal(arrays['channel_seeds'],channel_seeds) and
            np.array_equal(arrays['factor_seeds'],factor_seeds), 'Native seed assignment mismatch')
    require(metadata['channel_seeds']==channel_seeds and metadata['factor_seeds']==factor_seeds,
            'Case seed assignment mismatch')
    offsets=np.array([np.random.default_rng(seed).uniform(-6,6) for seed in factor_seeds])
    require(np.array_equal(offsets,arrays['offset_db']) and np.array_equal(offsets,metadata['offset_db']),
            'Large-scale factor regeneration failed')
    scale=np.sqrt(10.**((metadata['snr_db']+offsets)/10)/.1)
    channels=np.asarray(case['channels_re'])+1j*np.asarray(case['channels_im'])
    require(channels.shape==(16,2,8) and np.isfinite(channels).all(), 'Stored channel shape/finite')
    require(np.allclose(channels,arrays['native_h']*scale[:,None,None],rtol=2e-14,atol=1e-14),
            'Case differs from declared frequency-flat nominal-SNR scaling')
    require(metadata['initialization_seed']==profile['initialization']['effective_seed'] and
            metadata['search_seed']==profile['search']['effective_seed'], 'Purpose seed metadata mismatch')
    require(metadata['normalize'] is False and metadata['spec_version']=='19.2', 'Native CDL convention')
    return channels


def audit(pilot=False):
    began=time.monotonic()
    destination=HERE/('audit_campaign_pilot.json' if pilot else 'audit_campaign.json')
    report=dict(status='FAIL',scope='pilot' if pilot else 'main-and-sensitivity',errors=[])
    context='source and seed preflight'
    try:
        source=read(HERE/'source_manifest.json'); source_hash=sha(HERE/'source_manifest.json')
        for path,digest in source['hashes'].items():
            require(sha(local_path(PROJECT,path))==digest, 'Frozen source hash changed: '+path)
        manifest=read(HERE/'seed_manifest.json'); seed_hash=sha(HERE/'seed_manifest.json')
        require(sha(HERE/'generator.py')==manifest['sources']['generator_sha256'], 'Generator seed freeze hash')
        require(sha(HERE/'PROTOCOL.md')==manifest['sources']['protocol_sha256'], 'Protocol seed freeze hash')
        profile_seeds,seed_report=seed_audit(manifest)
        phase='pilot' if pilot else 'main'
        generation=read(HERE/f'generator_validation_{phase}.json')
        require(generation['status']=='PASS' and generation['seed_manifest_sha256']==seed_hash
                and generation['generator_sha256']==sha(HERE/'generator.py'), 'Generator preflight receipt')
        stages=('pilot','pilot-sensitivity') if pilot else ('main','sensitivity')
        models={}; channels_cache={}; native_cache={}; evaluations={}; common_starts={}
        runs_hashes={}; extra_hashes={}; receipts=[]; max_scalar=max_matrix=0.
        final_count=history_count=starts_count=0
        for stage in stages:
            folder=HERE/'runs'/stage
            stage_manifest=read(folder/'manifest.json')
            is_long='sensitivity' in stage
            cap,block=(30.,10.) if is_long else (10.,5.)
            arms=ARMS[:3] if is_long else ARMS
            profiles=('B',) if is_long else tuple('ABC')
            snrs=(10,) if pilot or is_long else (0,10,20)
            blocks=(0,) if pilot else tuple(range(20))
            expected={(b,p,s,a) for b in blocks for p in profiles for s in snrs for a in arms}
            require(stage_manifest['source_manifest_sha256']==source_hash and
                    stage_manifest['cap_seconds']==cap and stage_manifest['block_seconds']==block,
                    'Stage/source manifest mismatch')
            extra_hashes[str((folder/'manifest.json').relative_to(HERE)).replace('\\','/')]=sha(folder/'manifest.json')
            files=[p for p in sorted(folder.glob('*.json')) if p.name!='manifest.json' and not p.name.endswith('-starts.json')]
            seen=set()
            for path in files:
                context=str(path.relative_to(HERE))
                require('FAILURE' not in path.name and 'rejected' not in path.name.lower(), 'Unresolved failed/rejected run')
                row=read(path); key=(row['block'],row['profile'],row['snr_db'],row['arm'])
                require(key in expected and key not in seen, 'Unexpected/duplicate result identity')
                seen.add(key)
                require(row['stage']==stage and row['source_manifest_sha256']==source_hash, 'Result stage/source binding')
                case_path=local_path(HERE,row['case_path'])
                require(sha(case_path)==row['case_sha256']==stage_manifest['cases'][row['case_path']], 'Case hash binding')
                case=read(case_path); metadata=case['metadata']
                require(case['name']==row['case'] and (metadata['block'],metadata['profile'],metadata['snr_db'])==key[:3]
                        and bool(metadata['pilot'])==pilot, 'Case identity/namespace mismatch')
                require(metadata['seed_manifest_sha256']==seed_hash, 'Case seed-manifest binding')
                require((case['K'],case['S'],case['M'])==(16,8,2) and
                        tuple(map(F,(case['pmin'],case['pmax'],case['budget'])))==(F(1,1000),F(1,5),F(52,25)),
                        'Case dimension or physical power domain')
                if row['case_path'] not in models:
                    profile=profile_seeds[phase,metadata['block'],metadata['profile']]
                    channels_cache[row['case_path']]=native_audit(case,profile,native_cache)
                    models[row['case_path']]=checker.reconstruct(case)
                    extra_hashes[row['case_path']]=sha(case_path)
                model=models[row['case_path']];channels=channels_cache[row['case_path']]
                starts_path=folder/(case['name']+'-starts.json'); starts_record=read(starts_path)
                require(starts_record['case_sha256']==row['case_sha256'] and
                        starts_record['initialization_seed']==metadata['initialization_seed'] and
                        len(starts_record['starts'])==8, 'Offered-start binding')
                start_hash=sha(starts_path)
                if str(starts_path) not in common_starts:
                    for schedule in starts_record['starts']:
                        checker.check_schedule(schedule,model);starts_count+=1
                    common_starts[str(starts_path)]=start_hash
                    extra_hashes[str(starts_path.relative_to(HERE)).replace('\\','/')]=start_hash
                pair_key=(phase,metadata['block'],metadata['profile'])
                if pair_key in common_starts:
                    require(starts_record['starts']==common_starts[pair_key], 'Starts changed across paired SNR/budget cases')
                else:
                    common_starts[pair_key]=starts_record['starts']
                require(row['initialization_seed']==metadata['initialization_seed'] and
                        row['search_seed']==metadata['search_seed'], 'Run RNG binding')
                require(row['cap_seconds']==cap and row['block_seconds']==block and
                        math.isfinite(row['elapsed_seconds']) and row['elapsed_seconds']>=0 and
                        0<=row['overrun_seconds']<.5 and
                        abs(row['overrun_seconds']-max(0,row['elapsed_seconds']-cap))<1e-8,
                        'Recorded timing/cap/overrun')
                history=row['history']
                require(isinstance(history,list) and history and history[0]['kind']=='initial' and
                        history[0]['schedule']==starts_record['starts'][0], 'Initial feasible anchor/history')
                require(row['counts']['accepted']==len(history)-1, 'Accepted-history count mismatch')
                previous_time=-1.; previous_rate=-math.inf
                for index,item in enumerate(history+[row]):
                    if index<len(history):
                        require(math.isfinite(item['seconds']) and previous_time<=item['seconds']<=cap,
                                'Late or nonmonotone retained history')
                        require(index==0 or item['kind']=='improvement', 'Unexpected retained event')
                        require(item['rate_nats']>=previous_rate, 'Retained objective decreased')
                        previous_time=item['seconds'];previous_rate=item['rate_nats'];history_count+=1
                    ident=(row['case_path'],canonical(item['schedule']))
                    if ident not in evaluations:
                        evaluations[ident]=evaluate(item['schedule'],model,channels)
                    receipt=evaluations[ident]
                    scalar_error,matrix_error=check_reported(item,receipt)
                    max_scalar=max(max_scalar,scalar_error);max_matrix=max(max_matrix,matrix_error)
                    receipts.append(dict(result=context,event='final' if index==len(history) else index,
                        independent_lower_nats=str(receipt['lower']),independent_upper_nats=str(receipt['upper']),
                        scalar_error_nats=scalar_error,matrix_error_nats=matrix_error))
                require(row['schedule']==history[-1]['schedule'] and row['rate_nats']==history[-1]['rate_nats'],
                        'Final allocation differs from last accepted incumbent')
                if row['arm']=='Fixed-SQP':
                    require(all(part['users']==[2*part['resource'],2*part['resource']+1] for part in row['schedule']),
                            'Fixed-pair ablation changed sequential pairing')
                if row['arm']=='DP-uniform':
                    require(all(F(p)==F(13,100) for part in row['schedule'] for p in part['powers']),
                            'Uniform-power ablation changed powers')
                runs_hashes[context.replace('\\','/')]=sha(path);final_count+=1
            require(seen==expected, f'Incomplete {stage}: {len(seen)} of {len(expected)}')
            require(len(stage_manifest['cases'])==len(expected)//len(arms), 'Stage case count')
        require(final_count==(18 if pilot else 960), 'Full allocation count')
        report.update(status='PASS',final_allocations=final_count,retained_history_allocations=history_count,
            offered_starts_checked=starts_count,unique_schedules_evaluated=len(evaluations),
            case_count=len(models),native_profile_count=len(native_cache),
            max_scalar_error_nats=max_scalar,max_matrix_error_nats=max_matrix,
            max_fourier_error=max(x['_fourier_error'] for x in native_cache.values()),
            seed_audit=seed_report,source_manifest_sha256=source_hash,seed_manifest_sha256=seed_hash,
            runs_sha256=runs_hashes,additional_evidence_sha256=extra_hashes,
            checker_sources_sha256={name:sha(CERT/name) for name in ('checker.py','integer_logs.py')},
            qualification='Independent rate enclosures evaluate feasible allocations; they are not bounds on the network optimum. No optimizer or generator module was imported.')
        for native_path in native_cache:
            report['additional_evidence_sha256'][str(native_path.relative_to(HERE)).replace('\\','/')]=sha(native_path)
        report['receipts_file']='audit_receipts_pilot.json' if pilot else 'audit_receipts.json'
        (HERE/report['receipts_file']).write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf-8')
    except Exception as exc:
        report['errors'].append(dict(context=context,error=type(exc).__name__+': '+str(exc)))
    report['seconds']=time.monotonic()-began
    destination.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','scope','seconds','errors')}))
    if report['status']!='PASS':
        raise SystemExit(1)


def self_test():
    # Four orthogonal fixture users; these self-check values are never saved as results.
    h=np.zeros((4,2,2),complex)
    h[0,0,:]=1;h[1,1,:]=1;h[2,0,:]=2;h[3,1,:]=2
    pairs=[]
    for u in range(4):
        for v in range(u+1,4):
            for s in range(2):
                g=F(float(np.vdot(h[u,:,s],h[u,:,s]).real));q=F(float(np.vdot(h[v,:,s],h[v,:,s]).real))
                r=F(float(abs(np.vdot(h[u,:,s],h[v,:,s]))**2))/(g*q)
                pairs.append(dict(users=[u,v],resource=s,gain1=str(g),gain2=str(q),r=str(r)))
    case=dict(K=4,S=2,M=2,pmin='1/1000',pmax='1/5',budget='2/5',
              channels_re=h.real.tolist(),channels_im=h.imag.tolist(),pairs=pairs)
    model=checker.reconstruct(case)
    schedule=[dict(users=[0,1],resource=0,powers=['1/10','1/10']),
              dict(users=[2,3],resource=1,powers=['1/10','1/10'])]
    checked=evaluate(schedule,model,h)
    require(abs(checked['matrix']-2*math.log1p(.1)-2*math.log1p(.4))<1e-14,'Fixture matrix mismatch')
    bad=json.loads(json.dumps(schedule));bad[0]['powers'][0]='1/4'
    try:
        evaluate(bad,model,h)
    except ValueError:
        pass
    else:
        raise AssertionError('Power-box violation was accepted')
    require(checked['lower']<=checked['decimal_lower']<=checked['decimal_upper']<=checked['upper'],
            'Outward arithmetic mismatch')
    print('PASS: independent channel reconstruction, integer/Decimal enclosure, matrix rate and infeasibility rejection; no outcomes written')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot',action='store_true')
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    self_test() if args.self_test else audit(args.pilot)
