import sys, json, time, hashlib
from pathlib import Path
from fractions import Fraction as F
import mpmath as mp
import sympy as sp
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
SNAP = ROOT / 'audit/frozen/ORACLE-CR015-A01'
sys.path.insert(0, str(SNAP / 'research/novelty-resolution'))
from rational_oracle import maximize, ln_point
mp.mp.dps = 170
def mm(x):
    x=F(x)
    return mp.mpf(x.numerator)/x.denominator
def val(x,y,r,p,q):
    x,y,r,p,q=map(mm,(x,y,r,p,q))
    d=1+x+y+(1-r)*x*y
    return mp.log(d*d/((1+x)*(1+y)))-p*x-q*y
started=time.perf_counter()
rows=[]
cases=[('cancelled_denominator',F(3,4),0,0,(0,5,0,5),None),
 ('repeated_boundary',F(1,2),1,1,(0,5,0,5),(0,0)),
 ('negative_prices',1,-2,-3,(1,7,2,6),(7,6)),
 ('collapsed_x',F(2,3),F(1,7),F(1,9),(2,2,0,9),None),
 ('collapsed_y',1,F(1,7),F(1,9),(0,9,2,2),None),
 ('singleton',F(1,2),-1,2,(2,2,3,3),(2,3)),
 ('separable_signed',0,-1,F(1,3),(1,5,0,8),(5,2)),
 ('narrow_box',F(9,10),F(1,5),F(1,7),(1,1+F(1,10**20),2,2+F(1,10**20)),None)]
for r in [F(1,10),F(1,10**30),F(1,4)]:
    x,y=F(1),F(2); d=1+x+y+(1-r)*x*y
    p=2*(1+(1-r)*y)/d-1/(1+x)
    q=2*(1+(1-r)*x)/d-1/(1+y)
    cases.append(('known_concave_max_'+str(r),r,p,q,(0,4,0,5),(x,y)))
for name,r,p,q,box,known in cases:
    out=maximize(r,p,q,box)
    lo,hi=mm(out['lower']),mm(out['upper'])
    assert out['upper']-out['lower']<=F(1,10**8)
    assert lo<=val(*out['point'],r,p,q)<=hi, name
    if known is not None:
        assert lo<=val(*known,r,p,q)<=hi, name
    xl,xu,yl,yu=map(F,box)
    for i in range(11):
        for j in range(11):
            assert val(xl+(xu-xl)*i/10,yl+(yu-yl)*j/10,r,p,q)<=hi, (name,i,j)
    rows.append({'name':name,'candidate_boxes':out['candidate_boxes'],'digits':out['root_digits'],'width':str(out['upper']-out['lower'])})
logcases=[F(1),F(1,10**100),F(10**100),F(10**100-1,10**100),F(10**100+1,10**100),F(7,13)]
for z in logcases:
    lo,hi=ln_point(z)
    assert mm(lo)<=mp.log(mm(z))<=mm(hi)
try:
    maximize(F(1,3),F(1,5),F(1,7),(0,4,0,4),F(1,10**100))
except ArithmeticError:
    closed=True
else:
    raise AssertionError('unexpected ultra-tight enclosure')
for args in [(-1,0,0,(0,1,0,1)),(F(1,2),0,0,(-1,1,0,1)),(F(1,2),0,0,(2,1,0,1))]:
    try: maximize(*args)
    except ValueError: pass
    else: raise AssertionError('invalid domain accepted')
X=sp.Symbol('X');r=sp.Rational(1,2);a=1-r;A=1+X;k=1+a*X
C=A*(1-A);B=2*a*A-k*(1+A)
P=sp.Poly((2*k-2*A)*B**2-(k-(A+k))*C*B-k*C**2,X)
assert sp.gcd(P,P.diff()).degree()>0
result={'status':'PASS','cases':rows,'independent_feasible_grid_points':len(cases)*121,'log_cases':len(logcases),'exhaustion_fails_closed':closed,'repeated_root_fixture_verified':True,'elapsed_seconds':time.perf_counter()-started,'scope':'isolated pair software checks; sampling is not proof of an upper bound'}
print(json.dumps(result,indent=2))
