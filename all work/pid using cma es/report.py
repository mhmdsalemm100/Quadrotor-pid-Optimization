"""Save publication-style plots, raw traces, a readable HTML report, and export notes."""
import csv
import html
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from model import run
from study import write_csv
from linear_analysis import local_analysis

COLORS={'baseline':'#64748b','CMA-ES':'#007f86','robust_CMA-ES':'#b86427'}

def table(rows,columns=None):
    if not rows: return '<p>No rows.</p>'
    columns=columns or list(rows[0])
    def fmt(v):
        if v is None: return 'not reached'
        if isinstance(v,(float,np.floating)): return f'{v:.5g}'
        return str(v)
    return '<div class="scroll"><table><thead><tr>'+''.join(f'<th>{html.escape(c)}</th>' for c in columns)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{html.escape(fmt(r.get(c,"")))}</td>' for c in columns)+'</tr>' for r in rows)+'</tbody></table></div>'

def build_report(out,cfg,export,results,base,gains,train,holdout,metrics,mc,sensitivity,numerical,experiments):
    out=Path(out); figures=out/'plots'; traces=out/'traces'
    figures.mkdir(exist_ok=True); traces.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'white','axes.grid':True,'grid.alpha':.2,'savefig.dpi':170})
    def save(fig,name):
        fig.savefig(figures/(name+'.png'),bbox_inches='tight'); fig.savefig(figures/(name+'.svg'),bbox_inches='tight'); plt.close(fig)
    alltr={}
    for scenario in train+holdout:
        for label,g in [('baseline',base),('CMA-ES',gains)]:
            m,d,tr=run(g,scenario,cfg,True); alltr[(scenario['name'],label)]=tr
            np.savez_compressed(traces/f'{scenario["name"]}_{label}.npz',trace=tr,metrics=m,diagnostics=d)
    columns=['time_s','roll_rad','pitch_rad','yaw_rad','p_rad_s','q_rad_s','r_rad_s',
             'roll_ref_rad_or_rad_s','pitch_ref_rad_or_rad_s','yaw_rate_ref_rad_s',
             'p_ref_rad_s','q_ref_rad_s','r_ref_rad_s','roll_raw','pitch_raw','yaw_raw',
             'roll_limited','pitch_limited','yaw_limited','motor1_raw','motor2_raw','motor3_raw','motor4_raw',
             'motor1_limited','motor2_limited','motor3_limited','motor4_limited','min_omega_rad_s',
             'omega1_rad_s','omega2_rad_s','omega3_rad_s','omega4_rad_s','quat_w','quat_x','quat_y','quat_z']
    (traces/'columns.json').write_text(json.dumps(columns,indent=2))
    for s in train:
        for label in ['baseline','CMA-ES']:
            np.savetxt(traces/f'{s["name"]}_{label}.csv',alltr[(s['name'],label)],delimiter=',',header=','.join(columns),comments='',fmt='%.9g')
    fig,axs=plt.subplots(2,3,figsize=(14,7),layout='constrained')
    for ax,s in zip(axs.flat,train):
        j=int(np.flatnonzero(s['target'])[0]); col=1+j if j<2 else 6
        for label in ['baseline','CMA-ES']:
            tr=alltr[(s['name'],label)]; t=tr[:,0]-cfg['pre_step_s']
            ax.plot(t,np.rad2deg(tr[:,col]),label=label,color=COLORS[label],lw=1.7)
        ax.axhline(s['target'][j],color='#da9130',ls='--',lw=1,label='command')
        ax.axhspan(s['target'][j]*.98,s['target'][j]*1.02,color='#da9130',alpha=.12)
        ax.set(title=s['name'].replace('_',' '),xlabel='Time after step (s)',ylabel='Angle (deg)' if j<2 else 'Yaw rate (deg/s)',xlim=(-.1,1.8))
    axs[0,0].legend(); fig.suptitle('Training responses | same model and limits for both controllers',fontsize=15)
    save(fig,'01_step_responses')
    fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    for r in results:
        h=r['history']; x=[v['iteration'] for v in h]; y=[v['best'] for v in h]
        axs[0].plot(x,y,label=f'Seed {r["seed"]}')
        axs[1].plot(x,[100*v['feasible_fraction'] for v in h],label=f'Seed {r["seed"]}')
    axs[0].set(xlabel='Iteration',ylabel='Best fitness (lower is better)',yscale='log',title='Convergence across independent seeds')
    axs[1].set(xlabel='Iteration',ylabel='Feasible candidates (%)',ylim=(0,105),title='Constraint satisfaction')
    axs[0].legend(); save(fig,'02_cmaes_iterations')
    fig,axs=plt.subplots(2,2,figsize=(13,7),layout='constrained')
    for label in ['baseline','CMA-ES']:
        tr=alltr[('coupled_10_8_40',label)]; t=tr[:,0]-cfg['pre_step_s']
        axs[0,0].plot(t,np.rad2deg(tr[:,1]),label=f'{label}: roll',color=COLORS[label])
        axs[0,0].plot(t,np.rad2deg(tr[:,2]),label=f'{label}: pitch',color=COLORS[label],ls='--')
        axs[0,1].plot(t,np.rad2deg(tr[:,6]),label=label,color=COLORS[label])
    tr=alltr[('coupled_10_8_40','CMA-ES')]; t=tr[:,0]-cfg['pre_step_s']
    for j in range(4):
        axs[1,0].plot(t,tr[:,19+j],label=f'M{j+1} raw',lw=1)
        axs[1,1].plot(t,tr[:,23+j],label=f'M{j+1}',lw=1)
    for ax in axs[1]:
        ax.axhline(0,color='k',ls=':'); ax.axhline(1,color='k',ls=':')
    for ax,title,ylabel in zip(axs.flat,['Held-out coupled angle response','Held-out yaw-rate response','CMA-ES mixer demands before clipping','CMA-ES motor commands after clipping'],['Angle (deg)','Yaw rate (deg/s)','Normalized command','Normalized command']):
        ax.set(title=title,xlabel='Time after step (s)',ylabel=ylabel,xlim=(-.1,2)); ax.legend(fontsize=8)
    save(fig,'03_coupled_and_saturation')
    fig,axs=plt.subplots(1,3,figsize=(14,4),layout='constrained')
    for ax,j,sname in zip(axs,[0,1,2],['inner_roll30','inner_pitch30','yaw_30dps']):
        for label in ['baseline','CMA-ES']:
            tr=alltr[(sname,label)]; ax.plot(tr[:,0]-cfg['pre_step_s'],np.rad2deg(tr[:,4+j]),color=COLORS[label],label=label)
        ax.axhline(30,color='#da9130',ls='--'); ax.set(title=['Roll rate','Pitch rate','Yaw rate'][j],xlabel='Time after step (s)',ylabel='Rate (deg/s)',xlim=(-.05,1))
    axs[0].legend(); fig.suptitle('Inner-loop response checks',fontsize=15); save(fig,'04_inner_loops')
    fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    for label in ['baseline','CMA-ES','robust_CMA-ES']:
        rows=[r for r in mc if r['controller']==label and r['group']=='single_axis_uncertainty']; vals=np.sort([r['max_settling_s'] for r in rows])
        axs[0].plot(vals,np.arange(1,len(vals)+1)/len(vals),color=COLORS[label],label=label)
        axs[1].scatter([r['max_overshoot_pct'] for r in rows],[r['motor_clip_pct'] for r in rows],label=label,color=COLORS[label],alpha=.65,s=20)
    axs[0].set(title='Single-axis held-out parameter uncertainty',xlabel='Worst-axis settling time (s; 3 means unresolved or end)',ylabel='Empirical cumulative fraction')
    axs[1].axvline(100*cfg['max_overshoot_fraction'],color='k',ls=':'); axs[1].axhline(100*cfg['max_motor_clipping_fraction'],color='k',ls=':')
    axs[1].set(title='Overshoot and motor clipping',xlabel='Worst-axis overshoot (%)',ylabel='Motor clipping duty (%)')
    axs[0].legend(); axs[1].legend(); save(fig,'05_robustness')
    fig,axs=plt.subplots(2,4,figsize=(15,6),layout='constrained')
    for ax,p in zip(axs.flat,cfg['parameters']):
        rows=[r for r in sensitivity if r['parameter']==p['name']]
        ax.plot([r['factor_requested'] for r in rows],[r['fitness'] for r in rows],marker='o',color=COLORS['CMA-ES'])
        ax.set(title=p['name'].replace('_',' '),xlabel='Multiplier',ylabel='Training fitness',yscale='log')
    save(fig,'06_gain_sensitivity')
    fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    cases=[s['name'] for s in train]; x=np.arange(len(cases)); width=.36
    for offset,label in [(-width/2,'baseline'),(width/2,'CMA-ES')]:
        rows=[next(r for r in metrics if r['controller']==label and r['scenario']==s) for s in cases]
        axs[0].bar(x+offset,[r['settling_s'] or cfg['response_horizon_s'] for r in rows],width,label=label,color=COLORS[label])
        axs[1].bar(x+offset,[r['overshoot_pct'] for r in rows],width,label=label,color=COLORS[label])
    for ax in axs: ax.set_xticks(x,cases,rotation=30,ha='right'); ax.legend()
    axs[0].set(title='Settling time',ylabel='Seconds'); axs[1].set(title='Overshoot',ylabel='Percent')
    axs[1].axhline(100*cfg['max_overshoot_fraction'],color='k',ls=':'); save(fig,'07_metric_comparison')
    # Fitness breakdown from the raw saved cases.
    details=json.loads((out/'case_details.json').read_text()); breakdown=[]
    for label in ['baseline','CMA-ES']:
        terms=[]
        for case in details[label][:len(train)]:
            active=np.abs(case['scenario']['target'])>0; m=np.array(case['metrics'])[active]
            H=cfg['response_horizon_s']; w=cfg['fitness_weights']
            terms.append([w['settling']*m[:,1].mean()/H,w['rise']*m[:,0].mean()/H,
                          w['itae']*2*m[:,5].mean()/H**2,w['iae']*m[:,4].mean()/H])
        breakdown.append(np.mean(terms,axis=0))
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained'); bottom=np.zeros(2)
    for i,label in enumerate(['settling','rise','ITAE','IAE']):
        vals=np.array(breakdown)[:,i]; ax.bar(['baseline','CMA-ES'],vals,bottom=bottom,label=label); bottom+=vals
    ax.set(ylabel='Weighted mean normalized contribution',title='Fitness composition (before worst-case / effort terms)'); ax.legend()
    save(fig,'08_fitness_components')
    linear={'baseline':local_analysis(base,cfg),'CMA-ES':local_analysis(gains,cfg)}
    (out/'local_linear_analysis.json').write_text(json.dumps(linear,indent=2))
    summaryrows=[]
    for s in train:
        b=next(r for r in metrics if r['controller']=='baseline' and r['scenario']==s['name'])
        o=next(r for r in metrics if r['controller']=='CMA-ES' and r['scenario']==s['name'])
        summaryrows.append({'test':s['name'],'baseline_settle_s':b['settling_s'],'CMA-ES_settle_s':o['settling_s'],
                            'settling_reduction_pct':100*(1-o['settling_s']/b['settling_s']) if o['settling_s'] and b['settling_s'] else None,
                            'CMA-ES_overshoot_pct':o['overshoot_pct'],'CMA-ES_motor_clip_pct':o['motor_clip_pct']})
    write_csv(out/'baseline_vs_cmaes.csv',summaryrows)
    lowmotor=[]
    for (name,label),tr in alltr.items():
        minimum=float(np.nanmin(tr[:,27]))
        if minimum<0: lowmotor.append({'scenario':name,'controller':label,'minimum_motor_speed_rad_s':minimum})
    write_csv(out/'negative_motor_speed_cases.csv',lowmotor)
    boundrows=[]
    for p,v in zip(cfg['parameters'],gains):
        fraction=np.log(v/p['lower'])/np.log(p['upper']/p['lower'])
        boundrows.append({'parameter':p['name'],'gain':v,'lower':p['lower'],'upper':p['upper'],
                          'near_bound_within_5pct_of_log_range':fraction<.05 or fraction>.95})
    mcrows=[{'group':group,'controller':label,
             'passes':sum(r['feasible'] for r in mc if r['controller']==label and r['group']==group),
             'total':sum(r['controller']==label and r['group']==group for r in mc)}
            for group in ['single_axis_uncertainty','combined_axis_stress']
            for label in ['baseline','CMA-ES','robust_CMA-ES']]
    robust=json.loads((out/'robust_gains.json').read_text())
    rg=np.array(list(robust['gains'].values()))
    rmetrics=list(csv.DictReader((out/'robust_metrics.csv').open()))
    robust_compare=[]
    for s in train:
        nr=next(r for r in metrics if r['controller']=='CMA-ES' and r['scenario']==s['name'])
        rr=next(r for r in rmetrics if r['scenario']==s['name'])
        robust_compare.append({'test':s['name'],'nominal_CMA-ES_settle_s':nr['settling_s'],
                               'robust_CMA-ES_settle_s':float(rr['settling_s']) if rr['settling_s'] else None,
                               'robust_CMA-ES_overshoot_pct':float(rr['overshoot_pct'])})
    fig,axs=plt.subplots(1,3,figsize=(14,4),layout='constrained')
    for ax,j,s in zip(axs,[0,1,2],[train[1],train[3],train[5]]):
        for label,g in [('baseline',base),('CMA-ES',gains),('robust_CMA-ES',rg)]:
            _,_,tr=run(g,s,cfg,True)
            ax.plot(tr[:,0]-cfg['pre_step_s'],np.rad2deg(tr[:,1+j if j<2 else 6]),label=label,color=COLORS[label])
        ax.axhline(s['target'][j],ls=':',color='k'); ax.set(title=s['name'],xlabel='Time after step (s)',ylabel='deg / deg/s',xlim=(-.05,1))
    axs[0].legend(); fig.suptitle('Nominal speed versus uncertainty-focused tuning'); save(fig,'09_robust_candidate')
    rc=robust['transfer_functions']
    (out/'ROBUST_SIMULINK_PARAMETER_MAP.txt').write_text(
        'UNCERTAINTY-FOCUSED CANDIDATE; SAME TIMING ASSUMPTIONS AS NOMINAL\n'
        +f'Gain2 (roll outer): {rg[0]:.12g}\nGain1 (pitch outer): {rg[3]:.12g}\n'
        +f'Roll Discrete Transfer Fcn2: numerator={rc["roll"]["numerator"]}, denominator={rc["roll"]["denominator"]}\n'
        +f'Pitch Discrete Transfer Fcn3: numerator={rc["pitch"]["numerator"]}, denominator={rc["pitch"]["denominator"]}\n'
        +f'Kp_YAW_AngleRate={rg[6]:.12g}\nKi_YAW_AngleRate={rg[7]:.12g}\nKd_YAW_AngleRate=0\n'
        +'Separate candidate for comparison, not a validated universal controller. See report for combined-axis failures.\n',encoding='utf-8')
    failures=[r for r in metrics if r['controller']=='CMA-ES' and r['group']!='training' and not r['feasible_under_design_constraints']]
    gain_text='\n'.join(f'{k} = {v:.12g}' for k,v in export['gains'].items())
    transfer_text='\n'.join(f'{axis}: numerator = {export[axis+"_transfer_function"]["numerator"]}; denominator = {export[axis+"_transfer_function"]["denominator"]}' for axis in ['roll','pitch'])
    applied=f'''PYTHON CMA-ES CANDIDATE — MANUAL SIMULINK PARAMETER MAP
Assumed controller sample time: {cfg['controller_dt_s']} s; mixer: {cfg['mixer_dt_s']} s.
{export['status']}

Control System/AttitudeControl/Gain2 (ROLL): {gains[0]:.12g}
Control System/AttitudeControl/Gain1 (PITCH): {gains[3]:.12g}
Control System/AttitudeControl/Discrete Transfer Fcn2 (ROLL):
  Numerator: {export['roll_transfer_function']['numerator']}
  Denominator: {export['roll_transfer_function']['denominator']}
Control System/AttitudeControl/Discrete Transfer Fcn3 (PITCH):
  Numerator: {export['pitch_transfer_function']['numerator']}
  Denominator: {export['pitch_transfer_function']['denominator']}
Init_control.m variables:
  Kp_YAW_AngleRate = {gains[6]:.12g}
  Ki_YAW_AngleRate = {gains[7]:.12g}
  Kd_YAW_AngleRate = 0

Use numerator/denominator values for the existing roll/pitch transfer blocks.
The equivalent Kp/Ki parameterization is a leaky controller, not an ideal PI block.
Keep saturation limits as in the source for this candidate comparison.
Confirm compiled controller and mixer timing BEFORE interpreting Python performance
as Simulink performance. Reproduce the same initialized operating point and steps.
Do not assume the 220 rate limit means degrees/s: the supplied model applies 220 rad/s.
No source SLX or MATLAB file has been edited or executed.
'''
    (out/'SIMULINK_PARAMETER_MAP.txt').write_text(applied,encoding='utf-8')
    fitness_improve=100*(1-export['optimized_unpenalized_response_cost']/export['baseline_unpenalized_response_cost'])
    from cma_diagnostics import build_diagnostics
    build_diagnostics(out)
    images=''.join(f'<figure><img src="plots/{name}.png" alt="{caption}"><figcaption>{caption}</figcaption></figure>' for name,caption in [
        ('12_cma_adaptation','CMA-ES step size, covariance axis ratio and final genotype correlation. Coordinate indices follow the eight gain parameters; these are not physical-gain correlations.'),
        ('01_step_responses','Baseline versus optimized training responses. Shading: ±2% of command.'),
        ('02_cmaes_iterations','All main CMA-ES seeds; global-best memory preserves the best candidate.'),
        ('07_metric_comparison','Response metrics on the six training commands.'),
        ('04_inner_loops','Rate-loop checks; roll/pitch angle loop bypassed for these validation tests.'),
        ('03_coupled_and_saturation','Held-out simultaneous command and mixer saturation.'),
        ('08_fitness_components','How settling, rise, and tracking error contribute to fitness.'),
        ('05_robustness','Held-out Monte Carlo parameter/command uncertainty.'),
        ('06_gain_sensitivity','Local sensitivity: one gain varied at a time, others fixed.'),
        ('09_robust_candidate','Separate uncertainty-focused CMA-ES candidate versus nominal tuning.')])
    body=f'''<h1>PID / transfer-function tuning using a CMA-ES optimizer</h1>
<p class="lead">Equation-based study of your <b>AttitudeControl_Sim.slx</b>. Python simulation only.</p>
<div class="cards"><div><b>{fitness_improve:.1f}%</b><span>reduction in unpenalized response cost</span></div><div><b>{len(results)}</b><span>independent main CMA-ES seeds</span></div><div><b>{len(train)}</b><span>training step tests</span></div><div><b>{mcrows[1]['passes']}/{mcrows[1]['total']}</b><span>nominal CMA-ES single-axis uncertainty passes</span></div></div>
<p><b>Status:</b> {html.escape(export['status'])} “Best” means lowest main-study training fitness among the tested candidates, within the configured bounds. It does not prove a globally fastest controller.</p>
<p><a href="METHOD_COMPARISON.html">Open the CMA-ES-versus-GA/PSO/CSO/DSA comparison</a></p><h2>1. Result and baseline comparison</h2>{table(summaryrows)}
<p>Baseline penalized fitness: {export['baseline_training_fitness']:.6g}; CMA-ES penalized fitness: {export['training_fitness']:.6g}. Because feasibility penalties can dominate, the percentage above compares the unpenalized response cost only ({export['baseline_unpenalized_response_cost']:.6g} → {export['optimized_unpenalized_response_cost']:.6g}). The baseline is not exempted from the motor-speed validity constraint.</p>
<p>Settling uses ±2% of the requested change, not the achieved final value. It must remain in that band through the end of the simulation, including a minimum {cfg['minimum_final_hold_s']} s final hold. A finite horizon cannot prove permanent settling.</p>
<h2>2. Optimized parameters and transfer functions</h2><pre>{html.escape(gain_text)}</pre><pre>{html.escape(transfer_text)}</pre>
<p>Yaw Kd remains zero, matching the source. Roll/pitch discrete poles remain 0.9997. The optimizer changes the outer proportional gains and both numerator coefficients via a positive leaky-PI parameterization.</p>
<p><a href="SIMULINK_PARAMETER_MAP.txt">Exact manual Simulink block/variable map</a> · <a href="best_gains.json">Machine-readable gains</a> · <a href="metrics.csv">All metrics</a></p>
<h2>3. Equations and source fidelity</h2>
<pre>e_angle = angle_reference - measured_angle
rate_reference = clip(K_outer * e_angle, -220, +220)  [rad/s]
C(z) = (b0 + b1 z^-1) / (1 - a z^-1)
a = 0.9997; b0 = Kp_equiv + Ki_equiv * Ts; b1 = -a * Kp_equiv
u[k] = a*u[k-1] + b0*e_rate[k] + b1*e_rate[k-1]
yaw_u[k] = Kp_yaw*e_yaw[k] + I[k]
I[k+1] = clip(I[k] + Ki_yaw*Ts*e_yaw[k], -0.2, +0.2)
roll/pitch u limited to +/-1; yaw u limited to +/-0.5

motor demand = [T-R+P+Y, T+R-P+Y, T+R+P-Y, T-R-P-Y]
motor input = clip(demand, 0, 1)
omega_dot = (1148*motor_input - 141.4 - omega) / 0.02
M_prop = allocation_matrix * omega^2
M_damping = -[0.0035,0.0039,0.0034] * body_rate * abs(body_rate)
M_gyro = J_rotor * [q*spin, -p*spin, 0]; spin = w1+w2-w3-w4
J * body_rate_dot = M_prop + M_damping + M_gyro - body_rate x (J*body_rate)
quaternion_dot = 0.5 * Omega(body_rate) * quaternion
</pre>
<p>The exact source allocation matrix and quaternion equations are implemented in model.py and recorded in source/inventory.json. Motor and rotational states use RK4. Quaternion normalization controls numerical drift. All three axes are simulated together, including coupling. Translation does not feed the rotational subsystem in this source, so it is excluded from attitude fitness; full_rhs also supplies the source translational equations for trajectory work. This study does not optimize altitude or position.</p>
<p><b>Preserved source issues:</b> roll/pitch rate saturation is 220 rad/s as implemented; the low-throttle motor law can request negative speed; the unused motorMinThr and roll/pitch integral-limit variables are not added as new dynamics. No invented anti-windup is used. Mathematical degree conversion uses pi/180 rather than the source's rounded decimal.</p>
<h2>4. Fitness and constraints</h2>
<pre>For each active channel, with A = absolute command and H = test horizon:
IAE  = integral |reference - response| / A dt
ITAE = integral t * |reference - response| / A dt
Q_channel = {cfg['fitness_weights']['settling']}*settling/H + {cfg['fitness_weights']['rise']}*rise/H
          + {cfg['fitness_weights']['itae']}*2*ITAE/H^2 + {cfg['fitness_weights']['iae']}*IAE/H
Q_case = mean of active channel scores
Q = (1-worst_weight)*mean(Q_case) + worst_weight*max(Q_case)
    + effort_weight*mean(mean((motor_input - collective)^2))
worst_weight = {cfg['worst_case_weight']}; effort_weight = {cfg['effort_weight']}
Fitness = Q if feasible
Fitness = 1000 + 100*sum(normalized constraint violations) + (2/pi)*atan(Q) otherwise
</pre>
<p>Rise time is first 10% to first 90% crossing (sampled). Overshoot is normalized excess beyond the command, including negative steps. Final error is the magnitude of mean signed error over the final hold interval. Unsettled responses incur a violation; missing rise/settling times are shown as “not reached”. These conventions and the reference-based settling rule are explicit so misleading final-value normalization cannot hide poor tracking.</p>
<ul><li>Overshoot ≤ {100*cfg['max_overshoot_fraction']:.0f}% on every commanded training channel.</li><li>Final mean error ≤ {100*cfg['max_final_error_fraction']:.0f}%; settle within the finite test horizon.</li><li>Any-motor clipping time ≤ {100*cfg['max_motor_clipping_fraction']:.0f}% of the response window.</li><li>Modeled motor speed must remain nonnegative: the optimizer may not benefit from the source's questionable low-throttle behavior. This is a fitness constraint, not a change to the plant.</li><li>Uncommanded angle excursions ≤0.5°; uncommanded yaw rate ≤3°/s.</li><li>Roll/pitch magnitude ≤75°; numerical blow-up and excessive rates fail immediately.</li></ul>
<p>These are configurable engineering study choices, not specifications supplied by the user. Clipping constraints are duty limits, not a prohibition of all clipping. Every signal limit is included in the simulation even when not separately penalized.</p>
<h2>5. Search design and bounds</h2>{table(boundrows)}
<p>CMA-ES through pycma 4.5.0: {cfg['swarm_size']} candidates per generation, {cfg['iterations']} covariance updates, seeds {cfg['seeds']}; initial normalized sigma={cfg['sigma0']}, active covariance={cfg['cma_active']}, diagonal covariance={cfg['cma_diagonal']}. A common stratified initial population is evaluated first and its best point initializes the distribution mean. Pycma BoundTransform enforces [0,1] bounds. Adaptation learns covariance and step size. Full history, means and covariance matrices are saved. Earlier optimized gains do not initialize main runs. <a href="https://cma-es.github.io/apidocs-pycma/">Official pycma documentation</a>; see STUDY_METHOD.md.</p>
{table([{'seed':r['seed'],'fitness':r['fitness'],'evaluations':r['unique_evaluations'],'seconds':r['seconds']} for r in results])}
<p>Main-run final fitness: mean {np.mean([r['fitness'] for r in results]):.6g}, standard deviation {np.std([r['fitness'] for r in results]):.6g}. A bound-adjacent result warrants a separate expanded-bound study; it is not evidence that the unconstrained optimum has been found.</p>
<h2>6. Validation and limitations</h2>{table(mcrows)}
<p><b>Combined-axis tracking is a limitation, not a passed result.</b> A sustained body yaw rate while holding nonzero Euler roll/pitch requires nonzero body p/q rates. The source uses independent proportional angle loops without that kinematic feedforward, so it can retain angle errors. Faster single-axis steps do not imply precise combined maneuver tracking. The report retains all failing cases below.</p>
<p>Validation includes negative/unseen steps, maximum commands, simultaneous axes, inertia ±15%, motor time constant ±30%, thrust/torque coefficients ±10%, damping ±30% in Monte Carlo, collective variation, a torque pulse, deterministic measurement perturbations, zero-speed startup, and alternate timing. Holdouts do not participate in main gain selection. This is a bounded synthetic robustness study, not a probability of success on hardware.</p>
<p><b>CMA-ES validation cases failing the main design constraints:</b></p>{table(failures,['scenario','axis','overshoot_pct','settling_s','motor_clip_pct','violation']) if failures else '<p>None in the listed deterministic cases.</p>'}
<p><b>Negative modeled motor speed cases:</b></p>{table(lowmotor) if lowmotor else '<p>None among the saved deterministic traces.</p>'}
<p><b>Timing assumption:</b> controller Ts={cfg['controller_dt_s']} s; mixer period={cfg['mixer_dt_s']} s; integration step={cfg['integration_dt_s']} s. The XML leaves controller timing inherited. This cannot be resolved without compiling the model. Alternate-controller-timing validation preserves exported coefficients; it does not silently redesign them.</p>
<p>Nominal study tests start with equal steady motor speeds at collective 0.609, whereas the source initializes motors at zero. A separate startup case uses zero motor speed. No altitude-hold loop is added. No sensor dynamics, transport delay, ground contact, battery dynamics, or motor dead zone absent from the source is invented.</p>
<h2>6a. Separate uncertainty-focused candidate</h2>
<p>A second CMA-ES uses the six nominal cases plus six predeclared single-axis uncertainty cases (inertia ±15%, motor lag ±30%, force coefficients ±10%). Two seeds, 48 candidates, 35 iterations; it is warm-started with the nominal candidate. The held-out Monte Carlo cases are not used in this search. This comparison is not a full worst-case robustness guarantee.</p>
{table(robust_compare)}
<p><a href="robust_gains.json">Uncertainty-focused gains and search settings</a> · <a href="ROBUST_SIMULINK_PARAMETER_MAP.txt">Separate Simulink parameter map</a> · <a href="robust_metrics.csv">All uncertainty-candidate metrics</a>. Its robust-training fitness is {robust['robust_training_fitness']:.6g}; a value ≥1000 means at least one design constraint was not met.</p>
<h2>7. Numerical convergence and local stability</h2>{table(numerical)}
<p>The step is halved while controller and mixer periods stay fixed. Local hover linearization includes the motor lag, digital controller and mixer hold via a lifted transition matrix over one mixer period. Saturation is inactive in this local analysis. Yaw analysis covers rate stability; yaw heading remains uncontrolled.</p>
{table([{'controller':label,'axis':axis,'spectral_radius':v['spectral_radius'],'locally_stable':v['locally_stable'],'period_s':v['lifted_period_s']} for label,axes in linear.items() for axis,v in axes.items()])}
<p><a href="local_linear_analysis.json">Linearized rate plant coefficients and closed-loop eigenvalues</a>. A local stable linearization and finite nonlinear tests do not prove global stability.</p>
<h2>8. Fitness / CMA-ES parameter sensitivity</h2>{table([{'experiment':e['name'],'own_fitness':e['own_fitness'],'score_under_main_fitness':e['common_main_fitness']} for e in experiments])}
<p>These are compact, single-seed warm-started reoptimizations (32 candidates ×24 iterations), changing settling/error weights or initial step size or diagonal covariance. They are exploratory comparisons, not statistically powered hyperparameter conclusions; they do not replace the main three-seed result. Own-objective scores are not directly comparable across weight choices. gain_sensitivity.csv independently varies each final gain by ±10% and ±20%, clipping to the declared bounds.</p>
<h2>9. Plots</h2>{images}
<h2>10. Reproduction and references</h2>
<p>Run <code>python -m pip install -r requirements.txt</code>, then <code>python test_study.py</code> and <code>python run_study.py --mode full</code>. Configuration, seeds, source hashes, all iteration candidate positions, metric tables, traces and installed package versions are saved alongside this report. Consult README.md and STUDY_METHOD.md for the full workflow.</p>
<p>Primary definitions: <a href="https://www.mathworks.com/help/simulink/slref/discretetransferfcn.html">MathWorks Discrete Transfer Fcn</a>; <a href="https://www.mathworks.com/help/control/ref/dynamicsystem.stepinfo.html">MathWorks step-response metrics</a>. The source equations and numerical parameter values come from the supplied ZIP, not from an unrelated generic quadcopter model.</p>
'''
    style='''body{font-family:Segoe UI,Arial,sans-serif;color:#183045;background:#f2f6f8;margin:0;line-height:1.6}main{max-width:1160px;margin:auto;padding:42px;background:white}h1{font-size:34px;line-height:1.2;color:#075e66}h2{margin-top:38px;border-bottom:2px solid #e2eaee;padding-bottom:8px}.lead{font-size:20px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:25px 0}.cards div{padding:20px;background:#eaf5f3;border-radius:10px}.cards b{display:block;font-size:30px;color:#007f86}.cards span{font-size:13px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:9px;border-bottom:1px solid #dce4e8}th{background:#edf3f5}.scroll{overflow-x:auto}pre{background:#eef3f5;padding:18px;overflow:auto;font-size:13px;line-height:1.6}figure{margin:25px 0}img{max-width:100%}figcaption{font-size:13px;color:#526878}a{color:#007f86}@media(max-width:700px){main{padding:20px}.cards{grid-template-columns:repeat(2,1fr)}}'''
    (out/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CMA-ES attitude tuning study</title><style>'+style+'</style><main>'+body+'</main></html>',encoding='utf-8')
    (out/'SUMMARY.md').write_text('# CMA-ES attitude tuning results\n\n'+export['status']+'\n\n'+f'Penalized training fitness: {export["baseline_training_fitness"]:.6g} → {export["training_fitness"]:.6g}. Unpenalized response-cost reduction: {fitness_improve:.1f}%.\n\n'+f'Single-axis Monte Carlo design-constraint passes: {mcrows[1]["passes"]}/{mcrows[1]["total"]}.\n\n'+'```text\n'+gain_text+'\n\n'+transfer_text+'\n```\n\nCombined-axis limitations and a separate uncertainty-focused candidate are documented in REPORT.html. See also baseline_vs_cmaes.csv, metrics.csv and SIMULINK_PARAMETER_MAP.txt.\n',encoding='utf-8')
