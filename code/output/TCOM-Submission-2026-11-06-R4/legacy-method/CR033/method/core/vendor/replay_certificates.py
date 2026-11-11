"""Reconstruct every timely accepted bound independently; never call producer."""
from pathlib import Path
from fractions import Fraction as F
import json,argparse,time,hashlib
import verify_upper
from persistence import digest,read_receipt
from controller import universal

def replay(root,seconds=120):
    root=Path(root);began=time.perf_counter();deadline=began+seconds;ledger=json.loads((root/'campaign-ledger.json').read_text());checks=[];errors=[];verified_inputs={};cache_hits=0;last_case=None
    for row in ledger['rows']:
        name=f"{row['case']}-{row['method']}"+(f"-repeat{row['index']}" if row['panel']=='reliability' else '');cell=root/'cells'/name
        if not (cell/'attempt.json').exists():continue
        if time.perf_counter()>=deadline:errors.append({'cell':name,'error':'REPLAY_RESOURCE_LIMIT'});break
        attempt=json.loads((cell/'attempt.json').read_text())
        if attempt['case_sha256']!=last_case:
            verify_upper.clear_caches();verified_inputs.clear();last_case=attempt['case_sha256']
        # Always resolve within this supplied artifact, never silently use the live original.
        casepath=root/'inputs'/('reliability' if row['panel']=='reliability' else row['scene'])/(row['case']+'.json')
        try:
            assert digest(casepath)==attempt['case_sha256'];case=json.loads(casepath.read_text());low=high=None;n=0
            for r in row.get('receipts',[]):
                if not r['timely']:continue
                assert digest(cell/r['file'])==r['sha256'] and r['completed_at']<=attempt['deadline']
                cand,receipt=read_receipt(cell,r['file'],attempt)
                inp={'schedule':cand['schedule'],'proof':cand.get('proof') or universal(case)}
                key=(attempt['case_sha256'],hashlib.sha256(json.dumps(inp,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest())
                if key in verified_inputs:v=verified_inputs[key];cache_hits+=1
                else:
                    v=verify_upper.verify(case,inp,seconds=max(0,deadline-time.perf_counter()));verified_inputs[key]=v
                assert v['lower_nats']==receipt['verification']['lower_nats'] and v['upper_nats']==receipt['verification']['upper_nats']
                lo,hi=F(v['lower_nats']),F(v['upper_nats']);low=lo if low is None else max(low,lo);high=hi if high is None else min(high,hi);n+=1
            assert (str(low) if low is not None else None)==row.get('lower_nats')
            assert (str(high) if high is not None else None)==row.get('upper_nats')
            assert bool(low is not None and high-low<=F(1,100))==row['mathematical_success']
            checks.append({'cell':name,'timely_receipts':n,'valid':True})
        except Exception as e:errors.append({'cell':name,'error':repr(e)})
    report={'valid':not errors,'cells_checked':len(checks),'receipts_checked':sum(x['timely_receipts'] for x in checks),'identical_verified_input_cache_hits':cache_hits,'checks':checks,'errors':errors,'seconds':time.perf_counter()-began,'scope':'All receipt/candidate/attempt/time hashes checked before reuse; each distinct case+schedule+proof independently reconstructed. Offline reuse only, charged controller still clears caches each cell; no optimization rerun'}
    (root/'CERTIFICATE_REPLAY.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['checks']}))
    if errors:raise RuntimeError('Independent replay has unresolved errors')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--seconds',type=float,default=120);a=p.parse_args();replay(a.root,a.seconds)
