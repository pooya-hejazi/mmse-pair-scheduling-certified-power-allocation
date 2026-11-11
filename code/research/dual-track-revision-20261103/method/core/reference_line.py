"""Independent symbolic line reference; no transfer polynomial code imported."""
from fractions import Fraction as F
import sympy as sp
from reference_orthogonal import log_interval

def _add(a,b):return a[0]+b[0],a[1]+b[1]
def _mul(a,b):
    values=[x*y for x in a for y in b];return min(values),max(values)
def _log(a):return log_interval(a[0])[0],log_interval(a[1])[1]
def _scale(c,a):return (c*a[0],c*a[1]) if c>=0 else (c*a[1],c*a[0])

def solve(problem,assignment,p,direction,lo,hi):
    p=list(map(F,p));direction=list(map(F,direction));lo,hi=F(lo),F(hi)
    t=sp.Symbol('t',real=True);expr=sp.Integer(0)
    for s,(i,j) in enumerate(assignment):
        g,h,r=problem.model.data[i,j,s];x=sp.Rational(g)*(sp.Rational(p[i])+sp.Rational(direction[i])*t);y=sp.Rational(h)*(sp.Rational(p[j])+sp.Rational(direction[j])*t)
        expr+=2*sp.log(1+x+y+sp.Rational(1-r)*x*y)-sp.log(1+x)-sp.log(1+y)
    num=sp.fraction(sp.cancel(sp.diff(expr,t)))[0];poly=sp.Poly(num,t)
    intervals=[(lo,lo),(hi,hi)]
    if lo<=0<=hi:intervals.append((F(0),F(0)))
    if not poly.is_zero and poly.degree()>0:
        for interval,multiplicity in poly.intervals(eps=sp.Rational(1,10**22)):
            a,b=map(F,interval);a=max(lo,a);b=min(hi,b)
            if a<=b:intervals.append((a,b))
    def objective(interval):
        total=(F(0),F(0))
        for s,(i,j) in enumerate(assignment):
            g,h,r=problem.model.data[i,j,s]
            x=_scale(g,_add((p[i],p[i]),_scale(direction[i],interval)))
            y=_scale(h,_add((p[j],p[j]),_scale(direction[j],interval)))
            d=_add(_add(_add((F(1),F(1)),x),y),_scale(1-r,_mul(x,y)))
            term=_add(_add(_scale(2,_log(d)),_scale(-1,_log(_add((F(1),F(1)),x)))),_scale(-1,_log(_add((F(1),F(1)),y))))
            total=_add(total,term)
        return total
    upper=max(objective(iv)[1] for iv in intervals)
    candidates=[(objective(((a+b)/2,(a+b)/2))[0],(a+b)/2) for a,b in intervals]
    lower,point=max(candidates)
    return dict(lower=lower,upper=upper,point=point,degree=int(poly.degree()) if not poly.is_zero else -1,roots=len(intervals)-2)
