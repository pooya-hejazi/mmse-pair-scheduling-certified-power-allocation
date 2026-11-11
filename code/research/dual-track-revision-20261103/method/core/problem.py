"""Common exact feasible model; producer checks are not independent receipts."""
import os
for _key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[_key]='1'
import sys,json,math,time
from pathlib import Path
from fractions import Fraction as F
import numpy as np
VENDOR=Path(__file__).resolve().parent/'vendor'
if str(VENDOR) not in sys.path: sys.path.insert(0,str(VENDOR))
import certificates
import matching_baseline as mw

class Deadline(Exception): pass

def alive(deadline):
    if time.monotonic()>=deadline: raise Deadline()

def assignment_of(schedule):
    return tuple(tuple(sorted(row['users'])) for row in sorted(schedule,key=lambda x:x['resource']))

class Problem:
    def __init__(self,case):
        self.case=json.loads(Path(case).read_text(encoding='utf-8')) if isinstance(case,(str,Path)) else case
        self.model=certificates.Model(self.case)
        self.k,self.s=self.model.k,self.model.s
        self.low,self.high,self.budget=self.model.low,self.model.high,self.model.budget
        self.pmin,self.pmax=self.low,self.high
        self.m=int(self.case['M'])
        self.h=np.asarray(self.case['channels_re'],float)+1j*np.asarray(self.case['channels_im'],float)
        self.h.setflags(write=False)
        self.matrix_problem=mw._Problem(self.case)
        self.matrix_problem.validate_channels()
        self.lookup={key:tuple(map(float,val)) for key,val in self.model.data.items()}
        self.common_power_starts=[]

    def repair(self,p):
        if len(p)!=self.k or not all(math.isfinite(float(v)) for v in p): raise ValueError('nonfinite/length powers')
        vals=[max(self.low,min(self.high,v if isinstance(v,F) else F(float(v)))) for v in p]
        excess=max(F(0),sum(vals,F(0))-self.budget)
        for i in sorted(range(self.k),key=lambda j:(-(vals[j]-self.low),j)):
            take=min(excess,vals[i]-self.low);vals[i]-=take;excess-=take
        if excess or sum(vals,F(0))>self.budget: raise ValueError('infeasible rational repair')
        return tuple(vals)

    def value_gradient(self,assignment,p):
        p=np.asarray(p,float);grad=np.zeros(self.k);terms=[]
        for s,(i,j) in enumerate(assignment):
            g,h,r=self.lookup[i,j,s];x,y=g*p[i],h*p[j];a=1-r;d=1+x+y+a*x*y
            terms.extend((math.log1p(x*(a+r/(1+y))),math.log1p(y*(a+r/(1+x)))))
            grad[i]=g*(2*(1+a*y)/d-1/(1+x));grad[j]=h*(2*(1+a*x)/d-1/(1+y))
        return math.fsum(terms),grad

    def checked_candidate(self,assignment,p):
        assignment=tuple(tuple(sorted(map(int,pair))) for pair in assignment)
        exact=self.repair(p)
        schedule=self.model.encode(assignment,exact)
        self.model.decode(schedule)
        lo,hi=self.model.value(assignment,exact)
        numeric=np.array(list(map(float,exact)))
        value,_=self.value_gradient(assignment,numeric)
        if not math.isfinite(value): raise ValueError('nonfinite objective')
        return dict(schedule=schedule,assignment=assignment,powers=exact,numeric=numeric,lo=lo,hi=hi,value=value)

    def matrix_scalar_check(self,candidate):
        a=np.array([i for pair in candidate['assignment'] for i in pair],int)
        scalar=candidate['value'];matrix=mw._matrix_rate(self.h,a,candidate['numeric'])
        if abs(scalar-matrix)>2e-8+2e-8*max(abs(scalar),abs(matrix)): raise ValueError('matrix/scalar mismatch')
        return dict(scalar=scalar,matrix=matrix,discrepancy=abs(scalar-matrix))

    @staticmethod
    def improves(candidate,old):
        return candidate['lo']>old['hi'] and candidate['value']>old['value']+1e-10+1e-9*max(1,abs(old['value']))

    def anchor(self,anchor):
        if isinstance(anchor,dict) and 'schedule' in anchor: anchor=anchor['schedule']
        assignment,p=self.model.decode(anchor)
        return self.checked_candidate(assignment,p)
