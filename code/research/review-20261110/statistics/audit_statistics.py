from pathlib import Path
import csv, json, re, itertools, hashlib
from collections import Counter
from fractions import Fraction
import numpy as np
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[3]
R=ROOT/'research'
OUT=R/'review-20261110/statistics'
CDL=R/'phase1-cdl-20261109'
CROSS=R/'phase3-cdl-crosscheck-20261110/output'
METHODS=['grid','slsqp','iwmmse','matching','proposed']
def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def num(rows,key): return np.array([float(r[key]) for r in rows])
def wtl(x,eps=1e-4):
    x=np.asarray(x); return [int(np.sum(x>eps)),int(np.sum(np.abs(x)<=eps)),int(np.sum(x<-eps))]
def boot(x):
    x=np.asarray(x); rng=np.random.default_rng(20261109)
    draws=x[rng.integers(0,len(x),(10000,len(x)))]
    return {s:np.percentile(fn(draws,axis=1),[2.5,97.5]).tolist() for s,fn in [('mean',np.mean),('median',np.median)]}
def summary(g,abs_gain=None):
    g=np.asarray(g)
    d=dict(n=len(g),median_pct=float(np.median(g)*100),mean_pct=float(np.mean(g)*100),case_bootstrap_95ci_pct=boot(g*100),relative_band_wtl=wtl(g),min_pct=float(g.min()*100),max_pct=float(g.max()*100))
    if abs_gain is not None:
        a=np.asarray(abs_gain);d.update(abs_median_bpshz=float(np.median(a)),abs_mean_bpshz=float(np.mean(a)),abs_min_bpshz=float(a.min()),abs_max_bpshz=float(a.max()),absolute_band_wtl=wtl(a))
    return d
def cluster(g,seeds):
    g=np.asarray(g);seeds=np.asarray(seeds); unique=np.unique(seeds)
    groups=[np.flatnonzero(seeds==s) for s in unique]
    draws=[g[np.concatenate([groups[i] for i in ix])] for ix in itertools.product(range(len(groups)),repeat=len(groups))]
    return dict(method='Exact enumeration of 4^4=256 ordered seed-cluster bootstrap resamples, each selected cluster retains all its cases; pooled case-weighted statistic',seed_sizes={str(s):len(ix) for s,ix in zip(unique,groups)},seed_mean_pct={str(s):float(np.mean(g[ix])*100) for s,ix in zip(unique,groups)},seed_median_pct={str(s):float(np.median(g[ix])*100) for s,ix in zip(unique,groups)},mean_95ci_pct=np.percentile([np.mean(d)*100 for d in draws],[2.5,97.5]).tolist(),median_95ci_pct=np.percentile([np.median(d)*100 for d in draws],[2.5,97.5]).tolist(),limitation='Only four independent seed groups; sensitivity intervals, not reliable population-level confidence claims. Five extra sweep cases all belong to seed 2026110901.')
def paired(rows,baseline='best',s=None):
    p=num(rows,'proposed_rate');b=np.max(np.stack([num(rows,m+'_rate') for m in METHODS[:-1]]),axis=0) if baseline=='best' else num(rows,baseline+'_rate')
    if s is None:s=num(rows,'K')/2
    return summary((p-b)/b,(p-b)/(np.asarray(s)*np.log(2)))
def rates(rows):return {m:dict(mean=float(np.mean(num(rows,m+'_rate'))),median=float(np.median(num(rows,m+'_rate'))),upper_tail_p90_minus_median=float(np.quantile(num(rows,m+'_rate'),.9)-np.median(num(rows,m+'_rate'))),max_minus_median=float(np.max(num(rows,m+'_rate'))-np.median(num(rows,m+'_rate')))) for m in METHODS}
def runtime(rows):
    med={m:float(np.median(num(rows,m+'_time'))) for m in METHODS}
    return dict(median_seconds=med,ratio_median_vs_proposed={m:med[m]/med['proposed'] for m in METHODS[:-1]},proposed_fastest_case_count=int(sum(float(r['proposed_time'])<=min(float(r[m+'_time']) for m in METHODS[:-1]) for r in rows)),status_counts={m:dict(Counter(r[m+'_status'] for r in rows)) for m in METHODS})
primary=read(CDL/'cdl_results.csv');k8=read(CDL/'cdl_k8_results.csv');e2=read(CROSS/'e2_cases.csv');e3=read(CROSS/'e3a_results.csv')
assert len(primary)==53 and len(k8)==24 and len(e2)==53 and len(e3)==53
assert len({r['name'] for r in primary})==53
result={'methodology':{'case_bootstrap':'10,000 percentile resamples; numpy default_rng seed 20261109, linear percentile','ties':'Report both historical relative 1e-4 and stated absolute 1e-4 bit/s/Hz; choose and disclose consistently.','certification':'CSV arithmetic audit only; historic CDL returned schedules were not retained.'}}
result['cdl_k16']={'contrasts':{b:paired(primary,b) for b in ['best']+METHODS[:-1]},'rates':rates(primary),'runtime':runtime(primary),'profiles':{p:dict(contrast=paired([r for r in primary if r['profile']==p]),rates=rates([r for r in primary if r['profile']==p])) for p in 'ABC'}}
result['cdl_k8']={'contrasts':{b:paired(k8,b) for b in ['best']+METHODS[:-1]},'rates':rates(k8),'runtime':runtime(k8)}
seed=[int(re.search(r'-s(\d+)',r['name']).group(1)) for r in primary]
balanced=[float(r['separation']) in [.5,2,6,12] for r in primary]
assert sum(balanced)==48 and Counter(seed)=={2026110901:17,2026110902:12,2026110903:12,2026110904:12}
g=(num(primary,'proposed_rate')-np.max(np.stack([num(primary,m+'_rate') for m in METHODS[:-1]]),axis=0))/np.max(np.stack([num(primary,m+'_rate') for m in METHODS[:-1]]),axis=0)
result['primary_seed_sensitivity']={'pooled53':cluster(g,seed),'balanced48':dict(contrast=paired([r for r,b in zip(primary,balanced) if b]),cluster=cluster(g[balanced],np.asarray(seed)[balanced])),'sweep5':paired([r for r,b in zip(primary,balanced) if not b])}
for name,rows,gkey,akey in [('sionna',e2,'sionna_gain_case_mean','sionna_abs_bpshz_mean')]:
    vals=num(rows,gkey);ss=num(rows,'seed').astype(int);keep=num(rows,'separation')[:,None]==np.array([.5,2,6,12]); keep=keep.any(1)
    result[name]=dict(summary=summary(vals,num(rows,akey)),cluster53=cluster(vals,ss),balanced48=dict(summary=summary(vals[keep],num(rows,akey)[keep]),cluster=cluster(vals[keep],ss[keep])),profiles={p:summary(num([r for r in rows if r['profile']==p],gkey)) for p in 'ABC'})
    lookup={r['name']:r for r in primary}
    og=[(float(lookup[r['name']]['proposed_rate'])-max(float(lookup[r['name']][m+'_rate']) for m in METHODS[:-1]))/max(float(lookup[r['name']][m+'_rate']) for m in METHODS[:-1]) for r in rows]
    assert np.allclose(og,num(rows,'orig_gain'),atol=1e-14)
    result[name]['spearman']=float(spearmanr(og,vals).statistic)
result['e3a']={'summary':paired(e3),'cluster53':cluster(num(e3,'gain'),num(e3,'seed').astype(int)),'fraction_difference_median_from_sionna':abs(np.median(num(e3,'gain'))-np.median(num(e2,'sionna_gain_case_mean')))/np.median(num(e2,'sionna_gain_case_mean'))}
long=read(CDL/'cdl_long_baseline.csv')
result['long_baseline']={b:summary((num(long,'proposed10')-num(long,b))/num(long,b),(num(long,'proposed10')-num(long,b))/(8*np.log(2))) for b in ['matching30','slsqp30']}
abl=read(CDL/'cdl_ablation.csv')
result['cdl_ablation']={'n':len(abl),'mean_pct':{m:float(np.mean((num(abl,m)-num(abl,'uniform'))/num(abl,'uniform'))*100) for m in ['assignment','power','joint']},'by_profile':{p:{m:float(np.mean((num([r for r in abl if r['profile']==p],m)-num([r for r in abl if r['profile']==p],'uniform'))/num([r for r in abl if r['profile']==p],'uniform'))*100) for m in ['assignment','power','joint']} for p in 'ABC'}}
ms=read(R/'phase0-audit-20261109/phase0_m_scan.csv')
result['m_scan']={str(m):dict(n=len([r for r in ms if int(r['M_eff'])==m]),median_pct=float(np.median(num([r for r in ms if int(r['M_eff'])==m],'pairing_gain_uniform'))*100),p90_pct=float(np.percentile(num([r for r in ms if int(r['M_eff'])==m],'pairing_gain_uniform'),90)*100),gt1_count=int(sum(float(r['pairing_gain_uniform'])>.01 for r in ms if int(r['M_eff'])==m)),gt5_count=int(sum(float(r['pairing_gain_uniform'])>.05 for r in ms if int(r['M_eff'])==m))) for m in [2,4,8]}
ray=read(R/'phase1-benchmark-20261109/m2_results.csv');ctl=read(R/'phase1-benchmark-20261109/controlled_results.csv')
result['ray']={f'K{k}':dict(rates=rates([r for r in ray if int(r['K'])==k]),contrasts={b:paired([r for r in ray if int(r['K'])==k],b) for b in ['best','slsqp','matching']}) for k in [8,16]}
result['controlled']={'rates':rates(ctl),'contrasts':{b:paired(ctl,b) for b in ['best','matching']}}
cert=read(R/'phase1-benchmark-20261109/m2_certification.csv');gap=num(cert,'gap_nats')
result['m2_certification']=dict(n=len(cert),count_le_001=int(sum(gap<=.01)),tight_gap_range=[float(gap[gap<=.01].min()),float(gap[gap<=.01].max())],loose_gap_range=[float(gap[gap>.01].min()),float(gap[gap>.01].max())],status_counts=dict(Counter(r['status'] for r in cert)),note='producer upper versus independently checked schedule lower in run_certification.py; no replayed certificate-tree validation in that runner; separate rerun from rate benchmark.')
# Recompute per-case channel summaries directly from retained rational pair records.
channel_rows=[]
for path in sorted((CDL/'cases').glob('*.json')):
    c=json.loads(path.read_text());rv=np.array([float(Fraction(p['r'])) for p in c['pairs']]); h=np.asarray(c['channels_re'])+1j*np.asarray(c['channels_im']);gain=(abs(h)**2).sum(1);snr=10*np.log10(.1*gain)
    channel_rows.append(dict(name=c['name'],profile=c['metadata']['profile'],r_median=float(np.median(rv)),r_p90=float(np.percentile(rv,90)),snr_median_db=float(np.median(snr))))
result['cdl_channels']={p:{key:[min(r[key] for r in channel_rows if r['profile']==p),max(r[key] for r in channel_rows if r['profile']==p)] for key in ['r_median','r_p90','snr_median_db']} for p in 'ABC'}
result['input_hashes']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [CDL/'cdl_results.csv',CDL/'cdl_k8_results.csv',CDL/'cdl_long_baseline.csv',CDL/'cdl_ablation.csv',CROSS/'e2_cases.csv',CROSS/'e3a_results.csv',R/'phase0-audit-20261109/phase0_m_scan.csv',R/'phase1-benchmark-20261109/m2_results.csv',R/'phase1-benchmark-20261109/m2_certification.csv']}
# Self-check boundary count integrity and stored published central estimate.
assert abs(result['cdl_k16']['contrasts']['best']['median_pct']-1.3103914212041167)<1e-10
assert result['m_scan']['4']['gt5_count']>0
assert all(sum(result[k]['contrasts'][b]['absolute_band_wtl'])==result[k]['contrasts'][b]['n'] for k in ['cdl_k16','cdl_k8'] for b in result[k]['contrasts'])
(OUT/'corrected_statistics.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
with (OUT/'paired_contrasts.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['population','baseline','n','median_pct','mean_pct','mean_ci_lo_pct','mean_ci_hi_pct','median_ci_lo_pct','median_ci_hi_pct','abs_median_bpshz','wtl_relative','wtl_absolute']);w.writeheader()
    for pop in ['cdl_k16','cdl_k8']:
        for b,s in result[pop]['contrasts'].items():w.writerow(dict(population=pop,baseline=b,**{k:s[k] for k in ['n','median_pct','mean_pct','abs_median_bpshz']},mean_ci_lo_pct=s['case_bootstrap_95ci_pct']['mean'][0],mean_ci_hi_pct=s['case_bootstrap_95ci_pct']['mean'][1],median_ci_lo_pct=s['case_bootstrap_95ci_pct']['median'][0],median_ci_hi_pct=s['case_bootstrap_95ci_pct']['median'][1],wtl_relative='/'.join(map(str,s['relative_band_wtl'])),wtl_absolute='/'.join(map(str,s['absolute_band_wtl']))))
print(json.dumps({k:result[k] for k in ['primary_seed_sensitivity','m_scan','cdl_ablation','m2_certification','cdl_channels']},indent=2))
print('K16',json.dumps(result['cdl_k16']['contrasts'],indent=2));print('K8',json.dumps(result['cdl_k8'],indent=2))
# Additional retained-data checks: M=8 certification central claims and Sionna correlations.
final=R/'manuscript-refinement-20261106/certification/final'
frows=read(final/'results.csv')
newlow=num(frows,'new_lower_nats');newup=num(frows,'new_upper_nats');oldlow=num(frows,'old_full_lower_nats');anchor=num(frows,'anchor_lower_nats');baseup=num(frows,'baseline_upper_nats');ngap=num(frows,'new_gap_nats');bgap=num(frows,'baseline_gap_nats')
rho=1-(newup-anchor)/(baseup-anchor)
is_o1=np.array([r['scene']=='o1' for r in frows]);is_k8=np.array([r['K']=='8' for r in frows])
result['m8_certification']=dict(n=len(frows),new_target_count=int(sum(ngap<=.01)),baseline_target_count=int(sum(bgap<=.01)),new_target_by_scene={sc:sum(float(r['new_gap_nats'])<=.01 for r in frows if r['scene']==sc) for sc in ['o1','asu']},median_fixed_anchor_reduction_pct=float(np.median(rho)*100),remaining_gap_range=[float(ngap[ngap>.01].min()),float(ngap.max())],median_final_gap_nats=float(np.median(ngap)),median_baseline_gap_nats=float(np.median(bgap)),median_grid_gain_pct=float(np.median((newlow-anchor)/anchor)*100),grid_gt1_count=int(sum((newlow-anchor)/anchor>.01)),median_old_full_gain_pct=float(np.median((newlow-oldlow)/oldlow)*100),old_full_gt1_count=int(sum((newlow-oldlow)/oldlow>.01)),max_old_o1_gap_nats=float(np.max((newup-oldlow)[is_o1])),max_possible_old_full_relative_gain_k8_pct=float(np.max(((newup-oldlow)/oldlow)[is_k8])*100),median_times={key:float(np.median(num(frows,key))) for key in ['new_producer_seconds','new_checker_seconds','baseline_producer_seconds','baseline_checker_seconds']})
result['m8_curvature_counts']={sc:{key:sum(row['curvature'][key] for row in json.loads((final/'rows.json').read_text()) if row['scene']==sc) for key in ['total','quadrant','combined'] if key in json.loads((final/'rows.json').read_text())[0]['curvature']} for sc in ['o1','asu']}
# Pooled r summaries are descriptive: pair/resource records share users, seeds and channel draws.
from scipy.stats import ks_2samp
correlations=[]
for folder,pattern in [(CDL/'cases','*.json'),(R/'phase3-cdl-crosscheck-20261110/cases','*-sionna-r*.json')]:
    rr=[]
    for p in sorted(folder.glob(pattern)):
        c=json.loads(p.read_text(encoding='utf-8'));rr.extend(float(Fraction(t['r'])) for t in c['pairs'])
    correlations.append(np.asarray(rr))
result['correlation_crosscheck']={'n_records':[len(x) for x in correlations],'median':[float(np.median(x)) for x in correlations],'p90':[float(np.percentile(x,90)) for x in correlations],'ks_D':float(ks_2samp(*correlations).statistic),'warning':'Do not interpret iid two-sample KS p-value: pooled pair/resource records are dependent.'}
assert result['m8_certification']['new_target_count']==27
(OUT/'corrected_statistics.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('M8',json.dumps(result['m8_certification'],indent=2));print('correlation',result['correlation_crosscheck'])
# Count actual shared random streams, rather than treating three Sionna realizations as independent.
realization_groups={}
for p in sorted((R/'phase3-cdl-crosscheck-20261110/cases').glob('*-sionna-r*.json')):
    c=json.loads(p.read_text(encoding='utf-8'));md=c['metadata']; realization_groups.setdefault(md['base_case'],[]).extend(md['sionna_seeds'])
result['sionna_rng_audit']={'n_cases':len(realization_groups),'streams_per_case':sorted(set(len(x) for x in realization_groups.values())),'unique_streams_per_case':sorted(set(len(set(x)) for x in realization_groups.values())),'reused_entries_per_case':sorted(set(len(x)-len(set(x)) for x in realization_groups.values())),'cause':'realization*10+i seed stride with 16 users creates six overlaps between adjacent realizations','impact':'Realizations use overlapping underlying random streams. This invalidates the description three independent draws, although user gains/orientations differ. No campaign rerun was performed.'}
assert len(realization_groups)==53 and all(len(v)==48 and len(set(v))==36 for v in realization_groups.values())
curv=json.loads((final/'rows.json').read_text())
result['m8_curvature_counts']={sc:dict(total=sum(r['curvature']['price_rows'] for r in curv if r['scene']==sc),quadrant=sum(r['curvature']['quadrant_roots'] for r in curv if r['scene']==sc),combined=sum(r['curvature']['quadrant_roots']+r['curvature']['finite_box_only_roots'] for r in curv if r['scene']==sc)) for sc in ['o1','asu']}
k8g=(num(k8,'proposed_rate')-num(k8,'slsqp_rate'))/num(k8,'slsqp_rate')
result['k8_seed_sensitivity']=cluster(k8g,[int(re.search(r'-s(\d+)',r['name']).group(1)) for r in k8])
result['k8_seed_sensitivity']['limitation']='Only four independent seed groups; sensitivity interval. K8 has three profiles, two separations and four shared seeds.'
(OUT/'corrected_statistics.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('RNG',result['sionna_rng_audit']);print('curvature',result['m8_curvature_counts']);print('K8 cluster',result['k8_seed_sensitivity'])
