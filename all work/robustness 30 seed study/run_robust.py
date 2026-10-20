"""Run/resume all 150 robust optimizations under a hash-frozen contract."""
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor,as_completed
from pathlib import Path
import argparse,json,time,hashlib,os
from benchmark import METHODS,SEEDS,optimize
from robust_protocol import ROOT,FACTORS,TRAIN_SEED,TEST_SEED,training_cases,validation_cases,RobustObjective
from model import baseline

def worker(task):
    method,seed,cfg,budget=task
    objective=RobustObjective(cfg); objective(baseline())
    with ThreadPoolExecutor(max_workers=4) as pool:
        return optimize(method,seed,cfg,ROOT/'results/runs',budget,pool,objective)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--processes',type=int,default=3); args=parser.parse_args()
    out=ROOT/'results'; out.mkdir(exist_ok=True)
    cfg=json.loads((ROOT/'config.json').read_text())
    contract={'configuration':cfg,'budget':3264,'seeds':SEEDS,'methods':METHODS,
        'training_cases':training_cases(),'validation_cases':validation_cases(),
        'uncertainty_factors':FACTORS,'training_seed':TRAIN_SEED,'validation_seed':TEST_SEED,
        'code_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
            ['benchmark.py','model.py','study.py','robust_protocol.py','run_robust.py','dsa_reference.py']}}
    path=out/'contract.json'
    if path.exists() and json.loads(path.read_text())!=json.loads(json.dumps(contract)):
        raise ValueError('Frozen contract differs; do not mix results')
    path.write_text(json.dumps(contract,indent=2))
    tasks=[(m,s,cfg,3264) for s in SEEDS for m in METHODS if not (out/'runs'/f'{m}_{s}.json').exists()]
    done=150-len(tasks); start=time.perf_counter()
    (out/'execution.json').write_text(json.dumps({'processes':args.processes,'threads_per_process':4,
        'pid':os.getpid(),'resumed_completed':done},indent=2))
    with ProcessPoolExecutor(max_workers=args.processes) as pool:
        pending=[pool.submit(worker,t) for t in tasks]
        for future in as_completed(pending):
            r=future.result(); done+=1
            progress={'completed':done,'total':150,'method':r['method'],'seed':r['seed'],
                      'fitness':r['fitness'],'elapsed_this_session_s':time.perf_counter()-start}
            temp=out/'progress.tmp'; temp.write_text(json.dumps(progress,indent=2)); temp.replace(out/'progress.json')
            print(json.dumps(progress),flush=True)
    print('COMPLETE: 150 robust searches, 489600 unique evaluations, 14688000 scenario simulations.',flush=True)

if __name__=='__main__': main()
