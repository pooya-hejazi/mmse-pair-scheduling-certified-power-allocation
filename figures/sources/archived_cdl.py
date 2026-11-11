"""Historical CDL plots from the 10 November checked data and drawing routines."""
import csv
import math
import matplotlib.pyplot as plt
import numpy as np


def review_plots(research, output):
    """Plot M sensitivity and the two archived CDL panels from row-level CSVs."""
    R = research
    O = output
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
    methods=['grid','slsqp','iwmmse','matching','proposed']
    colors=['#777777','#d55e00','#009e73','#cc79a7','#0072b2']
    styles=[':','--','-.','--','-']
    gain=sorted((float(r['proposed_rate'])-max(float(r[m+'_rate']) for m in methods[:-1]))/(8*math.log(2)) for r in rows)
    fig,ax=plt.subplots(figsize=(3.35,2.3))
    ax.plot(range(1,54),gain,'-',color='#0072b2',lw=1.5)
    ax.axhline(.05,color='.4',ls='--',lw=.8,label='0.05 reference')
    ax.set(xlabel='Case rank by recorded gain',ylabel='SE difference (bit/s/Hz)',ylim=(0,.205))
    ax.legend();ax.grid(alpha=.25);save(fig,'cdl_absolute_gain')

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

def comparison_plot(research, output):
    """Plot the fixed-allowance 24-case comparison by channel profile."""
    ROOT = research / "review-20261110/comparison"
    figdir = output
    ARMS = ('DP-SQP', 'DP-Fu-SCA', 'DP-Thu-IDE')
    LABELS = ('Current DP + local SQP', 'DP + Fu-SCA adaptation', 'DP + Thu-IDE adaptation')
    COLORS = ('#185a9d', '#d55e00', '#009e73')
    STYLES = {'DP-SQP':'-', 'DP-Fu-SCA':'--', 'DP-Thu-IDE':':'}
    SEPS = (0.5, 2., 6., 12.)
    rows = list(csv.DictReader((ROOT/'campaign/raw.csv').open(encoding='utf-8')))
    assert len(rows) == 72 and len({(r['case'],r['arm']) for r in rows}) == 72
    for r in rows:
        for key in ('se_bits','aggregate_bits','rate_nats','elapsed_seconds','overrun_seconds','matrix_discrepancy','separation_deg'):
            r[key] = float(r[key])
        assert abs(r['se_bits']-r['rate_nats']/(8*math.log(2))) < 1e-12
        assert r['matrix_discrepancy'] < 1e-6 and r['overrun_seconds'] < .5
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.formatter.useoffset':False,'axes.grid':True,'grid.alpha':.22,'pdf.fonttype':42})
    def save(fig, name):
        fig.savefig(figdir/f'{name}.pdf', bbox_inches='tight')
        fig.savefig(figdir/f'{name}.png', dpi=220, bbox_inches='tight')
        plt.close(fig)
    def select(arm, sep, profile=None):
        return [r for r in rows if r['arm']==arm and r['separation_deg']==sep and (profile is None or r['profile']==profile)]
    fig, axs=plt.subplots(1,3,figsize=(10.5,4.4),sharey=True)
    for ax,profile in zip(axs,'ABC'):
        for arm,label,color,marker in zip(ARMS,LABELS,COLORS,('o','s','^')):
            ax.plot(SEPS,[np.mean([r['se_bits'] for r in select(arm,s,profile)]) for s in SEPS],label=label,color=color,marker=marker,linestyle=STYLES[arm],markerfacecolor='none')
        ax.set(title=f'CDL-{profile}',xlabel='Separation (degrees)',xticks=SEPS)
        ax.tick_params(labelsize=11.5)
        ax.xaxis.label.set_size(12)
        ax.title.set_size(13)
    axs[0].set_ylabel('Occupied-band SE (bit/s/Hz)',fontsize=12)
    handles,labels=axs[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,-.12),ncol=3,fontsize=11.5,frameon=False)
    fig.suptitle('Each point averages two fixed seeds; common DP and 10 s budget',fontsize=12)
    fig.tight_layout();save(fig,'modern_comparison_by_profile')
