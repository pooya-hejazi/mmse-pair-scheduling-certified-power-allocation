import sys, json, hashlib, time
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations
from collections import Counter
import numpy as np
import mpmath as mp
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
SNAP=ROOT/'audit/frozen/NETWORK-CR015-A01'
D=SNAP/'research/novelty-resolution'
sys.path.insert(0,str(D))
from rational_oracle import maximize, objective_iv, iv, ln_point
start=time.perf_counter();mp.mp.dps=100
res=json.loads((D/'network-result.json').read_text())
npz=SNAP/'research/comparison/inputs/power-8.npz'
digest=hashlib.sha256(npz.read_bytes()).hexdigest()
assert digest==res['input_sha256']
manifest=json.loads((SNAP/'research/comparison/inputs.json').read_text())
assert digest==next(z['sha256'] for z in manifest if z.get('mode')=='power' and z.get('users')==8)
execmanifest=json.loads((D/'network-manifest.json').read_text())
for path,dig in execmanifest['files'].items():
    assert hashlib.sha256((SNAP/path).read_bytes()).hexdigest()==dig
data=np.load(npz,allow_pickle=False);h=data['h']
assert h.shape==(8,32,4) and h.dtype in (np.dtype('complex64'),np.dtype('complex128'))
def rat(z): return F(*float(z).as_integer_ratio())
H={(u,t):[(rat(z.real),rat(z.imag)) for z in h[u,:,t]] for u in range(8) for t in range(4)}
g={key:sum(x*x+y*y for x,y in vec) for key,vec in H.items()}
def cross(u,v,t):
    re=sum(x*a+y*b for (x,y),(a,b) in zip(H[u,t],H[v,t]))
    im=sum(x*b-y*a for (x,y),(a,b) in zip(H[u,t],H[v,t]))
    return re*re+im*im
expected={(u,v,t) for u,v in combinations(range(8),2) for t in range(4)}
rows=res['pricing_certificates']
keys=[(*row['users'],row['resource']) for row in rows]
assert len(rows)==112 and set(keys)==expected and len(set(keys))==112
assert res['grid_columns']==112*9
alpha=list(map(F,res['alpha']));beta=list(map(F,res['beta']));lam=F(res['lambda'])
assert len(alpha)==8 and len(beta)==4 and lam>=0
maxes=[None]*4;maxwidth=F(0)
for row,(u,v,t) in zip(rows,keys):
    gu,gv=g[u,t],g[v,t];r=cross(u,v,t)/(gu*gv)
    assert gu==F(row['gain1']) and gv==F(row['gain2']) and r==F(row['r'])
    out=maximize(r,lam/gu,lam/gv,(gu/20,gu/5,gv/20,gv/5))
    assert out['upper']==F(row['pricing_upper_nats'])
    assert out['upper']-out['lower']==F(row['pricing_width'])<=F(1,10**8)
    assert out['root_digits']==row['root_digits']
    needed=out['upper']-alpha[u]-alpha[v]
    assert needed<=beta[t]
    maxes[t]=needed if maxes[t] is None else max(maxes[t],needed)
    maxwidth=max(maxwidth,F(row['pricing_width']))
assert maxes==beta
up=sum(alpha)+sum(beta)+lam*F(4,5)
assert up==F(res['upper_nats'])
users=Counter();resources=Counter();power=F(0);low=F(0);high=F(0);truevalue=mp.mpf(0)
def mm(z): return mp.mpf(z.numerator)/z.denominator
for row in res['schedule']:
    u,v=row['users'];t=row['resource'];p,q=map(F,row['powers'])
    assert u!=v and (min(u,v),max(u,v),t) in expected
    assert F(1,20)<=p<=F(1,5) and F(1,20)<=q<=F(1,5)
    users.update([u,v]);resources.update([t]);power+=p+q
    gu,gv=g[u,t],g[v,t];c=cross(u,v,t);r=c/(gu*gv)
    l,hi=objective_iv(iv(p*gu),iv(q*gv),r,0,0)
    assert l==F(row['rate_lower_nats']);low+=l;high+=hi
    # Exact Sherman-Morrison true-MMSE SINRs, evaluated independently.
    gamma1=p*gu-p*q*c/(1+q*gv)
    gamma2=q*gv-p*q*c/(1+p*gu)
    actual=mp.log(1+mm(gamma1))+mp.log(1+mm(gamma2))
    assert mm(l)<=actual<=mm(hi)
    truevalue+=actual
assert users==Counter(range(8)) and resources==Counter(range(4))
assert power==F(res['radiated_power_W'])==F(4,5)
assert low==F(res['lower_nats']) and 0<low<=up
assert abs(float(truevalue)-res['numerical_MILP_nats'])<1e-10
l2,h2=ln_point(2)
lb,ub=low/h2,up/l2
assert float(lb)==res['lower_sumSE_display'] and float(ub)==res['upper_sumSE_display']
assert float((up-low)/low)==res['relative_gap_upper_display']
scale=10**8
floor8=F((lb*scale).numerator//(lb*scale).denominator,scale)
ceil8=F(-(-(ub*scale).numerator//(ub*scale).denominator),scale)
output={'status':'PASS','shape':list(h.shape),'dtype':str(h.dtype),'npz_keys':data.files,'recomputed_pricings':112,'max_pricing_width':float(maxwidth),'all_gain_correlation_rows_match':True,'all_repaired_dual_constraints_valid':True,'exact_primal_feasible':True,'radiated_power_W':str(power),'lower_nats_display':float(low),'upper_nats_display':float(up),'outward_8decimal_sumSE':[str(floor8),str(ceil8)],'gap_upper_percent_display':float(100*(up-low)/low),'elapsed_seconds':time.perf_counter()-start,'scope':'one exact stored-input integration; accepted pair oracle reused, numerical LP/MILP not re-solved'}
print(json.dumps(output,indent=2))
