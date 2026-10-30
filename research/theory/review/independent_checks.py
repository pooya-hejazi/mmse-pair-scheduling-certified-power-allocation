"""Independent bounded technical diagnostics. Never imports/executes frozen code."""
import itertools as it
import json
import math
import time
from fractions import Fraction as F
from pathlib import Path
import numpy as np
from scipy.optimize import linprog, linear_sum_assignment

start = time.perf_counter()
rng = np.random.default_rng(20261030)
out = {}

def schedules(users, slots):
    if slots == 0:
        yield ()
        return
    for edge in it.combinations(users, 2):
        rest = tuple(u for u in users if u not in edge)
        for tail in schedules(rest, slots - 1):
            yield (edge,) + tail

def build(k, allowed, t):
    rows = [[F(0) for _ in range(k*k)] for _ in range(k)]
    for u in range(k):
        rows[u][u] = F(1)
    c = k
    for u, v in it.combinations(range(k), 2):
        rows[u][c] = t
        rows[v][c + int((u, v) in allowed)] = t
        c += 2
    assert c == k*k
    return rows

def gram(h):
    return [[sum(a*b for a,b in zip(u,v)) for v in h] for u in h]

def system(k):
    s = k//2
    edges = list(it.combinations(range(k),2))
    cols = list(it.product(range(s),edges))
    eq = np.array([[int(u in e) for r,e in cols] for u in range(k)] +
                  [[int(r == v) for r,e in cols] for v in range(s)])
    odd = [set(o) for n in range(3,k,2) for o in it.combinations(range(k),n)]
    cuts = np.array([[int(set(e)<=o) for r,e in cols] for o in odd])
    rhs = np.array([(len(o)-1)/2 for o in odd])
    return cols, eq, cuts, rhs

allowed = [{(0,1),(2,3)}, {(0,2),(1,3)}]
cols, eq, cuts, rhs = system(4)
cost = np.array([int(e not in allowed[s]) for s,e in cols])
x = np.array([F(1,2) if e in allowed[s] else F(0) for s,e in cols], dtype=object)
assert all(v == 1 for v in eq@x)
assert all(a <= b for a,b in zip(cuts@x,rhs))
clique = 1-cost
lp = linprog(cost,A_eq=eq,b_eq=np.ones(6),A_ub=cuts,b_ub=rhs,bounds=(0,1))
lp_c = linprog(cost,A_eq=eq,b_eq=np.ones(6),A_ub=np.vstack((cuts,clique)),b_ub=np.append(rhs,1),bounds=(0,1))
assert lp.success and lp_c.success and abs(lp.fun) < 1e-9 and abs(lp_c.fun-1)<1e-9
assert min(sum(int(e not in allowed[s]) for s,e in enumerate(a)) for a in schedules(tuple(range(4)),2)) == 1
assert clique@x == 2
for t in [F(1,4),F(1,100),F(1,10**6),F(3,2)]:
    g = 1+3*t*t
    for aset in allowed:
        h = build(4,aset,t)
        G = gram(h)
        assert all(G[u][v] == (g if u==v else F(0) if tuple(sorted((u,v))) in aset else t*t) for u in range(4) for v in range(4))
    A = (1+g)**2
    B = (1+g-t**4/(1+g))**2
    assert A > B > 0
    products = [math.prod(A if e in allowed[s] else B for s,e in enumerate(a)) for a in schedules(tuple(range(4)),2)]
    assert max(products)==A*B and A*A>A*B
out['four_user'] = {'exact_rational_t':['1/4','1/100','1/1000000','3/2'],'labeled_schedules':6,'lp_penalty':float(lp.fun),'odd_lp_plus_clique_penalty':float(lp_c.fun),'clique_lhs_at_witness':str(clique@x)}

# Larger tiny 3DM diagnostics, independent direct matching permutations versus
# general pair schedules (including same-side pairs).
counts = {}
for n, repetitions in [(1,2),(2,256),(3,60),(4,8)]:
    k = 2*n
    triples = list(it.product(range(n),range(n,2*n),range(n)))
    all_actions = list(schedules(tuple(range(k)),n))
    count_yes = 0
    for trial in range(repetitions):
        if n <= 2:
            T = {q for i,q in enumerate(triples) if (trial >> i)&1}
        else:
            density = [0.05,0.2,0.5,0.8][trial%4]
            T = {q for q in triples if rng.random() < density}
        sets = [{(x,y) for x,y,z in T if z==s} for s in range(n)]
        dm = any(all((px[z],py[z],z) in T for z in range(n)) for px in it.permutations(range(n)) for py in it.permutations(range(n,2*n)))
        ideal = any(all(e in sets[s] for s,e in enumerate(a)) for a in all_actions)
        assert dm == ideal
        count_yes += int(dm)
        if trial == 0:
            t = F(1,k)
            g = 1+(k-1)*t*t
            assert g < 2
            for aset in sets:
                G = gram(build(k,aset,t))
                assert all(G[u][v] == (g if u==v else F(0) if tuple(sorted((u,v))) in aset else t*t) for u in range(k) for v in range(k))
            # Algebraic ingredient of the inverse-polynomial raw-rate bound.
            assert t**4/(1+g)**2 >= F(1,9*k**4)
    counts[str(n)] = {'instances':repetitions,'yes':count_yes,'schedules_per_instance':len(all_actions)}
assert counts['2']['yes']==175
out['3dm'] = counts

# Direct complex MMSE inversion versus formula, then LP/odd-LP/IP/assignment bound.
max_mmse_error = 0.0
max_bound_violation = 0.0
for trial in range(24):
    k,s,m = 6,3,5
    h = (rng.normal(size=(s,k,m))+1j*rng.normal(size=(s,k,m)))/3
    cols,eq,cuts,rhs=system(k)
    a = np.log2(1+np.sum(abs(h)**2,axis=2))
    q,loss = [],[]
    for r,(u,v) in cols:
        hu,hv = h[r,u],h[r,v]
        gu,gv = np.vdot(hu,hu).real,np.vdot(hv,hv).real
        d2 = abs(np.vdot(hu,hv))**2
        fu,fv = gu-d2/(1+gv),gv-d2/(1+gu)
        iu = np.vdot(hu,np.linalg.solve(np.eye(m)+np.outer(hv,hv.conj()),hu)).real
        iv = np.vdot(hv,np.linalg.solve(np.eye(m)+np.outer(hu,hu.conj()),hv)).real
        max_mmse_error = max(max_mmse_error,abs(fu-iu),abs(fv-iv))
        pairq = np.log2(1+fu)+np.log2(1+fv)
        delta = -2*np.log2(1-d2/((1+gu)*(1+gv)))
        assert abs(pairq-(a[r,u]+a[r,v]-delta))<1e-12
        q.append(pairq); loss.append(delta)
    q,loss = np.array(q),np.array(loss)
    index = {col:i for i,col in enumerate(cols)}
    objectives = [sum(q[index[(r,e)]] for r,e in enumerate(action)) for action in schedules(tuple(range(k)),s)]
    ip = max(objectives)
    lp = linprog(-q,A_eq=eq,b_eq=np.ones(k+s),bounds=(0,1))
    oddlp = linprog(-q,A_eq=eq,b_eq=np.ones(k+s),A_ub=cuts,b_ub=rhs,bounds=(0,1))
    assert lp.success and oddlp.success
    us,slots = linear_sum_assignment(-np.repeat(a,2,axis=0).T)
    Q0 = sum(a[slot//2,u] for u,slot in zip(us,slots))
    schedule = [tuple(sorted(u for u,slot in zip(us,slots) if slot//2==r)) for r in range(s)]
    recovered = sum(q[index[(r,e)]] for r,e in enumerate(schedule))
    D = sum(max(loss[i] for i,(r,e) in enumerate(cols) if r==resource) for resource in range(s))
    violations = [Q0-D-recovered,ip+lp.fun,-lp.fun-Q0,ip+oddlp.fun,-oddlp.fun+lp.fun,-lp.fun-recovered-D]
    max_bound_violation = max(max_bound_violation,max(violations))
    assert max(violations)<1e-9
out['mmse_and_additive'] = {'random_complex_channel_tables':24,'k':6,'resources':3,'dimension':5,'max_mmse_error':max_mmse_error,'max_bound_violation':max_bound_violation}

# Exact finite-power sample supports (but does not replace) Jensen equality proof.
g=F(19,16); d2=F(1,256); pbar=F(1,10)
threshold=(1+g*pbar)**4
tested=0
for powers in it.product([F(1,20),F(1,10),F(3,20),F(1,5)],repeat=4):
    if sum(powers)>4*pbar:
        continue
    for action in schedules(tuple(range(4)),2):
        product=F(1)
        for s,(u,v) in enumerate(action):
            d=F(0) if (u,v) in allowed[s] else d2
            product*=1+g*powers[u]-powers[u]*powers[v]*d/(1+g*powers[v])
            product*=1+g*powers[v]-powers[u]*powers[v]*d/(1+g*powers[u])
        assert product<threshold
        tested+=1
out['joint_power']={'exact_grid_schedule_checks_on_no_instance':tested,'interpretation':'Finite checks only; compactness/Jensen are the continuous proof.'}
out['elapsed_seconds']=time.perf_counter()-start
out['result']='PASS'
Path(__file__).with_name('independent_checks.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
