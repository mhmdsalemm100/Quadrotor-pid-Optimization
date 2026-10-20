"""Six explicitly specified bounded continuous-search variants.
All operate in normalized log-gain coordinates; the original objective is unchanged.
"""
from pathlib import Path
import json,time,hashlib
import numpy as np
from benchmark import Budget,BudgetExhausted,initial_population
from study import decode
METHODS=['GDA','TA','ALNS','VND','SBRS','PRW']
FULL_NAMES={'GDA':'Great Deluge Algorithm','TA':'Threshold Accepting','ALNS':'Adaptive Large Neighborhood Search','VND':'Variable Neighborhood Descent (budgeted multistart)','SBRS':'Shrinking Ball Random Search','PRW':'Pure Random Walk (constant proposal step)'}
SEEDS=[11,29,47]+list(range(101,128))
PILOT_SEEDS=[5011,5021,5039]

def reflect(x):
    y=np.mod(x,2.);return np.where(y<=1.,y,2.-y)

def direction(rng,d):
    while True:
        z=rng.normal(size=d);norm=np.linalg.norm(z)
        if norm>0:return z/norm

def merit(f):return float(np.log1p(f))

def accept(method,current,trial,level):
    if method=='PRW':return True
    if method=='GDA':return trial<=current or merit(trial)<=level
    if method in ['TA','ALNS']:return merit(trial)<=merit(current)+level
    return trial<current

def parameter_grid(method):
    if method=='GDA':return [{'step':s,'water_slack':a} for s in [.03,.12] for a in [.05,.25]]
    if method=='TA':return [{'step':s,'threshold0':a} for s in [.03,.12] for a in [.02,.20]]
    if method=='ALNS':return [{'repair_sigma':s,'reaction':r,'threshold0':.05,'segment':64} for s in [.04,.16] for r in [.1,.4]]
    if method=='VND':return [{'radius':r,'neighborhood_order':o} for r in [.05,.20] for o in ['large_to_small','small_to_large']]
    if method=='SBRS':return [{'radius0':r,'radius_ratio':q} for r in [.15,.50] for q in [.01,.1]]
    if method=='PRW':return [{'step':r} for r in [.01,.04,.12,.30]]
    raise ValueError(method)

def optimize(method,seed,cfg,params,out=None,limit=3264,objective=None):
    if method not in METHODS:raise ValueError(method)
    if limit<65:raise ValueError('At least 65 evaluations required for shared initialization plus search')
    rng,x0=initial_population(seed,cfg);init_hash=hashlib.sha256(x0.tobytes()).hexdigest()
    b=Budget(cfg,limit,None,objective);events=[];restarts=0;accepted=0
    try:
        f0=b.score(x0);idx=int(np.argmin(f0));x=x0[idx].copy();f=float(f0[idx]);initial_best=f
        water0=merit(f)+params.get('water_slack',0.)
        wd=np.ones(4);wr=np.ones(3);sd=np.zeros(4);sr=np.zeros(3);nd=np.zeros(4);nr=np.zeros(3)
        radii=params.get('radius',.1)*np.array([1.,.5,.1,.02])
        if params.get('neighborhood_order')=='small_to_large':radii=radii[::-1]
        k=0;coord=0;cycle_start=x.copy()
        while True:
            b.iteration+=1;p=b.progress();level=0.;opd=-1;opr=-1;restart=False
            if method in ['GDA','TA','PRW']:
                trial=reflect(x+params['step']*direction(rng,len(x)))
                level=water0*(1-p) if method=='GDA' else params.get('threshold0',0.)*(1-p)
            elif method=='SBRS':
                radius=params['radius0']*params['radius_ratio']**p
                trial=reflect(x+radius*rng.random()**(1/len(x))*direction(rng,len(x)))
                level=radius
            elif method=='VND':
                if k==len(radii):
                    trial=rng.random(len(x));restart=True;restarts+=1;level=-1.
                else:
                    trial=x.copy();trial[coord//2]+=radii[k]*(1 if coord%2==0 else -1);trial=reflect(trial);level=float(radii[k])
            else:
                opd=int(rng.choice(4,p=wd/wd.sum()));opr=int(rng.choice(3,p=wr/wr.sum()))
                dims=rng.choice(len(x),[1,2,4,8][opd],replace=False);trial=x.copy()
                if opr==0:trial[dims]=rng.random(len(dims))
                elif opr==1:trial[dims]+=rng.normal(0,params['repair_sigma'],len(dims))
                else:
                    elite=np.array([row[4:] for row in sorted(b.ledger,key=lambda row:row[2])[:16]])
                    a,c,d=elite[rng.choice(len(elite),3,replace=False)]
                    trial[dims]=a[dims]+.5*(c[dims]-d[dims])
                trial=reflect(trial);level=params['threshold0']*(1-p)
            old_best=b.best;old_f=f;ft=float(b.score([trial])[0]);take=restart or accept(method,f,ft,level)
            if take:x=trial;f=ft;accepted+=1
            events.append([len(b.cache),old_f,ft,f,int(take),float(level),opd,opr,int(restart)])
            if method=='VND':
                if restart or take:k=0;coord=0
                else:
                    coord+=1
                    if coord==2*len(x):coord=0;k+=1
            if method=='ALNS':
                reward=5. if ft<old_best else (3. if ft<old_f else (1. if take else .1))
                sd[opd]+=reward;sr[opr]+=reward;nd[opd]+=1;nr[opr]+=1
                if b.iteration%params['segment']==0:
                    rho=params['reaction'];wd=(1-rho)*wd+rho*np.divide(sd,nd,out=wd.copy(),where=nd>0);wr=(1-rho)*wr+rho*np.divide(sr,nr,out=wr.copy(),where=nr>0)
                    sd[:]=0;sr[:]=0;nd[:]=0;nr[:]=0
    except BudgetExhausted:pass
    assert len(b.cache)==limit
    r={'method':method,'variant':FULL_NAMES[method],'seed':seed,'parameters':params,'budget':limit,'unique_evaluations':len(b.cache),
       'fitness':b.best,'gains':decode(b.point,cfg).tolist(),'initial_population_sha256':init_hash,'seconds':time.perf_counter()-b.start,
       'last_iteration':b.iteration,'history':b.history,'restarts':restarts,'accepted_moves_before_final_evaluation':accepted,
       'proposals_including_final_batch':b.proposals,'stop':'strict evaluation budget; final evaluated point retained in best archive even if no state update follows',
       'acceptance_score':'log(1+fitness) for GDA/TA/ALNS; original constrained fitness for reporting and best-point selection'}
    if method=='ALNS':r['final_destroy_weights']=wd.tolist();r['final_repair_weights']=wr.tolist()
    if out is not None:
        out=Path(out);out.mkdir(parents=True,exist_ok=True);stem=out/f'{method}_{seed}'
        with stem.with_suffix('.npz.tmp').open('wb') as file:np.savez_compressed(file,ledger=np.array(b.ledger),transitions=np.array(events))
        stem.with_suffix('.npz.tmp').replace(out/f'{method}_{seed}_evaluations.npz')
        tmp=stem.with_suffix('.json.tmp');tmp.write_text(json.dumps(r,indent=2),encoding='utf-8');tmp.replace(stem.with_suffix('.json'))
    return r
