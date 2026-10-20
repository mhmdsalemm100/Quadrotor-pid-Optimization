"""Supplemental exhaustive vertex audit; never used by the optimizer."""
from concurrent.futures import ThreadPoolExecutor
from itertools import product
import gzip,json
import numpy as np
from robust_protocol import ROOT,plant_from_unit
from study import evaluate,write_csv
from model import baseline

def failure_counts(details):
    flags={k:0 for k in ['overshoot_failures','final_error_failures','settling_failures',
                         'motor_clipping_failures','negative_speed_failures','cross_axis_failures',
                         'bank_limit_failures','numerical_failures']}
    for c in details:
        m=c['metrics']; d=c['diagnostics']; active=[j for j,t in enumerate(c['scenario']['target']) if t]
        flags['overshoot_failures']+=int(any(m[j][2]>.1+1e-10 for j in active))
        flags['final_error_failures']+=int(any(m[j][3]>.02+1e-10 for j in active))
        flags['settling_failures']+=int(any(m[j][8]<1 for j in active))
        flags['motor_clipping_failures']+=int(d[0]>.05+1e-10)
        flags['negative_speed_failures']+=int(d[6]<-1e-8)
        flags['cross_axis_failures']+=int(any(m[j][6]>np.deg2rad([.5,.5,3.][j])+1e-10 for j in range(3) if j not in active))
        flags['bank_limit_failures']+=int(d[4]>np.deg2rad(75)+1e-10)
        flags['numerical_failures']+=int(bool(d[5]))
    return flags

def corner_cases():
    cases=[]
    for i,u in enumerate(product([0.,1.],repeat=9)):
        p=plant_from_unit(u)
        for j,amp in enumerate([20,20,100]):
            target=[0,0,0]; target[j]=amp
            cases.append({'name':f'vertex_{i:03d}_axis{j}','target':target,'plant':p.tolist(),'group':'joint_corner',
                          'physical_inertia':bool(2*max(p[:3])<=sum(p[:3]))})
    return cases

def check_corners(data,cfg):
    out=ROOT/'results'; folder=out/'corner_validation'; folder.mkdir(exist_ok=True); cases=corner_cases()
    (out/'corner_scenarios.json').write_text(json.dumps(cases,indent=2))
    tasks=[]
    for mode,methods in data.items():
        for m,rr in methods.items():
            rr=sorted(rr,key=lambda r:(r['fitness'],r['seed'])); median=np.median([r['fitness'] for r in rr])
            for label,r in [('best',rr[0]),('median',min(rr,key=lambda r:(abs(r['fitness']-median),r['seed'])))]:
                tasks.append((mode,m,label,r))
    tasks.append(('baseline','source','original',{'seed':0,'gains':baseline().tolist()}))
    def check(task):
        mode,m,label,r=task; path=folder/f'{mode}_{m}_{label}.json.gz'
        if path.exists():
            with gzip.open(path,'rt',encoding='utf-8') as f: cached=json.load(f)
            return {**cached['summary'],**failure_counts(cached['cases'])}
        _,details=evaluate(np.array(r['gains']),cases,cfg,True)
        physical=[c for c in details if c['scenario']['physical_inertia']]
        result={'mode':mode,'method':m,'selection':label,'seed':r['seed'],
                'passes':sum(c['feasible'] for c in details),'cases':len(details),
                'physical_passes':sum(c['feasible'] for c in physical),'physical_cases':len(physical),
                'worst_violation':max(c['violation'] for c in details),**failure_counts(details)}
        with gzip.open(path,'wt',encoding='utf-8') as f: json.dump({'summary':result,'cases':details},f)
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=[]
        for row in pool.map(check,tasks):
            rows.append(row); print('Corner audit: '+json.dumps(row),flush=True)
    write_csv(out/'corner_validation_summary.csv',rows)
    return rows
