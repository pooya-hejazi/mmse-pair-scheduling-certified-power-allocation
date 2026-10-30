"""Bounded power-grid MILP/LP study. GPU PDHG is an experiment, never an ILP solver."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import sys,time,json,itertools,hashlib,ctypes,platform
import numpy as np,scipy
from scipy import sparse
from scipy.optimize import linprog,milp,Bounds,LinearConstraint

R=Path(__file__).resolve().parent
GRID=np.array([.05,.1,.2]); BW=50e6/32; NF=7.; NOISE=10**((-174+NF-30)/10)*BW
FEAS=1e-6; GAP=1e-6; LIMIT_MIP=20.; LIMIT_LP=30.

def gpu_init():
    os.environ['CUPY_CACHE_DIR']=str(R/'cache')
    lib=Path(sys.prefix)/'Library/bin'
    handles=[]
    if os.name=='nt':
        handles.append(os.add_dll_directory(str(lib)))
        os.environ['PATH']=str(lib)+os.pathsep+os.environ['PATH']
        dll=lib/'nvrtc-builtins64_128.dll'
        if dll.exists():handles.append(ctypes.WinDLL(str(dll)))
    import cupy as cp
    cp.get_default_memory_pool().set_limit(size=4*1024**3)
    return cp,handles

def rates(h,edges,xp):
    """Pair linear-MMSE sum SE, all resource/power profiles; no SIC."""
    gram=xp.einsum('ums,vms->uvs',h.conj(),h)
    uv=xp.asarray(edges)
    gu=gram[uv[:,0],uv[:,0]].real
    gv=gram[uv[:,1],uv[:,1]].real
    cr=xp.abs(gram[uv[:,0],uv[:,1]])**2
    rho=xp.clip(cr/xp.maximum(gu*gv,1e-300),0,1)
    powers=xp.asarray(list(itertools.product(GRID,repeat=2)))
    aa=gu[:,:,None]*powers[None,None,:,0]/NOISE
    bb=gv[:,:,None]*powers[None,None,:,1]/NOISE
    su=aa*(1+bb*(1-rho[:,:,None]))/(1+bb)
    sv=bb*(1+aa*(1-rho[:,:,None]))/(1+aa)
    return xp.log1p(su)/xp.log(2.)+xp.log1p(sv)/xp.log(2.)

def matrices(n):
    s=n//2;edges=list(itertools.combinations(range(n),2));m=len(edges)*s*9
    eix=np.repeat(np.arange(len(edges)),s*9);slot=np.tile(np.repeat(np.arange(s),9),len(edges));pidx=np.tile(np.arange(9),len(edges)*s)
    uv=np.asarray(edges)[eix];col=np.arange(m)
    A=sparse.coo_matrix((np.ones(3*m),(np.r_[uv[:,0],uv[:,1],n+slot],np.tile(col,3))),shape=(n+s,m)).tocsr()
    profiles=np.array(list(itertools.product(GRID,repeat=2)))
    power=profiles[pidx].sum(1)
    return edges,A,power,slot,pidx

def feasibility(x,A,power,budget,integer=False,q=None,target=None):
    if x is None:return {'valid':False}
    eq=float(np.max(abs(A@x-1)));box=float(max(0,-x.min(),x.max()-1));pv=float(max(0,power@x-budget))
    rv=float(max(0,target-q@x)) if target is not None else 0.
    ir=float(np.max(abs(x-np.rint(x)))) if integer else None
    valid=eq<=FEAS and box<=FEAS and pv<=FEAS and rv<=FEAS and (not integer or ir<=FEAS)
    return {'valid':bool(valid),'equality':eq,'box':box,'power_W':pv,'rate_Mbps':rv,'integrality':ir}

def cpu_solve(q,A,power,budget,kind,integer,mask=None,target=None):
    before=time.perf_counter();mask=np.arange(len(q)) if mask is None else mask
    aa=A[:,mask];qq=q[mask];ee=power[mask]
    C=sparse.vstack([aa,sparse.csr_matrix(ee[None,:])],format='csc')
    lo=np.r_[np.ones(aa.shape[0]),-np.inf];hi=np.r_[np.ones(aa.shape[0]),budget]
    if target is not None:
        C=sparse.vstack([C,sparse.csr_matrix(qq[None,:])],format='csc');lo=np.r_[lo,target];hi=np.r_[hi,np.inf]
    objective=-qq if kind=='max_rate' else ee
    setup=time.perf_counter()-before;before=time.perf_counter()
    if integer:
        sol=milp(objective,integrality=np.ones(len(qq)),bounds=Bounds(0,1),constraints=LinearConstraint(C,lo,hi),options={'time_limit':LIMIT_MIP,'mip_rel_gap':0})
    else:
        Aub=sparse.csr_matrix(ee[None,:]);bub=np.array([budget])
        if target is not None:Aub=sparse.vstack([Aub,-sparse.csr_matrix(qq[None,:])]);bub=np.r_[bub,-target]
        sol=linprog(objective,A_eq=aa,b_eq=np.ones(aa.shape[0]),A_ub=Aub,b_ub=bub,bounds=(0,1),method='highs',options={'time_limit':LIMIT_LP,'primal_feasibility_tolerance':1e-8,'dual_feasibility_tolerance':1e-8})
    elapsed=time.perf_counter()-before
    x=None
    if sol.x is not None:x=np.zeros(len(q));x[mask]=sol.x
    check=feasibility(x,A,power,budget,integer,q,target)
    out={'status':int(sol.status),'message':str(sol.message),'setup_seconds':setup,'solve_seconds':elapsed,'feasibility':check,'optimal':bool(sol.status==0 and check['valid']),'rate_Mbps':float(q@x) if check['valid'] else None,'power_W':float(power@x) if check['valid'] else None,'selected':np.flatnonzero(x>.5).tolist() if integer and check['valid'] else None}
    if integer:
        dual=getattr(sol,'mip_dual_bound',None)
        out['solver_bound']=float(-dual if kind=='max_rate' else dual) if dual is not None and np.isfinite(dual) else None
        out['solver_relative_gap']=float(sol.mip_gap) if getattr(sol,'mip_gap',None) is not None and np.isfinite(sol.mip_gap) else None
    return out,x

def gpu_lp(q,A,power,budget,cp):
    """PDHG with conservative norm bound; report residuals even on nonconvergence."""
    from cupyx.scipy import sparse as cs
    start=time.perf_counter();K=sparse.vstack([A,sparse.csr_matrix(power[None,:])],format='csr')
    rhs=np.r_[np.ones(A.shape[0]),budget];scale=np.sqrt(np.asarray(K.multiply(K).sum(1)).ravel())
    K=sparse.diags(1/scale)@K;rhs=rhs/scale;qscale=float(q.max());c=q/qscale
    host_setup=time.perf_counter()-start;start=time.perf_counter()
    kd=cs.csr_matrix(K);kt=kd.T.tocsr();b=cp.asarray(rhs);c=cp.asarray(c)
    x=cp.zeros(len(q));xb=x.copy();y=cp.zeros(len(rhs));avg=x.copy()
    cp.cuda.Stream.null.synchronize();transfer=time.perf_counter()-start
    # Each row has unit Euclidean norm: ||K||_2 <= sqrt(number of rows).
    step=.9/np.sqrt(len(rhs));best_upper=float('inf');converged=False
    start=time.perf_counter();checks=0;best_record=None
    for it in range(1,1000001):
        y+=step*(kd@xb-b);y[-1]=cp.maximum(y[-1],0)
        xn=cp.clip(x+step*(c-kt@y),0,1);xb=2*xn-x;x=xn
        avg+=(x-avg)/it
        if it%200==0:
            dual=float((b@y+cp.maximum(0,c-kt@y).sum()).get())*qscale
            best_upper=min(best_upper,dual);checks+=1
            candidates=[]
            for xx,label in [(x,'last'),(avg,'average')]:
                residual=cp.asnumpy((kd@xx-b))*scale
                primal=float((c@xx).get())*qscale
                violation=max(float(np.max(abs(residual[:-1]))),max(0,float(residual[-1])))
                candidates.append({'iterate':label,'violation':violation,'primal_objective_Mbps_not_feasible_bound':primal,'dual_minus_primal_Mbps':best_upper-primal})
            best_record=min(candidates,key=lambda v:v['violation'])
            converged=best_record['violation']<=FEAS and abs(best_record['dual_minus_primal_Mbps'])<=GAP*max(1,abs(best_upper))
            if converged or time.perf_counter()-start>=LIMIT_LP:break
    cp.cuda.Stream.null.synchronize();elapsed=time.perf_counter()-start
    return {'status':'TOLERANCE_MET' if converged else 'TIME_LIMIT_NOT_CONVERGED','iterations':it,'host_setup_seconds':host_setup,'transfer_setup_seconds':transfer,'iteration_and_check_seconds':elapsed,'checks':checks,'dual_upper_Mbps':best_upper,'floating_point_margin_Mbps':1e-8*max(1,abs(best_upper)),**best_record,'pool_bytes':int(cp.get_default_memory_pool().total_bytes()),'scope':'P-T LP only; residual above tolerance invalidates primal feasibility; fractional LP is not an ILP solution'}

def matchings(nodes):
    if not nodes:yield [];return
    for v in nodes[1:]:
        for m in matchings([u for u in nodes[1:] if u!=v]):yield [(nodes[0],v)]+m

def checks(cp):
    rng=np.random.default_rng(126000);h=(rng.normal(size=(4,5,2))+1j*rng.normal(size=(4,5,2)))*np.sqrt(NOISE)
    edges,A,power,slot,pidx=matrices(4);val=rates(h,edges,np)
    for e,(u,v) in enumerate(edges):
        for s in range(2):
            for j,(pu,pv) in enumerate(itertools.product(GRID,repeat=2)):
                hu=h[u,:,s];hv=h[v,:,s];eye=NOISE*np.eye(5)
                su=pu*np.vdot(hu,np.linalg.solve(eye+pv*np.outer(hv,hv.conj()),hu)).real
                sv=pv*np.vdot(hv,np.linalg.solve(eye+pu*np.outer(hu,hu.conj()),hv)).real
                assert np.isclose(val[e,s,j],np.log2(1+su)+np.log2(1+sv),rtol=1e-10,atol=1e-10)
    warm=time.perf_counter();vg=cp.asnumpy(rates(cp.asarray(h),edges,cp));cp.cuda.Stream.null.synchronize();warm=time.perf_counter()-warm
    assert np.allclose(val,vg,rtol=1e-8,atol=1e-8)
    q=val.ravel();fixed=np.flatnonzero(pidx==4)
    fi,xf=cpu_solve(q,A,power,.4,'max_rate',True,mask=fixed);assert fi['optimal'];target=.95*fi['rate_Mbps']
    actions=[]
    for m in matchings(list(range(4))):
        for perm in itertools.permutations(range(2)):
            for profiles in itertools.product(range(9),repeat=2):
                ix=[(edges.index(e)*2+s)*9+p for e,s,p in zip(m,perm,profiles)]
                if power[ix].sum()<=.4+1e-12:actions.append((q[ix].sum(),power[ix].sum()))
    exact_max=max(v for v,p in actions);exact_min=min(p for v,p in actions if v>=target-1e-10)
    for kind,optimum in [('max_rate',exact_max),('min_power',exact_min)]:
        target0=None if kind=='max_rate' else target
        ip,_=cpu_solve(q,A,power,.4,kind,True,target=target0);lp,_=cpu_solve(q,A,power,.4,kind,False,target=target0)
        key='rate_Mbps' if kind=='max_rate' else 'power_W'
        assert ip['optimal'] and lp['optimal'] and abs(ip[key]-optimum)<1e-7
        assert lp[key]>=ip[key]-1e-7 if kind=='max_rate' else lp[key]<=ip[key]+1e-7
    # Actual installed constructor's one-path convention is also tested in check_units.py.
    return {'matrix_vs_closed_form':True,'CPU_GPU_coefficients':True,'full_power_schedule_enumeration':True,'objectives_both_bound_directions':True,'warmup_seconds':warm}

def peak_host_bytes():
    if os.name!='nt':return None
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(s,ctypes.c_size_t) for s in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
    c=Counters();c.cb=ctypes.sizeof(c)
    handle=ctypes.windll.kernel32.GetCurrentProcess;handle.restype=ctypes.c_void_p
    ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(handle()),ctypes.byref(c),c.cb)
    return int(c.PeakWorkingSetSize)

def main():
    start=time.perf_counter();cp,handles=gpu_init();check=checks(cp)
    data=np.load(R/'channels32.npz');loc=data['location'];H=data['H']
    order=np.lexsort((loc[:,0],loc[:,1]));pool=order[int(.55*len(H)):int(.68*len(H))]
    old=np.load(R.parent/'reproduction/split-indices.npz');assert not set(pool)&set(old['test'].ravel())
    props=cp.cuda.runtime.getDeviceProperties(0)
    out={'scope':'one development seed per size; known CSI; no publication or generalization claim','config':{'power_grid_W':GRID.tolist(),'noise_W_per_carrier':NOISE,'NF_dB':NF,'bandwidth_Hz_per_carrier':BW,'coherence_symbols':200,'pilot_symbols':'U (cost assumption only)','FEAS':FEAS,'GAP':GAP,'MILP_time_limit':LIMIT_MIP,'LP_time_limit':LIMIT_LP,'channel_factor':'sqrt(32), per-carrier watts'},'environment':{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'numpy':np.__version__,'scipy':scipy.__version__,'cupy':cp.__version__,'gpu':props['name'].decode() if isinstance(props['name'],bytes) else props['name'],'VRAM_bytes':int(props['totalGlobalMem']),'BLAS_threads':1,'HiGHS_threads':'library default; same for CPU arms'},'checks':check,'rows':[]}
    for n in [8,16,32,64]:
        m=n*(n-1)//2*(n//2)*9
        predicted_gpu=m*160;predicted_host=H.nbytes+m*1400
        if predicted_gpu>=4*1024**3 or predicted_host>=8*1024**3:
            out['rows'].append({'users':n,'status':'SKIPPED_MEMORY_PREDICTION','predicted_GPU_bytes':predicted_gpu,'predicted_host_bytes':predicted_host});break
        rng=np.random.default_rng(125000+n);ids=rng.choice(pool,n,replace=False);s=n//2
        h=(np.sqrt(32)*H[ids]).reshape(n,32,32)[:,:,:s].astype(np.complex128)
        edges,A,power,slot,pidx=matrices(n)
        before=time.perf_counter();v=rates(h,edges,np);cpucoeff=time.perf_counter()-before
        before=time.perf_counter();hg=cp.asarray(h);cp.cuda.Stream.null.synchronize();h2d=time.perf_counter()-before
        before=time.perf_counter();vg=rates(hg,edges,cp);cp.cuda.Stream.null.synchronize();gpucoeff=time.perf_counter()-before
        before=time.perf_counter();vg=cp.asnumpy(vg);d2h=time.perf_counter()-before
        assert np.allclose(v,vg,rtol=1e-8,atol=1e-8)
        q=v.ravel()*BW*(1-n/200)/1e6;budget=.1*n
        row={'users':n,'resources':s,'columns':m,'seed':125000+n,'ids':ids.tolist(),'occupied_BW_MHz':s*BW/1e6,'power_budget_W':budget,'coefficients':{'CPU_seconds':cpucoeff,'GPU_kernel_seconds':gpucoeff,'H2D_seconds':h2d,'D2H_seconds':d2h,'max_abs_error_SE':float(abs(v-vg).max())},'predicted_GPU_bytes':predicted_gpu,'predicted_host_bytes':predicted_host}
        print('START',n,m,flush=True)
        fixed,xf=cpu_solve(q,A,power,budget,'max_rate',True,mask=np.flatnonzero(pidx==4));row['fixed_power_MILP']=fixed
        lp,xlp=cpu_solve(q,A,power,budget,'max_rate',False);row['joint_power_LP']=lp
        ip,xip=cpu_solve(q,A,power,budget,'max_rate',True);row['joint_power_MILP']=ip
        if lp['optimal'] and ip['feasibility']['valid']:assert lp['rate_Mbps']>=ip['rate_Mbps']-FEAS
        glp=gpu_lp(q,A,power,budget,cp);row['GPU_PDHG']=glp
        if lp['optimal']:
            assert glp['dual_upper_Mbps']+glp['floating_point_margin_Mbps']>=lp['rate_Mbps']-FEAS
            row['GPU_upper_excess_vs_CPU_LP_Mbps']=glp['dual_upper_Mbps']-lp['rate_Mbps']
        if fixed['feasibility']['valid']:
            target=.95*fixed['rate_Mbps'];row['minimum_power_target_Mbps']=target
            pe,xe=cpu_solve(q,A,power,budget,'min_power',True,target=target);pel,xel=cpu_solve(q,A,power,budget,'min_power',False,target=target)
            row['minimum_power_MILP']=pe;row['minimum_power_LP']=pel
            if pel['optimal'] and pe['feasibility']['valid']:assert pel['power_W']<=pe['power_W']+FEAS
        else:row['minimum_power_status']='SKIPPED_NO_VALID_FIXED_POWER_INCUMBENT'
        row['peak_host_bytes']=peak_host_bytes();row['GPU_pool_bytes']=int(cp.get_default_memory_pool().total_bytes())
        # Save input coefficient family for reproducible CPU replay, separately from JSON.
        np.savez_compressed(R/f'instance-{n}.npz',q=q,power=power,ids=ids)
        row['instance_sha256']=hashlib.sha256((R/f'instance-{n}.npz').read_bytes()).hexdigest()
        out['rows'].append(row);out['seconds_so_far']=time.perf_counter()-start
        (R/'results.json').write_text(json.dumps(out,indent=2));print('DONE',n,round(out['seconds_so_far'],2),flush=True)
        if row['peak_host_bytes'] and row['peak_host_bytes']>=8*1024**3:raise RuntimeError('host memory budget reached')
        assert row['GPU_pool_bytes']<4*1024**3
        if time.perf_counter()-start>1200:raise RuntimeError('packet20minute budget reached')
    out['total_seconds']=time.perf_counter()-start;(R/'results.json').write_text(json.dumps(out,indent=2))

if __name__=='__main__':main()
