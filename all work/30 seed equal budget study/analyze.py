"""Analyze completed runs; validate every seed winner without selecting on validation."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
import json,hashlib,csv
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from benchmark import METHODS,SEEDS,ROOT
from model import baseline,NOMINAL,coefficients,run
from study import evaluate,training_scenarios,validation_scenarios,metric_rows,write_csv
from linear_analysis import local_analysis

COLORS={'GA':'#45658b','PSO':'#cb861c','CSO':'#b54d70','DSA':'#00858b','CMA-ES':'#794aad'}

def uncertainty_cases():
    rng=np.random.default_rng(20261004); cases=[]
    for i in range(90):
        p=NOMINAL.copy(); p[:3]*=rng.uniform(.85,1.15,3); p[10]*=rng.uniform(.7,1.3)
        p[4:6]*=rng.uniform(.9,1.1,2); p[6:9]*=rng.uniform(.7,1.3,3)
        s={'name':f'mc_{i:03d}','target':[float(rng.choice([-1,1])*rng.uniform(5,18)),float(rng.choice([-1,1])*rng.uniform(5,15)),float(rng.choice([-1,1])*rng.uniform(20,70))],
           'plant':p.tolist(),'throttle':float(rng.uniform(.54,.68)),
           'group':'single_axis_uncertainty' if i<60 else 'combined_axis_stress'}
        if i<60: s['target']=[v if j==i%3 else 0. for j,v in enumerate(s['target'])]
        cases.append(s)
    return cases

def main():
    out=ROOT/'results'; contract=json.loads((out/'contract.json').read_text()); cfg=contract['configuration']; budget=contract['budget']
    plots=out/'plots'; plots.mkdir(exist_ok=True); exports=out/'exports'; exports.mkdir(exist_ok=True)
    data={m:[json.loads((out/'runs'/f'{m}_{s}.json').read_text()) for s in SEEDS] for m in METHODS}
    curves={m:[] for m in METHODS}; audits=[]
    for idx,seed in enumerate(SEEDS):
        assert len({data[m][idx]['initial_population_sha256'] for m in METHODS})==1
        initial_ledgers=[]
        for m in METHODS:
            r=data[m][idx]; ledger=np.load(out/'runs'/f'{m}_{seed}_evaluations.npz')['ledger']
            assert len(ledger)==r['unique_evaluations']==budget
            assert np.array_equal(ledger[:,0],np.arange(1,budget+1))
            assert np.all(np.diff(ledger[:,3])<=0) and abs(ledger[:,2].min()-r['fitness'])<1e-12
            assert np.all((ledger[:,4:]>=0)&(ledger[:,4:]<=1))
            assert len({tuple(np.round(x,13)) for x in ledger[:,4:]})==budget
            initial_ledgers.append(ledger[:64]); curves[m].append(ledger[:,3])
        for a in initial_ledgers[1:]: np.testing.assert_allclose(a,initial_ledgers[0],rtol=0,atol=0)
    scores=np.array([[data[m][i]['fitness'] for m in METHODS] for i in range(30)])
    ranks=stats.rankdata(scores,axis=1); rng=np.random.default_rng(7102026); draws=rng.integers(0,30,(10000,30))
    summary=[]; allruns=[]
    for j,m in enumerate(METHODS):
        a=scores[:,j]; means=a[draws].mean(axis=1); medians=np.median(a[draws],axis=1)
        summary.append({'method':m,'best':float(a.min()),'median':float(np.median(a)),'mean':float(a.mean()),'std':float(a.std(ddof=1)),
            'q1':float(np.quantile(a,.25)),'q3':float(np.quantile(a,.75)),'worst':float(a.max()),'feasible_runs':int(np.sum(a<1000)),
            'mean_ci95_low':float(np.quantile(means,.025)),'mean_ci95_high':float(np.quantile(means,.975)),
            'median_ci95_low':float(np.quantile(medians,.025)),'median_ci95_high':float(np.quantile(medians,.975)),
            'mean_paired_rank':float(ranks[:,j].mean()),'budget_per_run':budget})
        allruns += [{k:r[k] for k in ['method','seed','fitness','unique_evaluations','last_iteration','seconds']} for r in data[m]]
    write_csv(out/'summary.csv',summary); write_csv(out/'all_runs.csv',allruns)
    # Use a within-seed permutation calibration; five methods is a small number for chi-square approximation.
    obs=float(np.sum(ranks.sum(axis=0)**2)); count=0; permutations=20000
    for _ in range(20):
        order=np.argsort(rng.random((1000,30,5)),axis=2)
        perm=np.take_along_axis(np.broadcast_to(ranks,(1000,30,5)),order,axis=2)
        val=np.sum(perm.sum(axis=1)**2,axis=1); count+=int(np.sum(val>=obs-1e-9))
    friedman=stats.friedmanchisquare(*[scores[:,j] for j in range(5)])
    pairs=[]
    for i,j in combinations(range(5),2):
        delta=np.round(scores[:,i]-scores[:,j],12)
        p=1. if not np.any(delta) else float(stats.wilcoxon(delta,alternative='two-sided',method='auto').pvalue)
        boot=delta[draws].mean(axis=1)
        pairs.append({'A':METHODS[i],'B':METHODS[j],'mean_A_minus_B':float(delta.mean()),'median_A_minus_B':float(np.median(delta)),
            'A_wins':int(np.sum(delta< -1e-10)),'ties':int(np.sum(abs(delta)<=1e-10)),'B_wins':int(np.sum(delta>1e-10)),
            'wilcoxon_p':p,'mean_difference_ci95_low':float(np.quantile(boot,.025)),'mean_difference_ci95_high':float(np.quantile(boot,.975))})
    order=np.argsort([p['wilcoxon_p'] for p in pairs]); prev=0
    for rank,idx in enumerate(order):
        prev=max(prev,min(1.,pairs[idx]['wilcoxon_p']*(len(pairs)-rank)))
        pairs[idx]['holm_p']=prev; pairs[idx]['holm_significant_0.05']=bool(prev<.05)
    write_csv(out/'paired_comparisons.csv',pairs)
    statistics={'friedman_statistic':float(friedman.statistic),'friedman_asymptotic_p':float(friedman.pvalue),
                'within_seed_permutation_p':(count+1)/(permutations+1),'permutations':permutations,
                'bootstrap_resamples':10000,'bootstrap_seed':7102026,'paired':True,
                'caveat':'Inference concerns optimizer randomness on this one fixed problem. Wilcoxon uses symmetric paired-difference null; intervals are descriptive percentile bootstrap and not multiplicity-adjusted.'}
    (out/'statistics.json').write_text(json.dumps(statistics,indent=2))
    train=training_scenarios(); held=validation_scenarios(); mc=uncertainty_cases()
    (out/'scenarios.json').write_text(json.dumps({'training':train,'held_out':held,'monte_carlo':mc},indent=2))
    validation=[]
    def validate(task):
        m,r=task; g=np.array(r['gains']); score=evaluate(g,train,cfg)
        assert abs(score-r['fitness'])<1e-11
        _,details=evaluate(g,held+mc,cfg,True)
        return {'method':m,'seed':r['seed'],'training_fitness':score,
                'held_out_passes':sum(z['feasible'] for z in details[:18]),
                'single_axis_passes':sum(z['feasible'] for z in details[18:78]),
                'combined_passes':sum(z['feasible'] for z in details[78:]),
                'details':details}
    validate_dir=out/'validation'; validate_dir.mkdir(exist_ok=True)
    tasks=[(m,r) for m in METHODS for r in data[m]]
    pending=[t for t in tasks if not (validate_dir/f'{t[0]}_{t[1]["seed"]}.json').exists()]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i,v in enumerate(pool.map(validate,pending)):
            (validate_dir/f'{v["method"]}_{v["seed"]}.json').write_text(json.dumps(v,indent=2))
            if i%10==0: print(f'Validated {i+1}/{len(pending)} pending candidates',flush=True)
    for m,r in tasks:
        v=json.loads((validate_dir/f'{m}_{r["seed"]}.json').read_text()); validation.append({k:v[k] for k in ['method','seed','training_fitness','held_out_passes','single_axis_passes','combined_passes']})
    write_csv(out/'validation_summary.csv',validation)
    selected=[]; met=[]; best_gains={}; numcheck=[]; stability={}
    for m in METHODS:
        runs=sorted(data[m],key=lambda r:(r['fitness'],r['seed'])); target=np.median([r['fitness'] for r in runs])
        reps={'best':runs[0],'median_representative':min(runs,key=lambda r:(abs(r['fitness']-target),r['seed']))}
        for kind,r in reps.items():
            g=np.array(r['gains']); v=next(v for v in validation if v['method']==m and v['seed']==r['seed'])
            exp={'method':m,'selection':kind,'seed':r['seed'],'training_fitness':r['fitness'],
                 'gains':dict(zip([p['name'] for p in cfg['parameters']],g.tolist())),
                 'transfer_functions':coefficients(g,cfg['controller_dt_s'],cfg['fixed_discrete_pole']),
                 'yaw':{'Kp':float(g[6]),'Ki':float(g[7]),'Kd':0.},'validation':v,
                 'status':'Python-model candidate; assumed controller timing 1 ms and mixer timing 4 ms; not verified in Simulink.'}
            (exports/f'{m}_{kind}_gains.json').write_text(json.dumps(exp,indent=2))
            (exports/f'{m}_{kind}_SIMULINK_MAP.txt').write_text('\n'.join([exp['status'],f'Selection: {kind}; seed {r["seed"]}',
                f'Roll outer gain: {g[0]:.17g}',f'Pitch outer gain: {g[3]:.17g}',
                'Roll Discrete Transfer Fcn: '+json.dumps(exp['transfer_functions']['roll']),
                'Pitch Discrete Transfer Fcn: '+json.dumps(exp['transfer_functions']['pitch']),
                'Yaw PI: '+json.dumps(exp['yaw']),'Keep the source saturation locations, limits and forward-Euler yaw integrator.']),encoding='utf-8')
            selected.append({'method':m,'selection':kind,'seed':r['seed'],'fitness':r['fitness'],**{k:v[k] for k in ['single_axis_passes','combined_passes','held_out_passes']}})
            if kind=='best':
                best_gains[m]=g; rr,_=metric_rows(g,train+held,cfg,m); met+=rr; stability[m]=local_analysis(g,cfg)
                for s in [train[1],train[3],train[5]]:
                    _,_,a=run(g,s,cfg,True); _,_,b=run(g,{**s,'dt':.0005},cfg,True)
                    err=np.rad2deg(np.max(abs(a[:,1:7]-b[::2,1:7]),axis=0))
                    numcheck.append({'method':m,'scenario':s['name'],'angle_error_deg':float(err[:3].max()),'rate_error_deg_s':float(err[3:].max())})
    write_csv(out/'selected_candidates.csv',selected); write_csv(out/'best_metrics.csv',met); write_csv(out/'numerical_checks.csv',numcheck)
    (out/'local_stability.json').write_text(json.dumps(stability,indent=2))
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    def save(name):
        for ext in ['png','svg']: plt.savefig(plots/f'{name}.{ext}',dpi=180,bbox_inches='tight')
        plt.close()
    fig,ax=plt.subplots(figsize=(12,5),layout='constrained'); ax.boxplot([scores[:,i] for i in range(5)],tick_labels=METHODS,showfliers=False)
    jitter=np.random.default_rng(2)
    for i,m in enumerate(METHODS): ax.scatter(i+1+jitter.uniform(-.15,.15,30),scores[:,i],color=COLORS[m],alpha=.75,s=25)
    ax.set(ylabel='Final constrained fitness (lower is better)',title=f'30 seeds per method | exactly {budget} unique evaluations')
    if scores.max()>1: ax.set_yscale('log')
    save('01_fitness_distributions')
    fig,axs=plt.subplots(1,2,figsize=(13,4.6),layout='constrained')
    for m in METHODS:
        a=np.array(curves[m]); x=np.arange(1,budget+1); q=np.quantile(a,[.25,.5,.75],axis=0)
        for ax in axs: ax.plot(x,q[1],color=COLORS[m],label=m); ax.fill_between(x,q[0],q[2],color=COLORS[m],alpha=.12)
    axs[0].set(yscale='log',xlabel='Unique evaluations',ylabel='Best-so-far fitness',title='Median and interquartile range')
    axs[1].set(xlim=(500,budget),ylim=(.045,.14),xlabel='Unique evaluations',ylabel='Best-so-far fitness',title='Feasible-score detail (fixed display range)'); axs[0].legend()
    save('02_convergence')
    fig,ax=plt.subplots(figsize=(11,4.8),layout='constrained')
    ax.boxplot([[v['single_axis_passes'] for v in validation if v['method']==m] for m in METHODS],tick_labels=METHODS,showfliers=True)
    for i,m in enumerate(METHODS): ax.scatter(i+1+jitter.uniform(-.15,.15,30),[v['single_axis_passes'] for v in validation if v['method']==m],color=COLORS[m],alpha=.6,s=18)
    ax.set(ylabel='Passes out of 60 uncertainty cases',ylim=(-1,62),title='Held-out performance of all 150 selected controllers'); save('03_robustness')
    fig,axs=plt.subplots(2,3,figsize=(14,7),layout='constrained')
    for ax,s in zip(axs.flat,train):
        j=int(np.flatnonzero(s['target'])[0]); col=1+j if j<2 else 6
        for m,g in {'baseline':baseline(),**best_gains}.items():
            _,_,tr=run(g,s,cfg,True); ax.plot(tr[:,0]-.2,np.rad2deg(tr[:,col]),label=m,color=COLORS.get(m,'#777'),lw=1.5)
        ax.axhline(s['target'][j],ls=':',color='k'); ax.set(title=s['name'],xlabel='Time after step (s)',ylabel='deg' if j<2 else 'deg/s',xlim=(-.02,1.))
    axs[0,0].legend(fontsize=8,ncol=2); save('04_best_responses')
    robustsummary=[]
    for m in METHODS:
        vv=[v for v in validation if v['method']==m]; a=np.array([v['single_axis_passes'] for v in vv])
        robustsummary.append({'method':m,'median_single_axis_passes':float(np.median(a)),'min_single_axis_passes':int(a.min()),'max_single_axis_passes':int(a.max()),
            'controllers_passing_all_60':int(np.sum(a==60)), 'total_combined_passes_out_of_900':sum(v['combined_passes'] for v in vv)})
    write_csv(out/'robustness_summary.csv',robustsummary)
    def table(rr,keys=None):
        keys=keys or list(rr[0]); return '<div class="scroll"><table><tr>'+''.join('<th>'+k+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+ (f'{r[k]:.7g}' if isinstance(r[k],float) else str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rr)+'</table></div>'
    winner=min(summary,key=lambda x:x['median'])['method']
    html=f'''<!doctype html><html><meta charset="utf-8"><title>30-seed equal-budget benchmark</title><style>body{{font:16px Segoe UI,sans-serif;max-width:1250px;margin:40px auto;color:#193749;line-height:1.6}}table{{border-collapse:collapse;font-size:13px;width:100%}}td,th{{padding:8px;border-bottom:1px solid #ddd;text-align:left}}th{{background:#edf3f7}}img{{max-width:100%}}.scroll{{overflow:auto}}</style>
    <h1>Five methods, 30 seeds, equal evaluation budget</h1><p><b>Completed: 150 runs × {budget} = {150*budget:,} unique training objective evaluations.</b> Each fitness evaluation simulates six training cases. All initial populations match within seed; the original controller is included.</p>
    <h2>Conclusion</h2><p>{winner} has the lowest median final fitness in this benchmark. Rank methods by the full distribution, not the best seed alone. Statistical comparisons concern these settings and this single model, not general superiority. Validation is reported separately and did not select gains.</p>
    <p>GA mutation and PSO inertia now decrease with consumed evaluation budget. Other hyperparameters retain the previous settings. Final batches are stopped exactly at the cap. No padding, retrospective budget truncation or reuse of previous optimized controllers.</p>
    <h2>Final fitness across 30 seeds</h2>{table(summary)}<img src="plots/01_fitness_distributions.png"><img src="plots/02_convergence.png">
    <h2>Paired analysis</h2><p>Friedman statistic={statistics['friedman_statistic']:.6g}; within-seed permutation p={statistics['within_seed_permutation_p']:.6g} (20,000 permutations). All ten pairwise two-sided Wilcoxon tests use Holm correction. Negative A-minus-B favors A. Bootstrap intervals use 10,000 paired seed resamples; intervals are not multiplicity-adjusted. Wilcoxon assumes a symmetric paired-difference null.</p>{table(pairs)}
    <h2>Validation of all 150 seed winners</h2>{table(robustsummary)}<img src="plots/03_robustness.png"><p>Each controller receives the same 18 deterministic hold-outs, 60 single-axis uncertainty cases and 30 combined-axis stress cases. Counts across these fixed synthetic scenarios are descriptive; they are not independent hardware success probabilities. No new uncertainty-focused optimization or hyperparameter search is mixed into the main comparison.</p>
    <h2>Selected best and median-representative candidates</h2>{table(selected)}<p>Best means minimum training fitness. Median representative is an actual run closest to the method median, with seed as tie-breaker. Both exports are retained, including any validation failures. The best-of-30 result is a selected extreme, not typical performance.</p><img src="plots/04_best_responses.png">
    <h2>Implementation limits</h2><p>Same source nonlinear rotation/motor model, saturations and eight bounds as the earlier work. Controller timing remains assumed at 1 ms, mixer 4 ms. Roll/pitch coefficients parameterize the source discrete controller; yaw regulates rate, not heading. Negative motor speed is a feasibility violation. Compiled Simulink trace validation remains necessary.</p>
    <h2>Reproducibility</h2><p>contract.json freezes code hashes, seeds, budget and configuration. runs/ contains all 150 ledgers (NPZ: evaluation, iteration, fitness, best-so-far, eight normalized gains) and JSON summaries. exports/ contains best and median gains plus parameter maps. validation/ retains every assessed case. Read README.md for exact protocol.</p>
    <p>Statistical references: <a href="https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.friedmanchisquare.html">SciPy Friedman</a>; <a href="https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html">SciPy Wilcoxon</a>. Optimizer definitions and primary links are recorded in README.md.</p></html>'''
    (out/'REPORT.html').write_text(html,encoding='utf-8')
    verification={'runs':150,'unique_evaluations_per_run':budget,'total_unique_evaluations':150*budget,'all_initial_populations_and_scores_match':True,
                  'all_ledgers_have_exact_budget_and_unique_keys':True,'all_exported_fitnesses_recomputed':True,'best_archive_monotonic':True,
                  'main_median_winner':winner,'statistics':statistics}
    (out/'verification.json').write_text(json.dumps(verification,indent=2))
    print(json.dumps(verification,indent=2),flush=True)

if __name__=='__main__': main()
