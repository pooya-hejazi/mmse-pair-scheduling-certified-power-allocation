from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal,localcontext
import json,time
import mpmath as mp
from rational_oracle import maximize,ln_point
D=Path(__file__).resolve().parent;start=time.perf_counter();mp.mp.dps=100
logs=0
for z in [F(1),F(2),F(1,3),F(10**30),F(1,10**30),F(10**70+1,10**70),F(10**70-1,10**70)]:
 lo,hi=ln_point(z)
 val=mp.log(mp.mpf(z.numerator)/z.denominator)
 assert mp.mpf(lo.numerator)/lo.denominator<=val<=mp.mpf(hi.numerator)/hi.denominator
 logs+=1
rows=[]
settings=[(F(0),F(0),(0,5,0,5)),(F(1,5),F(3,10),(0,5,0,5)),(F(-1,10),F(1,5),(0,10,0,10)),(F(1),F(2),(0,100,0,100)),(F(1,100),F(1,1000),(1,2,1,2))]
for r in [F(0),F(1,10),F(293,1000),F(9,10),F(1)]:
 for l1,l2,box in settings:
  out=maximize(r,l1,l2,box)
  def mm(f):return mp.mpf(f.numerator)/f.denominator
  x,y=map(mm,out['point']);rr=mm(r)
  value=2*mp.log(1+x+y+(1-rr)*x*y)-mp.log(1+x)-mp.log(1+y)-mm(l1)*x-mm(l2)*y
  assert mm(out['lower'])<=value<=mm(out['upper'])
  assert out['upper']-out['lower']<=F(1,10**8)
  rows.append({'r':str(r),'prices':[str(l1),str(l2)],'box':box,**{k:str(v) if isinstance(v,F) else [str(a) for a in v] if k=='point' else v for k,v in out.items()},'width_float_for_display':float(out['upper']-out['lower'])})
for box in [(1,1,0,5),(0,5,2,2),(1,1,2,2)]:
 out=maximize(F(1,2),F(1,5),F(3,10),box);assert out['upper']-out['lower']<=F(1,10**8)
result={'status':'PASS','rational_pricing_cases':len(rows),'degenerate_cases':3,'log_enclosure_cases':logs,'max_enclosure_width':max(r['width_float_for_display'] for r in rows),'rows':rows,'elapsed_seconds':time.perf_counter()-start,'scope':'provisional exact-root/interval implementation checks; no whole-network certificate or independent software acceptance'}
p=D/'oracle-checks.json';assert not p.exists();p.write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
