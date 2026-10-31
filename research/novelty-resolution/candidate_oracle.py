"""Numerical prototype of finite-candidate MMSE pair pricing. NOT an upper certificate."""
import numpy as np
from numpy.polynomial import Polynomial as P

def value(x,y,r,l1,l2):
    return 2*np.log1p(x+y+(1-r)*x*y)-np.log1p(x)-np.log1p(y)-l1*x-l2*y

def real_roots(poly):
    # Numerical engineering only: filtering and root computation need interval
    # replacements before this routine may certify a global upper bound.
    coef=np.array(poly.coef,dtype=float)
    while len(coef)>1 and coef[-1]==0:coef=coef[:-1]
    if len(coef)==1:return []
    return [z.real for z in P(coef).roots() if abs(z.imag)<1e-7*(1+abs(z.real))]

def maximize(r,l1,l2,box):
    xl,xu,yl,yu=map(float,box)
    assert 0<=r<=1 and 0<=xl<=xu and 0<=yl<=yu
    pts=[(x,y) for x in [xl,xu] for y in [yl,yu]]
    def add(x,y):
        if xl-1e-8<=x<=xu+1e-8 and yl-1e-8<=y<=yu+1e-8:
            pts.append((float(np.clip(x,xl,xu)),float(np.clip(y,yl,yu))))
    if r==0:
        def one(l,lo,hi):return hi if l<=0 else np.clip(1/l-1,lo,hi)
        add(one(l1,xl,xu),one(l2,yl,yu))
    else:
        a=1-r;X=P([0,1]);A=1+X;k=1+a*X
        C=A*(1-l1*A);B=2*a*A-k*(1+l1*A)
        Q=(2*k-(1+l2)*A)*B*B-(k-l2*(A+k))*C*B-l2*k*C*C
        for x in real_roots(Q):
            if abs(B(x))>1e-12:add(x,-C(x)/B(x))
        for x in [xl,xu]:
            aa=1+x;kk=1+a*x
            eq=P([2*kk-(1+l2)*aa,kk-l2*(aa+kk),-l2*kk])
            for y in real_roots(eq):add(x,y)
        for y in [yl,yu]:
            aa=1+y;kk=1+a*y
            eq=P([2*kk-(1+l1)*aa,kk-l1*(aa+kk),-l1*kk])
            for x in real_roots(eq):add(x,y)
    unique=list(dict.fromkeys(pts))
    vals=[float(value(x,y,r,l1,l2)) for x,y in unique]
    j=int(np.argmax(vals))
    return {'point':unique[j],'value':vals[j],'candidates':len(unique),'numerical_upper_certificate':False}
