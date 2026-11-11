"""Regenerate archived plots directly from unchanged CSV evidence."""
from pathlib import Path
import csv, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

H=Path(__file__).resolve().parent
R=H.parent
O=H/'paper/images'
O.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.labelsize':9,
                    'legend.fontsize':7.5,'pdf.fonttype':42,'ps.fonttype':42})
def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save(fig,name):
    fig.tight_layout(pad=.5)
    fig.savefig(O/(name+'.pdf'),bbox_inches='tight')
    fig.savefig(O/(name+'.png'),dpi=180,bbox_inches='tight')
    plt.close(fig)
rows=read(R/'phase1-cdl-20261109/cdl_results.csv')
k8=read(R/'phase1-cdl-20261109/cdl_k8_results.csv')
methods=['grid','slsqp','iwmmse','matching','proposed']
labels=['Grid','SLSQP','I-WMMSE','Matching–WMMSE','DP–SQP']
colors=['#777777','#d55e00','#009e73','#cc79a7','#0072b2']
styles=[':','--','-.','--','-']
fig,ax=plt.subplots(figsize=(3.35,2.5))
for m,label,c,ls in zip(methods,labels,colors,styles):
    v=sorted(float(r[m+'_rate'])/(8*math.log(2)) for r in rows)
    ax.step(v,np.arange(1,len(v)+1)/len(v),where='post',label=label,color=c,ls=ls,lw=1.6)
ax.set(xlabel='Occupied-band spectral efficiency (bit/s/Hz)',ylabel='Empirical cumulative fraction')
ax.legend(loc='lower right',fontsize=6.5);ax.grid(alpha=.25);save(fig,'cdl_rate_by_method')

gain=sorted((float(r['proposed_rate'])-max(float(r[m+'_rate']) for m in methods[:-1]))/(8*math.log(2)) for r in rows)
fig,ax=plt.subplots(figsize=(3.35,2.3))
ax.plot(range(1,54),gain,'-',color='#0072b2',lw=1.5)
ax.axhline(.05,color='.4',ls='--',lw=.8,label='0.05 reference')
ax.set(xlabel='Case rank by recorded gain',ylabel='SE difference (bit/s/Hz)',ylim=(0,.205))
ax.legend();ax.grid(alpha=.25);save(fig,'cdl_absolute_gain')

fig,ax=plt.subplots(figsize=(3.35,2.5))
for m,label,c,ls in zip(methods,labels,colors,styles):
    vals=[np.median([float(r[m+'_time']) for r in a]) for a in [k8,rows]]
    ax.plot([8,16],vals,marker='o',label=label,color=c,ls=ls,lw=1.3,ms=4)
ax.set(xlabel='Number of users K',ylabel='Median callable time (s)',yscale='log',xticks=[8,16])
ax.legend(loc='lower right',fontsize=6.5);ax.grid(alpha=.25,which='both');save(fig,'cdl_runtime')

ms=read(R/'phase0-audit-20261109/phase0_m_scan.csv')
fig,ax=plt.subplots(figsize=(3.35,2.35))
for name in sorted(set(r['name'] for r in ms)):
    a=sorted((r for r in ms if r['name']==name),key=lambda r:int(r['M_eff']))
    ax.plot([int(r['M_eff']) for r in a],[100*float(r['pairing_gain_uniform']) for r in a],color='.75',alpha=.45,lw=.55)
med=[np.median([100*float(r['pairing_gain_uniform']) for r in ms if int(r['M_eff'])==m]) for m in [2,4,8]]
ax.plot([2,4,8],med,'o-',color='#0072b2',lw=1.8,label='Median (32 cases)',ms=4)
ax.set(xlabel='Retained receive coordinates M',ylabel='Reassignment gain (%)',xticks=[2,4,8])
ax.legend();ax.grid(alpha=.25);save(fig,'phase1_pairing_vs_M')

abl=read(R/'phase1-cdl-20261109/cdl_ablation.csv')
fig,ax=plt.subplots(figsize=(3.35,2.35))
for m,label,c,ls in zip(['assignment','power','joint'],['Assignment only','Power only','Joint search'],colors[1:4],styles[1:4]):
    v=[np.mean([100*(float(r[m])/float(r['uniform'])-1) for r in abl if r['profile']==p]) for p in 'ABC']
    ax.plot(list('ABC'),v,marker='o',label=label,color=c,ls=ls,lw=1.4,ms=4)
ax.set(xlabel='CDL-derived profile',ylabel='Mean improvement (%)')
ax.legend(fontsize=7);ax.grid(alpha=.25);save(fig,'cdl_ablation')
print('Generated five revised data plots.')
