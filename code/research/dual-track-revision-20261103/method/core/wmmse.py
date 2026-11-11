"""Stronger matching/WMMSE power and assignment updates on common exact model."""
import numpy as np
from problem import mw,alive,Deadline

def flatten(assignment):return np.array([i for pair in assignment for i in pair],int)
def pairs(flat):return tuple(tuple(sorted(map(int,flat[2*s:2*s+2]))) for s in range(len(flat)//2))

def refine_power(problem,assignment,p0,deadline,rng,publish):
    return _refine(problem,assignment,p0,deadline,publish,False)

def refine_matching(problem,assignment,p0,deadline,publish):
    return _refine(problem,assignment,p0,deadline,publish,True)

def _refine(problem,assignment,p0,deadline,publish,matching):
    current=problem.checked_candidate(assignment,p0)
    stats=dict(iterations=0,matching_calls=0,power_steps=0,bisections=0,accepted=0,rejected=0,cap_stops=0,stop_reason='running')
    try:
        for iteration in range(10000):
            alive(deadline);before=current['value'];flat=flatten(current['assignment']);p=current['numeric']
            if matching:
                u,w=mw._mmse(problem.h,flat,p)
                scores=mw._assignment_scores(problem.h,p,u,w)
                proposal=pairs(mw._perfect_assignment(scores));stats['matching_calls']+=1
                candidate=problem.checked_candidate(proposal,p)
                if problem.improves(candidate,current):
                    current=candidate;stats['accepted']+=1
                    if publish:publish(current['assignment'],current['powers'],dict(stats))
                else:stats['rejected']+=1
            alive(deadline);flat=flatten(current['assignment']);p=current['numeric']
            u,w=mw._mmse(problem.h,flat,p)
            a,b=mw._power_coefficients(problem.h,flat,u,w)
            proposed,n=mw._amplitude_update(a,b,problem.low,problem.high,problem.budget)
            stats['power_steps']+=1;stats['bisections']+=n
            candidate=problem.checked_candidate(current['assignment'],proposed)
            if problem.improves(candidate,current):
                current=candidate;stats['accepted']+=1
                if publish:publish(current['assignment'],current['powers'],dict(stats))
            else:stats['rejected']+=1
            stats['iterations']+=1
            if current['value']-before<=1e-10+1e-9*max(1,abs(before)):
                stats['stop_reason']='objective_tolerance';break
        else:stats['cap_stops']+=1;stats['stop_reason']='iteration_cap'
    except Deadline:stats['stop_reason']='deadline'
    if matching:return current,stats
    return current['numeric'],stats
