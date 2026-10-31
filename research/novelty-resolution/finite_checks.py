from pathlib import Path
from fractions import Fraction as F
from itertools import combinations
import json,time,hashlib
import numpy as np
from scipy.optimize import differential_evolution
from candidate_oracle import maximize,value
D=Path(__file__).resolve().parent
start=time.perf_counter()
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def candidate(t,parent):
    t=F(t)
    if parent is None:
        den=1+t*t+t**4
        return (2*t/den,2*t*t/den,(1-t*t-t**4)/den)
    z=(F(0),F(0),F(1));v=tuple(z[i]-parent[i] for i in range(3))
    b=((1-t*t)/(1+t*t),2*t/(1+t*t),F(0))
    if dot(v,v)==0:return b
    c=2*dot(v,b)/dot(v,v)
    return tuple(b[i]-c*v[i] for i in range(3))
def forest(edges,n=7):
    adj=[[] for _ in range(n)]
    for u,v in edges:adj[u].append(v);adj[v].append(u)
    visited=set();order=[]
    for root in range(n):
        if root in visited:continue
        visited.add(root);queue=[(root,None)]
        for u,parent in queue:
            order.append((u,parent))
            for v in adj[u]:
                if v==parent:continue
                if v in visited:return None
                visited.add(v);queue.append((v,u))
    return order
def represent(edges):
    order=forest(edges)
    if order is None:return None
    h={};tries=[]
    for u,parent in order:
        for t in range(100):
            w=candidate(t,None if parent is None else h[parent])
            if all((dot(w,v)==0)==(j==parent) and abs(dot(w,v))!=1 for j,v in h.items()):break
        else:raise AssertionError('candidate cap')
        assert dot(w,w)==1
        h[u]=w;tries.append(t)
    es={tuple(sorted(e)) for e in edges}
    for u,v in combinations(range(7),2):
        assert (dot(h[u],h[v])==0)==((u,v) in es)
        assert abs(dot(h[u],h[v]))!=1
    return h,max(tries)
count=0;maxt=0;maxbits=0;minnonzero=F(1);alphabet=set()
all_edges=list(combinations(range(6),2))
for m in range(4):
    for edges in combinations(all_edges,m):
        got=represent(edges)
        if got is None:continue
        h,t=got;count+=1;maxt=max(maxt,t)
        alphabet.update(h.values())
        for v in h.values():
            for z in v:maxbits=max(maxbits,abs(z.numerator).bit_length(),z.denominator.bit_length())
        for u,v in combinations(range(7),2):
            d=abs(dot(h[u],h[v]))
            if d:minnonzero=min(minnonzero,d)
assert count==556
identities=0
for r in [F(1,10),F(1,2),F(1)]:
 for l1,l2 in [(F(0),F(0)),(F(1,5),F(3,7)),(F(-1),F(2))]:
  for x,y in [(F(0),F(0)),(F(1,3),F(4,5)),(F(20),F(10))]:
   a=1-r;A=1+x;k=1+a*x;d=A+k*y
   C=A*(1-l1*A);B=2*a*A-k*(1+l1*A)
   fx=2*(1+a*y)/d-1/A-l1
   fy=2*k/d-1/(1+y)-l2
   assert fx*A*d==C+B*y
   assert fy*(1+y)*d==2*k-(1+l2)*A+(k-l2*(A+k))*y-l2*k*y*y
   identities+=2
  A=F(0);k=r;B=-r;C=0
  assert (2*k-(1+l2)*A)*B*B-(k-l2*(A+k))*C*B-l2*k*C*C==2*r**3
rows=[]
rs=[0.,.1,1-1/np.sqrt(2)-1e-7,1-1/np.sqrt(2)+1e-7,.9,1.]
settings=[(0.,0.,(0,5,0,5)),(.2,.3,(0,5,0,5)),(-.1,.2,(0,10,0,10)),(1.,2.,(0,100,0,100)),(.01,.001,(1,2,1,2))]
for i,(r,(l1,l2,box)) in enumerate((r,s) for r in rs for s in settings):
 sol=maximize(r,l1,l2,box)
 x=np.linspace(box[0],box[1],101)[:,None];y=np.linspace(box[2],box[3],101)[None,:]
 grid=float(value(x,y,r,l1,l2).max())
 de=differential_evolution(lambda z:-value(z[0],z[1],r,l1,l2),[(box[0],box[1]),(box[2],box[3])],seed=1000+i,maxiter=120,popsize=8,tol=1e-10,polish=True,workers=1)
 assert sol['value']>=grid-1e-7,(r,sol,grid)
 assert sol['value']>=-de.fun-1e-6,(r,sol,-de.fun)
 assert sol['candidates']<=17
 rows.append({'r':r,'prices':[l1,l2],'box':box,**sol,'grid_value':grid,'DE_feasible_value':float(-de.fun)})
result={'status':'PASS','forest_templates':count,'rational_dimension':3,'max_parameter_tried':maxt,'max_coordinate_bits':maxbits,'distinct_rational_vectors':len(alphabet),'minimum_nonzero_dot_local_templates':str(minnonzero),'exact_derivative_identities':identities,'pricing_cases':len(rows),'max_candidates_seen':max(z['candidates'] for z in rows),'rows':rows,'elapsed_seconds':time.perf_counter()-start,'scope':'exact template identities plus numerical prototype sanity; no new global numerical certificate or novelty clearance'}
out=D/'finite-checks.json';assert not out.exists()
out.write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
