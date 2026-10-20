"""PNG scientific figures and machine-readable plot data; no PDF figures."""
from pathlib import Path
import csv,json,gzip
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
from methods import METHODS,SEEDS,FULL_NAMES
from study import training_scenarios,write_csv,evaluate
from robust_protocol import training_cases
from model import run,baseline
from analyze_extension import get_data,selected,read,OUT
P=OUT/'plots';D=OUT/'plot_data'
COLORS=dict(zip(METHODS,['#17669a','#c16a17','#773ea0','#13846c','#c14367','#555c69']))
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18,'figure.facecolor':'white'})
def save(fig,name,folder=P):
    folder.mkdir(parents=True,exist_ok=True);fig.savefig(folder/f'{name}.png',dpi=220,bbox_inches='tight');plt.close(fig)
def rows(path):
    with open(path,encoding='utf-8') as f:return list(csv.DictReader(f))
def curves(data,mode,m):
    return np.array([np.load(OUT/mode/'runs'/f'{m}_{r["seed"]}_evaluations.npz')['ledger'][:,3] for r in data[mode][m]])

def overview(data,methods):
    fig=plt.figure(figsize=(12,4.4),layout='constrained');grid=fig.add_gridspec(1,2)
    for column,mode in enumerate(['nominal','robust']):
        a=[[r['fitness'] for r in data[mode][m]] for m in methods]
        flat=np.concatenate(a);penalized=flat[flat>=1000];feasible=flat[flat<1000]
        if len(penalized) and len(feasible):
            sub=grid[0,column].subgridspec(2,1,height_ratios=[1,3],hspace=.06)
            top=fig.add_subplot(sub[0]);ax=fig.add_subplot(sub[1],sharex=top)
            for part in [top,ax]:part.boxplot(a,tick_labels=methods,showfliers=True)
            top.set(title=mode.capitalize()+' training — broken fitness axis',ylim=(980,max(penalized)*1.025),ylabel='Penalty')
            top.axhline(1000,c='#9b2226',ls=':',lw=1);top.tick_params(axis='x',labelbottom=False,bottom=False)
            top.spines.bottom.set_visible(False)
            ax.set(yscale='log',ylim=(min(feasible)*.94,max(feasible)*1.15),ylabel='Feasible fitness (log scale)')
            for part,y in [(top,0),(ax,1)]:
                for x in [0,1]:part.plot([x-.012,x+.012],[y-.018,y+.018],transform=part.transAxes,color='black',clip_on=False,lw=1)
        else:
            ax=fig.add_subplot(grid[0,column]);ax.boxplot(a,tick_labels=methods,showfliers=True)
            ax.set(yscale='log',title=mode.capitalize()+' training',ylabel='Constrained fitness (log scale)')
        ax.tick_params(axis='x',rotation=25)
    save(fig,'01_fitness_distributions')
    fig,axs=plt.subplots(2,3,figsize=(12,7),layout='constrained');cr=[]
    for ax,m in zip(axs.flat,methods):
        for mode,c in [('nominal','#17669a'),('robust','#c16a17')]:
            a=curves(data,mode,m);q=np.quantile(a,[.25,.5,.75],axis=0);x=np.arange(1,len(q[0])+1)
            ax.plot(x,q[1],color=c,label=mode);ax.fill_between(x,q[0],q[2],color=c,alpha=.16)
            cr.extend({'method':m,'mode':mode,'evaluation':int(xi),'q25':float(ql),'median':float(qm),'q75':float(qh)} for xi,ql,qm,qh in zip(x,*q))
        ax.set(title=m,yscale='log',xlabel='Unique evaluations',ylabel='Best-so-far fitness');ax.legend(fontsize=8)
    save(fig,'02_convergence');write_csv(D/'convergence_quantiles.csv',cr)
    vv=rows(OUT/'validation_summary.csv');fig,axs=plt.subplots(1,3,figsize=(14,4.5),layout='constrained')
    for ax,key,label in zip(axs,['single_axis_mc_passes','one_at_a_time_passes','combined_stress_passes'],['Random single-axis / 300','One-factor boundaries / 54','Combined-axis stress / 90']):
        for j,mode in enumerate(['nominal','robust']):
            a=[[float(r[key]) for r in vv if r['mode']==mode and r['method']==m] for m in methods]
            b=ax.boxplot(a,positions=np.arange(len(methods))+(j-.5)*.3,widths=.24,patch_artist=True)
            for patch in b['boxes']:patch.set_facecolor(['#8eb6d2','#e4b082'][j])
        ax.set(xticks=np.arange(len(methods)),xticklabels=methods,title=label,ylabel='Passed cases');ax.tick_params(axis='x',rotation=30)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        if key=='combined_stress_passes':ax.set_ylim(-1,90)
    axs[0].legend(handles=[Patch(color='#8eb6d2',label='Nominal tuned'),Patch(color='#e4b082',label='Robust tuned')],fontsize=8)
    save(fig,'03_validation_passes')
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
    for m in methods:
        for mode,marker in [('nominal','o'),('robust','^')]:
            rr=[r for r in vv if r['mode']==mode and r['method']==m]
            ax.scatter([float(r['nominal_mean_settling_s']) for r in rr],[float(r['single_axis_mc_passes'])/3 for r in rr],c=COLORS[m],marker=marker,alpha=.55,s=25,label=f'{m} {mode}')
    ax.set(xlabel='Mean nominal settling time (s)',ylabel='Random single-axis pass rate (%)',title='Observed speed and robustness across all seeds')
    ax.legend(ncol=2,fontsize=8,bbox_to_anchor=(1.02,1),loc='upper left');save(fig,'04_speed_robustness')
    pp=rows(OUT/'parameter_selection.csv');fig,axs=plt.subplots(2,3,figsize=(12,6.5),layout='constrained')
    for ax,m in zip(axs.flat,methods):
        rr=[r for r in pp if r['method']==m];ax.bar([str(r['candidate']) for r in rr],[float(r['mean_rank']) for r in rr],color=['#13846c' if r['selected']=='True' else '#a7b8c7' for r in rr])
        ax.set(title=m,xlabel='Predeclared setting index',ylabel='Mean rank (lower is better)',ylim=(0,4.4))
    save(fig,'05_parameter_study')
    cc=rows(OUT/'corner_validation_summary.csv');fig,ax=plt.subplots(figsize=(11,4.4),layout='constrained')
    for j,(mode,label) in enumerate([(a,b) for a in ['nominal','robust'] for b in ['best','median']]):
        rr=[next(r for r in cc if r['mode']==mode and r['method']==m and r['selection']==label) for m in methods]
        ax.bar(np.arange(len(methods))+(j-1.5)*.18,[float(r['passes']) for r in rr],width=.17,label=f'{mode}, {label}')
    ax.set(xticks=np.arange(len(methods)),xticklabels=methods,ylabel='Passed cases / 1536',title='Joint-boundary audit of training-selected controllers',ylim=(0,1650));ax.legend(ncol=2,fontsize=8);save(fig,'06_joint_boundaries')
    if (OUT/'all_eleven_fitness_summary.csv').exists():
        aa=[r for r in rows(OUT/'all_eleven_fitness_summary.csv') if r['scope']=='exploratory_eleven'];labels=['GA','PSO','CSO','DSA','CMA-ES']+methods
        fig,axs=plt.subplots(1,2,figsize=(13,4.8),layout='constrained')
        for ax,mode in zip(axs,['nominal','robust']):
            rr=[next(r for r in aa if r['mode']==mode and r['method']==m) for m in labels]
            ax.bar(labels,[float(r['median']) for r in rr],color=['#9aa9b7']*5+[COLORS[m] for m in methods]);ax.set(yscale='log',title=mode.capitalize(),ylabel='Median training fitness');ax.tick_params(axis='x',rotation=45)
        fig.suptitle('Exploratory comparison: equal final budgets, unequal development effort',fontsize=11);save(fig,'07_eleven_methods')

def method_figures(data,cfg,m):
    folder=P/m;folder.mkdir(exist_ok=True);dd=D/m;dd.mkdir(exist_ok=True)
    reps={mode:selected(data[mode][m]) for mode in ['nominal','robust']}
    # Four real training-selected controllers plus original controller, no averaged gains.
    fig,axs=plt.subplots(2,3,figsize=(13,7),layout='constrained');metrics=[]
    for ax,s in zip(axs.flat,training_scenarios()):
        j=int(np.flatnonzero(s['target'])[0]);col=[1,2,6][j]
        trace_rows=[]
        for mode,color in [('nominal','#17669a'),('robust','#c16a17')]:
            for label,r in reps[mode]:
                met,diag,tr=run(np.asarray(r['gains']),s,cfg,True);y=np.rad2deg(tr[:,col]);t=tr[:,0]-.2
                ax.plot(t,y,c=color,ls='-' if label=='best' else '--',lw=1.25,label=f'{mode} {label} (seed {r["seed"]})')
                metrics.append({'method':m,'mode':mode,'selection':label,'seed':r['seed'],'scenario':s['name'],'rise_s':float(met[j,0]),'settling_s':float(met[j,1]),'settled':bool(met[j,8]),'overshoot_pct':float(met[j,2]*100),'final_error_pct':float(met[j,3]*100),'motor_clipping_pct':float(diag[0]*100)})
                trace_rows.extend({'mode':mode,'selection':label,'seed':r['seed'],'time_from_step_s':float(tt),'response_deg_or_deg_s':float(yy)} for tt,yy in zip(t,y))
        _,_,tr=run(baseline(),s,cfg,True);ax.plot(tr[:,0]-.2,np.rad2deg(tr[:,col]),c='#555',lw=1,ls=':',label='Original controller')
        trace_rows.extend({'mode':'baseline','selection':'original','seed':0,'time_from_step_s':float(tt-.2),'response_deg_or_deg_s':float(yy)} for tt,yy in zip(tr[:,0],np.rad2deg(tr[:,col])))
        ax.axhline(s['target'][j],c='black',ls=':',lw=.8);ax.axhspan(.98*s['target'][j],1.02*s['target'][j],color='gray',alpha=.1)
        ax.set(title=['Roll','Pitch','Yaw rate'][j]+f' {s["target"][j]}'+('°' if j<2 else '°/s'),xlabel='Time from command (s)',ylabel='Angle (°)' if j<2 else 'Rate (°/s)',xlim=(-.025,1))
        write_csv(dd/f'response_{s["name"]}.csv',trace_rows)
    handles,labels=axs.flat[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=3,fontsize=8)
    fig.suptitle(m+': nominal responses, first second');save(fig,'01_responses',folder)
    for ax in axs.flat:ax.set_xlim(-.05,3)
    fig.suptitle(m+': nominal responses, full horizon');save(fig,'07_full_responses',folder);write_csv(dd/'selected_response_metrics.csv',metrics)
    fig,axs=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for ax,mode in zip(axs,['nominal','robust']):
        a=curves(data,mode,m);x=np.arange(1,3265)
        for line in a:ax.plot(x,line,c=COLORS[m],alpha=.16,lw=.65)
        ax.plot(x,np.median(a,axis=0),c=COLORS[m],lw=2,label='Median');ax.set(title=mode.capitalize(),yscale='log',xlabel='Unique evaluations',ylabel='Best-so-far fitness');ax.legend()
    fig.suptitle(m+': all 30 trajectories');save(fig,'02_convergence',folder)
    # Plot individual uncertainty responses for training plants (no misleading average envelope).
    fig,axs=plt.subplots(1,3,figsize=(12,4),layout='constrained');g=np.asarray(reps['robust'][0][1]['gains']);unc=[];slowest=0.
    for j,ax in enumerate(axs):
        cases=[s for s in training_cases() if s['target'][j] in [20,100] and s['target'][j]!=0]
        for k,s in enumerate(cases):
            met,_,tr=run(g,s,cfg,True);slowest=max(slowest,float(met[j,1]));yy=np.rad2deg(tr[:,[1,2,6][j]]);ax.plot(tr[:,0]-.2,yy,c=plt.cm.viridis(k/max(1,len(cases)-1)),lw=1,alpha=.8)
            unc.extend({'scenario':s['name'],'axis':j,'time_from_step_s':float(t-.2),'response_deg_or_deg_s':float(y)} for t,y in zip(tr[:,0],yy))
        ax.axhline([20,20,100][j],c='black',ls=':',lw=.8);ax.set(title=['Roll 20°','Pitch 20°','Yaw rate 100°/s'][j],xlabel='Time from command (s)',ylabel='Angle (°)' if j<2 else 'Rate (°/s)',xlim=(-.05,3))
    for ax in axs:ax.set_xlim(-.025,max(1.,min(3.,1.15*slowest)))
    fig.suptitle(m+': best robust controller, nine training plants (individual traces)',fontsize=11);save(fig,'03_uncertain_responses',folder);write_csv(dd/'uncertain_training_traces.csv',unc)
    fig,axs=plt.subplots(2,3,figsize=(12,6.5),layout='constrained');act=[];slowest=0.
    for j,s in enumerate([training_scenarios()[k] for k in [1,3,5]]):
        met,_,tr=run(g,s,cfg,True);slowest=max(slowest,float(met[j,1]))
        for k in range(4):axs[0,j].plot(tr[:,0]-.2,tr[:,23+k],lw=1,label=f'Motor {k+1}')
        axs[0,j].axhline(0,c='black',ls=':');axs[0,j].axhline(1,c='black',ls=':');axs[0,j].set(title=s['name'].replace('_',' '),ylabel='Clipped motor command',ylim=(-.03,1.03))
        for k in range(3):axs[1,j].plot(tr[:,0]-.2,tr[:,16+k],lw=1,label=['Roll','Pitch','Yaw'][k])
        axs[1,j].set(xlabel='Time from command (s)',ylabel='Controller output')
        for line in tr:act.append({'scenario':s['name'],'time_from_step_s':float(line[0]-.2),**{f'raw_motor{k+1}':float(line[19+k]) for k in range(4)},**{f'motor{k+1}':float(line[23+k]) for k in range(4)},**{f'rotor{k+1}_rad_s':float(line[28+k]) for k in range(4)},**{f'control{k}':float(line[16+k]) for k in range(3)}})
    for ax in axs.flat:ax.set_xlim(-.025,max(1.,min(3.,1.15*slowest)))
    axs[0,0].legend(fontsize=7,ncol=2);axs[1,0].legend(fontsize=7);fig.suptitle(m+': best robust controller actuation');save(fig,'04_actuation',folder);write_csv(dd/'actuation.csv',act)
    vals=rows(OUT/'validation_summary.csv');fig,axs=plt.subplots(1,3,figsize=(11,4),layout='constrained')
    for ax,key,title in zip(axs,['single_axis_mc_passes','one_at_a_time_passes','combined_stress_passes'],['Random cases / 300','One-factor edges / 54','Combined stress / 90']):
        ax.boxplot([[float(r[key]) for r in vals if r['method']==m and r['mode']==mode] for mode in ['nominal','robust']],tick_labels=['Nominal','Robust']);ax.set(title=title,ylabel='Passed cases')
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        if key=='combined_stress_passes':ax.set_ylim(-1,90)
    fig.suptitle(m+': independent validation across 30 seeds');save(fig,'05_validation',folder)
    sens=rows(OUT/'one_factor_sensitivity.csv');fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    names=list(dict.fromkeys(r['case'] for r in sens if r['method']==m));factors=list(dict.fromkeys(n.rsplit('_',2)[0][4:] for n in names))
    for ax,mode in zip(axs,['nominal','robust']):
        mat=[]
        for factor in factors:
            mat.append([np.mean([r['feasible']=='True' for r in sens if r['method']==m and r['mode']==mode and r['case']==f'oat_{factor}_{edge}_{axis}'])*100 for edge in [0,1] for axis in range(3)])
        im=ax.imshow(mat,vmin=0,vmax=100,cmap='RdYlGn',aspect='auto');ax.set(yticks=range(len(factors)),yticklabels=factors,xticks=range(6),xticklabels=['R−','P−','Y−','R+','P+','Y+'],title=mode.capitalize()+' tuned')
        for i,row in enumerate(mat):
            for j,value in enumerate(row):
                rgb=im.cmap(value/100)[:3];light=sum(c*w for c,w in zip(rgb,[.2126,.7152,.0722]))
                ax.text(j,i,f'{value:.0f}',ha='center',va='center',fontsize=8,color='white' if light<.45 else 'black')
    fig.colorbar(im,ax=axs,label='Controllers passing case (%)',shrink=.8);fig.suptitle(m+': one-factor boundary sensitivity; signs indicate factor bound',fontsize=10);save(fig,'06_sensitivity',folder)

def main():
    assert read(OUT/'analysis_complete.json')['complete'];P.mkdir(exist_ok=True);D.mkdir(exist_ok=True)
    marker=OUT.parent/'METHOD.json';methods=[read(marker)['method']] if marker.exists() else METHODS
    data={mode:{m:[read(OUT/mode/'runs'/f'{m}_{s}.json') for s in SEEDS] for m in methods} for mode in ['nominal','robust']}
    cfg=read(OUT/'contract.json')['configuration']
    if not marker.exists():overview(data,methods)
    for m in methods:method_figures(data,cfg,m);print('Figures: '+m,flush=True)
    (OUT/'plots_complete.json').write_text(json.dumps({'complete':True,'png_count':len(list(P.rglob('*.png')))}),encoding='utf-8')
if __name__=='__main__':main()
