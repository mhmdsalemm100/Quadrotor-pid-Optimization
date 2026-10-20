"""Bounded Wu-Yao-Yang Dolphin Swarm Algorithm; see STUDY_METHOD.md."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json,time
import numpy as np
from model import baseline
from study import decode,encode,evaluate,write_csv

def predation_radius(distance, local_distance, best_fitness, local_fitness, reduction):
    # Algebraic simplification of both outer-radius cases, equations 20 and 23.
    ratio=best_fitness/max(local_fitness,1e-300)
    return max(0.,distance-(distance+(distance-local_distance)*ratio)/reduction)

def communicate(x,k,kf,timers,speed,acceleration,maximum):
    distance=np.linalg.norm(x[:,None,:]-x[None,:,:],axis=2)
    delay=np.maximum(1,np.ceil(distance/(speed*acceleration))).astype(np.int64)
    better=kf[:,None]>kf[None,:]
    timers=np.where(better & (timers>delay),delay,timers)-1
    arrived=timers<=0
    nextk=k.copy(); nextf=kf.copy(); adopted=0
    for i in range(len(x)):
        senders=np.flatnonzero(arrived[i] & better[i])
        if len(senders):
            j=senders[np.argmin(kf[senders])]
            nextk[i]=k[j]; nextf[i]=kf[j]; adopted+=1
    timers[arrived]=maximum
    return nextk,nextf,timers,adopted

def dolphin_swarm(cfg,scenarios,seed,outdir,initial=None,label='main',objective=None):
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    n=int(cfg['swarm_size']); d=len(cfg['parameters']); m=int(cfg['sound_directions']); ticks=int(cfg['search_time_steps'])
    speed=float(cfg['sound_speed']); reduction=float(cfg['radius_reduction'])
    if min(n,m,ticks,cfg['iterations'])<1 or n<2 or speed<=0 or reduction<=2 or cfg['communication_acceleration']<=0:
        raise ValueError('Invalid Dolphin Swarm settings')
    rng=np.random.default_rng(seed); x=rng.random((n,d))
    for j in range(d): x[:,j]=(rng.permutation(n)+rng.random(n))/n
    x[0]=encode(baseline(cfg['controller_dt_s']),cfg)
    if initial is not None: x[1]=encode(np.asarray(initial),cfg)
    names=[p['name'] for p in cfg['parameters']]
    archive=x[0].copy(); best=float('inf'); cache={}; history=[]; rows=[]; evaluations=[]
    start=time.perf_counter(); proposals=0; iteration=0; phase='initial'
    def raw_score(unit):
        gains=decode(unit,cfg)
        f=objective(gains) if objective is not None else evaluate(gains,scenarios,cfg)
        if np.isfinite(f) and f<0: raise ValueError('DSA fitness ratios require nonnegative fitness')
        return float(f) if np.isfinite(f) else 1e12
    first_value=raw_score(x[0])
    with ThreadPoolExecutor(max_workers=cfg['workers']) as pool:
        def evaluate_points(points):
            nonlocal archive,best,proposals,first_value
            proposals+=len(points); keys=[tuple(np.round(p,13)) for p in points]; new={}
            for key,p in zip(keys,points):
                if key not in cache and key not in new: new[key]=p.copy()
            items=list(new.items()); todo=[]; scores={}; first_key=tuple(np.round(x[0],13))
            for key,p in items:
                if first_value is not None and key==first_key: scores[key]=first_value; first_value=None
                else: todo.append((key,p))
            for (key,p),f in zip(todo,pool.map(raw_score,[p for _,p in todo])): scores[key]=f
            for key,p in items:
                f=scores[key]; cache[key]=f
                if f<best: best=f; archive=p.copy()
                evaluations.append({'evaluation':len(cache),'iteration':iteration,'phase':phase,'fitness':f,'best_so_far':best,**dict(zip(names,decode(p,cfg)))})
            return np.array([cache[key] for key in keys])
        values=evaluate_points(x); k=x.copy(); kf=values.copy()
        timers=np.full((n,n),cfg['maximum_transmission_time'],dtype=np.int64)
        adopted=0; near_count=0
        for iteration in range(cfg['iterations']+1):
            if iteration:
                phase='search'
                directions=rng.normal(size=(n,m,d)); directions/=np.linalg.norm(directions,axis=2,keepdims=True)
                probes=np.clip(x[:,None,None,:]+speed*directions[:,:,None,:]*np.arange(1,ticks+1)[None,None,:,None],0,1)
                scores=evaluate_points(probes.reshape(-1,d)).reshape(n,m*ticks)
                idx=np.argmin(scores,axis=1); local=probes.reshape(n,m*ticks,d)[np.arange(n),idx]
                lf=scores[np.arange(n),idx]; improve=lf<kf
                k[improve]=local[improve]; kf[improve]=lf[improve]
                k,kf,timers,adopted=communicate(x,k,kf,timers,speed,cfg['communication_acceleration'],cfg['maximum_transmission_time'])
                phase='predation'; trial=np.empty_like(x); near_count=0
                for i in range(n):
                    distance=np.linalg.norm(x[i]-k[i]); q=np.linalg.norm(local[i]-k[i])
                    if distance<=ticks*speed:
                        trial[i]=k[i]+(x[i]-k[i])*(1-2/reduction); near_count+=1
                    else:
                        radius=predation_radius(distance,q,kf[i],lf[i],reduction)
                        direction=rng.normal(size=d); direction/=np.linalg.norm(direction)
                        trial[i]=k[i]+direction*radius
                x=np.clip(trial,0,1); values=evaluate_points(x)
                improve=values<kf; k[improve]=x[improve]; kf[improve]=values[improve]
            history.append({'iteration':iteration,'best':best,'median':float(np.median(values)),'worst':float(values.max()),
                'feasible_fraction':float(np.mean(values<1000)),'elapsed_s':time.perf_counter()-start,
                'unique_evaluations':len(cache),'candidate_proposals':proposals,'received_improvements':adopted,
                'near_predations':near_count,'position_spread':float(np.mean(np.std(x,axis=0)))})
            for i in range(n):
                rows.append({'iteration':iteration,'dolphin':i,'fitness':float(values[i]),'knowledge_fitness':float(kf[i]),
                    **dict(zip(names,decode(x[i],cfg))),**{'known_'+a:float(b) for a,b in zip(names,decode(k[i],cfg))}})
            if iteration%5==0 or iteration==cfg['iterations']:
                print(f'{label} seed={seed} iteration={iteration:02d} fitness={best:.6g} evaluations={len(cache)}',flush=True)
                (outdir/f'checkpoint_{label}_{seed}.json').write_text(json.dumps({'seed':seed,'history':history,'gains':decode(archive,cfg).tolist()},indent=2))
    write_csv(outdir/f'history_{label}_{seed}.csv',history); write_csv(outdir/f'dolphins_{label}_{seed}.csv',rows)
    write_csv(outdir/f'evaluations_{label}_{seed}.csv',evaluations)
    limit=cfg.get('comparison_evaluation_budget',3264); budget_rows=evaluations[:limit]; snapshot=min(budget_rows,key=lambda a:a['fitness'])
    result={'algorithm':'bounded Wu-Yao-Yang Dolphin Swarm Algorithm (2016)','seed':seed,'fitness':best,'gains':decode(archive,cfg).tolist(),
        'seconds':time.perf_counter()-start,'unique_evaluations':len(cache),'candidate_proposals':proposals,'history':history,
        'comparison_budget':limit,'evaluations_at_comparison_budget':len(budget_rows),'fitness_at_comparison_budget':snapshot['fitness'],
        'gains_at_comparison_budget':[snapshot[name] for name in names]}
    (outdir/f'run_{label}_{seed}.json').write_text(json.dumps(result,indent=2)); return result
