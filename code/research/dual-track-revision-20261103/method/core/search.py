"""Common multistart/four-user outer; deterministic starts and immutable anchor."""
import itertools,time,hashlib,json
import numpy as np
from problem import alive,Deadline
import transfer,slsqp_power,wmmse


def start_at(problem,seed,index):
    if index==-1:
        return tuple((2*s,2*s+1) for s in range(problem.s)),np.full(problem.k,float(min(problem.high,problem.budget/problem.k)))
    rng=np.random.default_rng(np.random.SeedSequence([int(seed),int(index)]))
    flat=rng.permutation(problem.k)
    assignment=tuple(tuple(sorted(map(int,flat[2*s:2*s+2]))) for s in range(problem.s))
    residual=(float(problem.high)-float(problem.low))*rng.random(problem.k)
    available=float(problem.budget-problem.k*problem.low)
    if residual.sum()>available and residual.sum()>0:residual*=available/residual.sum()
    return assignment,np.array(list(map(float,problem.repair(float(problem.low)+residual))))

def run(method,problem,anchor,deadline,seed,publish=None,refiners=None):
    began=time.monotonic();best=problem.anchor(anchor)
    stats=dict(method=method,starts_started=0,starts_completed=0,exchange_candidates=0,exchange_accepted=0,
               neighborhoods_completed=0,publish_calls=0,rejected=0,phase_records=[],errors=[],seed=int(seed),
               common_anchor=best['schedule'],power_call_policy='full_remaining_deadline')
    active_phase='initialization'
    def retain(assignment,powers,diagnostics):
        nonlocal best
        alive(deadline)
        candidate=problem.checked_candidate(assignment,powers)
        if problem.improves(candidate,best):
            problem.matrix_scalar_check(candidate)
            if publish:
                # Commit global retention only after callback returns successfully.
                stats['publish_calls']+=1;publish(candidate['assignment'],candidate['powers'],diagnostics)
            best=candidate
            return True
        stats['rejected']+=1;return False
    functions={'T':transfer.refine_power,'S':slsqp_power.refine_power,'W':wmmse.refine_power}
    functions.update(refiners or {})
    if method not in functions:raise ValueError('unregistered method/refiner')
    refiner=functions[method]
    # Do not mutate independent streams: modern adapters receive separate native RNG.
    rng=np.random.default_rng(np.random.SeedSequence([int(seed),987654]))
    problem.common_power_starts=[start_at(problem,seed,i)[1] for i in [-1]+list(range(8))]
    manifest=[dict(assignment=start_at(problem,seed,i)[0],powers=[str(x) for x in problem.repair(start_at(problem,seed,i)[1])]) for i in [-1]+list(range(8))]
    stats['planned_start_sha256']=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    def power(assignment,powers,phase):
        alive(deadline)
        stop=deadline
        p,diagnostic=refiner(problem,assignment,powers,stop,rng,retain)
        candidate=problem.checked_candidate(assignment,p)
        initial=problem.checked_candidate(assignment,powers)
        if not problem.improves(candidate,initial):candidate=initial
        retain(candidate['assignment'],candidate['powers'],diagnostic)
        rec=dict(diagnostic);rec['phase']=phase
        stats['phase_records'].append(rec)
        return candidate
    def exchange(current):
        while True:
            alive(deadline);changed=False
            for s1,s2 in itertools.combinations(range(problem.s),2):
                four=sorted(current['assignment'][s1]+current['assignment'][s2])
                for first in itertools.combinations(four,2):
                    alive(deadline);second=tuple(i for i in four if i not in first)
                    assignment=list(current['assignment']);assignment[s1]=tuple(first);assignment[s2]=second;assignment=tuple(assignment)
                    if assignment==current['assignment']:continue
                    stats['exchange_candidates']+=1
                    # Every changed schedule may be worse before its all-user power refinement.
                    candidate=power(assignment,current['powers'],'exchange')
                    if problem.improves(candidate,current):
                        current=candidate;stats['exchange_accepted']+=1;changed=True;break
                if changed:break
            if not changed:stats['neighborhoods_completed']+=1;return current
    status='running'
    try:
        starts=[(best['assignment'],best['powers'])]+[start_at(problem,seed,i) for i in [-1]+list(range(8))]
        index=0
        # W retains its full initial multistart matching phase before exchange.
        while True:
            alive(deadline);active_phase='start';stats['starts_started']+=1
            assignment,p=starts[index] if index<len(starts) else start_at(problem,seed,index-2)
            if method=='W':
                current,diagnostic=wmmse.refine_matching(problem,assignment,p,deadline,retain)
                stats['phase_records'].append(dict(diagnostic,phase='matching_start'))
                retain(current['assignment'],current['powers'],diagnostic)
                if index>=len(starts)-1:
                    active_phase='exchange';exchange(best)
            else:
                current=power(assignment,p,'start')
                active_phase='exchange';exchange(current)
            stats['starts_completed']+=1;index+=1
    except Deadline:status='deadline'
    except Exception as exc:
        status='error';stats['errors'].append(dict(type=type(exc).__name__,message=str(exc),phase=active_phase))
    stats['elapsed_seconds']=time.monotonic()-began
    stats['stopped_phase']=active_phase
    return dict(candidate=best,status=status,diagnostics=stats)
