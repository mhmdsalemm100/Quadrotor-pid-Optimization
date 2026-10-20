"""Run the study: python run_study.py --mode full (or --mode quick)."""
import argparse
import copy
import json
import platform
import sys
import time
from pathlib import Path
import numpy as np
from model import baseline, coefficients, NOMINAL, run
from study import (training_scenarios, validation_scenarios,
                   evaluate, metric_rows, write_csv, robust_training_scenarios)

from dsa import dolphin_swarm

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['quick','full'],default='full')
    parser.add_argument('--config',type=Path,default=ROOT/'config.json')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--resume',action='store_true',help='Reuse completed DSA runs only if saved configuration matches.')
    args=parser.parse_args()
    cfg=json.loads(args.config.read_text()); out=args.output or ROOT/('results' if args.mode=='full' else 'results_quick')
    out.mkdir(parents=True,exist_ok=True); start=time.perf_counter()
    if args.mode=='quick': cfg.update(swarm_size=24,iterations=8,seeds=[11])
    saved=out/'configuration.json'
    if args.resume and saved.exists() and json.loads(saved.read_text())!=cfg:
        raise ValueError('Resume configuration differs from the saved run. Use a new output folder.')
    saved.write_text(json.dumps(cfg,indent=2))
    from inspect_source import inventory
    inv=inventory()
    train=training_scenarios(); holdout=validation_scenarios()
    (out/'scenarios.json').write_text(json.dumps({'training':train,'validation':holdout},indent=2))
    base=baseline(cfg['controller_dt_s'])
    print('Evaluating baseline and compiling numerical kernel...',flush=True)
    basefitness=evaluate(base,train,cfg)
    print(f'Baseline fitness: {basefitness:.6g}',flush=True)
    results=[]
    for seed in cfg['seeds']:
        path=out/f'run_main_{seed}.json'
        result=json.loads(path.read_text()) if args.resume and path.exists() else dolphin_swarm(cfg,train,seed,out)
        results.append(result)
    best=min(results,key=lambda r:r['fitness']); gains=np.asarray(best['gains'])
    # Never export a poorer replacement silently.
    if best['fitness']>basefitness:
        gains=base.copy(); selection='baseline retained; DSA found no better candidate'
    else: selection=f'best training fitness across seeds; seed {best["seed"]}'
    coeff=coefficients(gains,cfg['controller_dt_s'],cfg['fixed_discrete_pole'])
    export={'selection':selection,'training_fitness':evaluate(gains,train,cfg),
            'baseline_training_fitness':basefitness,
            'training_feasible':evaluate(gains,train,cfg)<1000,
            'controller_dt_s_assumed':cfg['controller_dt_s'],'mixer_dt_s_assumed':cfg['mixer_dt_s'],
            'gains':dict(zip([p['name'] for p in cfg['parameters']],gains.tolist())),
            'roll_transfer_function':coeff['roll'],'pitch_transfer_function':coeff['pitch'],
            'yaw':{'Kp':float(gains[6]),'Ki':float(gains[7]),'Kd':0.0},
            'source_sha256':inv['sha256']['AttitudeControl_Sim.slx'],
            'status':'Python-model candidate; not verified in compiled Simulink; no global optimality claim.'}
    for label,g in [('baseline',base),('optimized',gains)]:
        _,cases=evaluate(g,train,cfg,True)
        speed=np.array([c['speed'] for c in cases])
        export[label+'_unpenalized_response_cost']=float((1-cfg['worst_case_weight'])*speed.mean()+cfg['worst_case_weight']*speed.max()+cfg['effort_weight']*np.mean([c['effort'] for c in cases]))
    (out/'best_gains.json').write_text(json.dumps(export,indent=2))
    allmetrics=[]; case_details={}
    for name,g in [('baseline',base),('DSA',gains)]:
        rows,details=metric_rows(g,train+holdout,cfg,name)
        allmetrics+=rows; case_details[name]=details
    write_csv(out/'metrics.csv',allmetrics)
    (out/'case_details.json').write_text(json.dumps(case_details,indent=2))
    robust_train=robust_training_scenarios()
    robust_cfg=copy.deepcopy(cfg)
    robust_cfg.update(swarm_size=48 if args.mode=='full' else 24,
                      iterations=35 if args.mode=='full' else 8,seeds=[71,89] if args.mode=='full' else [71])
    robust_runs=[]
    for seed in robust_cfg['seeds']:
        path=out/f'run_robust_{seed}.json'
        rr=json.loads(path.read_text()) if args.resume and path.exists() else dolphin_swarm(robust_cfg,robust_train,seed,out,initial=gains,label='robust')
        robust_runs.append(rr)
    rg=np.array(min(robust_runs,key=lambda r:r['fitness'])['gains'])
    robust_export={'gains':dict(zip([p['name'] for p in cfg['parameters']],rg.tolist())),
                   'transfer_functions':coefficients(rg,cfg['controller_dt_s'],cfg['fixed_discrete_pole']),
                   'yaw':{'Kp':float(rg[6]),'Ki':float(rg[7]),'Kd':0.},
                   'robust_training_fitness':evaluate(rg,robust_train,cfg),
                   'nominal_training_fitness':evaluate(rg,train,cfg),
                   'training_scenarios':robust_train,'configuration':robust_cfg,
                   'status':'Separate uncertainty-focused single-axis candidate; no guarantee on combined-axis maneuvers.'}
    (out/'robust_gains.json').write_text(json.dumps(robust_export,indent=2))
    robustrows,_=metric_rows(rg,train+holdout,cfg,'robust_DSA')
    write_csv(out/'robust_metrics.csv',robustrows)
    print('Running held-out robustness, gain sensitivity, and numerical checks...',flush=True)
    # Random held-out parameter perturbations do not participate in winner selection.
    rng=np.random.default_rng(20261004); mc=[]
    count=60 if args.mode=='full' else 9
    for i in range(count+(30 if args.mode=='full' else 3)):
        p=NOMINAL.copy(); p[:3]*=rng.uniform(.85,1.15,3); p[10]*=rng.uniform(.7,1.3)
        p[4:6]*=rng.uniform(.9,1.1,2); p[6:9]*=rng.uniform(.7,1.3,3)
        s={'name':f'mc_{i:03d}','target':[float(rng.choice([-1,1])*rng.uniform(5,18)),
                                                   float(rng.choice([-1,1])*rng.uniform(5,15)),
                                                   float(rng.choice([-1,1])*rng.uniform(20,70))],
           'plant':p.tolist(),'throttle':float(rng.uniform(.54,.68)),
           'group':'single_axis_uncertainty' if i<count else 'combined_axis_stress'}
        if i<count:
            axis=i%3
            s['target']=[v if j==axis else 0. for j,v in enumerate(s['target'])]
        for label,g in [('baseline',base),('DSA',gains),('robust_DSA',rg)]:
            score,details=evaluate(g,[s],cfg,True); a=details[0]
            mc.append({'sample':i,'group':s['group'],'controller':label,'fitness':score,'feasible':a['feasible'],
                       'violation':a['violation'],'max_settling_s':max(np.array(a['metrics'])[:,1]),
                       'max_overshoot_pct':100*max(np.array(a['metrics'])[:,2]),
                       'motor_clip_pct':100*a['diagnostics'][0],
                       'scenario_json':json.dumps(s)})
    write_csv(out/'monte_carlo.csv',mc)
    sensitivity=[]
    for j,p in enumerate(cfg['parameters']):
        for factor in [.8,.9,1.,1.1,1.2]:
            changed=gains.copy(); changed[j]=np.clip(changed[j]*factor,p['lower'],p['upper'])
            sensitivity.append({'parameter':p['name'],'factor_requested':factor,'actual_gain':changed[j],
                                'fitness':evaluate(changed,train,cfg)})
    write_csv(out/'gain_sensitivity.csv',sensitivity)
    numerical=[]
    for s in [train[1],train[3],train[5],holdout[6]]:
        _,_,tr=run(gains,s,cfg,True); _,_,fine=run(gains,{**s,'dt':cfg['integration_dt_s']/2},cfg,True)
        err=np.max(np.abs(tr[:,1:7]-fine[::2,1:7]),axis=0)
        numerical.append({'scenario':s['name'],'max_angle_error_deg':float(np.rad2deg(err[:3].max())),
                          'max_rate_error_deg_s':float(np.rad2deg(err[3:].max()))})
    write_csv(out/'numerical_convergence.csv',numerical)
    # Independent compact reoptimizations quantify fitness/hyperparameter sensitivity.
    experiments=[]
    if args.mode=='full':
        variants=[('settling_priority',{'fitness_weights':{'settling':.7,'rise':.1,'itae':.15,'iae':.05}}),
                  ('error_priority',{'fitness_weights':{'settling':.2,'rise':.1,'itae':.5,'iae':.2}}),
                  ('slower_sound',{'sound_speed':.04}),
                  ('gentler_predation',{'radius_reduction':4.})]
        for label,changes in variants:
            alt=copy.deepcopy(cfg); alt.update(swarm_size=32,iterations=24,seeds=[101]); alt.update(changes)
            path=out/f'run_{label}_101.json'
            result=json.loads(path.read_text()) if args.resume and path.exists() else dolphin_swarm(alt,train,101,out,initial=gains,label=label)
            experiments.append({'name':label,'own_fitness':result['fitness'],
                                'common_main_fitness':evaluate(np.array(result['gains']),train,cfg),
                                'gains':result['gains'],'settings':alt,
                                'note':'Warm-started exploratory study; not used to select main exported gains.'})
    (out/'fitness_and_dsa_sensitivity.json').write_text(json.dumps(experiments,indent=2))
    timing={'elapsed_this_invocation_s':time.perf_counter()-start,'python':sys.version,
            'platform':platform.platform(),'mode':args.mode,
            'main_runs':[{'seed':r['seed'],'fitness':r['fitness'],'unique_evaluations':r['unique_evaluations'],'seconds':r['seconds']} for r in results]}
    (out/'execution.json').write_text(json.dumps(timing,indent=2))
    from report import build_report
    build_report(out,cfg,export,results,base,gains,train,holdout,allmetrics,mc,sensitivity,numerical,experiments)
    from compare_methods import compare_methods
    compare_methods(out,cfg)
    print(f'Completed. Report: {out / "REPORT.html"}',flush=True)
    print(json.dumps(export,indent=2),flush=True)

if __name__=='__main__': main()
