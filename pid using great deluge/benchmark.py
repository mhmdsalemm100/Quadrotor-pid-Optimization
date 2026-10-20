"""Five optimizers with one strict, unique-evaluation budget and shared objective."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,time,hashlib,argparse
import numpy as np
import cma
from model import baseline
from study import encode,decode,evaluate,training_scenarios,write_csv
from dsa_reference import communicate,predation_radius

ROOT=Path(__file__).resolve().parent
METHODS=['GA','PSO','CSO','DSA','CMA-ES']
SEEDS=[11,29,47]+list(range(101,128))
FOLDERS=['pid using ga','pid using pso','pid using cat swarm','pid using dolphin swarm','pid using cma es']

class BudgetExhausted(Exception): pass

class Budget:
    def __init__(self,cfg,limit,pool,objective=None):
        self.cfg=cfg; self.limit=limit; self.pool=pool; self.objective=objective
        self.cache={}; self.best=float('inf'); self.point=None; self.ledger=[]; self.history=[]
        self.iteration=0; self.proposals=0; self.start=time.perf_counter(); self.stalls=0
    def raw(self,p):
        g=decode(p,self.cfg)
        f=self.objective(g) if self.objective else evaluate(g,training_scenarios(),self.cfg)
        if not np.isfinite(f): raise FloatingPointError('Nonfinite objective')
        return float(f)
    def score(self,points):
        points=np.asarray(points); self.proposals+=len(points)
        assert np.isfinite(points).all() and (points>=0).all() and (points<=1).all()
        keys=[tuple(np.round(p,13)) for p in points]; new={}
        for k,p in zip(keys,points):
            if k not in self.cache and k not in new: new[k]=p.copy()
        items=list(new.items())[:self.limit-len(self.cache)]
        vals=list(self.pool.map(self.raw,[p for _,p in items])) if self.pool else [self.raw(p) for _,p in items]
        for (key,p),f in zip(items,vals):
            self.cache[key]=f
            if f<self.best: self.best=f; self.point=p.copy()
            self.ledger.append([len(self.cache),self.iteration,f,self.best,*p.tolist()])
        self.history.append({'iteration':self.iteration,'evaluations':len(self.cache),'best':self.best,'proposals':self.proposals})
        if len(self.cache)==self.limit: raise BudgetExhausted()
        self.stalls=0 if items else self.stalls+1
        if self.stalls>100: raise RuntimeError('No new evaluations for 100 batches; no fake padding allowed')
        return np.array([self.cache[k] for k in keys])
    def progress(self): return max(0,min(1,(len(self.cache)-64)/(self.limit-64)))

def initial_population(seed,cfg,n=64):
    rng=np.random.default_rng(seed); x=rng.random((n,8))
    for j in range(8): x[:,j]=(rng.permutation(n)+rng.random(n))/n
    x[0]=encode(baseline(cfg['controller_dt_s']),cfg)
    return rng,x

def optimize(method,seed,cfg,out,limit=3264,pool=None,objective=None):
    rng,x=initial_population(seed,cfg); n,d=x.shape
    initial_hash=hashlib.sha256(x.tobytes()).hexdigest()
    b=Budget(cfg,limit,pool,objective); state=[]
    # Preserve pre-initial-evaluation random consumption of the previous swarms.
    if method in ['PSO','CSO']: velocity=rng.uniform(-.1,.1,(n,d))
    try:
        f=b.score(x)
        if method=='PSO': personal=x.copy(); pf=f.copy()
        if method=='DSA': k=x.copy(); kf=f.copy(); timers=np.full((n,n),1000000,dtype=np.int64)
        if method=='CMA-ES':
            es=cma.CMAEvolutionStrategy(x[np.argmin(f)].tolist(),.25,{'popsize':64,'bounds':[0.,1.],
                'CMA_active':True,'CMA_diagonal':False,'randn':np.random.RandomState(seed).randn,
                'seed':seed,'verbose':-9,'verb_log':0,'verb_disp':0})
        while True:
            b.iteration+=1
            if method=='GA':
                order=np.argsort(f,kind='stable'); x=x[order]; f=f[order]
                sigma=.14+(.035-.14)*b.progress(); children=[p.copy() for p in x[:4]]
                def parent():
                    ids=rng.integers(n,size=3); return x[ids[np.argmin(f[ids])]]
                while len(children)<n:
                    if rng.random()<.08: children.append(rng.random(d)); continue
                    a=parent(); z=parent(); child=a.copy()
                    if rng.random()<.9:
                        alpha=rng.uniform(-.15,1.15,d); child=alpha*a+(1-alpha)*z
                    child+=(rng.random(d)<.25)*rng.normal(0,sigma,d)
                    children.append(np.clip(child,0,1))
                x=np.array(children); f=b.score(x)
            elif method=='PSO':
                inertia=.9+(.4-.9)*b.progress()
                velocity=inertia*velocity+1.7*rng.random((n,d))*(personal-x)+1.7*rng.random((n,d))*(b.point-x)
                velocity=np.clip(velocity,-.2,.2); trial=x+velocity; hit=(trial<0)|(trial>1)
                x=np.clip(trial,0,1); velocity[hit]*=-.5; f=b.score(x)
                improve=f<pf; personal[improve]=x[improve]; pf[improve]=f[improve]
            elif method=='CSO':
                tracing=set(rng.choice(n,13,replace=False)); points=[]; spans=[]; nv=velocity.copy(); g=b.point.copy()
                for i in range(n):
                    begin=len(points)
                    if i in tracing:
                        nv[i]=np.clip(velocity[i]+2*rng.random(d)*(g-x[i]),-.2,.2)
                        trial=x[i]+nv[i]; nv[i,(trial<0)|(trial>1)]*=-.5; points.append(np.clip(trial,0,1))
                    else:
                        points.append(x[i].copy())
                        for _ in range(4):
                            trial=x[i].copy(); dims=rng.choice(d,4,replace=False)
                            trial[dims]*=1+rng.choice(np.array([-1.,1.]),4)*.2; points.append(np.clip(trial,0,1))
                    spans.append((begin,len(points)))
                points=np.array(points); scores=b.score(points)
                for i,(a,z) in enumerate(spans):
                    w=scores[a:z].max()-scores[a:z]; prob=w/w.sum() if w.sum()>0 else np.full(z-a,1/(z-a))
                    idx=a if i in tracing else a+int(rng.choice(z-a,p=prob))
                    x[i]=points[idx]; f[i]=scores[idx]
                velocity=nv
            elif method=='DSA':
                directions=rng.normal(size=(n,2,d)); directions/=np.linalg.norm(directions,axis=2,keepdims=True)
                probes=np.clip(x[:,None,None,:]+.08*directions[:,:,None,:]*np.arange(1,3)[None,None,:,None],0,1)
                scores=b.score(probes.reshape(-1,d)).reshape(n,4)
                ids=np.argmin(scores,axis=1); local=probes.reshape(n,4,d)[np.arange(n),ids]; lf=scores[np.arange(n),ids]
                improved=lf<kf; k[improved]=local[improved]; kf[improved]=lf[improved]
                k,kf,timers,_=communicate(x,k,kf,timers,.08,10.,1000000)
                trial=np.empty_like(x)
                for i in range(n):
                    dist=np.linalg.norm(x[i]-k[i]); q=np.linalg.norm(local[i]-k[i])
                    if dist<=.16: trial[i]=k[i]+(x[i]-k[i])*(1-2/3.)
                    else:
                        direction=rng.normal(size=d); direction/=np.linalg.norm(direction)
                        trial[i]=k[i]+direction*predation_radius(dist,q,kf[i],lf[i],3.)
                x=np.clip(trial,0,1); f=b.score(x); improved=f<kf; k[improved]=x[improved]; kf[improved]=f[improved]
            elif method=='CMA-ES':
                samples=es.ask(); x=np.array(samples); f=b.score(x); es.tell(samples,f.tolist())
                state.append({'iteration':b.iteration,'sigma':float(es.sigma),'mean':es.mean.tolist(),
                              'stop_flags':{str(k):str(v) for k,v in es.stop().items()}})
    except BudgetExhausted: pass
    assert len(b.cache)==limit
    result={'method':method,'seed':seed,'budget':limit,'unique_evaluations':len(b.cache),
            'proposals_including_final_batch':b.proposals,'fitness':b.best,'gains':decode(b.point,cfg).tolist(),
            'initial_population_sha256':initial_hash,'seconds':time.perf_counter()-b.start,
            'last_iteration':b.iteration,'stop':'strict budget; final batch may be partial', 'history':b.history}
    if out is not None:
        out=Path(out); out.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(out/f'{method}_{seed}_evaluations.npz',ledger=np.array(b.ledger))
        (out/f'{method}_{seed}.json').write_text(json.dumps(result,indent=2))
        if state: (out/f'{method}_{seed}_distribution.json').write_text(json.dumps(state,indent=2))
    return result

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--budget',type=int,default=3264); parser.add_argument('--resume',action='store_true'); args=parser.parse_args()
    cfg=json.loads((ROOT/'config.json').read_text()); out=ROOT/'results'; out.mkdir(exist_ok=True); runs=out/'runs'; runs.mkdir(exist_ok=True)
    contract={'budget':args.budget,'seeds':SEEDS,'methods':METHODS,'configuration':cfg,
        'code_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['benchmark.py','model.py','study.py','dsa_reference.py']}}
    path=out/'contract.json'
    if path.exists() and json.loads(path.read_text())!=contract: raise ValueError('Contract changed: use a new output directory')
    path.write_text(json.dumps(contract,indent=2))
    evaluate(baseline(),training_scenarios(),cfg) # compile once before worker calls
    done=0; started=time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        for seed in SEEDS:
            for method in METHODS:
                file=runs/f'{method}_{seed}.json'
                result=json.loads(file.read_text()) if args.resume and file.exists() else optimize(method,seed,cfg,runs,args.budget,pool)
                done+=1
                print(f'{done}/150 {method} seed={seed} F={result["fitness"]:.8f} evaluations={result["unique_evaluations"]} elapsed={time.perf_counter()-started:.1f}s',flush=True)
                (out/'progress.json').write_text(json.dumps({'completed':done,'total':150,'method':method,'seed':seed,'elapsed_s':time.perf_counter()-started},indent=2))
    print('All 150 searches complete.',flush=True)

if __name__=='__main__': main()
