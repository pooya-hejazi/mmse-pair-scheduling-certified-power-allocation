from pathlib import Path
from unittest.mock import patch
import json
from supervisor import atomic
R=Path(__file__).resolve().parent
original=Path.replace;count=[0]
def transient(self,target):
 count[0]+=1
 if count[0]<=2:raise PermissionError('injected sharing conflict')
 return original(self,target)
with patch.object(Path,'replace',transient):atomic(R/'storage-check-output.json',{'intact':True})
assert count[0]==3 and json.loads((R/'storage-check-output.json').read_text())['intact']
def permanent(self,target):raise PermissionError('injected persistent conflict')
failed=False
try:
 with patch.object(Path,'replace',permanent):atomic(R/'storage-permanent.json',{'checkpoint':1})
except PermissionError:failed=True
assert failed and (R/'storage-permanent.tmp').exists() and not (R/'storage-permanent.json').exists()
print('PASS: bounded transient retry, explicit permanent failure and intact temp checkpoint')
