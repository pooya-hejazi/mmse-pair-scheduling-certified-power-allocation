"""Small independent oracles for the scalar corrections and joint upper bound."""
from decimal import Decimal, localcontext
from fractions import Fraction as F
from itertools import combinations, product
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate as v


def dec(x):
    x = F(x)
    return Decimal(x.numerator)/Decimal(x.denominator)


def physical_ratio(g, h, r, p, t):
    # Reconstruct the rate via the two physical SINRs rather than the determinant.
    x, y = g*p, h*t
    return (1+x*(1-r*y/(1+y)))*(1+y*(1-r*x/(1+x)))


def test_axis_and_edges():
    for g, c, left in [(0,0,0), (2,2,F(1,2)), (2,2,0), (2,2,1),
                       (100,8,0), (100,8,F(1,3)), (1,1,0),
                       (F(1,2**80),F(1,2**160),0),
                       (2**100,F(1,2**80),F(1,1000))]:
        g, c, left = map(F, (g,c,left))
        upper = dec(v.axis_upper(g,c,left))
        for n in range(101):
            z = left + (1-left)*n/100
            ratio = ((1+c*z)/(1+c))**2 * (1+g)/(1+g*z)
            assert upper >= dec(ratio).ln() + dec(1-z)
        if (g,c,left) == (2,2,0):
            # For an orthogonal pair the unique axis maximum is z=1-1/g.
            exact = dec(F(2,3)).ln() + dec(F(1,2))
            assert 0 <= upper-exact < dec(F(1,10**16))
    for (g,h,r), low, b in [
            ((0,0,0),0,F(1,2)), ((0,9,0),0,F(1,4)),
            ((20,20,1),F(1,1000),F(1,8)), ((13,8,0),0,F(1,3)),
            ((1000,700,F(7,8)),F(1,100),F(1,8))]:
        g,h,r,low,b = map(F,(g,h,r,low,b))
        cap = dec(F(v.edge_weights((g,h,r),low,b)[1], v.SCALE))
        levels = [low + (2*b-low)*n/20 for n in range(21)]
        for p,t in product(levels, repeat=2):
            priced = dec(physical_ratio(g,h,r,p,t)).ln() + dec(2-(p+t)/b)
            assert cap >= priced


def small_case():
    vectors = [[(0,0),(2,0)],[(2,0),(0,1)],[(2,1),(1,2)],[(4,2),(2,-1)]]
    re = [[[vectors[u][t][a] for t in range(2)] for a in range(2)] for u in range(4)]
    pairs = []
    for i,j in combinations(range(4),2):
        for t in range(2):
            a,b = vectors[i][t], vectors[j][t]
            g,h = sum(x*x for x in a), sum(y*y for y in b)
            r = F(sum(x*y for x,y in zip(a,b))**2, g*h) if g*h else F(0)
            pairs.append(dict(users=[i,j],resource=t,gain1=str(g),gain2=str(h),r=str(r)))
    return dict(K=4,S=2,M=2,pmin="0",pmax="3/4",budget="3/2",channels_re=re,
                channels_im=[[[0,0],[0,0]] for _ in range(4)],pairs=pairs)


def test_joint():
    case = small_case()
    for low, high, budget in [(0,F(3,4),F(3,2)), (0,F(3,4),4),
                              (F(3,8),F(3,4),F(3,2)), (0,F(3,4),0), (0,0,1)]:
        case.update(pmin=str(low), pmax=str(high), budget=str(budget))
        model = v.reconstruct(case)
        b, equal_ub, analytic = v.upper_bounds(model)
        data = model[5]
        levels = sorted({F(low),F(high),b,F(low+high,2)})
        feasible = [p for p in product(levels,repeat=4) if sum(p)<=budget]
        best = equal = F(0)
        for i,j in combinations(range(4),2):
            m,n = sorted(set(range(4))-{i,j})
            def ratio(p):
                return (physical_ratio(*data[i,j,0],p[i],p[j])
                        * physical_ratio(*data[m,n,1],p[m],p[n]))
            equal = max(equal, ratio([b]*4))
            best = max(best, *(ratio(p) for p in feasible))
        assert dec(analytic) >= dec(best).ln()
        assert 0 <= dec(equal_ub)-dec(equal).ln() < dec(F(3,v.SCALE))
        if b == low:
            assert equal_ub == analytic


if __name__ == "__main__":
    with localcontext() as ctx:
        ctx.prec = 90
        test_axis_and_edges()
        test_joint()
    print("PASS: larger-root and endpoint enclosures, priced edges above/below uniform, "
          "exhaustive tiny joint model, zero gains, collinearity, singleton rails, slack and zero budget")
