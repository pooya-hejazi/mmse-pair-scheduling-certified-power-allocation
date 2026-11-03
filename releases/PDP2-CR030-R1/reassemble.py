from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
m=json.loads((root/'ARCHIVE_PARTS.json').read_text(encoding='utf-8'))
out=root/m['archive']
sha=lambda b:hashlib.sha256(b).hexdigest()
if out.exists():
 if out.stat().st_size==m['bytes'] and sha(out.read_bytes())==m['sha256']:
  print('Archive already present and verified.');raise SystemExit(0)
 raise SystemExit('Destination exists with different bytes; preserve it and choose a fresh folder.')
data=[]
for p in m['parts']:
 b=(root/p['name']).read_bytes()
 if len(b)!=p['bytes'] or sha(b)!=p['sha256']:raise SystemExit('Invalid part: '+p['name'])
 data.append(b)
b=b''.join(data)
if len(b)!=m['bytes'] or sha(b)!=m['sha256']:raise SystemExit('Combined archive mismatch')
with out.open('xb') as f:f.write(b)
print('Verified '+m['archive']+': '+m['sha256'])
