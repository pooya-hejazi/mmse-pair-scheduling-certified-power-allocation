"""Build compact three-panel manuscript figure from retained campaign CSV."""
import os,csv
from pathlib import Path
BASE=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(BASE/'matplotlib-cache')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
rows=list(csv.DictReader((BASE/'campaign/raw.csv').open()))
assert len(rows)==72
for r in rows:
    for k in ('se_bits','elapsed_seconds','separation_deg'):r[k]=float(r[k])
arms=('DP-SQP','DP-Fu-SCA','DP-Thu-IDE')
labels=('DP + local SQP','DP + Fu-SCA adaptation','DP + Thu-IDE adaptation')
colors=('#185a9d','#d55e00','#009e73');styles=('-','--',':');markers=('o','s','^')
seps=(.5,2,6,12)
plt.rcParams.update({'font.size':7,'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.2,'axes.formatter.useoffset':False,'pdf.fonttype':42})
fig,axs=plt.subplots(1,3,figsize=(7.1,2.35))
for arm,label,color,style,marker in zip(arms,labels,colors,styles,markers):
    rr=lambda s:[r for r in rows if r['arm']==arm and r['separation_deg']==s]
    kw=dict(color=color,linestyle=style,marker=marker,markersize=3.5,markerfacecolor='none',linewidth=1.1,label=label)
    axs[0].plot(seps,[np.mean([r['se_bits'] for r in rr(s)]) for s in seps],**kw)
    axs[2].plot(seps,[np.mean([r['elapsed_seconds'] for r in rr(s)]) for s in seps],**kw)
    if arm!='DP-SQP':
        diffs=[]
        for s in seps:
            cur={r['case']:r for r in rows if r['arm']=='DP-SQP' and r['separation_deg']==s}
            diffs.append(np.mean([100*(cur[r['case']]['se_bits']-r['se_bits'])/r['se_bits'] for r in rr(s)]))
        axs[1].plot(seps,diffs,**kw)
axs[1].axhline(0,color='.4',linewidth=.6)
axs[2].axhline(10,color='.4',linewidth=.6,linestyle=':')
for ax,title,ylabel in zip(axs,('(a) Achieved SE','(b) Paired difference','(c) Actual runtime'),('SE (bit/s/Hz)','Relative SE difference (%)','Search time (s)')):
    ax.set(title=title,ylabel=ylabel,xlabel='Separation (degrees)',xticks=seps)
    ax.tick_params(labelsize=6.5)
handles,labels=axs[0].get_legend_handles_labels()
fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,-.015),ncol=3,frameon=False,fontsize=7)
fig.tight_layout(rect=(0,.09,1,1),pad=.7,w_pad=1)
for suffix in ('pdf','png'):
    fig.savefig(BASE/f'figures/modern_comparison_main.{suffix}',dpi=240,bbox_inches='tight')
print('Wrote figures/modern_comparison_main.pdf and .png')
