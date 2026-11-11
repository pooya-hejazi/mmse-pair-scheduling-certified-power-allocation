"""Serial prospective cells. Immutable outputs and parent-validated receipts."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
from fractions import Fraction as F
import json,sys,time,subprocess,hashlib
import psutil
from persistence import publish,digest

D=Path(__file__).parent

def universal(case):
    # Schema only: no optimizing bound implementation imported.
    case_hash=hashlib.sha256(json.dumps(case,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return {'schema':'MMSE_PARTITION_PROOF_V1','case_sha256':case_hash,'universal':True,'dual':None,'spatial':None}

def launch(case_path,row,destination):
    import verify_upper as verifier
    verifier.clear_caches()
    out=Path(destination);out.mkdir(parents=True,exist_ok=False);case_path=Path(case_path)
    start=time.perf_counter();deadline=start+row['charged'];external=start+row['charged']+2
    case=json.loads(case_path.read_text());attempt=dict(row,started_at=start,deadline=deadline,external_deadline=external,case_sha256=digest(case_path),case_file=str(case_path))
    publish(out/'attempt.json',attempt)
    p=min(F(case['pmax']),F(case['budget'])/case['K']);initial=[dict(users=[2*s,2*s+1],resource=s,powers=[str(p),str(p)]) for s in range(case['S'])]
    seen=set();receipts=[];errors=[];verification_timeouts=[];peak=0;best_lo=None;best_hi=None;best_schedule=None
    def accept(path):
        nonlocal best_lo,best_hi,best_schedule
        if time.perf_counter()>=deadline:return
        candidate=json.loads(path.read_text());proof=candidate.get('proof') or universal(case)
        result=verifier.verify(case,{'proof':proof,'schedule':candidate['schedule']},seconds=max(0,deadline-time.perf_counter()))
        if time.perf_counter()>=deadline:return
        verified=dict(candidate_file=path.name,candidate_sha256=digest(path),case_sha256=attempt['case_sha256'],
                      attempt_sha256=digest(out/'attempt.json'),validated_at=time.perf_counter(),verification=result)
        name=f'receipt-{len(receipts):06d}.json';pub=publish(out/name,verified)
        timely=pub['completed_at']<=deadline
        receipts.append(dict(file=name,sha256=pub['sha256'],completed_at=pub['completed_at'],timely=timely))
        if timely:
            lo,hi=F(result['lower_nats']),F(result['upper_nats'])
            if best_lo is None or lo>best_lo:best_lo=lo;best_schedule=candidate['schedule']
            best_hi=hi if best_hi is None else min(best_hi,hi)
    publish(out/'parent-fallback.json',{'schedule':initial,'status':'PARENT_FALLBACK','proof':universal(case)})
    try:accept(out/'parent-fallback.json')
    except Exception as e:errors.append({'stage':'fallback_verification','error':repr(e)})
    cmd=[sys.executable,'-B',str(D/'worker.py'),'--case',str(case_path),'--output',str(out),'--method',row['method'],
         '--started',str(start),'--deadline',str(deadline),'--reserve','5','--seed',str(row['seed'])]
    proc=None;reason='RETURNED';returncode=None
    with (out/'worker.log').open('xb') as stream:
        try:
            proc=subprocess.Popen(cmd,stdout=stream,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));ps=psutil.Process(proc.pid)
            while True:
                try:peak=max(peak,ps.memory_info().rss)
                except psutil.Error:pass
                # Read each unique file once, never lock a name the writer replaces.
                for path in sorted(out.glob('candidate-*.json')):
                    if path.name in seen:continue
                    seen.add(path.name)
                    try:accept(path)
                    except TimeoutError:verification_timeouts.append(path.name)
                    except Exception as e:errors.append({'stage':'candidate_verification','file':path.name,'error':repr(e)})
                if proc.poll() is not None:
                    returncode=proc.returncode
                    # One final scan closes the exit-between-scan-and-poll race.
                    for path in sorted(out.glob('candidate-*.json')):
                        if path.name in seen:continue
                        seen.add(path.name)
                        try:accept(path)
                        except TimeoutError:verification_timeouts.append(path.name)
                        except Exception as e:errors.append({'stage':'candidate_verification','file':path.name,'error':repr(e)})
                    break
                if time.perf_counter()>=external or peak>8*1024**3:
                    reason='EXTERNAL_WATCHDOG' if peak<=8*1024**3 else 'RAM_LIMIT';proc.kill();proc.wait();returncode=proc.returncode;break
                time.sleep(.02)
        except Exception as e:
            reason='CONTROLLER_ERROR';errors.append({'stage':'controller','error':repr(e)})
            if proc is not None and proc.poll() is None:proc.kill();proc.wait();returncode=proc.returncode
    statusfile=out/'worker-status.json';status=json.loads(statusfile.read_text()) if statusfile.exists() else None
    normal=(reason=='RETURNED' and returncode==0 and status is not None and status.get('normal') is True and not errors and time.perf_counter()<=external)
    gap=(best_hi-best_lo) if best_lo is not None and best_hi is not None else None
    mathematical=gap is not None and gap<=F(1,100)
    result=dict(row,status=reason,worker_status=status,returncode=returncode,normal=normal,errors=errors,verification_timeouts=verification_timeouts,receipts=receipts,
                lower_nats=str(best_lo) if best_lo is not None else None,upper_nats=str(best_hi) if best_hi is not None else None,
                gap_nats=float(gap) if gap is not None else None,mathematical_success=mathematical,operational_success=bool(mathematical and normal),
                schedule=best_schedule,elapsed=time.perf_counter()-start,peak_RSS_bytes=peak,all_seen_candidates=sorted(seen),
                scope='Parent independently reconstructed all accepted uppers; actual receipt completion by deadline; normal return required for primary success')
    publish(out/'result.json',result);return result
