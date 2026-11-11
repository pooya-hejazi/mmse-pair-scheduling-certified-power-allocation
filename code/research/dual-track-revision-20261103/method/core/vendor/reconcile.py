"""Read-only-to-trials interrupted-controller accounting; never rerun a cell."""
from pathlib import Path
import argparse,json
from persistence import publish

def reconcile(root):
    root=Path(root);target=root/'campaign-ledger.json'
    if target.exists():return json.loads(target.read_text())
    plan=json.loads((root/'dispatch-plan.json').read_text());rows=[]
    for block in plan:
        for row in block:
            name=f"{row['case']}-{row['method']}"+(f"-repeat{row['index']}" if row['panel']=='reliability' else '')
            cell=root/'cells'/name
            if (cell/'result.json').exists():result=json.loads((cell/'result.json').read_text())
            elif (cell/'outer-error.json').exists():result=json.loads((cell/'outer-error.json').read_text())
            else:
                attempted=(cell/'attempt.json').exists()
                result=dict(row,status='INTERRUPTED_DISPATCHED' if attempted else 'NOT_RUN_UNDISPATCHED',operational_success=False if attempted else None,
                            mathematical_success=False if attempted else None,normal=False,timely_availability_unknown=attempted,
                            note='Without final parent receipt-completion records, no timely certificate is reconstructed from worker timestamps.',raw_receipts=[p.name for p in cell.glob('receipt-*.json')] if cell.exists() else [])
            rows.append(result)
    assert len(rows)==128
    report={'rows':rows,'planned_cells':128,'status':'INTERRUPTED_ACCOUNTING_ONLY','diagnostics':{'status':'INSPECT_RAW_FILES'},'elapsed_seconds':None}
    publish(target,report);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');a=p.parse_args();r=reconcile(a.root);print(json.dumps({'rows':len(r['rows']),'status':r['status']}))
