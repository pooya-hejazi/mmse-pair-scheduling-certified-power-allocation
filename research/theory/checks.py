from fractions import Fraction as F
from pathlib import Path
import itertools,json,time
import numpy as np
from scipy.optimize import linprog,milp,Bounds,LinearConstraint
R=Path(__file__).resolve().parent

def channels(k,allowed,t):
    """M=K² rational coordinates: K private +2 per unorderedpair."""
    pairs=list(itertools.combinations(range(k),2));H=[[F(0)]*(k*k) for _ in range(k)]
    for u in range(k):H[u][u]=F(1)
    for j,(u,v) in enumerate(pairs):
        coordinate=k+2*j;H[u][coordinate]=t;H[v][coordinate+(1 if (u,v) in allowed else 0)]=t
    return H
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def actions(k):
    if k!=4:raise ValueError('tiny exact check only')
    for g in itertools.combinations(range(4),2):yield [tuple(g),tuple(u for u in range(4) if u not in g)]

start=time.perf_counter();pairs=list(itertools.combinations(range(4),2));allowed=[{(0,1),(2,3)},{(0,2),(1,3)}]
results=[]
for t in [F(1,4),F(1,10),F(1,100)]:
    H=[channels(4,a,t) for a in allowed];g=1+3*t*t
    for s in range(2):
        for u,v in itertools.product(range(4),repeat=2):
            expected=g if u==v else (F(0) if tuple(sorted((u,v))) in allowed[s] else t*t)
            assert dot(H[s][u],H[s][v])==expected
    # q_allowed=log2(A), q_forbidden=log2(B), A>B exact rational.
    A=(1+g)**2;B=(1+g-t**4/(1+g))**2;assert A>B>0
    products=[np.prod([A if e in allowed[s] else B for s,e in enumerate(action)]) for action in actions(4)]
    assert max(products)==A*B and A*A>A*B
    # Fractional objective2log2(A); each supported column has value1/2.
    support=[(s,e,F(1,2)) for s in range(2) for e in allowed[s]]
    assert all(sum(x for s,e,x in support if u in e)==1 for u in range(4))
    assert all(sum(x for ss,e,x in support if ss==s)==1 for s in range(2))
    for odd in itertools.combinations(range(4),3):assert sum(x for s,e,x in support if set(e)<=set(odd))<=1
    results.append({'t':str(t),'norm_squared':str(g),'normalized_correlation':str(t*t/g),'allowed_pair_rate_product':str(A),'forbidden_pair_rate_product':str(B),'LP_to_IP_rate_product_ratio':str(A/B),'gap_formula':'log2(A/B)=-2log2(1-t^4/(1+g)^2)','all_odd_sets_satisfied':True})
# Cost formulation exactly represents reward ordering: every forbidden column paysdelta.
mat=np.zeros((6,12));cost=[]
for s in range(2):
 for j,e in enumerate(pairs):mat[list(e)+[4+s],s*6+j]=1;cost.append(0 if e in allowed[s] else 1)
cuts=np.array([[int(set(e)<=set(odd)) for s in range(2) for e in pairs] for odd in itertools.combinations(range(4),3)])
lp=linprog(cost,A_eq=mat,b_eq=np.ones(6),A_ub=cuts,b_ub=np.ones(4),bounds=(0,1),method='highs')
ip=milp(cost,integrality=np.ones(12),bounds=Bounds(0,1),constraints=LinearConstraint(mat,1,1))
assert lp.success and ip.status==0 and abs(lp.fun)<1e-9 and abs(ip.fun-1)<1e-9
# All2x2x2 3DM inputs; compare a cross-triple perfect matching to ideal rate attainment.
triples=list(itertools.product(range(2),range(2,4),range(2)));yes=0
for mask in range(256):
    T={triples[j] for j in range(8) if mask>>j&1};allowed_s=[{(x,y) for x,y,z in T if z==s} for s in range(2)]
    matched=any(a[0]!=b[0] and a[1]!=b[1] and a[2]!=b[2] for a,b in itertools.combinations(T,2))
    ideal=any(all(e in allowed_s[s] for s,e in enumerate(action)) for action in actions(4))
    assert matched==ideal;yes+=matched
    for s in range(2):
        H=channels(4,allowed_s[s],F(1,4))
        assert all(dot(H[u],H[v])==(F(0) if (u,v) in allowed_s[s] else F(1,16)) for u,v in pairs)
out={'result':'PASS','four_user_witnesses':results,'LP_penalty':float(lp.fun),'IP_penalty':float(ip.fun),'threeDM_patterns_checked':256,'yes_patterns':yes,'seconds':time.perf_counter()-start,'scope':'exact tiny rational identities and reduction checks, not independent proof acceptance or novelty clearance'}
assert out['seconds']<120
(R/'checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
