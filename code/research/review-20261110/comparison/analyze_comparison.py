"""Render and summarize only the new campaign, preserving paired losses and ties."""
import csv, hashlib, json, math, os
from pathlib import Path
import numpy as np
os.environ['MPLCONFIGDIR'] = str(Path(__file__).resolve().parent/'matplotlib-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parent
ARMS = ('DP-SQP', 'DP-Fu-SCA', 'DP-Thu-IDE')
LABELS = ('Current DP + local SQP', 'DP + Fu-SCA adaptation', 'DP + Thu-IDE adaptation')
COLORS = ('#185a9d', '#d55e00', '#009e73')
STYLES = {'DP-SQP':'-', 'DP-Fu-SCA':'--', 'DP-Thu-IDE':':'}
SEPS = (0.5, 2., 6., 12.)
manifest = json.loads((ROOT/'campaign/manifest.json').read_text(encoding='utf-8'))
# Archive layout preserves paths below PostDocPaper2; verify the packaged copies.
def source_path(path):
    normalized = path.replace('\\', '/')
    relative = normalized.split('/PostDocPaper2/', 1)[1]
    return ROOT.parents[2] / relative
assert all(hashlib.sha256(source_path(path).read_bytes()).hexdigest() == digest for path,digest in manifest['hashes'].items()), 'source/protocol changed during campaign'
rows = list(csv.DictReader((ROOT/'campaign/raw.csv').open(encoding='utf-8')))
assert len(rows) == 72 and len({(r['case'],r['arm']) for r in rows}) == 72
for r in rows:
    for key in ('se_bits','aggregate_bits','rate_nats','elapsed_seconds','overrun_seconds','matrix_discrepancy','separation_deg'):
        r[key] = float(r[key])
    assert abs(r['se_bits']-r['rate_nats']/(8*math.log(2))) < 1e-12
    assert r['matrix_discrepancy'] < 1e-6 and r['overrun_seconds'] < .5
paired = {r['case']:{x['arm']:x for x in rows if x['case']==r['case']} for r in rows}
figdir = ROOT/'figures'; figdir.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                     'axes.spines.right':False,'axes.formatter.useoffset':False,'axes.grid':True,'grid.alpha':.22,'pdf.fonttype':42})
def save(fig, name):
    fig.savefig(figdir/f'{name}.pdf', bbox_inches='tight')
    fig.savefig(figdir/f'{name}.png', dpi=220, bbox_inches='tight')
    plt.close(fig)
def select(arm, sep, profile=None):
    return [r for r in rows if r['arm']==arm and r['separation_deg']==sep and (profile is None or r['profile']==profile)]
summary=[]
for arm in ARMS:
    for sep in SEPS:
        rr=select(arm,sep)
        summary.append(dict(arm=arm,separation_deg=sep,n=len(rr),mean_se=np.mean([r['se_bits'] for r in rr]),
                       min_se=min(r['se_bits'] for r in rr),max_se=max(r['se_bits'] for r in rr),
                       mean_runtime=np.mean([r['elapsed_seconds'] for r in rr])))
with (ROOT/'summary.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
fig, ax=plt.subplots(figsize=(6.6,4.1))
for arm,label,color,marker in zip(ARMS,LABELS,COLORS,('o','s','^')):
    ax.plot(SEPS,[np.mean([r['se_bits'] for r in select(arm,s)]) for s in SEPS],
            label=label,color=color,marker=marker,linewidth=1.7,markersize=6,
            linestyle=STYLES[arm],markerfacecolor='none')
ax.set(xlabel='Nominal user-angle separation (degrees)',ylabel='Occupied-band SE (bit/s/Hz)',
       xticks=SEPS,title='Common DP assignment; equal 10 s search budgets')
ax.legend(fontsize=8.5,frameon=False)
fig.text(.5,-.025,'Mean of CDL A/B/C and two fixed seeds (n=6 per point); source power components adapted.',ha='center',fontsize=8)
save(fig,'comparison_se')
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
fig.tight_layout();save(fig,'comparison_by_profile')
fig, axs=plt.subplots(1,2,figsize=(10,3.7))
for arm,label,color,marker in zip(ARMS[1:],LABELS[1:],COLORS[1:],('s','^')):
    delta=[]
    for sep in SEPS:
        cases=[p for p in paired.values() if p['DP-SQP']['separation_deg']==sep]
        delta.append(np.mean([100*(p['DP-SQP']['se_bits']-p[arm]['se_bits'])/p[arm]['se_bits'] for p in cases]))
    axs[0].plot(SEPS,delta,label=label,color=color,marker=marker,linestyle=STYLES[arm],markerfacecolor='none')
axs[0].axhline(0,color='.35',linewidth=.8)
axs[0].set(ylabel='Mean paired relative SE difference (%)',xlabel='Separation (degrees)',xticks=SEPS,title='(Current - adaptation) / adaptation')
axs[0].legend(frameon=False,fontsize=8)
for arm,label,color,marker in zip(ARMS,LABELS,COLORS,('o','s','^')):
    axs[1].plot(SEPS,[np.mean([r['elapsed_seconds'] for r in select(arm,s)]) for s in SEPS],label=label,color=color,marker=marker,linestyle=STYLES[arm],markerfacecolor='none')
axs[1].axhline(10,color='.35',linestyle=':',label='10 s budget')
axs[1].set(ylabel='Search wall time (s)',xlabel='Separation (degrees)',xticks=SEPS,title='Actual runtime, including search checks')
axs[1].legend(frameon=False,fontsize=8)
fig.tight_layout();save(fig,'comparison_difference_runtime')
comparisons={}
for arm in ARMS[1:]:
    diffs=np.array([p['DP-SQP']['se_bits']-p[arm]['se_bits'] for p in paired.values()])
    relative=np.array([100*(p['DP-SQP']['se_bits']-p[arm]['se_bits'])/p[arm]['se_bits'] for p in paired.values()])
    comparisons[arm]=dict(wins=int(sum(diffs>1e-5)),ties=int(sum(abs(diffs)<=1e-5)),losses=int(sum(diffs < -1e-5)),
        mean_absolute_difference=float(np.mean(diffs)),mean_paired_relative_percent=float(np.mean(relative)),
        min_relative_percent=float(min(relative)),max_relative_percent=float(max(relative)))
armstats={}
for arm in ARMS:
    rr=[r for r in rows if r['arm']==arm]
    records=[json.loads((ROOT/'campaign'/f'{r["case"]}-{arm}.json').read_text()) for r in rr]
    ds=[d for record in records for d in record['diagnostics']]
    reasons={}
    for d in ds:
        reason=d.get('stop_reason',d.get('message','unspecified'));reasons[reason]=reasons.get(reason,0)+1
    armstats[arm]=dict(mean_se=float(np.mean([r['se_bits'] for r in rr])),
        mean_seconds=float(np.mean([r['elapsed_seconds'] for r in rr])),
        deadline_cases=sum(r['status']=='deadline' for r in rr),
        total_starts_completed=sum(int(r['starts_completed']) for r in rr),
        total_dp_completed=sum(int(r['dp_completed']) for r in rr),power_stop_reasons=reasons,
        power_errors=sum(d.get('error_count',0) for d in ds),
        ide_complete_generations=sum(d.get('generations',0) for d in ds))
report=dict(cases=24,arms=armstats,comparisons=comparisons,max_matrix_discrepancy=max(r['matrix_discrepancy'] for r in rows),
            max_overrun_seconds=max(r['overrun_seconds'] for r in rows))
(ROOT/'results_summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
lines=['# New common-model comparison results','',
'All 24 predeclared CDL-inspired cases completed, with three arms (72 allocations). These compare local/power-search components under a shared exact fixed-power DP assignment wrapper. They do not reproduce the source papers end to end. The current method is DP + local SQP, not a globally exact continuous optimizer.','',
'Occupied-band SE is R/(8 ln 2); aggregate_bits in raw.csv preserves R/ln 2. A first pilot used aggregate reporting; pilot_normalized repeats the normalized checks. No search parameter was selected from those rankings.','',
'| Arm | Mean SE (bit/s/Hz) | Mean search time (s) | Deadline cases | Completed starts |','|---|---:|---:|---:|---:|']
for arm,s in armstats.items():
    lines.append(f'| {arm} | {s["mean_se"]:.8f} | {s["mean_seconds"]:.3f} | {s["deadline_cases"]}/24 | {s["total_starts_completed"]}/192 |')
lines += ['','Paired outcomes for the current method; ties use absolute SE tolerance 1e-5 bit/s/Hz.','',
'| Comparator | Wins / ties / losses | Mean paired relative difference | Relative range |', '|---|---:|---:|---:|']
for arm,s in comparisons.items():
    lines.append(f'| {arm} | {s["wins"]} / {s["ties"]} / {s["losses"]} | {s["mean_paired_relative_percent"]:+.6f}% | {s["min_relative_percent"]:+.6f}% to {s["max_relative_percent"]:+.6f}% |')
lines += ['', 'Power-block termination diagnostics (feasibility is checked even when the optimizer does not declare success):']
for arm, stats in armstats.items():
    lines.append(f'- {arm}: {stats["power_stop_reasons"]}; complete IDE generations={stats["ide_complete_generations"]}; caught adapter exceptions/validation failures={stats["power_errors"]}.')
lines += ['', 'Fu subproblem diagnostics: 267 success statuses and 170 status-8 line-search terminations; stationarity residuals 5.63e-5 to 3.12e-4 exceed the 1e-7 threshold. The DP searches the assignment family exhaustively using floating-point weights; it does not certify an outward-rounded fixed-power optimum.', '',f'All final exact-rational schedules passed user-incidence, resource, box and budget checks. Maximum matrix/scalar discrepancy: {report["max_matrix_discrepancy"]:.3g} nats; maximum observed deadline overrun: {report["max_overrun_seconds"]:.6f} s. Retained search improvements were checked to precede the global deadline.',
'', 'Interpretation limits: two fixed seeds per profile, four separations, M=2 and K=16 only. Means are descriptive; there is no confidence or full-population superiority claim. A 2 s local block can truncate IDE initialization/generations, and the 10 s result is not a converged-algorithm comparison. Fu and Thu retain their documented component modifications; original satellite/cell-free/energy-efficiency objectives are not transferred. No upper-bound gap or global exactness is inferred.',
'', 'Figures: comparison_se.pdf/png (mean over six paired cases per separation); comparison_by_profile.pdf/png (two seeds per profile); comparison_difference_runtime.pdf/png (signed paired differences and actual times). Raw allocations and per-power-call status diagnostics are in campaign/*.json; every aggregate can be reconstructed from campaign/raw.csv and summary.csv.',
'', 'Wrapper repairs: box/budget-feasible random starts; guarded DP deadlines; reject K>20 before exponential allocation; retain only pre-deadline improvements; count completed rather than offered starts. The 2 s block cap is shared by all arms and differs from the historical 5 s proposed cap. Original source modules and frozen historical data were not edited.',
'', 'Not checked: source-paper full-system reproduction, convergence at larger time budgets, additional seeds, K32, M>2, and physical calibration/standards conformance of the archived CDL-inspired generator.']
(ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))







