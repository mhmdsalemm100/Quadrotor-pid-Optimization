"""Bounded two-mode Cat Swarm Optimization with an all-evaluations best archive.

Reference: Chu, Tsai & Pan, PRICAI 2006. Coordinate scaling, batch scheduling,
archive policy and boundary handling are documented in STUDY_METHOD.md.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json,time
import numpy as np
from model import baseline
from study import decode,encode,evaluate,write_csv

def selection_probabilities(values):
    values=np.asarray(values,dtype=float)
    weights=values.max()-values
    if weights.sum()<=0: return np.full(len(values),1/len(values))
    return weights/weights.sum()

def cat_swarm(cfg,scenarios,seed,outdir,initial=None,label='main',objective=None):
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    n=int(cfg['swarm_size']); d=len(cfg['parameters']); smp=int(cfg['seeking_memory_pool'])
    if n<2 or smp<2 or cfg['iterations']<1: raise ValueError('Need >=2 cats, SMP>=2 and >=1 iteration.')
    if not 0<=cfg['mixture_ratio']<=1: raise ValueError('MR must be in [0,1].')
    rng=np.random.default_rng(seed)
    x=rng.random((n,d))
    for j in range(d): x[:,j]=(rng.permutation(n)+rng.random(n))/n
    x[0]=encode(baseline(cfg['controller_dt_s']),cfg)
    if initial is not None: x[1]=encode(np.asarray(initial),cfg)
    v=rng.uniform(-cfg['initial_velocity_limit'],cfg['initial_velocity_limit'],(n,d))
    tracing_count=int(round(n*cfg['mixture_ratio']))
    change_count=max(1,min(d,int(round(d*cfg['dimensions_to_change_fraction']))))
    names=[p['name'] for p in cfg['parameters']]
    archive=x[0].copy(); best=float('inf'); cache={}; history=[]; cat_rows=[]; evaluations=[]
    start=time.perf_counter(); proposals=0; iteration=0
    def raw_score(unit):
        gains=decode(unit,cfg)
        f=objective(gains) if objective is not None else evaluate(gains,scenarios,cfg)
        return float(f) if np.isfinite(f) else 1e12
    # Compile once; its result is consumed rather than evaluated a second time.
    first_value=raw_score(x[0])
    with ThreadPoolExecutor(max_workers=cfg['workers']) as pool:
        def evaluate_points(points):
            nonlocal archive,best,proposals,first_value
            proposals+=len(points)
            keys=[tuple(np.round(p,13)) for p in points]
            new={}
            for key,p in zip(keys,points):
                if key not in cache and key not in new: new[key]=p.copy()
            items=list(new.items()); todo=[]; scores={}
            first_key=tuple(np.round(x[0],13))
            for key,p in items:
                if first_value is not None and key==first_key:
                    scores[key]=first_value; first_value=None
                else: todo.append((key,p))
            for (key,p),f in zip(todo,pool.map(raw_score,[p for _,p in todo])): scores[key]=f
            # Deterministic evaluation order independent of worker completion order.
            for key,p in items:
                f=scores[key]; cache[key]=f
                if f<best: best=f; archive=p.copy()
                evaluations.append({'evaluation':len(cache),'iteration':iteration,'fitness':f,
                                    'best_so_far':best,**dict(zip(names,decode(p,cfg)))})
            return np.array([cache[k] for k in keys])
        values=evaluate_points(x)
        modes=np.full(n,'initial',dtype='<U8')
        for iteration in range(cfg['iterations']+1):
            if iteration:
                modes[:]='seeking'
                if tracing_count: modes[rng.choice(n,tracing_count,replace=False)]='tracing'
                points=[]; spans=[]; nextv=v.copy(); frozen_best=archive.copy()
                for i in range(n):
                    begin=len(points)
                    if modes[i]=='tracing':
                        nextv[i]=np.clip(v[i]+cfg['tracing_coefficient']*rng.random(d)*(frozen_best-x[i]),
                                         -cfg['velocity_limit'],cfg['velocity_limit'])
                        trial=x[i]+nextv[i]; hit=(trial<0)|(trial>1)
                        nextv[i,hit]*=-cfg['boundary_damping']
                        points.append(np.clip(trial,0,1))
                    else:
                        copies=smp-int(cfg['self_position_considering'])
                        if cfg['self_position_considering']: points.append(x[i].copy())
                        for _ in range(copies):
                            trial=x[i].copy(); dims=rng.choice(d,change_count,replace=False)
                            signs=rng.choice(np.array([-1.,1.]),change_count)
                            trial[dims]*=1+signs*cfg['seeking_range']
                            points.append(np.clip(trial,0,1))
                    spans.append((begin,len(points)))
                points=np.asarray(points); scores=evaluate_points(points)
                for i,(begin,end) in enumerate(spans):
                    chosen=begin if modes[i]=='tracing' else begin+int(rng.choice(end-begin,p=selection_probabilities(scores[begin:end])))
                    x[i]=points[chosen]; values[i]=scores[chosen]
                v=nextv
            history.append({'iteration':iteration,'best':best,'median':float(np.median(values)),
                            'worst':float(values.max()),'feasible_fraction':float(np.mean(values<1000)),
                            'elapsed_s':time.perf_counter()-start,'unique_evaluations':len(cache),
                            'candidate_proposals':proposals,
                            'seeking_cats':int(np.sum(modes=='seeking')),'tracing_cats':int(np.sum(modes=='tracing')),
                            'position_spread':float(np.mean(np.std(x,axis=0)))})
            for i in range(n):
                cat_rows.append({'iteration':iteration,'cat':i,'mode':str(modes[i]),'fitness':float(values[i]),
                                 **dict(zip(names,decode(x[i],cfg))),
                                 **{f'velocity_{j}':float(v[i,j]) for j in range(d)}})
            if iteration%5==0 or iteration==cfg['iterations']:
                print(f'{label} seed={seed} iteration={iteration:02d} fitness={best:.6g} evaluations={len(cache)} feasible={history[-1]["feasible_fraction"]:.0%}',flush=True)
                (outdir/f'checkpoint_{label}_{seed}.json').write_text(json.dumps({'seed':seed,'history':history,'gains':decode(archive,cfg).tolist()},indent=2))
    write_csv(outdir/f'history_{label}_{seed}.csv',history)
    write_csv(outdir/f'cats_{label}_{seed}.csv',cat_rows)
    write_csv(outdir/f'evaluations_{label}_{seed}.csv',evaluations)
    limit=cfg.get('comparison_evaluation_budget',3264)
    budget_rows=evaluations[:limit]; snapshot=min(budget_rows,key=lambda a:a['fitness'])
    result={'algorithm':'bounded two-mode Cat Swarm Optimization','seed':seed,'fitness':best,
            'gains':decode(archive,cfg).tolist(),'seconds':time.perf_counter()-start,
            'unique_evaluations':len(cache),'candidate_proposals':proposals,'history':history,
            'comparison_budget':limit,'evaluations_at_comparison_budget':len(budget_rows),
            'fitness_at_comparison_budget':snapshot['fitness'],
            'gains_at_comparison_budget':[snapshot[name] for name in names]}
    (outdir/f'run_{label}_{seed}.json').write_text(json.dumps(result,indent=2))
    return result
