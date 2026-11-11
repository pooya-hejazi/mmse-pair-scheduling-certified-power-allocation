"""Deterministic adapter correctness fixtures, never campaign inputs."""
import json
import math
import sys
import time
from fractions import Fraction as F
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'core'))
from problem import Problem
import matching_baseline as mw
import fu_sca as fu
import thu_ide as thu
from common import project, improves, DeadlineReached


def make_problem(vectors):
    h = np.asarray(vectors, complex)[:, :, None]
    g = [sum(F(float(z.real))**2+F(float(z.imag))**2 for z in row) for row in h[:, :, 0]]
    cross = sum(complex(x).conjugate()*complex(y) for x, y in zip(h[0, :, 0], h[1, :, 0]))
    # Fixtures have dyadic real/imag parts; compute exact inner product directly.
    re = sum(F(float(x.real))*F(float(y.real))+F(float(x.imag))*F(float(y.imag)) for x,y in zip(h[0,:,0],h[1,:,0]))
    im = sum(F(float(x.real))*F(float(y.imag))-F(float(x.imag))*F(float(y.real)) for x,y in zip(h[0,:,0],h[1,:,0]))
    r = (re*re+im*im)/(g[0]*g[1]) if g[0]*g[1] else F(0)
    case = dict(name='modern_deterministic_fixture', K=2, M=h.shape[1], S=1,
                pmin='1/20', pmax='1/5', budget='1/5', channels_re=h.real.tolist(),
                channels_im=h.imag.tolist(), pairs=[dict(users=[0,1], resource=0,
                gain1=str(g[0]), gain2=str(g[1]), r=str(r))])
    return Problem(case)


def fixture_matrix_scalar():
    for vectors in ([[1,0],[0,2]], [[1,0],[2,0]], [[1,0],[2,1/1024]],
                    [[1,1j],[.5,2j]], [[0,0],[0,2]]):
        p = make_problem(vectors)
        for powers in ([.05,.15], [.1,.1], [.15,.05]):
            cand = p.checked_candidate(((0,1),), powers)
            p.matrix_scalar_check(cand)


def fixture_fu_math():
    b, c, n = np.array([1.3,.9]), np.array([[0,.6],[.4,0]]), np.ones(2)
    vb = np.sqrt([.1,.1])
    a = fu.tangent_coefficients(b,c,n,vb)
    _, grad, t, _ = fu.surrogate(vb,b,c,n,a)
    gamma = (b*vb)**2/(n+c@(vb*vb))
    np.testing.assert_allclose(t,gamma,atol=2e-15)
    for v in (np.sqrt([.05,.15]), np.sqrt([.12,.08]), np.sqrt([.15,.05])):
        N = n+c@(v*v)
        tv = fu.surrogate(v,b,c,n,a)[2]
        gap = (b*v)**2/N-tv
        np.testing.assert_allclose(gap,(b*v-a*N)**2/N,atol=2e-15)
        assert min(gap) >= -1e-15
        epsilon = 1e-6
        fd = np.array([(fu.surrogate(v+epsilon*np.eye(2)[j],b,c,n,a)[0]-
                        fu.surrogate(v-epsilon*np.eye(2)[j],b,c,n,a)[0])/(2*epsilon) for j in range(2)])
        np.testing.assert_allclose(fd,fu.surrogate(v,b,c,n,a)[1],rtol=1e-7,atol=1e-8)
    v1,v2=np.sqrt([.05,.15]),np.sqrt([.15,.05])
    assert fu.surrogate((v1+v2)/2,b,c,n,a)[0] >= (fu.surrogate(v1,b,c,n,a)[0]+fu.surrogate(v2,b,c,n,a)[0])/2-1e-14
    # Literal printed extra old denominator destroys equality at expansion point.
    bad = t-a*a*(n+c@(vb*vb))
    assert np.max(gamma-bad)>1e-4


def fixture_fu_independent_subproblem():
    b,c,n=np.array([2.,1.]),np.zeros((2,2)),np.ones(2)
    vbar=np.sqrt([.1,.1]);a=fu.tangent_coefficients(b,c,n,vbar)
    result,_=fu.solve_surrogate(vbar,b,c,n,a,.05,.2,.2,time.monotonic()+5)
    assert result.success, str(result)
    # Independent scalar golden-section maximization on the active budget.
    def objective(p):
        return math.log1p(2*a[0]*b[0]*math.sqrt(p)-a[0]**2)+math.log1p(2*a[1]*b[1]*math.sqrt(.2-p)-a[1]**2)
    left,right=.05,.15
    ratio=(math.sqrt(5)-1)/2
    for _ in range(100):
        x=right-ratio*(right-left);y=left+ratio*(right-left)
        if objective(x)<objective(y):left=x
        else:right=y
    opt=objective((left+right)/2)
    actual=fu.surrogate(result.x,b,c,n,a)[0]
    assert abs(actual-opt)<2e-8,(actual,opt)


def fixture_fu_ascent_callback():
    prob=make_problem([[2,0],[0,1]])
    assignment=((0,1),);p0=np.array([.08,.12]);seen=[]
    def publish(a,p,d):
        seen.append(prob.checked_candidate(a,p));return False
    out,diag=fu.refine_power(prob,assignment,p0,time.monotonic()+2,None,publish)
    initial=prob.checked_candidate(assignment,p0)
    assert seen and improves(seen[-1],initial),diag
    assert prob.checked_candidate(assignment,out)['lo']>=seen[-1]['lo']
    for old,new in zip([initial]+seen[:-1],seen):assert improves(new,old)
    prob.matrix_scalar_check(prob.checked_candidate(assignment,out))
    # Callback errors propagate, preserving the core wrapper's global fallback.
    def throwing(*args):raise RuntimeError('callback fixture')
    try:fu.refine_power(prob,assignment,p0,time.monotonic()+2,None,throwing)
    except RuntimeError as exc:assert str(exc)=='callback fixture'
    else:raise AssertionError('callback exception swallowed')


def fixture_ou_wmmse():
    prob=make_problem([[2,0],[1,1]])
    assignment=((0,1),);p=np.array([.08,.12]);v=np.sqrt(p)
    b,c,n=fu.frozen_coefficients(prob,assignment,p)
    M=b*b*p;N=n+c@p;lam=M/N;z=np.sqrt((1+lam)*M)/(M+N)
    all_c=c+np.diag(b*b)
    Aq=(z*z)@all_c;Bq=z*np.sqrt(1+lam)*b
    u,weights=mw._mmse(prob.h,np.array([0,1]),p)
    Aw,Bw=mw._power_coefficients(prob.h,np.array([0,1]),u,weights)
    np.testing.assert_allclose(Aq,Aw,rtol=1e-13,atol=1e-13)
    np.testing.assert_allclose(Bq,Bw,rtol=1e-13,atol=1e-13)
    pq,_=mw._amplitude_update(Aq,Bq,prob.low,prob.high,prob.budget)
    pw,_=mw._amplitude_update(Aw,Bw,prob.low,prob.high,prob.budget)
    np.testing.assert_allclose(pq,pw,atol=1e-14)


class ScriptedRNG:
    def random(self,size=None):return .1 if size is None else np.full(size,.1)
    def integers(self,high):return 0
    def standard_cauchy(self):return 0.
    def normal(self,mean,scale):return mean


def record(z):
    val=float(sum(z));f=F(val)
    return dict(value=val,lo=f,hi=f,numeric=np.array(z),powers=tuple(map(F,z)))


def fixture_ide_mechanics():
    parent=np.array([.2,.4]);best=np.array([.6,.7]);r1=np.array([.9,.8]);r2=np.array([.1,.2])
    np.testing.assert_allclose(thu.mutation(parent,best,r1,r2,.5,0),[1.,1.])
    np.testing.assert_allclose(thu.mutation(parent,best,r1,r2,.5,1),[.8,.85])
    np.testing.assert_array_equal(thu.crossover(parent,best,0.,ScriptedRNG()),[.6,.4])
    assert abs(thu.lehmer([.2,.8],[1,3],.5)-(.25*.04+.75*.64)/(.25*.2+.75*.8))<1e-15
    assert thu.lehmer([],[],.3)==.3 and thu.lehmer([0],[1],.3)==.3
    assert thu.operator_probability([2,1],[2,4],.2)==.8
    assert thu.operator_probability([0,0],[1,1],.8)==.2
    assert thu.operator_probability([0,1],[0,1],.2)==.2
    pop=np.array([[0.,.1],[.2,.3],[.4,.5],[.6,.7]])
    original=pop.copy();archive=[np.array([.1,.1])];original_archive=archive[0].copy()
    records=list(map(record,pop));mf=np.array([.2,.2]);mc=np.ones(2);gains=np.zeros(2);counts=np.zeros(2,int)
    calls=[]
    def evaluate(z):calls.append(z.copy());return record(z),z.copy()
    nxt,recs,arc=thu.generation(pop,records,archive,mf,mc,.2,gains,counts,evaluate,ScriptedRNG(),time.monotonic()+2)
    np.testing.assert_array_equal(pop,original)
    np.testing.assert_array_equal(archive[0],original_archive)
    assert counts.tolist()==[4,0] and len(calls)==4
    assert sum(improves(new,old) for old,new in zip(records,recs))<4
    assert len(arc)<=len(pop)
    assert all(new['value']>=old['value'] for old,new in zip(records,recs))
    # First trial uses original top parent and distinct original donors.
    np.testing.assert_allclose(calls[0],pop[3]+.2*(pop[1]-pop[2]))
    trimmed=thu.trim_archive([np.array([i]) for i in range(6)],4,ScriptedRNG())
    assert [int(x[0]) for x in trimmed]==[2,3,4,5]


def fixture_projection_failure():
    raw=np.array([.19,.15,.12,.08]);y=project(raw,.05,.2,.4)
    assert sum(y)<=.4+1e-15 and min(y)>=.05 and max(y)<=.2
    free=(y>.05+1e-12)&(y<.2-1e-12)
    np.testing.assert_allclose((raw-y)[free],np.full(sum(free),(raw-y)[free][0]),atol=1e-14)
    for bad in ([np.nan,.1],[np.inf,.1]):
        try:project(bad,.05,.2,.2)
        except ValueError:pass
        else:raise AssertionError('nonfinite accepted')
    prob=make_problem([[1,0],[0,1]])
    exact=prob.repair(project([1.,1.],prob.low,prob.high,prob.budget))
    assert sum(exact)<=prob.budget and all(prob.low<=x<=prob.high for x in exact)
    old=record([.2,.3]);same=record([.2,.3]);assert not improves(same,old)
    overlap=dict(old);overlap.update(value=old['value']+.1,lo=old['lo'],hi=old['hi']+1)
    assert not improves(overlap,old)


def fixture_timeout_ide():
    prob=make_problem([[2,0],[0,1]]);assignment=((0,1),);p0=np.array([.08,.12])
    for fn in (fu.refine_power,thu.refine_power):
        out,d=fn(prob,assignment,p0,time.monotonic()-1,np.random.default_rng(77),lambda *args:False)
        np.testing.assert_array_equal(out,p0);assert d['stop_reason']=='deadline'
    seen=[]
    def pub(a,p,d):seen.append(prob.checked_candidate(a,p));return False
    out,d=thu.refine_power(prob,assignment,p0,time.monotonic()+.25,np.random.default_rng(77),pub)
    result=prob.checked_candidate(assignment,out);initial=prob.checked_candidate(assignment,p0)
    assert result['value']>=initial['value'] and d['stop_reason']=='deadline'
    assert d['evaluations']>0
    for old,new in zip([initial]+seen[:-1],seen):assert improves(new,old)
    prob.matrix_scalar_check(result)


def fixture_numerical_fallback_and_cap():
    from types import SimpleNamespace
    prob=make_problem([[2,0],[0,1]]);assignment=((0,1),);p0=np.array([.08,.12])
    original=fu.solve_surrogate
    def nonfinite(*args,**kwargs):return SimpleNamespace(x=np.array([np.nan,np.nan]),status=0),1
    try:
        fu.solve_surrogate=nonfinite
        out,d=fu.refine_power(prob,assignment,p0,time.monotonic()+1,None,lambda *args:False)
        np.testing.assert_array_equal(out,p0)
        assert d['stop_reason']=='subproblem_numerical_failure' and d['error_count']==1
    finally:fu.solve_surrogate=original
    calls=[0]
    def capped(*args,**kwargs):
        calls[0]+=1
        if calls[0]==1:return SimpleNamespace(x=np.array(args[0]),status=9),1
        return original(*args,**kwargs)
    try:
        fu.solve_surrogate=capped
        out,d=fu.refine_power(prob,assignment,p0,time.monotonic()+1,None,lambda *args:False)
        assert d['cap_count']==1 and calls[0]>=2
        assert prob.value_gradient(assignment,out)[0]>=prob.value_gradient(assignment,p0)[0]
    finally:fu.solve_surrogate=original
    pop=np.array([[0.,.1],[.2,.3],[.4,.5],[.6,.7]])
    records=list(map(record,pop));counts=np.zeros(2,int)
    nxt,recs,archive=thu.generation(pop,records,[],np.array([.2,.2]),np.ones(2),.2,
            np.zeros(2),counts,lambda z:(None,None),ScriptedRNG(),time.monotonic()+1)
    np.testing.assert_array_equal(nxt,pop)
    assert counts.tolist()==[4,0] and not archive


def fixture_singleton():
    prob=make_problem([[2,0],[0,1]])
    case=dict(prob.case);case.update(pmin='1/10',pmax='1/10')
    fixed=Problem(case)
    for fn in (fu.refine_power,thu.refine_power):
        out,d=fn(fixed,((0,1),),np.array([.1,.1]),time.monotonic()+1,np.random.default_rng(7),lambda *args:False)
        np.testing.assert_array_equal(out,[.1,.1])
        assert d['stop_reason']=='singleton_feasible_set'


def main():
    results=[]
    for name,fn in sorted(globals().copy().items()):
        if name.startswith('fixture_'):
            began=time.monotonic()
            try:fn();results.append(dict(name=name,status='PASS',seconds=time.monotonic()-began))
            except Exception as exc:
                import traceback
                results.append(dict(name=name,status='FAIL',seconds=time.monotonic()-began,error=repr(exc),traceback=traceback.format_exc()))
    print(json.dumps(dict(kind='deterministic_correctness_only',results=results,passed=all(x['status']=='PASS' for x in results)),indent=2))
    return 0 if all(x['status']=='PASS' for x in results) else 1

if __name__=='__main__':sys.exit(main())
