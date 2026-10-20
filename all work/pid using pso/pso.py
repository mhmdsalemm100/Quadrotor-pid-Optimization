"""Bounded global-best particle swarm optimization (no genetic operations)."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import time
import numpy as np
from model import baseline
from study import decode, encode, evaluate, write_csv

def particle_swarm(cfg, scenarios, seed, outdir, initial=None, label='main', objective=None):
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(seed); size=cfg['swarm_size']; dims=len(cfg['parameters'])
    if size<2 or cfg['iterations']<1: raise ValueError('Use at least two particles and one iteration.')
    # Preserve the GA's initial position distribution for a matched comparison.
    positions=rng.random((size,dims))
    for j in range(dims): positions[:,j]=(rng.permutation(size)+rng.random(size))/size
    positions[0]=encode(baseline(cfg['controller_dt_s']),cfg)
    if initial is not None: positions[1]=encode(np.asarray(initial),cfg)
    velocities=rng.uniform(-cfg['initial_velocity_limit'],cfg['initial_velocity_limit'],(size,dims))
    personal=positions.copy(); personal_values=np.full(size,np.inf)
    global_position=positions[0].copy(); global_value=np.inf
    cache={}; history=[]; particle_rows=[]; start=time.perf_counter()
    def score(position):
        key=tuple(np.round(position,13))
        if key not in cache:
            physical=decode(position,cfg)
            val=objective(physical) if objective is not None else evaluate(physical,scenarios,cfg)
            cache[key]=float(val) if np.isfinite(val) else 1e12
        return cache[key]
    score(positions[0])  # compile numerical kernel before threaded evaluation
    names=[p['name'] for p in cfg['parameters']]
    with ThreadPoolExecutor(max_workers=cfg['workers']) as pool:
        for iteration in range(cfg['iterations']+1):
            values=np.array(list(pool.map(score,positions)))
            improve=values<personal_values
            personal[improve]=positions[improve]; personal_values[improve]=values[improve]
            winner=int(np.argmin(personal_values))
            if personal_values[winner]<global_value:
                global_value=float(personal_values[winner]); global_position=personal[winner].copy()
            inertia=cfg['inertia_start']+(cfg['inertia_end']-cfg['inertia_start'])*min(iteration,max(0,cfg['iterations']-1))/max(1,cfg['iterations']-1)
            row={'iteration':iteration,'best':global_value,'median':float(np.median(values)),
                 'worst':float(values.max()),'feasible_fraction':float(np.mean(values<1000)),
                 'personal_best_feasible_fraction':float(np.mean(personal_values<1000)),
                 'elapsed_s':time.perf_counter()-start,'unique_evaluations':len(cache),
                 'candidate_proposals':size*(iteration+1),'inertia_for_next_update':inertia,
                 'position_spread':float(np.mean(np.std(positions,axis=0)))}
            history.append(row)
            physical=decode(positions,cfg)
            for j in range(size):
                particle_rows.append({'iteration':iteration,'particle':j,'fitness':float(values[j]),
                                      'personal_best_fitness':float(personal_values[j]),
                                      **dict(zip(names,physical[j])),
                                      **{f'velocity_{k}':float(velocities[j,k]) for k in range(dims)}})
            if iteration%5==0 or iteration==cfg['iterations']:
                print(f'{label} seed={seed} iteration={iteration:02d} fitness={global_value:.6g} feasible={row["feasible_fraction"]:.0%}',flush=True)
                (outdir/f'checkpoint_{label}_{seed}.json').write_text(json.dumps({'seed':seed,'history':history,'gains':decode(global_position,cfg).tolist()},indent=2))
            if iteration==cfg['iterations']: break
            r1=rng.random((size,dims)); r2=rng.random((size,dims))
            velocities=(inertia*velocities + cfg['cognitive_coefficient']*r1*(personal-positions)
                        + cfg['social_coefficient']*r2*(global_position-positions))
            velocities=np.clip(velocities,-cfg['velocity_limit'],cfg['velocity_limit'])
            trial=positions+velocities; hit=(trial<0)|(trial>1)
            positions=np.clip(trial,0,1)
            velocities[hit]*=-cfg['boundary_damping']
    write_csv(outdir/f'history_{label}_{seed}.csv',history)
    write_csv(outdir/f'particles_{label}_{seed}.csv',particle_rows)
    result={'algorithm':'global-best PSO','seed':seed,'fitness':global_value,
            'gains':decode(global_position,cfg).tolist(),'seconds':time.perf_counter()-start,
            'unique_evaluations':len(cache),'candidate_proposals':size*(cfg['iterations']+1),'history':history}
    (outdir/f'run_{label}_{seed}.json').write_text(json.dumps(result,indent=2))
    return result
