"""Data-free checks of published witness, MILP, exact small hull, and analytic pair loss."""
from pathlib import Path
import json,numpy as np
from scipy.optimize import linprog,milp,Bounds,LinearConstraint
import experiment as e
R=Path(__file__).resolve().parent
d=json.loads((R/'summary.json').read_text());w=d['headroom']['max_gap_witness']
h=(np.array(w['H_est_real'])+1j*np.array(w['H_est_imag'])).reshape(4,-1,2);e.NOISE=w['noise']
q=e.column_scores(h);assert np.allclose(q,w['q'])
cuts=np.zeros((6,12))
for j,g in enumerate(e.GROUPS):
    comp=tuple(u for u in range(4) if u not in g);cuts[j,e.COLS.index((g,0))]=1;cuts[j,e.COLS.index((comp,1))]=-1
rng=np.random.default_rng(4343)
for score in [q]+[rng.normal(size=12) for _ in range(100)]:
    exact=float((e.VERT@score).max())
    ip=milp(-score,integrality=np.ones(12),bounds=Bounds(0,1),constraints=LinearConstraint(e.MAT,np.ones(6),np.ones(6)),options={'time_limit':5,'mip_rel_gap':0})
    lp=linprog(-score,A_eq=np.vstack([e.MAT,cuts]),b_eq=np.r_[np.ones(6),np.zeros(6)],bounds=(0,1),method='highs')
    assert ip.status==0 and lp.success and np.allclose([-ip.fun,-lp.fun],exact,atol=1e-7)
lo,up,_,_=e.solve(q);assert abs(up-lo-w['gap'])<1e-7 and up-lo>.4
print(json.dumps({'result':'PASS','objectives':101,'physical_gap':up-lo,'scope':'data-free model checks; no claim of experiment reproduction or novelty'}))
