"""Numerical finite-candidate line proposals; never an exact/global oracle."""
import time,math,itertools
import numpy as np
from numpy.polynomial import Polynomial as Poly
from problem import Deadline,alive

def stationary_candidates(coeff,stats,root_solver=None):
    coeff=np.asarray(coeff,float)
    if not np.isfinite(coeff).all():
        stats['nonfinite_polynomial']+=1;return []
    scale=float(np.max(np.abs(coeff))) if len(coeff) else 0.
    if scale==0:
        stats['constant_lines']+=1;return []
    coeff=coeff/scale
    while len(coeff)>1 and abs(coeff[-1])<=1e-14:
        coeff=coeff[:-1];stats['degree_reductions']+=1
    stats['max_degree']=max(stats['max_degree'],len(coeff)-1)
    if len(coeff)<=1:return []
    try: roots=(root_solver or (lambda c:Poly(c).roots()))(coeff)
    except Exception:
        stats['root_failures']+=1;return []
    out=[]
    for z in roots:
        if not np.isfinite(z):stats['nonfinite_roots']+=1;continue
        if abs(z.imag)>1e-8*(1+abs(z.real)):continue
        x=float(z.real)
        if -1-1e-10<=x<=1+1e-10:
            x=min(1.,max(-1.,x))
            if not any(abs(x-a)<=1e-10 for a in out):out.append(x)
    return out

def new_stats():
    return dict(lines=0,evaluations=0,accepted=0,rejected=0,root_failures=0,nonfinite_roots=0,
                nonfinite_polynomial=0,constant_lines=0,degree_reductions=0,max_degree=0,
                sweeps=0,cap_stops=0,stop_reason='running')

def line_terms(problem,assignment,p,direction,mid,half):
    """Positive polynomial logarithm arguments on normalized [-1,1]."""
    terms=[]
    for s,(i,j) in enumerate(assignment):
        if direction[i]==0 and direction[j]==0:continue
        g,h,r=problem.lookup[i,j,s]
        x=Poly([g*(p[i]+direction[i]*mid),g*direction[i]*half])
        y=Poly([h*(p[j]+direction[j]*mid),h*direction[j]*half])
        for weight,poly in ((2.,1+x+y+(1-r)*x*y),(-1.,1+x),(-1.,1+y)):
            if np.any(poly.deriv().coef): terms.append((weight,poly))
    return terms

def numerator(terms):
    result=Poly([0.])
    for index,(weight,poly) in enumerate(terms):
        term=weight*poly.deriv()
        for j,(_,other) in enumerate(terms):
            if j!=index:term=term*other
        result=result+term
    return result

def line_best(problem,assignment,p,direction,lo,hi,deadline,stats=None,root_solver=None):
    stats=new_stats() if stats is None else stats
    alive(deadline);p=np.asarray(p,float);direction=np.asarray(direction,float)
    stats['lines']+=1
    if hi<lo-1e-14:raise ValueError('empty line interval')
    if hi<=lo:return p.copy()
    mid=(lo+hi)/2;half=(hi-lo)/2
    terms=line_terms(problem,assignment,p,direction,mid,half)
    coeff=numerator(terms).coef
    points=[-1.,1.]+stationary_candidates(coeff,stats,root_solver)
    if lo<=0<=hi:points.append(-mid/half)
    best=p.copy();bestvalue=problem.value_gradient(assignment,p)[0];stats['evaluations']+=1
    for z in points:
        alive(deadline)
        trial=p+direction*(mid+half*z)
        trial=np.array(list(map(float,problem.repair(trial))))
        value=problem.value_gradient(assignment,trial)[0];stats['evaluations']+=1
        if value>bestvalue:best,bestvalue=trial,value
    return best

def refine_power(problem,assignment,p0,deadline,rng,publish):
    stats=new_stats();current=problem.checked_candidate(assignment,p0)
    try:
        for sweep in range(10000):
            alive(deadline);changed=False
            # Coordinate moves include unused budget; no forced equality.
            for i in range(problem.k):
                alive(deadline);p=current['numeric'];remaining=float(problem.budget-sum(current['powers'])+current['powers'][i])
                lo=float(problem.low)-p[i];hi=min(float(problem.high),remaining)-p[i]
                direction=np.zeros(problem.k);direction[i]=1
                proposed=line_best(problem,assignment,p,direction,lo,hi,deadline,stats)
                candidate=problem.checked_candidate(assignment,proposed)
                if problem.improves(candidate,current):
                    current=candidate;changed=True;stats['accepted']+=1
                    if publish:publish(assignment,current['powers'],dict(stats))
                else:stats['rejected']+=1
            for i,j in itertools.combinations(range(problem.k),2):
                alive(deadline);p=current['numeric']
                lo=max(float(problem.low)-p[i],p[j]-float(problem.high))
                hi=min(float(problem.high)-p[i],p[j]-float(problem.low))
                direction=np.zeros(problem.k);direction[i]=1;direction[j]=-1
                proposed=line_best(problem,assignment,p,direction,lo,hi,deadline,stats)
                candidate=problem.checked_candidate(assignment,proposed)
                if problem.improves(candidate,current):
                    current=candidate;changed=True;stats['accepted']+=1
                    if publish:publish(assignment,current['powers'],dict(stats))
                else:stats['rejected']+=1
            stats['sweeps']+=1
            if not changed:stats['stop_reason']='coordinate_tolerance';break
        else:stats['cap_stops']+=1;stats['stop_reason']='sweep_cap'
    except Deadline:stats['stop_reason']='deadline'
    return current['numeric'],stats
