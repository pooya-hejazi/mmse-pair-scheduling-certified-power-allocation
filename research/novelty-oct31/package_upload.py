"""Verify retained evidence and prepare an explicit own-work upload allowlist."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
R=Path(__file__).resolve().parents[2]; D=Path(__file__).resolve().parent
counts={}
for name,entries in [('original',json.loads((R/'research/code-review/new-source-manifest.json').read_text())),('S02',json.loads((R/'research/reproduction/run-manifest.json').read_text())['files'])]:
 for e in entries:
  assert hashlib.sha256((R/e['path']).read_bytes()).hexdigest()==e['sha256'],e['path']
 counts[name]=len(entries)
F=R/'audit/frozen/THEORY-CR011-A01'
for e in json.loads((F/'manifest.json').read_text())['entries']:
 for base in [F,R]:
  assert hashlib.sha256((base/e['path']).read_bytes()).hexdigest()==e['sha256']
for p,h in json.loads((D/'bound-manifest.json').read_text())['files'].items():
 assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h,p
sys.path.insert(0,str(R/'research/tools'))
from bundle_tools import validate
record={'status':'PASS','utc':datetime.now(timezone.utc).isoformat(),'unchanged_file_counts':counts,'frozen_and_live_proof_hashes_match':True,'bound_manifest_unchanged':True,'planning_structure':validate(R),'scope':'manifest-listed files only; not scientific acceptance'}
(D/'preservation.json').write_text(json.dumps(record,indent=2),encoding='utf8')
names=['README.md','ATTRIBUTION_ADDENDUM.md','SOURCE_ACCESS.md','COMPARATOR_SCREEN.md','ASTRA_SCREEN.md','ASTRA_ALTERNATIVE.md','AUTHOR_STYLE.md','PROTOCOL.md','BOUND_PROTOCOL.md','GRID_CONTINUOUS_BOUND.md','bound_check.py','run_bound_check.py','bound-checks.json','bound-execution.json','bound-manifest.json','preservation.json','package_upload.py']
paths=[D/n for n in names]+[R/'research/ROADMAP.md',R/'research/theory/README.md']
entries=[];hashes={}
for p in paths:
 b=p.read_bytes();rel=p.relative_to(R).as_posix()
 entries.append({'path':rel,'mode':'100644','type':'blob','content':b.decode('utf8')})
 hashes[rel]=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
payload={'repository_full_name':'pooya-hejazi/6g-project','base_tree_sha':'a3cdaa4d8b8231ca5b877401893079e400f5c093','tree_elements':entries}
(D/'upload-payload.local.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf8')
(D/'upload-hashes.local.json').write_text(json.dumps(hashes,indent=2),encoding='utf8')
print(json.dumps({'files':len(entries),'bytes':sum(len(e['content'].encode('utf8')) for e in entries),'preservation':record},indent=2))
