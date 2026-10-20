"""Re-evaluate the saved GA candidate under unchanged PSO study equations."""
import csv
import html
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from model import run
from study import evaluate, metric_rows, training_scenarios, write_csv

ROOT=Path(__file__).resolve().parent

def compare_ga(out,cfg):
    out=Path(out); ref=ROOT/'ga_reference'
    old=json.loads((ref/'best_gains.json').read_text()); new=json.loads((out/'best_gains.json').read_text())
    gcfg=json.loads((ref/'configuration.json').read_text())
    # Guard the comparison against changes in equations/constraints/parameters.
    keys=['parameters','integration_dt_s','controller_dt_s','mixer_dt_s','pre_step_s',
          'response_horizon_s','settling_band_fraction','minimum_final_hold_s',
          'max_overshoot_fraction','max_final_error_fraction','max_motor_clipping_fraction',
          'minimum_motor_speed_rad_s','fixed_discrete_pole','fitness_weights','worst_case_weight','effort_weight']
    same=all(cfg[k]==gcfg[k] for k in keys)
    ga=np.array(list(old['gains'].values())); pso=np.array(list(new['gains'].values()))
    scenarios=training_scenarios(); ga_score=evaluate(ga,scenarios,cfg); pso_score=evaluate(pso,scenarios,cfg)
    if same and abs(ga_score-old['training_fitness'])>1e-10:
        raise AssertionError('Stored GA fitness does not reproduce; comparison is not valid.')
    grows,_=metric_rows(ga,scenarios,cfg,'GA'); prows,_=metric_rows(pso,scenarios,cfg,'PSO')
    write_csv(out/'ga_vs_pso_metrics.csv',grows+prows)
    runs=[]
    for label,folder in [('GA',ref),('PSO',out)]:
        for path in sorted(folder.glob('run_main_*.json')):
            d=json.loads(path.read_text())
            runs.append({'algorithm':label,'seed':d['seed'],'fitness':d['fitness'],
                         'unique_evaluations':d['unique_evaluations'],
                         'proposals':d.get('candidate_proposals',(gcfg['generations']+1)*gcfg['population']),
                         'seconds':d['seconds']})
    write_csv(out/'ga_vs_pso_runs.csv',runs)
    fig,axs=plt.subplots(2,3,figsize=(14,7),layout='constrained')
    for ax,s in zip(axs.flat,scenarios):
        j=int(np.flatnonzero(s['target'])[0]); col=1+j if j<2 else 6
        for label,g,color in [('GA',ga,'#64748b'),('PSO',pso,'#007f86')]:
            _,_,tr=run(g,s,cfg,True)
            ax.plot(tr[:,0]-cfg['pre_step_s'],np.rad2deg(tr[:,col]),label=label,color=color)
        ax.axhline(s['target'][j],ls='--',color='#b86427',lw=1)
        ax.set(title=s['name'],xlabel='Time after step (s)',ylabel='Angle (deg)' if j<2 else 'Yaw rate (deg/s)',xlim=(-.05,1.2))
    axs[0,0].legend(); fig.suptitle('Saved GA versus new PSO | same model, commands and constraints')
    fig.savefig(out/'plots/10_ga_vs_pso.png',dpi=170,bbox_inches='tight'); fig.savefig(out/'plots/10_ga_vs_pso.svg',bbox_inches='tight'); plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    for label,folder,color in [('GA',ref,'#64748b'),('PSO',out,'#007f86')]:
        scores=[]
        for k,path in enumerate(sorted(folder.glob('run_main_*.json'))):
            d=json.loads(path.read_text()); h=d['history']; scores.append(d['fitness'])
            axs[0].plot([v['unique_evaluations'] for v in h],[v['best'] for v in h],color=color,alpha=.7,label=label if k==0 else None)
        axs[1].scatter([label]*len(scores),scores,color=color,s=45)
    axs[0].set(yscale='log',xlabel='Unique objective evaluations',ylabel='Best fitness',title='Convergence: actual evaluations'); axs[0].legend()
    axs[1].set(ylabel='Final fitness',title='Independent main seeds (lower is better)')
    fig.savefig(out/'plots/11_ga_vs_pso_convergence.png',dpi=170,bbox_inches='tight'); fig.savefig(out/'plots/11_ga_vs_pso_convergence.svg',bbox_inches='tight'); plt.close(fig)
    summary={'same_problem_configuration':same,'GA_recomputed_fitness':ga_score,'PSO_fitness':pso_score,
             'PSO_fitness_reduction_vs_GA_pct':100*(1-pso_score/ga_score),
             'main_PSO_used_GA_initialization':False,
             'interpretation':'Descriptive comparison of best main-run candidates and three seeds, not proof of algorithm superiority.'}
    (out/'ga_vs_pso_summary.json').write_text(json.dumps(summary,indent=2))
    from report import table
    rows=[]
    for a,b in zip(grows,prows):
        rows.append({'test':a['scenario'],'GA_settling_s':a['settling_s'],'PSO_settling_s':b['settling_s'],
                     'GA_overshoot_pct':a['overshoot_pct'],'PSO_overshoot_pct':b['overshoot_pct']})
    text=f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>GA versus PSO</title>
<style>body{{font:16px Segoe UI,sans-serif;max-width:1150px;margin:40px auto;color:#17334a;line-height:1.6}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}img{{max-width:100%}}.scroll{{overflow-x:auto}}</style>
<h1>GA versus PSO</h1><p><a href="REPORT.html">Full PSO report</a></p>
<p>Recomputed GA fitness: <b>{ga_score:.8g}</b>. New PSO fitness: <b>{pso_score:.8g}</b>.
PSO change: <b>{summary['PSO_fitness_reduction_vs_GA_pct']:.2f}% reduction</b> (negative means worse).</p>
<p>Same equations, constraints, bounds and timing: <b>{same}</b>. Main PSO was initialized independently of GA gains.
Both full studies use 64 candidates and 50 updates plus the initial evaluation for each of three seeds.
The actual unique evaluations differ because GA preserves elites and both implementations cache repeats.
Wall-clock times are from separate executions; they are not a controlled hardware benchmark.</p>
<p>These are numerical candidates for the same finite tests. The comparison does not establish that one algorithm is always better.</p>
{table(rows)}{table(runs)}
<img src="plots/10_ga_vs_pso.png" alt="GA and PSO response comparison">
<img src="plots/11_ga_vs_pso_convergence.png" alt="Convergence by evaluations">
<p>Compiled Simulink timing still needs confirmation. Both studies retain the source's combined-axis tracking limitations.</p></html>'''
    (out/'GA_COMPARISON.html').write_text(text,encoding='utf-8')
