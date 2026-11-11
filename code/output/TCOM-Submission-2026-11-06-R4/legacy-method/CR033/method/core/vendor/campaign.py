"""One fixed prospective campaign; all cases recorded, no reruns."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import json,sys,time,subprocess,argparse,hashlib
import numpy as np
import psutil
from persistence import publish
from generate_cases import check_gate
from controller import launch
W=Path(__file__).resolve().parents[1];D=Path(__file__).parent

def run_bounded(cmd,stream,seconds):
    """Owned subprocess tree, wall/RSS caps; no retry or inherited console."""
    began=time.perf_counter();proc=subprocess.Popen(cmd,stdout=stream,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    parent=psutil.Process(proc.pid)
    try:
        while proc.poll() is None:
            try:members=[parent]+parent.children(recursive=True)
            except psutil.Error:members=[]
            rss=0
            for member in members:
                try:rss+=member.memory_info().rss
                except psutil.Error:pass
            if rss>8*1024**3:raise MemoryError('worker tree exceeds registered 8GiB RSS')
            if time.perf_counter()-began>=seconds:raise subprocess.TimeoutExpired(cmd,seconds)
            time.sleep(.02)
        return subprocess.CompletedProcess(cmd,proc.returncode)
    finally:
        if proc.poll() is None:
            try:children=parent.children(recursive=True)
            except psutil.Error:children=[]
            for child in reversed(children):
                try:child.kill()
                except psutil.Error:pass
            proc.kill();proc.wait()

def validate_generation(target,scene):
    """An entire scene is eligible only with all registered, hash-matched cases."""
    report=json.loads((target/'generation.json').read_text())
    assert report['protocol']=='CR024' and report['complete'] is True and report['coordinate_disjointness'] is True
    validity=report['input_validity'];wave=report['waveform']
    assert validity['all_retained_delays_below_fixed_guard'] and validity['pool_nonzero_users']>0
    assert wave['NFFT']==wave['CP_samples']==512 and wave['guard_seconds']==512/50e6 and wave['payload_SE_guard_factor']==.5
    assert validity['maximum_delay_seconds'] is not None and 0<=validity['minimum_delay_seconds']<=validity['maximum_delay_seconds']<wave['guard_seconds']
    assert all(report['selected_case_counts'][p]['nontrivial_cases']>0 for p in ['main','scale'])
    expected={f'{scene}-{panel}-{i:02d}' for panel,n in [('main',12),('scale',4)] for i in range(n)}
    rows=report['cases'];assert report['scene']==scene and len(rows)==16 and {r['name'] for r in rows}==expected
    assert hashlib.sha256((target/'pool.npz').read_bytes()).hexdigest()==report['source_pool_sha256']
    for row in rows:
        p=target/(row['name']+'.json');assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
        case=json.loads(p.read_text());assert case['name']==row['name'] and case['metadata']['scene']==scene
        meta=case['metadata'];assert meta['protocol']=='CR024' and meta['NFFT']==meta['CP_samples']==512
        assert meta['actual_FFT_indices']==[16*i for i in meta['resources']]
        assert 'gross' in meta['SE_scope'] and meta['payload_SE_guard_factor']==.5
        assert row['nontrivial']==bool(np.count_nonzero(case['channels_re'])+np.count_nonzero(case['channels_im']))
    return True

def account_diagnostics(folder):
    names=[f'c{c}-g{g}-s{s}' for c in [0.,.85] for g in [1.,100.] for s in [202611240,202611241]]
    ledger=folder/'diagnostic-ledger.json'
    existing={r['case']:r for r in json.loads(ledger.read_text())} if ledger.exists() else {}
    return [existing.get(n,{'case':n,'status':'INTERRUPTED_DIAGNOSTIC' if (folder/n/'case.json').exists() else 'NOT_RUN_DIAGNOSTIC_BLOCK','raw_files':[p.name for p in (folder/n).glob('*')]}) for n in names]

def dispatch_plan():
    rng=np.random.default_rng(202611330);blocks=[]
    for panel,n,methods,charged in [('main',12,['grid','curvature','full','joint'],18),('scale',4,['grid','pricing','joint'],28)]:
        for scene in ['o1','asu']:
            for i in range(n):
                case=f'{scene}-{panel}-{i:02d}'
                blocks.append([dict(panel=panel,scene=scene,index=i,case=case,method=str(m),charged=charged,seed=1101+i+(100 if scene=='asu' else 0)) for m in rng.permutation(methods)])
    reps=[dict(panel='reliability',scene='analytic',index=i,case='registered-reliability-fixture',method=m,charged=8,seed=1101) for i in range(2) for m in ['grid','curvature','full','joint']]
    np.random.default_rng(202611350).shuffle(reps);blocks.extend([[r] for r in reps]);return blocks

def main(a):
    check_gate(a.go)
    assert sys.version_info[:2]==(3,12) and Path(sys.executable).resolve()==Path('C:/ProgramData/anaconda3/python.exe').resolve(),'Original compatible controller clock required'
    original=W.parent/'campaign/LOCK.json';old=json.loads(original.read_text());began=time.perf_counter();stop=old['deadline']
    assert old['started_at']<began<stop and abs(stop-old['started_at']-3600)<.001,'Original absolute deadline expired or invalid'
    out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    plan=dispatch_plan();publish(out/'LOCK.json',{'started_at':began,'deadline':stop,'original_started_at':old['started_at'],'original_lock_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'go_sha256':hashlib.sha256(Path(a.go).read_bytes()).hexdigest(),'scope':'Separate CR024 post-diagnosis study, original absolute deadline retained. No scientific cell rerun.'})
    publish(out/'dispatch-plan.json',plan);generated={}
    fixture=W/'preflight/integration/case.json';fixture_dest=out/'inputs/reliability/registered-reliability-fixture.json'
    published=publish(fixture_dest,json.loads(fixture.read_text()))
    publish(out/'reliability-input.json',{'source_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'artifact_sha256':published['sha256'],'artifact_path':fixture_dest.relative_to(out).as_posix()})
    for scene in ['o1','asu']:
        target=out/'inputs'/scene
        with (out/(scene+'-generation.log')).open('xb') as stream:
            try:
                if stop-time.perf_counter()<=60:raise subprocess.TimeoutExpired('generation budget unavailable',0)
                cp=run_bounded(['C:/ProgramData/anaconda3/envs/6g_project/python.exe','-B',str(D/'generate_cases.py'),'--go',str(Path(a.go).resolve()),'--scene',scene,'--output',str(target.resolve())],stream,min(200,stop-time.perf_counter()-60))
                generated[scene]={'returncode':cp.returncode,'complete':cp.returncode==0 and validate_generation(target,scene)}
            except subprocess.TimeoutExpired:generated[scene]={'complete':False,'status':'GENERATION_TIME_LIMIT'}
            except Exception as e:generated[scene]={'complete':False,'status':'GENERATION_ERROR','error':repr(e)}
    publish(out/'generation-status.json',generated);rows=[]
    for bi,block in enumerate(plan):
        reserve=sum(r['charged']+2 for r in block)+60
        enough=time.perf_counter()+reserve<stop
        for row in block:
            name=f"{row['case']}-{row['method']}"+(f"-repeat{row['index']}" if row['panel']=='reliability' else '')
            case=fixture_dest if row['panel']=='reliability' else out/'inputs'/row['scene']/(row['case']+'.json')
            eligible=row['panel']=='reliability' or generated.get(row['scene'],{}).get('complete',False)
            reason='NOT_RUN_RESOURCE_LIMIT' if not enough else ('NOT_RUN_GENERATION_FAILURE' if not eligible or not case.exists() else None)
            if reason:
                record=dict(row,status=reason,operational_success=None,mathematical_success=None)
                target=out/'cells'/name;target.mkdir(parents=True,exist_ok=False);publish(target/'result.json',record)
            else:
                try:record=launch(case,row,out/'cells'/name)
                except Exception as e:
                    record=dict(row,status='CONTROLLER_UNCAUGHT',error=repr(e),operational_success=False,mathematical_success=False)
                    # Preserve partial cell; separate accounting name, never overwrite.
                    publish(out/'cells'/name/'outer-error.json',record)
            rows.append(record)
        print(json.dumps({'block':bi+1,'blocks':len(plan),'elapsed':time.perf_counter()-began}),flush=True)
    # Original fixed mechanism diagnostics are not repeated or counted as new evidence.
    original_diag=W.parent/'campaign/diagnostic-accounting.json'
    diag={'status':'REUSED_CR023_NOT_RERUN','source_sha256':hashlib.sha256(original_diag.read_bytes()).hexdigest(),'scope':'Original eight synthetic cases only; no second count or new outcomes'}
    publish(out/'diagnostic-provenance.json',diag)
    publish(out/'campaign-ledger.json',{'rows':rows,'planned_cells':128,'diagnostics':diag,'elapsed_seconds':time.perf_counter()-began,'status':'PLANNED_DISPATCH_ACCOUNTED'})
    assert len(rows)==128
    # At most60 additional seconds; original absolute deadline also applies.
    post_began=time.perf_counter();post_stop=min(stop,post_began+60);post={}
    for script,cap in [('analyze.py',5),('replay_certificates.py',60)]:
        available=min(cap,max(0,post_stop-time.perf_counter()))
        if available<=0:post[script]={'status':'NOT_RUN_RESOURCE_LIMIT'};continue
        with (out/(script+'.log')).open('xb') as stream:
            try:
                cmd=[sys.executable,'-B',str(D/script),str(out.resolve())]
                if script=='replay_certificates.py':cmd+=['--seconds',str(max(0,available-1))]
                cp=run_bounded(cmd,stream,available);post[script]={'returncode':cp.returncode}
            except Exception as e:post[script]={'status':'POSTPROCESSING_ERROR','error':repr(e)}
    publish(out/'POSTPROCESSING.json',{'steps':post,'total_campaign_seconds':time.perf_counter()-began,'postprocessing_seconds':time.perf_counter()-post_began,'seconds_since_original_start':time.perf_counter()-old['started_at'],'within_original_3600_seconds':time.perf_counter()<=stop})
    print(json.dumps({'cells':len(rows),'elapsed':time.perf_counter()-began,'diagnostics':diag}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--go',required=True);p.add_argument('--output',required=True);main(p.parse_args())
