"""Analytic-gradient SLSQP with feasible interval-checked retained candidates."""
import numpy as np
from scipy.optimize import minimize
from problem import alive,Deadline

def refine_power(problem,assignment,p0,deadline,rng,publish):
    current=problem.checked_candidate(assignment,p0)
    stats=dict(iterations=0,evaluations=0,cap_stops=0,rejected=0,accepted=0,restarts=0,stop_reason='running',solver_messages=[])
    def retain(p):
        nonlocal current
        candidate=problem.checked_candidate(assignment,p)
        if problem.improves(candidate,current):
            current=candidate;stats['accepted']+=1
            if publish:publish(assignment,current['powers'],dict(stats))
        else:stats['rejected']+=1
    def objective(p):
        alive(deadline);stats['evaluations']+=1
        value,gradient=problem.value_gradient(assignment,p)
        return -value,-gradient
    def callback(p):
        alive(deadline);retain(p)
    try:
        while True:
            alive(deadline)
            sol=minimize(objective,current['numeric'],jac=True,method='SLSQP',
                         bounds=[(float(problem.low),float(problem.high))]*problem.k,
                         constraints=[dict(type='ineq',fun=lambda p:float(problem.budget)-p.sum(),jac=lambda p:-np.ones(problem.k))],
                         callback=callback,options=dict(ftol=1e-10,maxiter=500))
            stats['iterations']+=int(sol.nit);stats['solver_messages'].append(str(sol.message));retain(sol.x)
            if sol.status==9:
                stats['cap_stops']+=1;stats['restarts']+=1
                continue
            stats['stop_reason']='solver_converged' if sol.success else 'numerical_stall'
            break
    except Deadline:stats['stop_reason']='deadline'
    return current['numeric'],stats
