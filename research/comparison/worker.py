"""Single solver/policy worker. Never spawns another process."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
from pathlib import Path
import sys,json,time,numpy as np
from core import *
from supervisor import atomic
R=Path(__file__).resolve().parent

def main(jobpath):
    start=time.perf_counter();job=json.loads(Path(jobpath).read_text());out=Path(job['output']);out.parent.mkdir(parents=True,exist_ok=True)
    def save(value):atomic(out,{'worker_elapsed':time.perf_counter()-start,**value})
    save({'stage':'loaded_job','completed':False})
    mode=job['mode']
    if mode=='watchdog_probe':
        time.sleep(5);save({'completed':True});return
    if mode=='invalid_probe':out.write_text('{broken');return
    d=np.load(job['input'])
    if mode=='power':
        h=d['h'];n=len(h);schedule=fixed_schedule(n);p=np.full(n,.1);value=evaluate(h,h,p,schedule)[0]
        current={'stage':'feasible_initial','completed':False,'p':p,'schedule':schedule,'nominal_SE':value,'power_W':float(p.sum()),'optimal':False}
        save(current)
        def checkpoint(p,sc,val):current.update(p=p,schedule=sc,nominal_SE=val,power_W=float(p.sum()),stage='incumbent');save(current)
        arm=job['arm']
        if arm=='uniform':result={'p':p,'schedule':schedule,'nominal_SE':value,'upper_SE':upper_bound(h,.1*n)}
        elif arm=='uniform_min':result=uniform_min_power(h,schedule,.95*value)
        elif arm=='slsqp':result=slsqp(h,schedule,.1*n,checkpoint)
        elif arm in ['iwmmse','cert_iwmmse']:result=iwmmse(h,schedule,.1*n,certificate=arm=='cert_iwmmse',callback=checkpoint)
        else:
            sys.path.insert(0,str(R.parent/'gpu'));import benchmark as old
            edges,A,power,slot,pidx=old.matrices(n)
            # old.rates expects physical noise; h is already whitened.
            q=old.rates(h*np.sqrt(old.NOISE),edges,np).ravel()
            save({**current,'stage':'solver_entered','columns':len(q)})
            result,x=old.cpu_solve(q,A,power,.1*n,'max_rate',arm=='grid')
            if x is not None:np.save(out.with_suffix('.primal.npy'),x)
            result['nominal_SE']=result.pop('rate_Mbps');result['scope']='finite power grid; reported objective in sumSE, not Mbps'
        save({**result,'power_W':float(np.sum(result['p'])) if 'p' in result else result.get('power_W'),'stage':'completed','completed':True,'arm':arm})
    elif mode=='info':
        # Only the evaluator below uses truth. Decision routines receive estimate/prior only.
        est=d['estimate'];truth=d['truth'];extra=d['extra'];noise=float(d['noise']);scale=np.sqrt(.1*noise)
        before=time.perf_counter();arm=job['arm'];after=est.copy();selection=None
        if arm=='uniform_probe':after+=(d['uniform_observation']-est)@d['Ku'].T
        elif arm!='no_probe':
            if arm=='random':selection=int(d['random_ue'])
            elif arm=='weakest':selection=int(np.sum(abs(est)**2,axis=1).argmin())
            else:
                sys.path.insert(0,str(R.parent/'selective'));import experiment
                scores=experiment.predictive_scores(est,d['C4'],d['K'],noise,np.random.default_rng(int(d['policy_seed'])),samples=8)
                selection=int(scores[2].argmax())
            after[selection]+=d['K']@(extra[selection]-est[selection])
        selection_seconds=time.perf_counter()-before
        h=after.reshape(4,-1,2)/scale
        result=optimize_all4(h,certificate=arm=='joint_cert');p=result['p'];sc=result['schedule']
        actual,per=evaluate(truth.reshape(4,-1,2)/scale,h,p,sc)
        tau=4 if arm=='no_probe' else 5
        save({**result,'stage':'completed','completed':True,'arm':arm,'selected_ue':selection,'selection_seconds':selection_seconds,'actual_sumSE':actual,'actual_bandwidth_SE':actual/2*(1-tau/200),'min_user_SE':float(per.min()),'power_W':float(p.sum()),'pilot_symbols':tau,'pilot_total_energy':16 if arm=='no_probe' else 17,'nominal_certificate_does_not_cover_true_CSI':True})
    else:raise ValueError(mode)
if __name__=='__main__':main(sys.argv[1])
