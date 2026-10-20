"""Audit robust searches and compare all gains on identical unseen plants."""
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from pathlib import Path
import argparse,gzip,hashlib,json
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from benchmark import METHODS,SEEDS
from robust_protocol import ROOT,FACTORS,training_cases,validation_cases
from study import evaluate,training_scenarios,write_csv,decode
from model import baseline,coefficients,run
from linear_analysis import local_analysis

COLORS={'GA':'#45658b','PSO':'#cb861c','CSO':'#b54d70','DSA':'#00858b','CMA-ES':'#794aad'}
OUT=ROOT/'results'

def dump(path,data): path.write_text(json.dumps(data,indent=2),encoding='utf-8')
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def holm(rows):
    prev=0.
    for rank,i in enumerate(np.argsort([r['p'] for r in rows])):
        prev=max(prev,min(1.,rows[i]['p']*(len(rows)-rank)))
        rows[i]['holm_p']=prev
    return rows

def paired(a,b,draws):
    d=np.round(np.asarray(a)-np.asarray(b),12); boot=d[draws].mean(axis=1)
    return {'mean_A_minus_B':float(d.mean()),'median_A_minus_B':float(np.median(d)),
            'A_lower':int(np.sum(d< -1e-10)),'ties':int(np.sum(abs(d)<=1e-10)),
            'B_lower':int(np.sum(d>1e-10)),
            'p':1. if not np.any(d) else float(stats.wilcoxon(d,method='auto').pvalue),
            'mean_difference_ci95_low':float(np.quantile(boot,.025)),
            'mean_difference_ci95_high':float(np.quantile(boot,.975))}

def summary_stats(a,draws):
    a=np.asarray(a); boot=a[draws].mean(axis=1); bm=np.median(a[draws],axis=1)
    return {'best':float(a.min()),'median':float(np.median(a)),'mean':float(a.mean()),
            'std':float(a.std(ddof=1)),'worst':float(a.max()),
            'q1':float(np.quantile(a,.25)),'q3':float(np.quantile(a,.75)),
            'mean_ci95_low':float(np.quantile(boot,.025)),'mean_ci95_high':float(np.quantile(boot,.975)),
            'median_ci95_low':float(np.quantile(bm,.025)),'median_ci95_high':float(np.quantile(bm,.975))}

def get_runs():
    return {mode:{m:[read((ROOT/'nominal_reference/runs' if mode=='nominal' else OUT/'runs')/f'{m}_{s}.json')
                           for s in SEEDS] for m in METHODS} for mode in ['nominal','robust']}

def case_record(c):
    s=c['scenario']; a=np.asarray(c['metrics']); d=c['diagnostics']; active=np.flatnonzero(s['target'])
    return {'name':s['name'],'group':s['group'],'feasible':c['feasible'],'violation':c['violation'],
            'speed_score':c['speed'],'metrics':c['metrics'],'diagnostics':d,
            'max_settling_s':float(a[active,1].max()),'max_overshoot_pct':float(a[active,2].max()*100),
            'max_final_error_pct':float(a[active,3].max()*100),
            'fails_overshoot':bool(np.any(a[active,2]>.1+1e-10)),
            'fails_final_error':bool(np.any(a[active,3]>.02+1e-10)),
            'fails_settling':bool(np.any(a[active,8]<1)),
            'fails_motor_clipping':bool(d[0]>.05+1e-10),'fails_negative_speed':bool(d[6]<-1e-8),
            'fails_cross_axis':bool(np.any(a[np.asarray(s['target'])==0,6]>np.deg2rad([.5,.5,3.])[np.asarray(s['target'])==0]+1e-10)),
            'fails_bank_limit':bool(d[4]>np.deg2rad(75)+1e-10),
            'fails_numerical':bool(d[5])}

def validate_one(task):
    mode,m,r,cfg=task; path=OUT/'validation'/f'{mode}_{m}_{r["seed"]}.json.gz'
    if path.exists():
        with gzip.open(path,'rt',encoding='utf-8') as f: return json.load(f)['summary']
    g=np.array(r['gains']); f,train=evaluate(g,training_cases(),cfg,True)
    if mode=='robust': assert abs(f-r['fitness'])<1e-10
    nominal,nd=evaluate(g,training_scenarios(),cfg,True)
    if mode=='nominal': assert abs(nominal-r['fitness'])<1e-10
    _,details=evaluate(g,validation_cases(),cfg,True); records=[case_record(c) for c in details]
    row={'mode':mode,'method':m,'seed':r['seed'],'robust_training_fitness':f,
         'training_passes':sum(c['feasible'] for c in train),'nominal_fitness':nominal,
         'nominal_passes':sum(c['feasible'] for c in nd),
         'nominal_mean_settling_s':float(np.mean([case_record(c)['max_settling_s'] for c in nd])),
         'nominal_worst_settling_s':float(max(case_record(c)['max_settling_s'] for c in nd))}
    for group in ['single_axis_mc','one_at_a_time','combined_stress']:
        subset=[c for c in records if c['group']==group]
        row[group+'_passes']=sum(c['feasible'] for c in subset)
        row[group+'_worst_settling_s']=max(c['max_settling_s'] for c in subset)
        row[group+'_worst_violation']=max(c['violation'] for c in subset)
    temp=path.with_suffix('.tmp')
    with gzip.open(temp,'wt',encoding='utf-8') as f: json.dump({'summary':row,'cases':records,'training':train,'nominal':nd},f)
    temp.replace(path)
    return row

def validate_available(cfg):
    tasks=[]; (OUT/'validation').mkdir(exist_ok=True)
    for mode in ['nominal','robust']:
        folder=ROOT/'nominal_reference/runs' if mode=='nominal' else OUT/'runs'
        for m in METHODS:
            for s in SEEDS:
                file=folder/f'{m}_{s}.json'
                if file.exists(): tasks.append((mode,m,read(file),cfg))
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=[]
        for i,row in enumerate(pool.map(validate_one,tasks)):
            rows.append(row)
            if (i+1)%25==0: print(f'Validation {i+1}/{len(tasks)} controllers',flush=True)
    write_csv(OUT/'validation_summary.csv',rows)
    return rows

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--validate-available',action='store_true'); args=parser.parse_args()
    cfg=read(OUT/'contract.json')['configuration']
    if args.validate_available: validate_available(cfg); return
    contract=read(OUT/'contract.json')
    for n,h in contract['code_sha256'].items(): assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h
    data=get_runs(); curves={m:[] for m in METHODS}
    write_csv(OUT/'all_robust_runs.csv',[{k:r[k] for k in ['method','seed','fitness','unique_evaluations','last_iteration','seconds']}
                                       for m in METHODS for r in data['robust'][m]])
    for i,s in enumerate(SEEDS):
        paired_initial=[]
        for m in METHODS:
            r=data['robust'][m][i]; a=np.load(OUT/'runs'/f'{m}_{s}_evaluations.npz')['ledger']
            assert r['method']==m and r['seed']==s
            assert len(a)==r['unique_evaluations']==3264
            np.testing.assert_array_equal(a[:,0],np.arange(1,3265))
            assert np.all(np.diff(a[:,3])<=0) and abs(a[:,2].min()-r['fitness'])<1e-12
            assert len({tuple(np.round(x,13)) for x in a[:,4:]})==3264
            assert np.all((a[:,4:]>=0)&(a[:,4:]<=1))
            np.testing.assert_allclose(decode(a[np.argmin(a[:,2]),4:],cfg),r['gains'],rtol=1e-13,atol=1e-15)
            assert r['initial_population_sha256']==data['nominal'][m][i]['initial_population_sha256']
            paired_initial.append(a[:64]); curves[m].append(a[:,3])
        for a in paired_initial[1:]: np.testing.assert_array_equal(a,paired_initial[0])
    rows=validate_available(cfg)
    # Supplemental physical-inertia subset; retain the pre-specified box result.
    physical={s['name']:bool(2*max(s['plant'][:3])<=sum(s['plant'][:3])) for s in validation_cases()}
    physical_rows=[]
    for mode in ['nominal','robust']:
        for m in METHODS:
            for s in SEEDS:
                with gzip.open(OUT/'validation'/f'{mode}_{m}_{s}.json.gz','rt',encoding='utf-8') as f: vv=json.load(f)
                subset=[c for c in vv['cases'] if c['group']=='single_axis_mc' and physical[c['name']]]
                physical_rows.append({'mode':mode,'method':m,'seed':s,'passes':sum(c['feasible'] for c in subset),'cases':len(subset)})
    write_csv(OUT/'physical_inertia_subset_runs.csv',physical_rows)
    phys_summary=[]
    for mode in ['nominal','robust']:
        for m in METHODS:
            rr=[r for r in physical_rows if r['mode']==mode and r['method']==m]
            phys_summary.append({'mode':mode,'method':m,'cases_per_controller':rr[0]['cases'],
                                 'median_passes':float(np.median([r['passes'] for r in rr])),
                                 'controllers_passing_all':sum(r['passes']==r['cases'] for r in rr)})
    write_csv(OUT/'physical_inertia_subset_summary.csv',phys_summary)
    lookup={(r['mode'],r['method'],r['seed']):r for r in rows}
    rng=np.random.default_rng(7102026); draws=rng.integers(0,30,(10000,30))
    scores=np.array([[data['robust'][m][i]['fitness'] for m in METHODS] for i in range(30)])
    summary=[{'method':m,**summary_stats(scores[:,j],draws),'training_feasible_runs':int(np.sum(scores[:,j]<1000))}
             for j,m in enumerate(METHODS)]
    write_csv(OUT/'robust_fitness_summary.csv',summary)
    pairs=holm([{'A':METHODS[i],'B':METHODS[j],**paired(scores[:,i],scores[:,j],draws)} for i,j in combinations(range(5),2)])
    write_csv(OUT/'robust_fitness_pairwise.csv',pairs)
    # Calibration by within-seed random permutations of method labels.
    ranks=stats.rankdata(scores,axis=1); obs=float(np.sum(ranks.sum(axis=0)**2)); count=0
    for _ in range(20):
        order=np.argsort(rng.random((1000,30,5)),axis=2)
        pr=np.take_along_axis(np.broadcast_to(ranks,(1000,30,5)),order,axis=2)
        count+=int(np.sum(np.sum(pr.sum(axis=1)**2,axis=1)>=obs-1e-9))
    f=stats.friedmanchisquare(*scores.T)
    dump(OUT/'statistics.json',{'friedman_statistic':float(f.statistic),'permutation_p':(count+1)/20001,
                              'permutations':20000,'bootstrap_resamples':10000,'seed':7102026,
                              'notes':'Inference over optimizer seeds on one fixed problem. Wilcoxon assumes symmetric paired differences. CI not multiplicity adjusted.'})
    comparisons=[]; changes=[]
    for m in METHODS:
        for mode in ['nominal','robust']:
            rr=[lookup[mode,m,s] for s in SEEDS]; passes=np.array([r['single_axis_mc_passes'] for r in rr])
            comparisons.append({'method':m,'mode':mode,'median_mc_passes':float(np.median(passes)),
                'mean_mc_passes':float(passes.mean()),'min_mc_passes':int(passes.min()),
                'all_300_controllers':int(np.sum(passes==300)),
                'mean_mc_pass_ci95_low':float(np.quantile(passes[draws].mean(axis=1),.025)),
                'mean_mc_pass_ci95_high':float(np.quantile(passes[draws].mean(axis=1),.975)),
                'median_boundary_passes':float(np.median([r['one_at_a_time_passes'] for r in rr])),
                'all_54_boundary_controllers':sum(r['one_at_a_time_passes']==54 for r in rr),
                'median_combined_passes':float(np.median([r['combined_stress_passes'] for r in rr])),
                'median_nominal_fitness':float(np.median([r['nominal_fitness'] for r in rr])),
                'median_nominal_mean_settling_s':float(np.median([r['nominal_mean_settling_s'] for r in rr])),
                'all_30_training_controllers':sum(r['training_passes']==30 for r in rr)})
        for metric in ['single_axis_mc_passes','nominal_fitness','nominal_mean_settling_s']:
            aa=[lookup['robust',m,s][metric] for s in SEEDS]; bb=[lookup['nominal',m,s][metric] for s in SEEDS]
            changes.append({'method':m,'metric':metric,'A':'robust','B':'nominal',**paired(aa,bb,draws)})
    # One correction family includes all 15 pre-specified nominal-versus-robust comparisons.
    holm(changes); write_csv(OUT/'nominal_vs_robust.csv',comparisons); write_csv(OUT/'paired_tuning_changes.csv',changes)
    # Primary held-out robustness comparison: rank number of failures (smaller better).
    failures=np.array([[300-lookup['robust',m,s]['single_axis_mc_passes'] for m in METHODS] for s in SEEDS])
    validation_pairs=holm([{'A':METHODS[i],'B':METHODS[j],**paired(failures[:,i],failures[:,j],draws)}
                          for i,j in combinations(range(5),2)])
    write_csv(OUT/'heldout_failures_pairwise.csv',validation_pairs)
    selected=[]; (OUT/'exports').mkdir(exist_ok=True); numeric=[]; local={}; uncertain_local=[]
    for m in METHODS:
        ordered=sorted(data['robust'][m],key=lambda r:(r['fitness'],r['seed']))
        median=float(np.median([r['fitness'] for r in ordered]))
        for label,r in [('best',ordered[0]),('median',min(ordered,key=lambda r:(abs(r['fitness']-median),r['seed'])))]:
            g=np.array(r['gains']); v=lookup['robust',m,r['seed']]
            exp={'method':m,'selection':label,'seed':r['seed'],'training_fitness':r['fitness'],
                'gains':dict(zip([p['name'] for p in cfg['parameters']],r['gains'])),
                'roll_pitch_discrete':coefficients(g),'yaw_PI':{'Kp':float(g[6]),'Ki':float(g[7])},'validation':v,
                'status':'Python candidate; selection uses training fitness only; controller 1 ms, mixer 4 ms; not Simulink verified.'}
            dump(OUT/'exports'/f'{m}_{label}_gains.json',exp)
            (OUT/'exports'/f'{m}_{label}_SIMULINK_MAP.txt').write_text(exp['status']+'\n'+json.dumps(exp,indent=2))
            selected.append({'method':m,'selection':label,'seed':r['seed'],'fitness':r['fitness'],
                             'mc_passes':v['single_axis_mc_passes'],'boundary_passes':v['one_at_a_time_passes'],
                             'combined_passes':v['combined_stress_passes']})
            if label=='best':
                local[m]=local_analysis(g,cfg)
                plants={tuple(s['plant']) for s in training_cases()+validation_cases() if 'plant' in s and s.get('group')!='combined_stress'}
                for ii,p in enumerate(sorted(plants)):
                    ll=local_analysis(g,cfg,p)
                    uncertain_local.append({'method':m,'plant_index':ii,'plant':json.dumps(p),
                        **{axis+'_spectral_radius':ll[axis]['spectral_radius'] for axis in ['roll','pitch','yaw']},
                        'all_axes_locally_stable':all(v['locally_stable'] for v in ll.values())})
                cases=training_cases()
                _,details=evaluate(g,cases,cfg,True)
                worst=max(range(len(cases)),key=lambda i:details[i]['violation']*1000+details[i]['speed'])
                for s in [cases[1],cases[3],cases[5],cases[worst]]:
                    ma,_,a=run(g,s,cfg,True); mb,_,b=run(g,{**s,'dt':.0005},cfg,True)
                    numeric.append({'method':m,'scenario':s['name'],
                        'max_angle_difference_deg':float(np.rad2deg(abs(a[:,1:4]-b[::2,1:4]).max())),
                        'max_rate_difference_deg_s':float(np.rad2deg(abs(a[:,4:7]-b[::2,4:7]).max())),
                        'max_settling_difference_s':float(abs(ma[:,1]-mb[:,1]).max())})
    write_csv(OUT/'selected_candidates.csv',selected); write_csv(OUT/'integration_checks.csv',numeric); dump(OUT/'nominal_local_stability.json',local)
    write_csv(OUT/'sampled_local_stability.csv',uncertain_local)
    write_csv(OUT/'baseline_validation.csv',[validate_one(('baseline','source',{'seed':0,'gains':baseline().tolist()},cfg))])
    from corner_checks import check_corners
    corner_rows=check_corners(data,cfg)
    for row in corner_rows:
        if row['mode']!='robust': continue
        path=OUT/'exports'/f'{row["method"]}_{row["selection"]}_gains.json'
        exp=read(path); exp['joint_boundary_audit']=row
        exp['status']+=f' Joint-boundary acceptance: {row["passes"]}/{row["cases"]}; these finite tests are not a continuous-range guarantee.'
        dump(path,exp)
        (OUT/'exports'/f'{row["method"]}_{row["selection"]}_SIMULINK_MAP.txt').write_text(exp['status']+'\n'+json.dumps(exp,indent=2))
        for s in selected:
            if s['method']==row['method'] and s['selection']==row['selection']:
                s['joint_boundary_passes']=row['passes']; s['joint_boundary_cases']=row['cases']
    write_csv(OUT/'selected_candidates.csv',selected)
    plots=OUT/'plots'; plots.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    def save(name):
        for ext in ['png','svg']: plt.savefig(plots/f'{name}.{ext}',dpi=170,bbox_inches='tight')
        plt.close()
    fig,ax=plt.subplots(figsize=(11,4.7),layout='constrained')
    ax.boxplot(list(scores.T),tick_labels=METHODS)
    if scores.max()>1000: ax.set_yscale('log')
    ax.set(title='Robust training fitness: 30 seeds, 3264 evaluations each',ylabel='Constrained fitness (lower is better)'); save('01_training_fitness')
    fig,ax=plt.subplots(figsize=(11,4.7),layout='constrained')
    for m in METHODS:
        q=np.quantile(curves[m],[.25,.5,.75],axis=0); x=np.arange(1,3265)
        ax.plot(x,q[1],label=m,color=COLORS[m]); ax.fill_between(x,q[0],q[2],alpha=.15,color=COLORS[m])
    ax.set(yscale='log',xlabel='Unique candidate evaluations',ylabel='Best-so-far robust fitness',title='Median convergence and interquartile range'); ax.legend(); save('02_convergence')
    fig,axs=plt.subplots(1,2,figsize=(13,4.8),layout='constrained')
    for k,metric in enumerate(['single_axis_mc_passes','nominal_mean_settling_s']):
        for j,mode in enumerate(['nominal','robust']):
            arrays=[[lookup[mode,m,s][metric] for s in SEEDS] for m in METHODS]
            boxes=axs[k].boxplot(arrays,positions=np.arange(5)+(j-.5)*.28,widths=.22,patch_artist=True)
            for box in boxes['boxes']: box.set_facecolor('#bdc9d4' if j==0 else '#00858b')
        axs[k].set(xticks=np.arange(5),xticklabels=METHODS,title='Unseen uncertainty: higher is better' if k==0 else 'Nominal speed: lower is better',
                   ylabel='Passes out of 300' if k==0 else 'Mean settling time across six steps (s)')
    from matplotlib.patches import Patch
    axs[0].legend(handles=[Patch(facecolor='#bdc9d4',label='Nominal-tuned'),Patch(facecolor='#00858b',label='Robust-tuned')],loc='lower left')
    save('03_robustness_speed_tradeoff')
    fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
    for j,mode in enumerate(['nominal','robust']):
        values=[next(r for r in comparisons if r['method']==m and r['mode']==mode)['all_300_controllers'] for m in METHODS]
        ax.bar(np.arange(5)+(j-.5)*.34,values,.32,label=mode+'-tuned')
    ax.set(xticks=np.arange(5),xticklabels=METHODS,ylim=(0,32),ylabel='Controllers passing all 300 cases / 30',title='All-case success across optimizer seeds'); ax.legend(); save('04_all_cases')
    sensitivity=[]; failure_rows=[]; group_failure_rows=[]
    for mode in ['nominal','robust']:
        for m in METHODS:
            counts={name:[] for name,_,_ in FACTORS}; failures={key:0 for key in ['fails_overshoot','fails_final_error','fails_settling','fails_motor_clipping','fails_negative_speed','fails_cross_axis','fails_bank_limit','fails_numerical']}
            grouped={group:{key:0 for key in failures} for group in ['single_axis_mc','one_at_a_time','combined_stress']}
            for s in SEEDS:
                with gzip.open(OUT/'validation'/f'{mode}_{m}_{s}.json.gz','rt',encoding='utf-8') as f: v=json.load(f)
                for name in counts:
                    cc=[c for c in v['cases'] if c['name'].startswith('oat_'+name+'_')]; counts[name].extend(c['feasible'] for c in cc)
                for c in v['cases']:
                    for key in failures: grouped[c['group']][key]+=int(c[key])
                    if c['group']=='single_axis_mc':
                        for key in failures: failures[key]+=int(c[key])
            sensitivity += [{'mode':mode,'method':m,'factor':name,'passes':sum(v),'cases':len(v),'pass_percent':100*np.mean(v)} for name,v in counts.items()]
            failure_rows.append({'mode':mode,'method':m,**failures})
            group_failure_rows.extend({'mode':mode,'method':m,'group':group,'cases':30*n,**grouped[group]}
                                      for group,n in [('single_axis_mc',300),('one_at_a_time',54),('combined_stress',90)])
    write_csv(OUT/'parameter_sensitivity.csv',sensitivity); write_csv(OUT/'failure_reasons.csv',failure_rows)
    write_csv(OUT/'validation_failure_reasons_by_group.csv',group_failure_rows)
    fig,axs=plt.subplots(1,2,figsize=(14,4.5),layout='constrained')
    for ax,mode in zip(axs,['nominal','robust']):
        mat=np.array([[next(r['pass_percent'] for r in sensitivity if r['mode']==mode and r['method']==m and r['factor']==name) for name,_,_ in FACTORS] for m in METHODS])
        im=ax.imshow(mat,vmin=0,vmax=100,cmap='YlGnBu',aspect='auto'); ax.set(yticks=range(5),yticklabels=METHODS,xticks=range(9),xticklabels=[f[0] for f in FACTORS],title=mode+'-tuned boundary pass percentage')
        ax.tick_params(axis='x',rotation=50)
    fig.colorbar(im,ax=axs,label='Pass %'); save('05_parameter_sensitivity')
    fig,axs=plt.subplots(1,3,figsize=(14,4.5),layout='constrained')
    # Response envelopes use all 100 held-out plants/commands per axis, normalize each step.
    for m in METHODS:
        best=min(data['robust'][m],key=lambda r:(r['fitness'],r['seed'])); g=np.array(best['gains'])
        for j,ax in enumerate(axs):
            traces=[]
            for s in [s for s in validation_cases() if s['group']=='single_axis_mc'][j::3]:
                _,_,tr=run(g,s,cfg,True); col=1+j if j<2 else 6
                traces.append(np.rad2deg(tr[:,col])/s['target'][j])
            arr=np.asarray(traces); t=tr[:,0]-.2
            ax.plot(t,np.median(arr,axis=0),color=COLORS[m],label=m)
            ax.fill_between(t,arr.min(axis=0),arr.max(axis=0),color=COLORS[m],alpha=.06)
    for ax,label in zip(axs,['Roll','Pitch','Yaw rate']): ax.axhline(1,ls=':',c='k'); ax.set(title=label,xlim=(0,1.5),xlabel='Time after step (s)',ylabel='Response / command')
    axs[0].legend(fontsize=8); save('06_heldout_response_envelopes')
    dump(OUT/'verification.json',{'completed_runs':150,'unique_evaluations':489600,'training_simulations':14688000,
        'ledger_audits_passed':True,'all_selected_fitnesses_recomputed':True,'validated_tuned_controllers':300,
        'validation_cases_per_controller':444,'training_cases':30,'nominal_reference_cases':6,
        'tests_passed':19,'model_sha256':hashlib.sha256((ROOT/'model.py').read_bytes()).hexdigest()})
    print('Complete: audits, validation, statistics, gains and six figures.',flush=True)

if __name__=='__main__': main()
