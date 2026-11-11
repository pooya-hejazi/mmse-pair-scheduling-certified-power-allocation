"""One method/case process; immutable progress; parent owns acceptance."""
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
import argparse,json,time,traceback,sys
from pathlib import Path
from fractions import Fraction as F
from persistence import publish

def fallback(case):
    p=min(F(case['pmax']),F(case['budget'])/case['K'])
    return [{'users':[2*s,2*s+1],'resource':s,'powers':[str(p),str(p)]} for s in range(case['S'])]

def run(a):
    case=json.loads(Path(a.case).read_text());out=Path(a.output);seq=0;last=0.;errors=[];best=fallback(case)
    def emit(payload,force=False):
        nonlocal seq,last,best
        now=time.perf_counter()
        if not force and now-last<.5:return
        if now>=a.deadline:return
        if payload.get('schedule'):best=payload['schedule']
        seq+=1;row=dict(payload,worker_elapsed=now-a.started,sequence=seq,method=a.method)
        if not force:row.pop('proof',None)
        publish(out/f'candidate-{seq:06d}.json',row);last=time.perf_counter()
    try:
        emit({'schedule':best,'status':'INITIAL_FALLBACK'},True)
        stop=a.deadline-a.reserve
        if a.method=='joint':
            from matching_baseline import solve
            result=solve(case,max(0,stop-time.perf_counter()),a.seed,progress=emit)
            emit(result,True)
            if result.get('errors'):errors.extend(result['errors'])
            if result.get('status') in ['invalid_input','numerical_error','progress_error']:errors.append(result['status'])
        else:
            import grid_core as grid
            grid.GRID_LEVELS=[F(1,20),F(1,10),F(1,5)];grid.NATIVE_CAP=1.25;grid.PROGRESS=emit
            result=grid.solve(case,'grid',min(3.,max(0,stop-time.perf_counter())))
            emit(dict(result,stage='grid'),True);best=result['schedule']
            errors.extend(result.get('errors',[]))
            if a.method!='grid' and time.perf_counter()<stop:
                from certificates import run
                result=run(case,a.method,initial=best,grid_duals=result if 'alpha' in result else None,
                           seconds=max(0,stop-time.perf_counter()),progress=emit)
                emit(result,True)
        publish(out/'worker-status.json',{'normal':not bool(errors),'errors':errors,'finished_at':time.perf_counter(),'sequence':seq})
    except BaseException as e:
        # Independent stderr diagnostic; do not recurse through a failing publisher.
        diagnostic={'normal':False,'error_type':type(e).__name__,'error':str(e),'errno':getattr(e,'errno',None),'winerror':getattr(e,'winerror',None),'traceback':traceback.format_exc(),'finished_at':time.perf_counter()}
        print(json.dumps(diagnostic),file=sys.stderr,flush=True)
        try:publish(out/'worker-status.json',diagnostic)
        except Exception:pass
        return 2
    return 2 if errors else 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--output',required=True);p.add_argument('--method',choices=['grid','curvature','full','pricing','joint'],required=True)
    p.add_argument('--started',type=float,required=True);p.add_argument('--deadline',type=float,required=True);p.add_argument('--reserve',type=float,default=5.);p.add_argument('--seed',type=int,default=1101)
    sys.exit(run(p.parse_args()))
