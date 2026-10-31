"""Root-isolated pair pricing with rational interval arithmetic and bounded logs.

Scope: rational inputs, true-channel unweighted MMSE, rectangular normalized power.
Trusted libraries: SymPy real-root isolation and Decimal correctly-rounded ln.
Raises on unresolved enclosure; never substitutes floating roots as a certificate.
"""
from fractions import Fraction as F
from decimal import Decimal,localcontext,ROUND_FLOOR,ROUND_CEILING
import sympy as s

def iv(x):return (F(x),F(x))
def add(a,b):return a[0]+b[0],a[1]+b[1]
def neg(a):return -a[1],-a[0]
def sub(a,b):return add(a,neg(b))
def mul(a,b):
    p=[x*y for x in a for y in b];return min(p),max(p)
def div(a,b):
    if b[0]<=0<=b[1]:raise ArithmeticError('denominator interval contains zero')
    return mul(a,(1/b[1],1/b[0]))
def poly_iv(p,z):
    out=iv(0)
    for c in p.all_coeffs():out=add(mul(out,z),iv(c))
    return out
def ln_point(z,precision=60):
    z=F(z)
    if z<=0:raise ValueError('log nonpositive')
    if z==1:return iv(0)
    with localcontext() as ctx:
        ctx.prec=precision
        ctx.rounding=ROUND_FLOOR;lo=Decimal(z.numerator)/Decimal(z.denominator)
        ctx.rounding=ROUND_CEILING;hi=Decimal(z.numerator)/Decimal(z.denominator)
        # ln itself is correctly rounded HALF_EVEN, irrespective of context mode.
        low=Decimal(0) if lo==1 else lo.ln().next_minus()
        high=Decimal(0) if hi==1 else hi.ln().next_plus()
        return F(low),F(high)
def log_iv(z):return ln_point(z[0])[0],ln_point(z[1])[1]
def objective_iv(x,y,r,l1,l2):
    d=add(add(add(iv(1),x),y),mul(iv(1-r),mul(x,y)))
    out=sub(sub(mul(iv(2),log_iv(d)),log_iv(add(iv(1),x))),log_iv(add(iv(1),y)))
    return sub(sub(out,mul(iv(l1),x)),mul(iv(l2),y))
def clip_interval(z,lo,hi):
    a=max(z[0],lo);b=min(z[1],hi)
    return None if a>b else (a,b)

def maximize(r,l1,l2,box,tolerance=F(1,10**8)):
    r,l1,l2=map(F,(r,l1,l2));xl,xu,yl,yu=map(F,box)
    if not (0<=r<=1 and 0<=xl<=xu and 0<=yl<=yu):raise ValueError('domain')
    if tolerance<=0:raise ValueError('tolerance')
    X=s.Symbol('X');a=1-r;A=1+X;k=1+a*X
    C=s.Poly(A*(1-l1*A),X,domain=s.QQ)
    B=s.Poly(2*a*A-k*(1+l1*A),X,domain=s.QQ)
    P=s.Poly((2*k-(1+l2)*A)*B.as_expr()**2-(k-l2*(A+k))*C.as_expr()*B.as_expr()-l2*k*C.as_expr()**2,X,domain=s.QQ)
    def edge(t,price):
        h=1+a*t;e=1+t
        return s.Poly(2*h*(1+X)-(e+h*X)-price*(1+X)*(e+h*X),X,domain=s.QQ)
    # Roots with B=0 are never feasible interior stationary points. Repeated
    # common factors are removed entirely, then each remaining root is isolated.
    if r>0:
        while True:
            g=s.gcd(P,B)
            if g.degree()<=0:break
            P=P.exquo(g)
        P=P.sqf_part()
    def roots(p,digits):
        if p.degree()<=0:return []
        return [(F(z[0]),F(z[1])) for z,m in p.intervals(eps=s.Rational(1,10**digits))]
    for digits in [12,24,36]:
        boxes=[(iv(x),iv(y)) for x in [xl,xu] for y in [yl,yu]]
        unresolved=False
        if r==0:
            def one(price,lo,hi):return hi if price<=0 else max(lo,min(hi,1/price-1))
            boxes.append((iv(one(l1,xl,xu)),iv(one(l2,yl,yu))))
        else:
            if xl<xu and yl<yu:
                for z in roots(P,digits):
                    z=clip_interval(z,xl,xu)
                    if z is None:continue
                    try:y=div(neg(poly_iv(C,z)),poly_iv(B,z))
                    except ArithmeticError:unresolved=True;break
                    y=clip_interval(y,yl,yu)
                    if y is not None:boxes.append((z,y))
            for x in set([xl,xu]):
                for y in roots(edge(x,l2),digits):
                    y=clip_interval(y,yl,yu)
                    if y is not None:boxes.append((iv(x),y))
            for y in set([yl,yu]):
                for x in roots(edge(y,l1),digits):
                    x=clip_interval(x,xl,xu)
                    if x is not None:boxes.append((x,iv(y)))
        if unresolved:continue
        upper=max(objective_iv(x,y,r,l1,l2)[1] for x,y in boxes)
        feasible=[]
        for x,y in boxes:
            point=((x[0]+x[1])/2,(y[0]+y[1])/2)
            feasible.append((objective_iv(iv(point[0]),iv(point[1]),r,l1,l2)[0],point))
        lower,point=max(feasible,key=lambda z:z[0])
        assert lower<=upper
        if upper-lower<=tolerance:
            return {'lower':lower,'upper':upper,'point':point,'candidate_boxes':len(boxes),'root_digits':digits,'tolerance':F(tolerance),'method':'rational root intervals and outward Decimal ln'}
    raise ArithmeticError('requested enclosure unresolved after bounded refinement')
