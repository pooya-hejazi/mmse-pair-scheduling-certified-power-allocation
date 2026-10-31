"""Reviewer-only exact checks; no imports or writes in the frozen input tree."""
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations
import hashlib, json, time
import sympy as s

start = time.perf_counter()
here = Path(__file__).resolve().parent
root = here.parents[1] / 'frozen' / 'RESOLUTION-CR015-A01'
manifest = json.loads((root/'manifest.json').read_text())
def hashes():
    return {e['path']: hashlib.sha256((root/e['path']).read_bytes()).hexdigest() == e['sha256'] for e in manifest['entries']}
before=hashes(); assert all(before.values())
x,y,a,l,m=s.symbols('x y a l m')
A=1+x; H=1+y; d=1+x+y+a*x*y; k=1+a*x
q=2*s.log(d)-s.log(A)-s.log(H)
assert s.cancel(s.diff(q,x,2)-(1/A**2-2*(1+a*y)**2/d**2))==0
assert s.cancel(s.diff(q,x,y)+2*(1-a)/d**2)==0
N=(2*A**2*(1+a*y)**2-d**2)*(2*H**2*k**2-d**2)-4*(1-a)**2*A**2*H**2
table={(4,4):a**4,(4,3):4*a**4,(4,2):2*a**2*(a**2+4*a-2),(4,1):4*a*(a*a+a-1),(4,0):2*a*a-1,
       (3,3):4*a*a*(4*a*a-a+1),(3,2):4*a*(2*a**3+6*a*a-3*a+1),(3,1):4*a*(3*a*a+3*a-2),(3,0):4*(a*a+a-1),
       (2,2):2*(2*a**4+16*a**3-a*a+1),(2,1):4*(a+1)*(2*a*a+2*a-1),(2,0):2*(-a*a+8*a-4),
       (1,1):4*(7*a-3),(1,0):4*(2-a)*(2*a-1),(0,0):(3-2*a)*(2*a-1)}
expanded=0
for (i,j),c in table.items():
    expanded += c*x**i*y**j
    if i!=j: expanded += c*x**j*y**i
assert s.expand(N-expanded)==0
assert s.cancel(s.det(s.hessian(q,(x,y)))-N/(A*A*H*H*d**4))==0
C=A*(1-l*A); B=2*a*A-k*(1+l*A)
G=2*k-(1+m)*A+(k-m*(A+k))*y-m*k*y*y
P=(2*k-(1+m)*A)*B**2-(k-m*(A+k))*C*B-m*k*C**2
assert s.cancel((s.diff(q,x)-l)*A*d-(C+B*y))==0
assert s.cancel((s.diff(q,y)-m)*H*d-G)==0
assert s.cancel(G.subs(y,-C/B)*B**2-P)==0
assert s.Poly(P,x).degree()<=5
assert s.expand(P.subs(x,-1)-2*(1-a)**3)==0
# Compare positive log arguments without dividing by xy, preserving axis cases.
assert s.expand(d*d-(1+x+y)*A*H-x*y*(a*a*x*y+(2*a-1)*(1+x+y)))==0

def dot(u,v): return sum(ui*vi for ui,vi in zip(u,v))
def unit(t,parent):
    t=F(t)
    if parent is None:
        den=1+t*t+t**4
        return (2*t/den,2*t*t/den,(1-t*t-t**4)/den)
    base=((1-t*t)/(1+t*t),2*t/(1+t*t),F(0))
    delta=(-parent[0],-parent[1],1-parent[2])
    if parent==(0,0,1): return base
    return tuple(base[i]-delta[i]*dot(delta,base)/(1-parent[2]) for i in range(3))
count=0; max_t=0
for size in range(4):
    for edges in combinations(list(combinations(range(6),2)),size):
        labels=list(range(7)); adj=[[] for _ in labels]
        def find(v):
            while labels[v]!=v: v=labels[v]
            return v
        cyclic=False
        for u,v in edges:
            if find(u)==find(v): cyclic=True; break
            labels[find(u)]=find(v); adj[u].append(v); adj[v].append(u)
        if cyclic: continue
        vectors={}
        def visit(v,parent):
            global max_t
            for t in range(101):
                candidate=unit(t,None if parent is None else vectors[parent])
                if all((dot(candidate,w)==0)==(i==parent) and abs(dot(candidate,w))!=1 for i,w in vectors.items()): break
            else: raise AssertionError('candidate exhaustion')
            max_t=max(max_t,t); vectors[v]=candidate
            assert dot(candidate,candidate)==1
            for child in sorted(adj[v]):
                if child!=parent: visit(child,v)
        for v in range(7):
            if v not in vectors: visit(v,None)
        for u,v in combinations(range(7),2):
            dv=dot(vectors[u],vectors[v])
            assert (dv==0)==((u,v) in edges)
            assert abs(dv)!=1
        count+=1
assert count==556
finite=json.loads((root/'research/novelty-resolution/finite-manifest.json').read_text())
assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in finite['files'].items())
results=json.loads((root/'research/novelty-resolution/finite-checks.json').read_text())
assert len(results['rows'])==30
assert all(not row['numerical_upper_certificate'] for row in results['rows'])
after=hashes(); assert all(after.values())
out={'status':'PASS','symbolic_checks':['Hessian entries and determinant','all 25 determinant coefficients','both stationarity identities','quintic elimination and nonzero polynomial','simplex comparison including axes'], 'independent_exact_forest_templates':count,'independent_traversal':'depth first, union-find cycle rejection','max_parameter_tried':max_t,'finite_input_hashes_match':True,'before_hashes':before,'after_hashes':after,'elapsed_seconds':time.perf_counter()-start,'scope':'exact algebra and finite template construction only; no certified numerical pricing or novelty claim'}
(here/'independent-results.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
