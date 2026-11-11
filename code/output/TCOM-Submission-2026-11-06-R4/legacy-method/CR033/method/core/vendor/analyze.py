"""Frozen descriptive analysis; does not run or alter a scientific cell."""
from pathlib import Path
import argparse,json,csv,math
import numpy as np
from scipy.stats import beta
from fractions import Fraction as F

def cp_interval(k,n,tail=.00625):
    return [float(beta.ppf(tail,k,n-k+1)) if k else 0.,float(beta.ppf(1-tail,k+1,n-k)) if k<n else 1.]

def analyze(root):
    root=Path(root);ledger=json.loads((root/'campaign-ledger.json').read_text());rows=ledger['rows'];assert len(rows)==128
    scalars=[]
    for row in rows:
        r={k:row.get(k) for k in ['panel','scene','index','case','method','charged','status','normal','operational_success','mathematical_success','elapsed','peak_RSS_bytes']}
        r['verification_timeouts']=len(row.get('verification_timeouts',[]));r['errors']=len(row.get('errors',[]))
        cellname=f"{row['case']}-{row['method']}"+(f"-repeat{row['index']}" if row['panel']=='reliability' else '')
        cell=root/'cells'/cellname;r['pricing_rows']=0;r['spatial_roots']=0;r['certificate_time']=None
        if (cell/'attempt.json').exists():
            attempt=json.loads((cell/'attempt.json').read_text());clo=None;chi=None
            for rec in row.get('receipts',[]):
                if not rec['timely']:continue
                v=json.loads((cell/rec['file']).read_text())['verification'];met=v.get('metrics',{})
                r['pricing_rows']=max(r['pricing_rows'],met.get('pricing_rows',0));r['spatial_roots']=max(r['spatial_roots'],met.get('spatial_roots',0))
                clo=F(v['lower_nats']) if clo is None else max(clo,F(v['lower_nats']));chi=F(v['upper_nats']) if chi is None else min(chi,F(v['upper_nats']))
                if r['certificate_time'] is None and chi-clo<=F(1,100):r['certificate_time']=rec['completed_at']-attempt['started_at']
        lo,hi=row.get('lower_nats'),row.get('upper_nats')
        if lo is not None and hi is not None:
            L,U=float(F(lo)),float(F(hi));S=8 if row['panel']=='scale' else (2 if row['panel']=='reliability' else 4)
            r.update(lower_nats=L,upper_nats=U,gap_nats=U-L,relative_gap=(U-L)/L if L>0 else None,SE=L/(S*math.log(2)))
        else:r.update(lower_nats=None,upper_nats=None,gap_nats=None,relative_gap=None,SE=None)
        if row.get('schedule'):
            r['power_W']=float(sum(F(v) for p in row['schedule'] for v in p['powers']))
            casepath=root/'inputs'/('reliability' if row['panel']=='reliability' else row['scene'])/(row['case']+'.json')
            case=json.loads(casepath.read_text());lookup={(p['users'][0],p['users'][1],p['resource']):p for p in case['pairs']};individual=[]
            for pair in row['schedule']:
                u,v=pair['users'];pw=list(map(F,pair['powers']))
                if u>v:u,v=v,u;pw.reverse()
                a=lookup[u,v,pair['resource']];x=float(F(a['gain1'])*pw[0]);y=float(F(a['gain2'])*pw[1]);rho=float(F(a['r']))
                individual.extend([math.log1p(x*(1+(1-rho)*y)/(1+y))/math.log(2)/case['S'],math.log1p(y*(1+(1-rho)*x)/(1+x))/math.log(2)/case['S']])
            r['min_user_SE']=min(individual);denom=len(individual)*sum(z*z for z in individual)
            r['jain_fairness']=sum(individual)**2/denom if denom else None
            r['curvature_fraction']=sum(2*(1-F(p['r']))**2>=1 for p in case['pairs'])/len(case['pairs'])
        scalars.append(r)
    strata=[]
    for scene in ['o1','asu']:
        a={r['index']:r for r in rows if r['scene']==scene and r['panel']=='main' and r['method']=='full'}
        b={r['index']:r for r in rows if r['scene']==scene and r['panel']=='main' and r['method']=='curvature'}
        assert len(a)==len(b)==12
        missing=sum(a[i]['operational_success'] is None or b[i]['operational_success'] is None for i in a)
        table={f'{x}{y}':0 for x in [0,1] for y in [0,1]}
        for i in a:
            if a[i]['operational_success'] is not None and b[i]['operational_success'] is not None:table[f"{int(a[i]['operational_success'])}{int(b[i]['operational_success'])}"]+=1
        if missing:interval=[-1.,1.];difference=None
        else:
            x,y=cp_interval(table['10'],12),cp_interval(table['01'],12);interval=[x[0]-y[1],x[1]-y[0]];difference=(table['10']-table['01'])/12
        strata.append({'scene':scene,'n':12,'missing':missing,'paired_table':table,'difference':difference,'conservative_interval':interval})
    missing=sum(s['missing'] for s in strata);interval=np.mean([s['conservative_interval'] for s in strata],axis=0).tolist()
    result={'primary':'equal-weight two-scene operational certificate fraction full-minus-curvature','strata':strata,'interval_95_bonferroni':interval,
            'difference':sum(s['difference'] for s in strata)/2 if not missing else None,'superiority_established':not missing and interval[0]>0,
            'complete_planned_nominal_cells':all(r['operational_success'] is not None for r in rows),'counts':{}}
    for panel in ['main','scale','reliability']:
        for method in sorted({r['method'] for r in rows if r['panel']==panel}):
            rr=[r for r in rows if r['panel']==panel and r['method']==method]
            result['counts'][panel+'/'+method]={'planned':len(rr),'normal':sum(bool(r.get('normal')) for r in rr),'operational':sum(r['operational_success'] is True for r in rr),'mathematical':sum(r['mathematical_success'] is True for r in rr),'missing':sum(r['operational_success'] is None for r in rr)}
    rng=np.random.default_rng(202611231);result['descriptive_paired_bootstrap']={}
    for field,left,right in [('SE','full','joint'),('gap_nats','full','curvature')]:
        arrays=[];counts=[]
        for scene in ['o1','asu']:
            aa={r['index']:r for r in scalars if r['panel']=='main' and r['scene']==scene and r['method']==left};bb={r['index']:r for r in scalars if r['panel']=='main' and r['scene']==scene and r['method']==right}
            d=np.array([aa[i][field]-bb[i][field] for i in aa if aa[i][field] is not None and bb[i][field] is not None]);counts.append(len(d))
            if len(d):arrays.append((d,float(d.mean()),rng.choice(d,size=(10000,len(d)),replace=True).mean(axis=1)))
        result['descriptive_paired_bootstrap'][field+'/'+left+'-'+right]={'valid_pairs_per_scene':counts,'mean_equal_scene_difference':sum(x[1] for x in arrays)/2 if len(arrays)==2 else None,'percentile_95':np.quantile((arrays[0][2]+arrays[1][2])/2,[.025,.975]).tolist() if len(arrays)==2 else None,'scope':'Exploratory complete-valid-interval pairs only; not primary test or replacement for failed-cell accounting'}
    dest=root/'analysis';dest.mkdir(exist_ok=False)
    keys=list(dict.fromkeys(k for r in scalars for k in r))
    with (dest/'all-cells.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(scalars)
    (dest/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');analyze(p.parse_args().root)
