"""Frozen serial native-CDL experiment; all final and retained allocations saved."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import sys
sys.dont_write_bytecode=True
import argparse, hashlib, importlib.util, json, math, platform, time
from pathlib import Path
import numpy as np
import scipy

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD=ROOT/'research/review-20261110/comparison/run_comparison.py'
spec=importlib.util.spec_from_file_location('checked_assignment',OLD)
shared=importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
Problem,guard,DeadlineReached=shared.Problem,shared.guard,shared.DeadlineReached
ARMS=('DP-SQP','DP-Fu-SCA','DP-Thu-IDE','Fixed-SQP','DP-uniform')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')
    temp.replace(path)

def record(candidate,seconds,kind):
    return dict(kind=kind,seconds=seconds,schedule=candidate['schedule'],
                rate_nats=candidate['value'],se_bits=candidate['value']/(8*math.log(2)),
                lower_nats=str(candidate['lo']),upper_nats=str(candidate['hi']))

def starts_for(problem,seed):
    rng=np.random.default_rng(seed)
    sequential=tuple((2*s,2*s+1) for s in range(problem.s))
    result=[(sequential,problem.repair([problem.budget/problem.k]*problem.k))]
    for _ in range(7):
        perm=list(map(int,rng.permutation(problem.k)))
        pairs=tuple(tuple(sorted(perm[2*s:2*s+2])) for s in range(problem.s))
        p=problem.repair(float(problem.low)+rng.random(problem.k)*float(problem.high-problem.low))
        problem.model.decode(problem.model.encode(pairs,p))
        result.append((pairs,p))
    return result

def solve(problem,starts,arm,search_seed,cap,block):
    shared.certificates.clear_caches()
    rng=np.random.default_rng(search_seed)
    problem.common_power_starts=[np.asarray(p,float) for _,p in starts]
    begun=time.monotonic();deadline=begun+cap
    best=problem.checked_candidate(*starts[0])
    problem.matrix_scalar_check(best)
    history=[record(best,time.monotonic()-begun,'initial')]
    diagnostics=[]
    counts=dict(starts_started=0,starts_completed=0,dp_completed=0,power_calls=0,accepted=0)
    reason='starts_exhausted'
    def retain(a,p,diagnostic=None):
        nonlocal best
        guard(deadline)
        candidate=problem.checked_candidate(a,p)
        problem.matrix_scalar_check(candidate)
        guard(deadline)
        if problem.improves(candidate,best):
            best=candidate;counts['accepted']+=1
            history.append(record(best,time.monotonic()-begun,'improvement'))
        return candidate
    try:
        if arm=='DP-uniform':
            counts['starts_started']=1
            a,value=shared.dp_assignment(problem.k,problem.lookup,starts[0][1],deadline)
            counts['dp_completed']=1
            candidate=retain(a,starts[0][1])
            assert abs(candidate['value']-value)<1e-7
            counts['starts_completed']=1;reason='uniform_dp_complete'
        else:
            for a,p in starts:
                guard(deadline);counts['starts_started']+=1
                if arm=='Fixed-SQP':a=starts[0][0]
                current=retain(a,p)
                for _ in range(8):
                    guard(deadline);before=current
                    if arm!='Fixed-SQP':
                        a,value=shared.dp_assignment(problem.k,problem.lookup,current['powers'],deadline)
                        counts['dp_completed']+=1
                        current=retain(a,current['powers'])
                        assert abs(current['value']-value)<1e-7
                    block_deadline=min(deadline,time.monotonic()+block)
                    counts['power_calls']+=1
                    if arm in ('DP-SQP','Fixed-SQP'):
                        stop=time.perf_counter()+max(0.,block_deadline-time.monotonic())
                        pp,d=shared.producer.refine(a,current['powers'],problem.model.data,
                                                  problem.low,problem.high,problem.budget,stop)
                        d['method']='LOCAL_SQP'
                    else:
                        fn=shared.fu_sca.refine_power if arm=='DP-Fu-SCA' else shared.thu_ide.refine_power
                        pp,d=fn(problem,a,current['numeric'],block_deadline,rng,retain)
                    diagnostics.append(d)
                    candidate=retain(a,pp)
                    if problem.improves(candidate,current):current=candidate
                    if current['assignment']==before['assignment'] and abs(current['value']-before['value'])<=1e-9*max(1.,abs(before['value'])):
                        break
                counts['starts_completed']+=1
    except DeadlineReached:
        reason='deadline'
    elapsed=time.monotonic()-begun
    final_began=time.monotonic()
    assignment,powers=problem.model.decode(best['schedule'])
    audit=problem.matrix_scalar_check(best)
    assert min(powers)>=problem.low and max(powers)<=problem.high and sum(powers)<=problem.budget
    assert all(item['seconds']<=cap for item in history),'late retained allocation'
    assert best['value']>=history[0]['rate_nats']-1e-9
    assert math.isfinite(best['value'])
    return dict(arm=arm,rate_nats=best['value'],se_bits=best['value']/(problem.s*math.log(2)),
                lower_nats=str(best['lo']),upper_nats=str(best['hi']),schedule=best['schedule'],
                total_power=str(sum(powers)),elapsed_seconds=elapsed,cap_seconds=cap,
                block_seconds=block,overrun_seconds=max(0.,elapsed-cap),
                audit_seconds=time.monotonic()-final_began,audit=audit,status=reason,
                counts=counts,history=history,diagnostics=diagnostics)

def freeze():
    method=ROOT/'research/dual-track-revision-20261103/method'
    files=[Path(__file__),HERE/'PROTOCOL.md',HERE/'generator.py',HERE/'seed_manifest.json',HERE/'analysis.py',HERE/'audit_campaign.py',OLD,
           ROOT/'research/manuscript-refinement-20261106/certification/producer.py']
    files+=sorted((method/'core').rglob('*.py'))+sorted((method/'modern').rglob('*.py'))
    # Include live project helpers such as integer_logs, not just direct imports.
    for module in tuple(sys.modules.values()):
        path=getattr(module,'__file__',None)
        if path:
            path=Path(path).resolve()
            if ROOT in path.parents and path.suffix=='.py':files.append(path)
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    path=HERE/'source_manifest.json'
    if path.exists():
        saved=json.loads(path.read_text())
        assert saved['hashes']==hashes,'frozen scientific source changed'
        return saved
    saved=dict(hashes=hashes,python=sys.version,numpy=np.__version__,scipy=scipy.__version__,
               platform=platform.platform(),created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    dump(path,saved)
    return saved

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',required=True,choices=['pilot','pilot-sensitivity','main','sensitivity'])
    args=parser.parse_args()
    shared.self_check()
    stage=args.stage
    pilot=stage.startswith('pilot')
    sensitivity='sensitivity' in stage
    cap,block=(30.,10.) if sensitivity else (10.,5.)
    arms=ARMS[:3] if sensitivity else ARMS
    if not pilot:
        gate=json.loads((HERE/'PREFLIGHT.json').read_text())
        assert gate['passed'] is True,'preflight not accepted'
    frozen=freeze()
    if not pilot:
        assert gate['source_manifest_sha256']==sha(HERE/'source_manifest.json'),'preflight source mismatch'
    cases=[]
    for path in sorted((HERE/'cases').glob('*.json')):
        case=json.loads(path.read_text())
        meta=case['metadata']
        if bool(meta['pilot'])!=pilot:continue
        if sensitivity and (meta['profile']!='B' or meta['snr_db']!=10):continue
        cases.append((path,case))
    expected=(1 if sensitivity else 3) if pilot else (20 if sensitivity else 180)
    assert len(cases)==expected,(stage,len(cases),expected)
    target=HERE/'runs'/stage
    target.mkdir(parents=True,exist_ok=True)
    assert not list(target.glob('*-FAILURE.json')),'document and resolve saved failures before resuming'
    manifest=dict(stage=stage,source_manifest_sha256=sha(HERE/'source_manifest.json'),cap_seconds=cap,
                  block_seconds=block,arms=arms,cases={p.relative_to(HERE).as_posix():sha(p) for p,_ in cases})
    if (target/'manifest.json').exists():
        assert json.loads((target/'manifest.json').read_text())==json.loads(json.dumps(manifest)), 'resume manifest mismatch'
    else:dump(target/'manifest.json',manifest)
    for index,(path,case) in enumerate(cases):
        metadata=case['metadata'];case_hash=sha(path)
        prepare=time.monotonic()
        problem=Problem(case)
        starts=starts_for(problem,metadata['initialization_seed'])
        preparation_seconds=time.monotonic()-prepare
        starts_path=target/(case['name']+'-starts.json')
        offered=[problem.model.encode(a,p) for a,p in starts]
        if not starts_path.exists():
            dump(starts_path,dict(case_sha256=case_hash,initialization_seed=metadata['initialization_seed'],
                 preparation_seconds=preparation_seconds,starts=offered))
        else:
            saved_starts=json.loads(starts_path.read_text())
            assert saved_starts['case_sha256']==case_hash and saved_starts['initialization_seed']==metadata['initialization_seed']
            assert saved_starts['starts']==offered,'offered starts changed on resume'
        order=arms[index%len(arms):]+arms[:index%len(arms)]
        for arm in order:
            destination=target/(case['name']+'-'+arm+'.json')
            if destination.exists():
                saved=json.loads(destination.read_text())
                assert saved['case_sha256']==case_hash and saved['source_manifest_sha256']==sha(HERE/'source_manifest.json')
                problem.model.decode(saved['schedule'])
                continue
            try:
                result=solve(problem,starts,arm,metadata['search_seed'],cap,block)
                result.update(case=case['name'],block=metadata['block'],profile=metadata['profile'],
                    snr_db=metadata['snr_db'],stage=stage,case_path=path.relative_to(HERE).as_posix(),
                    case_sha256=case_hash,source_manifest_sha256=sha(HERE/'source_manifest.json'),
                    initialization_seed=metadata['initialization_seed'],search_seed=metadata['search_seed'],
                    order=list(order),preparation_seconds=preparation_seconds)
                if result['overrun_seconds']>=.5:
                    dump(target/(case['name']+'-'+arm+'-rejected.json'),result)
                    raise AssertionError('unexpected deadline overrun')
                dump(destination,result)
                print(f'{stage} {index+1}/{len(cases)} {case["name"]} {arm}: {result["se_bits"]:.8f} bit/s/Hz; '
                      f'{result["elapsed_seconds"]:.3f}s; {result["counts"]}',flush=True)
            except Exception as exc:
                dump(target/(case['name']+'-'+arm+'-FAILURE.json'),
                     dict(case=case['name'],arm=arm,error=repr(exc),source_manifest_sha256=sha(HERE/'source_manifest.json')))
                raise
    # Check sources again after a long run, without importing another implementation.
    assert all(sha(ROOT/name)==digest for name,digest in frozen['hashes'].items()),'source changed during run'
    print('COMPLETE',stage,len(cases)*len(arms),'saved allocations',flush=True)

if __name__=='__main__':main()
