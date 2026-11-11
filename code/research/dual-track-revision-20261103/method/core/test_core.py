"""Deterministic correctness fixtures only; no registered/performance seeds."""
import json,time,itertools,math
from pathlib import Path
from fractions import Fraction as F
import numpy as np
from problem import Problem,certificates,Deadline
import transfer,reference_line,reference_orthogonal,search,wmmse
import verify_upper

ROOT=Path(__file__).resolve().parent

def physical_case(h,low='1/20',high='1/5',budget='2/5'):
    h=np.asarray(h,complex);k,m,s=h.shape;vectors={};gains={};rows=[]
    for i in range(k):
        for t in range(s):
            v=[(F(float(z.real)),F(float(z.imag))) for z in h[i,:,t]];vectors[i,t]=v;gains[i,t]=sum(a*a+b*b for a,b in v)
    for i,j in itertools.combinations(range(k),2):
        for t in range(s):
            re=sum(a*c+b*d for (a,b),(c,d) in zip(vectors[i,t],vectors[j,t]));im=sum(a*d-b*c for (a,b),(c,d) in zip(vectors[i,t],vectors[j,t]));g,q=gains[i,t],gains[j,t]
            r=(re*re+im*im)/(g*q) if g*q else F(0)
            rows.append(dict(users=[i,j],resource=t,gain1=str(g),gain2=str(q),r=str(r)))
    return dict(K=k,S=s,M=m,pmin=low,pmax=high,budget=budget,pairs=rows,channels_re=h.real.tolist(),channels_im=h.imag.tolist())

def scalar_problem(g1,g2,r,low='1/20',high='1/5',budget='2/5'):
    gains=[F(g1),F(g2),F(g1),F(g2)];case=dict(K=4,S=2,pmin=low,pmax=high,budget=budget,pairs=[])
    for i,j in itertools.combinations(range(4),2):
        for t in range(2):case['pairs'].append(dict(users=[i,j],resource=t,gain1=str(gains[i]),gain2=str(gains[j]),r=str(F(r) if gains[i]*gains[j] else 0)))
    p=Problem.__new__(Problem);p.case=case;p.model=certificates.Model(case);p.k=4;p.s=2;p.low=p.model.low;p.high=p.model.high;p.budget=p.model.budget;p.pmin=p.low;p.pmax=p.high;p.lookup={key:tuple(map(float,v)) for key,v in p.model.data.items()};return p

def main():
    results=[];assignment=((0,1),(2,3));rng=np.random.default_rng(991)
    for r in ['0','1/2','1']:
        for gains in [('1','1'),('1','10')]:
            problem=scalar_problem(*gains,r);p=[F(1,10)]*4
            for pair in [(0,1),(0,3)]:
                direction=[0]*4;direction[pair[0]]=1;direction[pair[1]]=-1
                stats=transfer.new_stats();out=transfer.line_best(problem,assignment,list(map(float,p)),direction,-.05,.05,time.monotonic()+5,stats)
                ref=reference_line.solve(problem,assignment,p,direction,F(-1,20),F(1,20))
                actual=problem.checked_candidate(assignment,out)
                deficit=float(ref['upper']-actual['lo']);assert deficit<=1e-6,(r,gains,pair,deficit)
                assert stats['max_degree']<=3
                results.append(dict(kind='line',r=r,gains=gains,pair=pair,deficit=deficit,degree=stats['max_degree']))
    # Direct branch fixtures are mathematical kernel tests, not network instances.
    st=transfer.new_stats();assert transfer.stationary_candidates([0,0],st)==[] and st['constant_lines']==1
    st=transfer.new_stats();assert transfer.stationary_candidates([1,0,1e-16],st)==[] and st['degree_reductions']>=1
    st=transfer.new_stats();assert any(abs(z)<1e-12 for z in transfer.stationary_candidates([0,0,1],st))
    st=transfer.new_stats();assert transfer.stationary_candidates([1,1],st,lambda c:[complex(.2,1e-10)])==[.2]
    def bad(c):raise ArithmeticError('injected root failure')
    st=transfer.new_stats();assert transfer.stationary_candidates([1,1],st,bad)==[] and st['root_failures']==1
    problem=scalar_problem('0','1','0');out,st=transfer.refine_power(problem,assignment,[.1]*4,time.monotonic()+.2,rng,None);assert all(math.isfinite(v) for v in out)
    problem=scalar_problem('1','10','1',low='1/10',high='1/10');out,st=transfer.refine_power(problem,assignment,[.1]*4,time.monotonic()+.2,rng,None);assert max(out)-min(out)==0
    problem=scalar_problem('1','10','1');p=[.05,.2,.05,.1];before=problem.checked_candidate(assignment,p)
    out,st=transfer.refine_power(problem,assignment,p,time.monotonic()+.4,rng,None);after=problem.checked_candidate(assignment,out);assert after['lo']>=before['lo']
    problem=scalar_problem('1','10','0');p=[.05]*4;before=problem.checked_candidate(assignment,p)
    out,st=transfer.refine_power(problem,assignment,p,time.monotonic()+.4,rng,None);after=problem.checked_candidate(assignment,out);assert after['lo']>before['hi'];assert sum(after['powers'])<=problem.budget
    results.append(dict(kind='kernel_edges',covered=['zero gains','equal bounds','active bounds','constant polynomial','degree trimming','repeated roots','near-real roots','forced root exception','budget slack']))
    for mode in ['orthogonal','collinear','unequal','near_collinear']:
        h=np.zeros((4,4,2),complex)
        for i in range(4):
            for s in range(2):
                if mode=='orthogonal':h[i,i,s]=(16+2*i+s)/16
                elif mode=='collinear':h[i,0,s]=1+i/4
                elif mode=='unequal':h[i,i,s]=[.25,1,2,8][i]*(1+s/4)
                else:h[i,0,s]=1+i/4;h[i,1,s]=(i+1)*2**-18;h[i,2,s]=s*2**-20
        case=physical_case(h);problem=Problem(case);candidate=problem.checked_candidate(assignment,[.1]*4)
        check=problem.matrix_scalar_check(candidate);value,grad=problem.value_gradient(assignment,candidate['numeric'])
        for i in range(4):
            delta=np.zeros(4);delta[i]=1e-6
            numeric=(problem.value_gradient(assignment,candidate['numeric']+delta)[0]-problem.value_gradient(assignment,candidate['numeric']-delta)[0])/2e-6
            assert abs(numeric-grad[i])<1e-6*max(1,abs(grad[i])),(mode,i,numeric,grad[i])
        verified=verify_upper.verify(case,dict(schedule=candidate['schedule'],proof=certificates.universal_proof(case)),seconds=3)
        assert verified['valid']
        results.append(dict(kind='matrix_gradient',mode=mode,**check))
        if mode=='orthogonal':
            ref=reference_orthogonal.solve(case,time.monotonic()+5);assert ref['status']=='certified' and ref['assignments_completed']==6 and F(ref['gap_nats'])<=F(1,10**6)
            verify_upper.verify(case,dict(schedule=ref['schedule'],proof=certificates.universal_proof(case)),seconds=3)
            results.append(dict(kind='independent_orthogonal_reference',gap=float(F(ref['gap_nats'])),assignments=6,registered_seed_used=False))
            anchor=candidate['schedule']
            for method in ['T','S','W']:
                result=search.run(method,problem,anchor,time.monotonic()+.3,991)
                assert result['status']=='deadline',(method,result['diagnostics']['errors'])
                assert result['candidate']['lo']>=candidate['lo']
                problem.matrix_scalar_check(result['candidate'])
                results.append(dict(kind='short_correctness_run',method=method,status=result['status'],starts=result['diagnostics']['starts_started']))
            # Already-expired deadline returns exact same anchor without publication.
            calls=[];result=search.run('T',problem,anchor,time.monotonic()-1,991,lambda *args:calls.append(args))
            assert result['candidate']['schedule']==anchor and not calls
            results.append(dict(kind='timeout_before_publication',passed=True))
    (ROOT/'CORE_TEST_RESULTS.json').write_text(json.dumps(dict(status='PASS',fixtures=results,performance_inputs_generated=False),indent=2),encoding='utf-8')
    print(json.dumps(dict(status='PASS',fixture_records=len(results))))
if __name__=='__main__':main()
