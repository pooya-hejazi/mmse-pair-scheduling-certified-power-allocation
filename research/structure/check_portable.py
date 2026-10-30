"""Data-free replay of all saved integer objectives and numerical certificates."""
from pathlib import Path
import json,numpy as np
from solver_study import structure,assignment
R=Path(__file__).resolve().parent
d=json.loads((R/'solver-results.json').read_text())
for row in d['rows']:
 q=np.asarray(row['q']);st=structure(row['users'])
 optimum=max(assignment(q,m)[0] for m in st[-1])
 assert row['status']=='OPTIMAL' and abs(optimum-row['MILP'])<1e-7
 assert row['lower']<=optimum+1e-7 and optimum<=row['upper_priced']+1e-7
 assert abs(row['upper_priced']-row['LP_odd'])<1e-7
 if row['conflictfree_certificate']:assert abs(row['lower']-optimum)<1e-7
print(json.dumps({'integer_objectives_replayed':len(d['rows']),'result':'PASS','scope':'saved coefficient tables; original data provenance/preservation not checked by this portable script'}))
