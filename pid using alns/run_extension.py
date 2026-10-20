"""Separate development selection followed by frozen 30-seed experiments."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import argparse,json,hashlib,time,os
import numpy as np
from scipy.stats import rankdata
from methods import METHODS,SEEDS,PILOT_SEEDS,parameter_grid,optimize
from robust_protocol import training_cases,validation_cases
from study import training_scenarios,evaluate,write_csv
from model import baseline
R=Path(__file__).resolve().parent

def dump(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(x,indent=2),encoding='utf-8');t.replace(p)

def worker(task):
 stage,mode,m,seed,params,cid=task;cfg=json.loads((R/'config.json').read_text())
 cases=training_scenarios() if mode=='nominal' else training_cases()
 objective=lambda g:evaluate(g,cases,cfg)
 objective(baseline())
 out=R/'results'/stage/(f'candidate_{cid}' if stage=='pilot' else 'runs')/mode
 if stage=='main':out=R/'results'/mode/'runs'
 file=out/f'{m}_{seed}.json'
 if file.exists():
  r=json.loads(file.read_text());assert r['parameters']==params and r['unique_evaluations']==3264
  assert (out/f'{m}_{seed}_evaluations.npz').exists()
 else:r=optimize(m,seed,cfg,params,out,3264,objective)
 return {'stage':stage,'mode':mode,'method':m,'seed':seed,'candidate':cid,'fitness':r['fitness'],'seconds':r['seconds']}

def execute(tasks,processes,stage):
 start=time.perf_counter();rows=[]
 with ProcessPoolExecutor(max_workers=processes) as pool:
  futures=[pool.submit(worker,t) for t in tasks]
  for future in as_completed(futures):
   r=future.result();rows.append(r);p={'stage':stage,'completed':len(rows),'total':len(tasks),'last':r,'elapsed_s':time.perf_counter()-start}
   dump(R/'results/progress.json',p);print(json.dumps(p),flush=True)
 return rows

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--processes',type=int,default=6);ap.add_argument('--pilot-only',action='store_true');args=ap.parse_args()
 cfg=json.loads((R/'config.json').read_text());files=['model.py','study.py','benchmark.py','robust_protocol.py','methods.py','run_extension.py']
 contract={'methods':METHODS,'main_seeds':SEEDS,'development_seeds':PILOT_SEEDS,'budget_per_run':3264,'pilot_candidates':{m:parameter_grid(m) for m in METHODS},'configuration':cfg,
 'training_cases':{'nominal':training_scenarios(),'robust':training_cases()},'validation_cases':validation_cases(),
 'selection':'minimum mean within-mode, within-development-seed rank across 4 candidate settings; ties by candidate index; one setting per method across both modes',
 'pilot_unique_evaluations':144*3264,'main_unique_evaluations':360*3264,
 'comparison_caveat':'Original five methods did not receive this new development-grid budget; final budgets match, total development budgets do not.',
 'code_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in files}}
 cp=R/'results/contract.json'
 if cp.exists():assert json.loads(cp.read_text())==contract,'Frozen contract changed: refuse to mix results'
 else:dump(cp,contract)
 dump(R/'results/execution.json',{'pid':os.getpid(),'processes':args.processes,'started_unix':time.time(),'threads_per_search':1})
 tasks=[('pilot',mode,m,s,p,cid) for m in METHODS for cid,p in enumerate(parameter_grid(m)) for mode in ['nominal','robust'] for s in PILOT_SEEDS]
 rows=execute(tasks,args.processes,'pilot');write_csv(R/'results/pilot_runs.csv',rows);settings={};selection=[]
 for m in METHODS:
  mat=np.array([[next(r['fitness'] for r in rows if r['method']==m and r['mode']==mode and r['seed']==s and r['candidate']==cid) for cid in range(4)] for mode in ['nominal','robust'] for s in PILOT_SEEDS])
  ranks=np.array([rankdata(x,method='average') for x in mat]);means=ranks.mean(axis=0);winner=int(np.argmin(means));settings[m]=parameter_grid(m)[winner]
  for cid in range(4):selection.append({'method':m,'candidate':cid,'mean_rank':float(means[cid]),'selected':cid==winner,'parameters':json.dumps(parameter_grid(m)[cid]),'nominal_median_fitness':float(np.median(mat[:3,cid])),'robust_median_fitness':float(np.median(mat[3:,cid]))})
 sf=R/'results/selected_parameters.json'
 if sf.exists():assert json.loads(sf.read_text())==settings
 else:dump(sf,settings)
 write_csv(R/'results/parameter_selection.csv',selection)
 print('PARAMETERS FROZEN: '+json.dumps(settings),flush=True)
 if args.pilot_only:return
 tasks=[('main',mode,m,s,settings[m],None) for s in SEEDS for mode in ['nominal','robust'] for m in METHODS]
 rows=execute(tasks,args.processes,'main');write_csv(R/'results/all_main_runs.csv',rows)
 dump(R/'results/search_complete.json',{'complete':True,'runs':len(rows),'unique_evaluations':len(rows)*3264,'validation_complete':False})
 print('SEARCH COMPLETE. Validation and analysis remain required.',flush=True)
if __name__=='__main__':main()
