"""Independent audit, held-out validation, exports and inferential statistics.

Run after run_extension.py. --validate-available can populate caches during a run.
No validation outcome selects search parameters or controller candidates.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
import argparse, gzip, hashlib, json, csv
import numpy as np
from scipy import stats
from methods import METHODS, SEEDS, PILOT_SEEDS, parameter_grid
from robust_protocol import training_cases, validation_cases
from study import decode, write_csv, evaluate, training_scenarios, validation_scenarios, metric_rows
from model import baseline, coefficients, run
from analyze_robust import validate_one, paired, holm, summary_stats
from corner_checks import check_corners
from linear_analysis import local_analysis

R=Path(__file__).resolve().parent
OUT=R/'results'
OLD=['GA','PSO','CSO','DSA','CMA-ES']
MODES=['nominal','robust']
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,v): Path(p).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def old_folder(mode):
    return R/'reference_benchmark'/mode/'runs'
def selected(rr):
    ordered=sorted(rr,key=lambda r:(r['fitness'],r['seed']))
    med=float(np.median([r['fitness'] for r in ordered]))
    return [('best',ordered[0]),('median',min(ordered,key=lambda r:(abs(r['fitness']-med),r['seed'])))]
def get_data():
    return {mode:{m:[read(OUT/mode/'runs'/f'{m}_{s}.json') for s in SEEDS] for m in METHODS} for mode in MODES}

def audit(data,cfg):
    contract=read(OUT/'contract.json')
    for name,h in contract['code_sha256'].items():
        assert hashlib.sha256((R/name).read_bytes()).hexdigest()==h, name
    for ref in read(R/'reference_benchmark/manifest.json'):
        assert hashlib.sha256((R/ref['snapshot']).read_bytes()).hexdigest()==ref['sha256']
    settings=read(OUT/'selected_parameters.json'); reference={}; count=0;diagnostics=[]
    pilot_count=0; pilot_selection=[]
    for m in METHODS:
        scores=[]
        for mode in MODES:
            for s in PILOT_SEEDS:
                block=[]
                for cid,params in enumerate(parameter_grid(m)):
                    folder=OUT/'pilot'/f'candidate_{cid}'/mode
                    r=read(folder/f'{m}_{s}.json');a=np.load(folder/f'{m}_{s}_evaluations.npz')['ledger']
                    assert r['method']==m and r['seed']==s and r['parameters']==params
                    assert len(a)==r['unique_evaluations']==3264 and np.isfinite(a).all()
                    assert np.all((a[:,4:]>=0)&(a[:,4:]<=1))
                    assert len({tuple(np.round(x,13)) for x in a[:,4:]})==3264
                    np.testing.assert_allclose(a[:,3],np.minimum.accumulate(a[:,2]),rtol=0,atol=1e-13)
                    assert abs(a[:,2].min()-r['fitness'])<1e-12
                    np.testing.assert_allclose(decode(a[np.argmin(a[:,2]),4:],cfg),r['gains'],rtol=1e-13,atol=1e-15)
                    block.append(r['fitness']);pilot_count+=1
                scores.append(block)
        rank=stats.rankdata(np.asarray(scores),axis=1).mean(axis=0);winner=int(np.argmin(rank))
        assert settings[m]==parameter_grid(m)[winner]
        pilot_selection.append({'method':m,'selected_candidate':winner,'mean_ranks':rank.tolist(),'ties_for_first':int(np.sum(abs(rank-rank.min())<1e-12))})
    for mode in MODES:
        for m in METHODS:
            for r in data[mode][m]:
                s=r['seed']; a=np.load(OUT/mode/'runs'/f'{m}_{s}_evaluations.npz')['ledger']
                events=np.load(OUT/mode/'runs'/f'{m}_{s}_evaluations.npz')['transitions']
                assert r['method']==m and r['parameters']==settings[m]
                assert len(a)==r['unique_evaluations']==3264
                np.testing.assert_array_equal(a[:,0],np.arange(1,3265))
                assert np.isfinite(a).all() and np.all((a[:,4:]>=0)&(a[:,4:]<=1))
                assert len({tuple(np.round(x,13)) for x in a[:,4:]})==3264
                np.testing.assert_allclose(a[:,3],np.minimum.accumulate(a[:,2]),rtol=0,atol=1e-13)
                assert abs(a[:,2].min()-r['fitness'])<1e-12
                np.testing.assert_allclose(decode(a[np.argmin(a[:,2]),4:],cfg),r['gains'],rtol=1e-13,atol=1e-15)
                assert r['last_iteration']==r['proposals_including_final_batch']-64
                assert len(events)==r['last_iteration']-1
                np.testing.assert_array_equal(events[1:,1],events[:-1,3])
                assert events[0,1]==float(a[:64,2].min())
                take=events[:,4].astype(bool)
                np.testing.assert_array_equal(events[:,3],np.where(take,events[:,2],events[:,1]))
                expected=(events[:,2]<=events[:,1]) | (np.log1p(events[:,2])<=events[:,5]) if m=='GDA' else (
                    np.log1p(events[:,2])<=np.log1p(events[:,1])+events[:,5] if m in ['TA','ALNS'] else (
                    np.ones(len(events),dtype=bool) if m=='PRW' else events[:,2]<events[:,1]))
                expected=expected | events[:,8].astype(bool)
                np.testing.assert_array_equal(take,expected)
                assert int(take.sum())==r['accepted_moves_before_final_evaluation']
                assert 0<=r['restarts']-int(events[:,8].sum())<=1
                if m=='PRW' and r['proposals_including_final_batch']==3264:
                    trajectory=np.vstack([a[np.argmin(a[:64,2]),4:],a[64:,4:]])
                    steps=np.linalg.norm(np.diff(trajectory,axis=0),axis=1);size=r['parameters']['step']
                    assert np.all(steps<=size+1e-12)
                    interior=np.all((trajectory[:-1]>=size)&(trajectory[:-1]<=1-size),axis=1)
                    np.testing.assert_allclose(steps[interior],size,rtol=0,atol=1e-12)
                if s not in reference: reference[s]=a[:64,4:].copy()
                np.testing.assert_array_equal(a[:64,4:],reference[s])
                previous=read(old_folder(mode)/f'GA_{s}.json')
                assert previous['initial_population_sha256']==r['initial_population_sha256']
                hits=np.flatnonzero(a[:,2]<1000)
                diagnostics.append({'mode':mode,'method':m,'seed':s,'unique_evaluations':len(a),
                    'iterations':r['last_iteration'],'proposals':r['proposals_including_final_batch'],
                    'cached_proposals':r['proposals_including_final_batch']-len(a),'seconds':r['seconds'],
                    'initial_best_fitness':float(a[:64,2].min()),'final_best_fitness':r['fitness'],
                    'first_feasible_evaluation':int(hits[0]+1) if len(hits) else None,
                    'incumbent_improvements_after_initialization':int(np.sum(np.diff(a[63:,3])<0)),
                    'accepted_moves_before_final_evaluation':r['accepted_moves_before_final_evaluation'],'restarts':r['restarts'],
                    'final_destroy_weights':json.dumps(r.get('final_destroy_weights')),
                    'final_repair_weights':json.dumps(r.get('final_repair_weights'))})
                count+=1
    write_csv(OUT/'search_diagnostics.csv',diagnostics)
    dump(OUT/'audit.json',{'passed':True,'runs':count,'evaluations':count*3264,'pilot_runs':pilot_count,'pilot_evaluations':pilot_count*3264,'independently_recomputed_parameter_selection':pilot_selection,
        'checks':['frozen code hashes','exact unique evaluation budget','finite values and gain bounds',
                  'best-so-far archive','decoded gains','paired initialization identical to original benchmark',
                  'acceptance transition replay','PRW accepts every move and fixed proposal length away from reflected boundaries']})

def validation(cfg,workers):
    (OUT/'validation').mkdir(exist_ok=True); tasks=[]
    for mode in MODES:
        for m in METHODS:
            for s in SEEDS:
                p=OUT/mode/'runs'/f'{m}_{s}.json'
                if p.exists(): tasks.append((mode,m,read(p),cfg))
    tasks.append(('baseline','baseline',{'seed':0,'gains':baseline().tolist()},cfg))
    rows=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i,row in enumerate(pool.map(validate_one,tasks)):
            rows.append(row)
            if (i+1)%20==0: print(f'Validated {i+1}/{len(tasks)} controllers',flush=True)
    write_csv(OUT/'validation_summary.csv',rows)
    return rows

def comparison_statistics(data,lookup):
    rng=np.random.default_rng(12102026); draws=rng.integers(0,30,(10000,30))
    summaries=[]; tests=[]; pairrows=[]; allsummary=[]
    for scope,methods in [('new_six',METHODS),('exploratory_eleven',OLD+METHODS)]:
        for mode in MODES:
            scores=np.array([[data[mode][m][i]['fitness'] if m in METHODS else read(old_folder(mode)/f'{m}_{s}.json')['fitness'] for m in methods] for i,s in enumerate(SEEDS)])
            ranks=stats.rankdata(scores,axis=1); obs=float(np.sum(ranks.sum(axis=0)**2)); count=0
            for _ in range(20):
                perm=np.argsort(rng.random((1000,30,len(methods))),axis=2)
                pr=np.take_along_axis(np.broadcast_to(ranks,(1000,30,len(methods))),perm,axis=2)
                count+=int(np.sum(np.sum(pr.sum(axis=1)**2,axis=1)>=obs-1e-9))
            f=stats.friedmanchisquare(*scores.T)
            tests.append({'scope':scope,'mode':mode,'friedman_statistic':float(f.statistic),'permutation_p':(count+1)/20001,'permutations':20000})
            pairs=holm([{'scope':scope,'mode':mode,'A':methods[i],'B':methods[j],**paired(scores[:,i],scores[:,j],draws)} for i,j in combinations(range(len(methods)),2)])
            pairrows+=pairs
            for j,m in enumerate(methods):
                row={'scope':scope,'mode':mode,'method':m,**summary_stats(scores[:,j],draws),'mean_rank':float(ranks[:,j].mean()),'training_feasible_runs':int(np.sum(scores[:,j]<1000))}
                allsummary.append(row)
                if scope=='new_six': summaries.append(row)
    write_csv(OUT/'fitness_summary.csv',summaries);write_csv(OUT/'all_eleven_fitness_summary.csv',allsummary)
    write_csv(OUT/'fitness_pairwise.csv',pairrows)
    dump(OUT/'statistics.json',{'tests':tests,'bootstrap_resamples':10000,'seed':12102026,
        'inference':'Across optimization seeds on this single model. Each scope/regime has its own Holm family. Wilcoxon assumes symmetric paired differences. Bootstrap confidence intervals are not multiplicity-adjusted.',
        'exploratory_caveat':'The original five algorithms did not receive the new four-setting development pilot. Equal final evaluation budgets do not imply equal total development effort.'})
    comparisons=[]; changes=[]; heldout=[]
    for m in METHODS:
        for mode in MODES:
            rr=[lookup[mode,m,s] for s in SEEDS]; passes=np.array([r['single_axis_mc_passes'] for r in rr])
            comparisons.append({'method':m,'mode':mode,'median_mc_passes':float(np.median(passes)),
                'mean_mc_passes':float(passes.mean()),'min_mc_passes':int(passes.min()),'all_300_controllers':int(np.sum(passes==300)),
                'mean_mc_pass_ci95_low':float(np.quantile(passes[draws].mean(axis=1),.025)),
                'mean_mc_pass_ci95_high':float(np.quantile(passes[draws].mean(axis=1),.975)),
                'median_boundary_passes':float(np.median([r['one_at_a_time_passes'] for r in rr])),
                'all_54_boundary_controllers':sum(r['one_at_a_time_passes']==54 for r in rr),
                'median_combined_passes':float(np.median([r['combined_stress_passes'] for r in rr])),
                'all_90_combined_controllers':sum(r['combined_stress_passes']==90 for r in rr),
                'median_nominal_fitness':float(np.median([r['nominal_fitness'] for r in rr])),
                'median_nominal_mean_settling_s':float(np.median([r['nominal_mean_settling_s'] for r in rr])),
                'all_30_training_controllers':sum(r['training_passes']==30 for r in rr)})
        for metric in ['single_axis_mc_passes','nominal_fitness','nominal_mean_settling_s']:
            changes.append({'method':m,'metric':metric,'A':'robust','B':'nominal',**paired([lookup['robust',m,s][metric] for s in SEEDS],[lookup['nominal',m,s][metric] for s in SEEDS],draws)})
    for mode in MODES:
        failures=np.array([[300-lookup[mode,m,s]['single_axis_mc_passes'] for m in METHODS] for s in SEEDS])
        heldout+=holm([{'mode':mode,'A':METHODS[i],'B':METHODS[j],**paired(failures[:,i],failures[:,j],draws)} for i,j in combinations(range(6),2)])
    write_csv(OUT/'nominal_vs_robust.csv',comparisons);write_csv(OUT/'paired_tuning_changes.csv',holm(changes))
    write_csv(OUT/'heldout_failures_pairwise.csv',heldout)
    with (R/'reference_benchmark/nominal_vs_robust.csv').open(encoding='utf-8') as f:previous=list(csv.DictReader(f))
    eleven=[]
    for row in comparisons+previous:
        score=next(r for r in allsummary if r['scope']=='exploratory_eleven' and r['mode']==row['mode'] and r['method']==row['method'])
        keys=['method','mode','median_mc_passes','all_300_controllers','median_boundary_passes','all_54_boundary_controllers','median_combined_passes','median_nominal_mean_settling_s']
        eleven.append({**{k:row[k] for k in keys},'median_training_fitness':score['median'],'training_feasible_runs':score['training_feasible_runs'],
            'additional_development_pilot':row['method'] in METHODS})
    write_csv(OUT/'exploratory_eleven_comparison.csv',eleven)

def supplemental(data):
    physical={s['name']:bool(2*max(s['plant'][:3])<=sum(s['plant'][:3])) for s in validation_cases()}
    rows=[]; failures=[]; boundary=[]
    for mode in MODES:
        for m in data[mode]:
            for r in data[mode][m]:
                with gzip.open(OUT/'validation'/f'{mode}_{m}_{r["seed"]}.json.gz','rt',encoding='utf-8') as f: v=json.load(f)
                for group in ['single_axis_mc','one_at_a_time','combined_stress']:
                    cc=[c for c in v['cases'] if c['group']==group];pp=[c for c in cc if physical[c['name']]]
                    rows.append({'mode':mode,'method':m,'seed':r['seed'],'group':group,'passes':sum(c['feasible'] for c in pp),'cases':len(pp)})
                    failures.append({'mode':mode,'method':m,'seed':r['seed'],'group':group,'cases':len(cc),**{k:sum(c[k] for c in cc) for k in cc[0] if k.startswith('fails_')}})
                for c in v['cases']:
                    if c['group']=='one_at_a_time': boundary.append({'mode':mode,'method':m,'seed':r['seed'],'case':c['name'],'feasible':c['feasible'],'violation':c['violation'],'settling_s':c['max_settling_s']})
    write_csv(OUT/'physical_inertia_subset_runs.csv',rows);write_csv(OUT/'failure_categories.csv',failures);write_csv(OUT/'one_factor_sensitivity.csv',boundary)
    summary=[]
    for mode in data:
        for m in data[mode]:
            for group in ['single_axis_mc','one_at_a_time','combined_stress']:
                rr=[r for r in rows if r['mode']==mode and r['method']==m and r['group']==group]
                summary.append({'mode':mode,'method':m,'group':group,'cases_per_controller':rr[0]['cases'],
                    'median_passes':float(np.median([r['passes'] for r in rr])),
                    'controllers_passing_all':sum(r['passes']==r['cases'] for r in rr),'controllers':len(rr)})
    write_csv(OUT/'physical_inertia_subset_summary.csv',summary)

def export_gains(data,cfg,lookup,corners):
    out=OUT/'exports';out.mkdir(exist_ok=True); allrows=[];chosen=[]
    names=[p['name'] for p in cfg['parameters']]
    for mode in MODES:
        for m in data[mode]:
            for r in data[mode][m]:
                c=coefficients(r['gains']);allrows.append({'mode':mode,'method':m,'seed':r['seed'],'fitness':r['fitness'],**dict(zip(names,r['gains'])),
                    'roll_b0':c['roll']['numerator'][0],'roll_b1':c['roll']['numerator'][1],
                    'pitch_b0':c['pitch']['numerator'][0],'pitch_b1':c['pitch']['numerator'][1],'a0':1.,'a1':-.9997})
            for label,r in selected(data[mode][m]):
                v=lookup[mode,m,r['seed']];corner=next(c for c in corners if c['mode']==mode and c['method']==m and c['selection']==label)
                exp={'mode':mode,'method':m,'selection':label,'seed':r['seed'],'training_fitness':r['fitness'],
                    'gains':dict(zip(names,r['gains'])),'roll_pitch_discrete':coefficients(r['gains']),
                    'yaw_PI':{'Kp':r['gains'][6],'Ki':r['gains'][7]},'validation':v,'joint_boundary_audit':corner,
                    'controller_dt_s':.001,'mixer_dt_s':.004,'selection_rule':'training fitness only; median is nearest actual seed, ties by seed',
                    'status':'Offline Python candidate. Not verified in Simulink, HIL, or flight. Finite uncertainty tests are not a continuous-range guarantee.'}
                dump(out/f'{mode}_{m}_{label}_gains.json',exp)
                (out/f'{mode}_{m}_{label}_SIMULINK_MAP.txt').write_text(json.dumps(exp,indent=2),encoding='utf-8')
                chosen.append({'mode':mode,'method':m,'selection':label,'seed':r['seed'],'fitness':r['fitness'],**dict(zip(names,r['gains'])),
                    'mc_passes':v['single_axis_mc_passes'],'boundary_passes':v['one_at_a_time_passes'],'combined_passes':v['combined_stress_passes'],
                    'corner_passes':corner['passes'],'corner_cases':corner['cases']})
    write_csv(out/'all_runs_gains.csv',allrows);write_csv(OUT/'selected_candidates.csv',chosen)

def stability_numeric(data,cfg):
    numeric=[];local={};uncertain=[]
    plants={tuple(s['plant']) for s in training_cases()+validation_cases() if 'plant' in s and s.get('group')!='combined_stress'}
    for m in data['robust']:
        g=np.asarray(selected(data['robust'][m])[0][1]['gains']);local[m]=local_analysis(g,cfg)
        for i,p in enumerate(sorted(plants)):
            ll=local_analysis(g,cfg,p);uncertain.append({'method':m,'plant_index':i,'plant':json.dumps(p),
                **{axis+'_spectral_radius':ll[axis]['spectral_radius'] for axis in ['roll','pitch','yaw']},
                'all_axes_locally_stable':all(v['locally_stable'] for v in ll.values())})
        cases=training_cases();_,details=evaluate(g,cases,cfg,True)
        worst=max(range(len(cases)),key=lambda i:details[i]['violation']*1000+details[i]['speed'])
        for s in [cases[1],cases[3],cases[5],cases[worst]]:
            ma,da,a=run(g,s,cfg,True);mb,db,b=run(g,{**s,'dt':.0005},cfg,True);bb=b[::2]
            assert a.shape==bb.shape
            finite=bool(np.isfinite(a).all() and np.isfinite(bb).all())
            numeric.append({'method':m,'scenario':s['name'],'finite':finite,'numerical_guard_dt1ms':bool(da[5]),'numerical_guard_dt05ms':bool(db[5]),
                'max_angle_difference_deg':float(np.rad2deg(abs(a[:,1:4]-bb[:,1:4]).max())) if finite else None,
                'max_rate_difference_deg_s':float(np.rad2deg(abs(a[:,4:7]-bb[:,4:7]).max())) if finite else None,
                'max_settling_difference_s':float(abs(ma[:,1]-mb[:,1]).max()) if np.isfinite(ma).all() and np.isfinite(mb).all() else None})
    write_csv(OUT/'integration_checks.csv',numeric);dump(OUT/'nominal_local_stability.json',local);write_csv(OUT/'sampled_local_stability.csv',uncertain)

def additional_diagnostics(data,cfg):
    rows=[];out=OUT/'additional_diagnostics';out.mkdir(exist_ok=True)
    for mode in data:
        for m in data[mode]:
            for label,r in selected(data[mode][m]):
                rr,details=metric_rows(np.asarray(r['gains']),validation_scenarios(),cfg,f'{mode}_{m}_{label}')
                rows.extend(rr)
                with gzip.open(out/f'{mode}_{m}_{label}.json.gz','wt',encoding='utf-8') as f:json.dump(details,f)
    write_csv(OUT/'additional_diagnostics.csv',rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--validate-available',action='store_true');ap.add_argument('--workers',type=int,default=4);args=ap.parse_args()
    cfg=read(OUT/'contract.json')['configuration']
    if args.validate_available: validation(cfg,args.workers);return
    assert read(OUT/'search_complete.json')['complete']
    data=get_data();audit(data,cfg);print('Search audit passed.',flush=True)
    rows=validation(cfg,args.workers);assert len(rows)==361
    lookup={(r['mode'],r['method'],r['seed']):r for r in rows}
    comparison_statistics(data,lookup);supplemental(data)
    corners=check_corners(data,cfg);export_gains(data,cfg,lookup,corners);stability_numeric(data,cfg);additional_diagnostics(data,cfg)
    dump(OUT/'analysis_complete.json',{'complete':True,'controllers':360,'heldout_cases_per_controller':444,'corner_controllers':25,'corner_cases_per_controller':1536})
    print('VALIDATION AND ANALYSIS COMPLETE. Plots, reports and delivery audit remain.',flush=True)
if __name__=='__main__':main()
