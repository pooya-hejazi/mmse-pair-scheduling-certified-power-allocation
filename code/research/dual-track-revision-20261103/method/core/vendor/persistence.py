"""Write-once publication: no reader-visible file is ever replaced."""
from pathlib import Path
import os,json,hashlib,time,uuid

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def publish(path,obj,hook=None):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    payload=(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    tmp=path.parent/(path.name+'.'+uuid.uuid4().hex+'.partial')
    with tmp.open('xb') as f:
        f.write(payload);f.flush();os.fsync(f.fileno())
    if hook:hook('closed',tmp)
    # Hard-link creation is atomic and fails if destination already exists.
    # Both paths share one directory/volume. Readers ignore *.partial.
    os.link(tmp,path)
    if hook:hook('published',path)
    tmp.unlink()
    return {'sha256':hashlib.sha256(payload).hexdigest(),'completed_at':time.perf_counter(),'bytes':len(payload)}

def safe_child(root,name):
    root=Path(root).resolve();p=(root/name).resolve()
    if p.parent!=root:raise ValueError('receipt path escapes cell')
    return p

def read_receipt(root,receipt_name,attempt):
    root=Path(root);rp=safe_child(root,receipt_name);r=json.loads(rp.read_text())
    if r['attempt_sha256']!=digest(root/'attempt.json'):raise ValueError('attempt altered')
    if r['case_sha256']!=attempt['case_sha256']:raise ValueError('wrong case')
    p=safe_child(root,r['candidate_file'])
    if digest(p)!=r['candidate_sha256']:raise ValueError('candidate altered')
    if not attempt['started_at']<=r['validated_at']<=attempt['deadline']:raise ValueError('late proof')
    return json.loads(p.read_text()),r
