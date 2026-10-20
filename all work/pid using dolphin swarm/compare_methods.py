"""DSA versus saved GA/PSO, with an explicit equal-evaluation-budget view."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from model import run
from study import evaluate,training_scenarios,metric_rows,write_csv

ROOT=Path(__file__).resolve().parent

def compare_methods(out,cfg):
    out=Path(out); scenarios=training_scenarios()
    folders={'GA':ROOT/'ga_reference','PSO':ROOT/'pso_reference','CSO':ROOT/'cso_reference','DSA':out}
    keys=['parameters','integration_dt_s','controller_dt_s','mixer_dt_s','pre_step_s','response_horizon_s',
          'settling_band_fraction','minimum_final_hold_s','max_overshoot_fraction','max_final_error_fraction',
          'max_motor_clipping_fraction','minimum_motor_speed_rad_s','fixed_discrete_pole',
          'fitness_weights','worst_case_weight','effort_weight']
    gains={}; summaries=[]; allmetrics=[]; runrows=[]
    colors={'GA':'#64748b','PSO':'#a96c27','CSO':'#bf526c','DSA':'#007f86','DSA_budget':'#6f51a3'}
    for label,folder in folders.items():
        oldcfg=json.loads((folder/'configuration.json').read_text())
        if not all(oldcfg[k]==cfg[k] for k in keys):
            raise ValueError('Problem configuration changed; cannot claim a matched comparison.')
        best=json.loads((folder/'best_gains.json').read_text()); g=np.array(list(best['gains'].values())); gains[label]=g
        score=evaluate(g,scenarios,cfg)
        if abs(score-best['training_fitness'])>1e-10: raise AssertionError(f'{label} saved fitness does not reproduce.')
        rows,_=metric_rows(g,scenarios,cfg,label); allmetrics+=rows
        runs=[json.loads(p.read_text()) for p in sorted(folder.glob('run_main_*.json'))]
        summaries.append({'method':label,'best_fitness':score,'mean_seed_fitness':float(np.mean([r['fitness'] for r in runs])),
                          'std_seed_fitness':float(np.std([r['fitness'] for r in runs])),
                          'min_unique_evaluations':min(r['unique_evaluations'] for r in runs),
                          'max_unique_evaluations':max(r['unique_evaluations'] for r in runs)})
        for r in runs:
            runrows.append({'method':label,'seed':r['seed'],'fitness':r['fitness'],
                            'unique_evaluations':r['unique_evaluations'],'seconds':r['seconds'],
                            'fitness_at_3264_or_run_end':r.get('fitness_at_comparison_budget',r['fitness'])})
    dsa_runs=[json.loads(p.read_text()) for p in sorted(out.glob('run_main_*.json'))]
    budget_best=min(dsa_runs,key=lambda r:r['fitness_at_comparison_budget'])
    bg=np.array(budget_best['gains_at_comparison_budget']); gains['DSA_budget']=bg
    rows,_=metric_rows(bg,scenarios,cfg,'DSA_budget'); allmetrics+=rows
    budget_score=evaluate(bg,scenarios,cfg)
    assert abs(budget_score-budget_best['fitness_at_comparison_budget'])<1e-10
    summaries.append({'method':'DSA at 3264 evaluations','best_fitness':budget_score,
                      'mean_seed_fitness':float(np.mean([r['fitness_at_comparison_budget'] for r in dsa_runs])),
                      'std_seed_fitness':float(np.std([r['fitness_at_comparison_budget'] for r in dsa_runs])),
                      'min_unique_evaluations':min(r['evaluations_at_comparison_budget'] for r in dsa_runs),
                      'max_unique_evaluations':max(r['evaluations_at_comparison_budget'] for r in dsa_runs)})
    write_csv(out/'method_comparison_metrics.csv',allmetrics)
    write_csv(out/'method_comparison_runs.csv',runrows)
    write_csv(out/'method_comparison_summary.csv',summaries)
    (out/'method_comparison_summary.json').write_text(json.dumps({'same_problem_configuration':True,
          'methods':summaries,'budget_candidate_seed':budget_best['seed'],
          'budget_candidate_gains':dict(zip([p['name'] for p in cfg['parameters']],bg.tolist())),
          'note':'Full DSA uses more evaluations. Budget snapshot is retrospective and is not a separate seeded run.'},indent=2))
    fig,axs=plt.subplots(2,3,figsize=(14,7),layout='constrained')
    for ax,s in zip(axs.flat,scenarios):
        j=int(np.flatnonzero(s['target'])[0]); col=1+j if j<2 else 6
        for label in ['GA','PSO','CSO','DSA']:
            _,_,tr=run(gains[label],s,cfg,True)
            ax.plot(tr[:,0]-cfg['pre_step_s'],np.rad2deg(tr[:,col]),label=label,color=colors[label])
        ax.axhline(s['target'][j],ls=':',color='k'); ax.set(title=s['name'],xlabel='Time after step (s)',ylabel='deg' if j<2 else 'deg/s',xlim=(-.05,1.2))
    axs[0,0].legend(); fig.suptitle('GA vs PSO vs CSO vs Dolphin Swarm | full-run candidates, unequal evaluation counts')
    for ext in ['png','svg']: fig.savefig(out/f'plots/10_method_responses.{ext}',dpi=170,bbox_inches='tight')
    plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(13,4),layout='constrained')
    for label,folder in folders.items():
        for k,path in enumerate(sorted(folder.glob('run_main_*.json'))):
            r=json.loads(path.read_text()); h=r['history']
            axs[0].plot([z['unique_evaluations'] for z in h],[z['best'] for z in h],color=colors[label],alpha=.65,label=label if k==0 else None)
    axs[0].axvline(cfg['comparison_evaluation_budget'],ls=':',color='k',label='3264 evaluations')
    axs[0].set(yscale='log',xlabel='Unique objective evaluations',ylabel='Best fitness',title='Convergence with evaluation cost'); axs[0].legend()
    axs[1].bar([s['method'] for s in summaries],[s['best_fitness'] for s in summaries],color=list(colors.values()))
    axs[1].tick_params(axis='x',labelrotation=18); axs[1].set(ylabel='Best fitness (lower is better)',title='Full runs and DSA budget snapshot')
    for ext in ['png','svg']: fig.savefig(out/f'plots/11_evaluation_comparison.{ext}',dpi=170,bbox_inches='tight')
    plt.close(fig)
    from report import table
    matrix=[]
    for s in scenarios:
        row={'test':s['name']}
        for label in ['GA','PSO','CSO','DSA','DSA_budget']:
            r=next(r for r in allmetrics if r['scenario']==s['name'] and r['controller']==label)
            row[label+'_settling_s']=r['settling_s']; row[label+'_overshoot_pct']=r['overshoot_pct']
        matrix.append(row)
    body=f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>GA / PSO / CSO / Dolphin Swarm comparison</title>
<style>body{{font:16px Segoe UI,sans-serif;max-width:1200px;margin:40px auto;color:#193749;line-height:1.6}}table{{border-collapse:collapse;font-size:13px;width:100%}}td,th{{padding:9px;border-bottom:1px solid #ddd;text-align:left}}img{{max-width:100%}}.scroll{{overflow:auto}}</style>
<h1>GA, PSO, CSO and Dolphin Swarm Optimization</h1><p><a href="REPORT.html">Full Dolphin Swarm report</a></p>
<p>The same model, fitness, bounds, limits and sample-time assumptions were verified; saved GA/PSO/CSO scores were reproduced. Main DSA receives no optimized GA/PSO/CSO gains.</p>
<p><b>Evaluation counts matter:</b> echolocation tests several probes per dolphin. Thus 50 DSA iterations cost more than 50 GA/PSO updates. Both full-run results and a best-so-far snapshot at {cfg['comparison_evaluation_budget']} unique evaluations per seed are reported. GA's actual count is slightly smaller because elites are cached. The snapshot is not an independently restarted search.</p>
{table(summaries)}{table(matrix)}{table(runrows)}
<img src="plots/10_method_responses.png" alt="Step responses">
<img src="plots/11_evaluation_comparison.png" alt="Evaluation budget comparison">
<p>These are three-seed numerical experiments, not proof that any method is generally superior. Separate execution times are not a controlled runtime benchmark. Simulink timing and combined-axis limitations remain.</p></html>'''
    (out/'METHOD_COMPARISON.html').write_text(body,encoding='utf-8')
