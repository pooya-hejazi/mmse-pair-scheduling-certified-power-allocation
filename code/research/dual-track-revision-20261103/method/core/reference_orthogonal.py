"""Independent global orthogonal K4 reference: exhaustive schedules and dual waterfill."""
import time,itertools
from fractions import Fraction as F
from decimal import Decimal,localcontext,ROUND_FLOOR,ROUND_CEILING

def log_interval(x):
    x=F(x)
    if x<=0:raise ValueError('log domain')
    if x==1:return F(0),F(0)
    with localcontext() as c:
        c.prec=65;c.rounding=ROUND_FLOOR;a=Decimal(x.numerator)/Decimal(x.denominator)
        c.rounding=ROUND_CEILING;b=Decimal(x.numerator)/Decimal(x.denominator)
        return F(a.ln().next_minus()),F(b.ln().next_plus())

def schedules(left):
    if not left:yield ();return
    for pair in itertools.combinations(left,2):
        for tail in schedules(tuple(x for x in left if x not in pair)):yield (pair,)+tail

def solve(case,deadline):
    if int(case['K'])!=4 or int(case['S'])!=2:raise ValueError('reference requires K4 S2')
    low,high,budget=map(F,(case['pmin'],case['pmax'],case['budget']))
    if not 0<low<=high or not 4*low<=budget:raise ValueError('reference domain')
    gains={}
    for row in case['pairs']:
        i,j=row['users'];s=row['resource'];g,h,r=map(F,(row['gain1'],row['gain2'],row['r']))
        if r!=0:raise ValueError('reference orthogonal only')
        for user,gain in ((i,g),(j,h)):
            if gain<0 or ((user,s) in gains and gains[user,s]!=gain):raise ValueError('gain inconsistency')
            gains[user,s]=gain
    if len(gains)!=8:raise ValueError('incomplete gains')
    ceiling=sum(max(log_interval(1+gains[i,s]*high)[1] for s in range(2)) for i in range(4))
    best_lower=None;best_schedule=None;uppers=[];completed=0;iterations=0
    def bound_value(gs,p):
        intervals=[log_interval(1+g*q) for g,q in zip(gs,p)]
        return sum(v[0] for v in intervals),sum(v[1] for v in intervals)
    for assignment in schedules(tuple(range(4))):
        if time.monotonic()>=deadline:break
        gs=[None]*4
        for s,pair in enumerate(assignment):
            for i in pair:gs[i]=gains[i,s]
        p=[min(high,budget/4)]*4
        lower,_=bound_value(gs,p);upper=sum(log_interval(1+g*high)[1] for g in gs)
        localbest=p[:];left=F(0);right=max(gs+[F(1)])
        while upper-lower>F(1,10**6) and time.monotonic()<deadline:
            iterations+=1;lam=(left+right)/2
            opt=[max(low,min(high,1/lam-1/g)) if g else low for g in gs]
            _,dual=bound_value(gs,opt);dual+=lam*(budget-sum(opt));upper=min(upper,dual)
            feasible=opt[:];excess=max(F(0),sum(feasible)-budget)
            for i in range(4):
                take=min(excess,feasible[i]-low);feasible[i]-=take;excess-=take
            candidate,_=bound_value(gs,feasible)
            if candidate>lower:lower=candidate;localbest=feasible
            if sum(opt)>budget:left=lam
            else:right=lam
            if iterations>=10000:break
        if best_lower is None or lower>best_lower:
            best_lower=lower;best_schedule=[dict(users=list(pair),resource=s,powers=[str(localbest[i]) for i in pair]) for s,pair in enumerate(assignment)]
        uppers.append(upper);completed+=1
        if iterations>=10000:break
    if best_lower is None:
        assignment=((0,1),(2,3));p=min(high,budget/4)
        best_schedule=[dict(users=list(pair),resource=s,powers=[str(p),str(p)]) for s,pair in enumerate(assignment)]
        best_lower=sum(log_interval(1+gains[i,s]*p)[0] for s,pair in enumerate(assignment) for i in pair)
    upper=max(uppers) if completed==6 else ceiling
    gap=upper-best_lower
    status='certified' if completed==6 and gap<=F(1,10**6) else ('iteration_cap' if iterations>=10000 else 'deadline')
    return dict(lower_nats=str(best_lower),upper_nats=str(upper),gap_nats=str(gap),schedule=best_schedule,
                status=status,assignments_completed=completed,iterations=iterations,scope='global orthogonal K4 subclass only')
