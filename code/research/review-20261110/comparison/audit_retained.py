"""Read-only retained-schedule audit. Run from any relocated archive root."""
import hashlib,json,math
from decimal import Decimal,localcontext
from fractions import Fraction as F
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def historical_path(path):
    return ROOT/path.replace('\\','/').split('/PostDocPaper2/',1)[1]
manifest=json.loads((BASE/'campaign/manifest.json').read_text(encoding='utf-8'))
for path, expected in manifest['hashes'].items():
    assert digest(historical_path(path))==expected, f'source hash mismatch: {path}'
records=list((BASE/'campaign').glob('*-DP-*.json'))
assert len(records)==72
max_matrix=max_decimal=0.
identities=set()
for path in records:
    result=json.loads(path.read_text())
    identities.add((result['case'],result['arm']))
    case_path=ROOT/'research/phase1-cdl-20261109/cases'/f'{result["case"]}.json'
    assert digest(case_path)==result['case_sha256'], 'input hash mismatch'
    case=json.loads(case_path.read_text())
    k,s,m=case['K'],case['S'],case['M']
    lo,hi,budget=map(F,(case['pmin'],case['pmax'],case['budget']))
    schedule=result['schedule']; assert len(schedule)==s
    powers=[None]*k; by_resource=[None]*s
    for row in schedule:
        u,v=row['users']; resource=row['resource']; p,q=map(F,row['powers'])
        assert 0<=u<v<k and 0<=resource<s and by_resource[resource] is None
        assert powers[u] is None and powers[v] is None and lo<=p<=hi and lo<=q<=hi
        powers[u],powers[v]=p,q;by_resource[resource]=(u,v)
    assert all(p is not None for p in powers) and sum(powers)<=budget
    pairs={(*row['users'],row['resource']):tuple(F(row[x]) for x in ('gain1','gain2','r')) for row in case['pairs']}
    with localcontext() as context:
        context.prec=70
        def dec(frac): return Decimal(frac.numerator)/Decimal(frac.denominator)
        scalar=Decimal(0)
        for resource,(u,v) in enumerate(by_resource):
            g,h,r=pairs[u,v,resource];x,y=g*powers[u],h*powers[v]
            scalar+=2*dec(1+x+y+(1-r)*x*y).ln()-dec(1+x).ln()-dec(1+y).ln()
        decimal_error=float(abs(scalar-Decimal(str(result['rate_nats']))))
    channels=np.asarray(case['channels_re'])+1j*np.asarray(case['channels_im'])
    matrix=0.
    for resource,pair in enumerate(by_resource):
        for user in pair:
            other=pair[1] if pair[0]==user else pair[0]
            channel=channels[user,:,resource]; interference=channels[other,:,resource]
            covariance=np.eye(m,dtype=complex)+float(powers[other])*np.outer(interference,interference.conj())
            sinr=float(powers[user])*float(np.vdot(channel,np.linalg.solve(covariance,channel)).real)
            matrix+=math.log1p(sinr)
    matrix_error=abs(matrix-result['rate_nats'])
    assert decimal_error<1e-10 and matrix_error<1e-8
    assert abs(result['se_bits']-result['rate_nats']/(s*math.log(2)))<1e-12
    assert all(item['seconds']<=result['cap_seconds'] for item in result['history'])
    max_matrix=max(max_matrix,matrix_error);max_decimal=max(max_decimal,decimal_error)
assert len(identities)==72
print(json.dumps(dict(status='PASS',schedules=72,source_hashes='PASS',input_hashes='PASS',
    exact_feasibility='PASS',max_matrix_error_nats=max_matrix,max_decimal_error_nats=max_decimal),indent=2))
