"""Independent tiny rational oracles for pricing, interpolation, incidence, and replay."""
import copy
from decimal import Decimal, localcontext
from fractions import Fraction as F
from itertools import combinations, permutations, product
import math
import numpy as np
import certificate as c


def expect_reject(fn):
    try:
        fn()
    except (ValueError, KeyError):
        return
    raise AssertionError("invalid witness or allocation accepted")


def dec(z):
    z = F(z)
    return Decimal(z.numerator)/Decimal(z.denominator)


def tiny_case():
    vectors = [[(1,0),(0,0)],[(0,2),(1,1)],[(1,0),(1,1)],[(2,0),(0,1)]]
    # vectors[user][resource] is a real two-antenna vector.
    re = [[[vectors[u][s][j] for s in range(2)] for j in range(2)] for u in range(4)]
    pairs = []
    for u,v in combinations(range(4),2):
        for s in range(2):
            a,b = vectors[u][s],vectors[v][s]
            g,h = sum(t*t for t in a),sum(t*t for t in b)
            r = F(sum(i*j for i,j in zip(a,b))**2,g*h) if g*h else F(0)
            pairs.append(dict(users=[u,v],resource=s,gain1=str(g),gain2=str(h),r=str(r)))
    return dict(K=4,S=2,M=2,pmin="1/1000",pmax="1/5",budget="1/2",channels_re=re,
                channels_im=[[[0,0],[0,0]] for _ in range(4)],pairs=pairs)


def physical_ratio(g,h,r,p,t):
    # Independent expression through both users' individual SINRs.
    return (1+g*p*(1-r*h*t/(1+h*t)))*(1+h*t*(1-r*g*p/(1+g*p)))


def main():
    ns = c.grid()
    assert ns[0]==10**6 and ns[-1]==2*10**8 and max(F(b,a) for a,b in zip(ns,ns[1:]))<=F(17,16)
    assert c.select_price(dict(diagnostics=[])) == 0
    assert c.select_price(dict(diagnostics=[dict(method="GRID_PRICE",price=.3),
             dict(method="OTHER",price=99),dict(method="GRID_PRICE",price=-2)])) == F(.3)
    for price in (F(0),F(3,2),F(100)):
        assert dec(c.exp_negative_upper(price)) >= (-dec(price)).exp()

    # Nonuniform subgrid and independently constructed physical SW-MMSE rates.
    sub = [ns[0],ns[10],ns[30],ns[-1]]
    n = np.array(sub,dtype=object)
    with localcontext() as ctx:
        ctx.prec = 85
        for g,h,r,price in [(F(0),F(0),F(0),F(40)),(F(0),F(5),F(0),F(0)),
                    (F(13),F(18),F(1),F(8)),(F(4),F(11),F(0),F(3)),
                    (F(1,2**125),F(2**95),F(1,2),F(300))]:
            tables,errors = c.axis_tables(sub,price,(g,h))
            params = c.coefficients(g,h,r)
            m = c.node_max(params,n,n[:,None]*n[None,:],tables[g],tables[h])
            c.verify_node_max(m,params,n,tables[g],tables[h])
            expect_reject(lambda: c.verify_node_max(m-1,params,n,tables[g],tables[h]))
            expect_reject(lambda: c.verify_node_max(m+1,params,n,tables[g],tables[h]))
            nodes = [F(v,c.D) for v in sub]
            brute = max(dec(physical_ratio(g,h,r,p,t))*(-dec(price*(p+t))).exp()
                        for p,t in product(nodes,repeat=2))
            assert dec(F(m,c.EXP_DENOM)) >= brute
            if (g,h,price) == (0,0,40):
                assert c.log_enclosure(F(m,c.EXP_DENOM))[1] < 0
            cap = c.log_enclosure(F(m,c.EXP_DENOM))[1]+errors[g]+errors[h]
            test_grid = sorted(nodes+[a+(b-a)*i/9 for a,b in zip(nodes,nodes[1:]) for i in range(1,9)])
            for p,t in product(test_grid,repeat=2):
                assert dec(cap) >= dec(physical_ratio(g,h,r,p,t)).ln()-dec(price*(p+t))

    case = tiny_case()
    run = dict(diagnostics=[dict(method="GRID_PRICE",price=7.)],
               schedule=[dict(users=[0,2],resource=0,powers=["1/10","1/5"]),
                         dict(users=[1,3],resource=1,powers=["1/10","1/10"])])
    binding = dict(case="tiny")
    result = c.make(case,run,binding)
    assert c.make(case,run,binding,result) == result
    require_rows = {(u,v,s):int(w) for u,v,s,m,w in result["edges"]}
    brute = max(sum(require_rows[*sorted(perm[2*s:2*s+2]),s] for s in range(2)) for perm in permutations(range(4)))
    assert brute == int(result["dp_max_integer"])
    data = {(row["users"][0],row["users"][1],row["resource"]):
            tuple(F(row[k]) for k in ("gain1","gain2","r")) for row in case["pairs"]}
    upper = F(result["global_upper_nats"])
    lower = F(result["feasible_lower_nats"])
    with localcontext() as ctx:
        ctx.prec = 85
        z = math.prod(physical_ratio(*data[*row["users"],row["resource"]],*map(F,row["powers"]))
                      for row in run["schedule"])
        assert dec(lower) <= dec(z).ln() <= dec(F(result["feasible_upper_nats"]))
        # Finite exhaustive feasible schedules/powers independent of the dual DP.
        levels = [F(1,1000),F(1,20),F(1,5)]
        best = F(0)
        for perm in permutations(range(4)):
            a,b = sorted(perm[:2]),sorted(perm[2:])
            for p in product(levels,repeat=4):
                if sum(p)<=F(1,2):
                    best=max(best,physical_ratio(*data[*a,0],p[a[0]],p[a[1]])*
                                  physical_ratio(*data[*b,1],p[b[0]],p[b[1]]))
        assert dec(upper) >= dec(best).ln()

    for key,new in (("binding",{}),("dp_max_integer","0"),("gap_upper_se","-1")):
        edited = dict(result)
        edited[key]=new
        expect_reject(lambda: c.make(case,run,binding,edited))
    edited=copy.deepcopy(result)
    edited["edges"][0][4]=str(int(edited["edges"][0][4])-1)
    expect_reject(lambda: c.make(case,run,binding,edited))
    bad=copy.deepcopy(run)
    bad["schedule"][0]["powers"][0]="100"
    expect_reject(lambda: c.make(case,bad,binding))
    bad=copy.deepcopy(run)
    bad["schedule"][0]["users"]=[0,1]
    expect_reject(lambda: c.make(case,bad,binding))
    bad=copy.deepcopy(case)
    bad["channels_re"][0][0][0]+=1
    expect_reject(lambda: c.make(bad,run,binding))
    print("PASS: exact feasibility and inputs, tiny exhaustive assignment/power oracle, signed pricing, "
          "off-grid inequalities, zero/extreme gains, upper/lower checks, witness mutations and replay")


if __name__ == "__main__":
    main()

