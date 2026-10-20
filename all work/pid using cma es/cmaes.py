"""Bounded active CMA-ES using pycma, with deterministic evaluation accounting."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json,time
import cma
import numpy as np
from model import baseline
from study import decode,encode,evaluate,write_csv

def distribution_state(es,dimension):
    matrix=es.sm.covariance_matrix
    matrix=np.eye(dimension) if matrix is None else np.asarray(matrix,dtype=float)
    scales=np.broadcast_to(np.asarray(es.sigma_vec.scaling,dtype=float),(dimension,))
    covariance=scales[:,None]*matrix*scales[None,:]
    eigenvalues=np.linalg.eigvalsh(covariance)
    if not np.all(np.isfinite(covariance)) or eigenvalues.min()<=0 or not np.isfinite(es.sigma) or es.sigma<=0:
        raise FloatingPointError('Invalid CMA distribution')
    return {'genotype_mean':es.mean.tolist(),'sigma':float(es.sigma),'covariance':covariance.tolist(),
            'covariance_eigenvalues':eigenvalues.tolist(),'axis_ratio':float(np.sqrt(eigenvalues.max()/eigenvalues.min()))}

def cma_es(cfg,scenarios,seed,outdir,initial=None,label='main',objective=None):
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    n=int(cfg['swarm_size']); d=len(cfg['parameters'])
    if n<4 or cfg['iterations']<1 or not 0<cfg['sigma0']<=1: raise ValueError('Invalid population, updates or sigma0')
    rng=np.random.default_rng(seed); x=rng.random((n,d))
    for j in range(d): x[:,j]=(rng.permutation(n)+rng.random(n))/n
    x[0]=encode(baseline(cfg['controller_dt_s']),cfg)
    if initial is not None: x[1]=encode(np.asarray(initial),cfg)
    names=[p['name'] for p in cfg['parameters']]
    archive=x[0].copy(); best=float('inf'); cache={}; history=[]; rows=[]; evaluations=[]; distributions=[]
    start=time.perf_counter(); proposals=0; iteration=0
    def raw_score(unit):
        gains=decode(unit,cfg); f=objective(gains) if objective is not None else evaluate(gains,scenarios,cfg)
        return float(f) if np.isfinite(f) else 1e12
    first_value=raw_score(x[0]); first_key=tuple(np.round(x[0],13))
    with ThreadPoolExecutor(max_workers=cfg['workers']) as pool:
        def evaluate_points(points):
            nonlocal archive,best,proposals,first_value
            proposals+=len(points); keys=[tuple(np.round(p,13)) for p in points]; new={}
            for key,p in zip(keys,points):
                if key not in cache and key not in new: new[key]=p.copy()
            items=list(new.items()); todo=[]; scores={}
            for key,p in items:
                if first_value is not None and key==first_key: scores[key]=first_value; first_value=None
                else: todo.append((key,p))
            for (key,p),f in zip(todo,pool.map(raw_score,[p for _,p in todo])): scores[key]=f
            for key,p in items:
                f=scores[key]; cache[key]=f
                if f<best: best=f; archive=p.copy()
                evaluations.append({'evaluation':len(cache),'iteration':iteration,'fitness':f,'best_so_far':best,**dict(zip(names,decode(p,cfg)))})
            return np.array([cache[key] for key in keys])
        values=evaluate_points(x)
        local_normal=np.random.RandomState(seed).randn
        options={'popsize':n,'bounds':[0.,1.],'BoundaryHandler':cma.BoundTransform,
                 'CMA_active':bool(cfg['cma_active']),'CMA_diagonal':bool(cfg['cma_diagonal']),
                 'seed':seed,'randn':local_normal,'verbose':-9,'verb_log':0,'verb_disp':0}
        es=cma.CMAEvolutionStrategy(x[np.argmin(values)].tolist(),cfg['sigma0'],options)
        for iteration in range(cfg['iterations']+1):
            if iteration:
                samples=es.ask(); x=np.asarray(samples)
                if np.any(x<0) or np.any(x>1): raise AssertionError('Pycma returned out-of-bound phenotype')
                values=evaluate_points(x); es.tell(samples,values.tolist())
            state=distribution_state(es,d); state['iteration']=iteration
            state['library_stop_flags']={str(k):str(v) for k,v in es.stop().items()}; distributions.append(state)
            history.append({'iteration':iteration,'best':best,'median':float(np.median(values)),'worst':float(values.max()),
                'feasible_fraction':float(np.mean(values<1000)),'elapsed_s':time.perf_counter()-start,
                'unique_evaluations':len(cache),'candidate_proposals':proposals,'sigma':state['sigma'],
                'covariance_axis_ratio':state['axis_ratio'],'position_spread':float(np.mean(np.std(x,axis=0)))})
            for i in range(n): rows.append({'iteration':iteration,'candidate':i,'fitness':float(values[i]),**dict(zip(names,decode(x[i],cfg)))})
            if iteration%5==0 or iteration==cfg['iterations']:
                print(f'{label} seed={seed} iteration={iteration:02d} fitness={best:.6g} evaluations={len(cache)} sigma={es.sigma:.4g}',flush=True)
                (outdir/f'checkpoint_{label}_{seed}.json').write_text(json.dumps({'seed':seed,'history':history,'gains':decode(archive,cfg).tolist()},indent=2))
    write_csv(outdir/f'history_{label}_{seed}.csv',history); write_csv(outdir/f'candidates_{label}_{seed}.csv',rows)
    write_csv(outdir/f'evaluations_{label}_{seed}.csv',evaluations)
    (outdir/f'distribution_{label}_{seed}.json').write_text(json.dumps(distributions,indent=2))
    limit=cfg.get('comparison_evaluation_budget',3264); budget_rows=evaluations[:limit]; snapshot=min(budget_rows,key=lambda a:a['fitness'])
    result={'algorithm':'pycma active CMA-ES with BoundTransform','pycma_version':cma.__version__,'seed':seed,'fitness':best,
        'gains':decode(archive,cfg).tolist(),'seconds':time.perf_counter()-start,'unique_evaluations':len(cache),
        'candidate_proposals':proposals,'history':history,'comparison_budget':limit,'evaluations_at_comparison_budget':len(budget_rows),
        'fitness_at_comparison_budget':snapshot['fitness'],'gains_at_comparison_budget':[snapshot[name] for name in names],
        'final_library_stop_flags':distributions[-1]['library_stop_flags']}
    (outdir/f'run_{label}_{seed}.json').write_text(json.dumps(result,indent=2)); return result
