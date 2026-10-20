"""Resume the frozen benchmark using three independent worker processes."""
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor,as_completed
from pathlib import Path
import json,time,hashlib
from benchmark import ROOT,METHODS,SEEDS,optimize
from model import baseline
from study import evaluate,training_scenarios

def worker(task):
    method,seed,cfg,budget=task
    evaluate(baseline(),training_scenarios(),cfg)
    with ThreadPoolExecutor(max_workers=4) as pool:
        return optimize(method,seed,cfg,ROOT/'results/runs',budget,pool)

def main():
    out=ROOT/'results'; contract=json.loads((out/'contract.json').read_text())
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in contract['code_sha256'].items())
    tasks=[(m,s,contract['configuration'],contract['budget']) for s in SEEDS for m in METHODS if not (out/'runs'/f'{m}_{s}.json').exists()]
    done=150-len(tasks); start=time.perf_counter()
    (out/'execution_driver.json').write_text(json.dumps({'processes':3,'fitness_threads_per_process':4,'resumed_completed_runs':done,
        'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'note':'Independent runs only; optimizer protocol unchanged. One interrupted incomplete run was restarted.'},indent=2))
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(worker,t) for t in tasks]
        for future in as_completed(futures):
            r=future.result(); done+=1
            print(f'{done}/150 {r["method"]} seed={r["seed"]} F={r["fitness"]:.8f} budget={r["unique_evaluations"]} parallel_elapsed={time.perf_counter()-start:.1f}s',flush=True)
            (out/'progress.json').write_text(json.dumps({'completed':done,'total':150,'method':r['method'],'seed':r['seed'],'elapsed_parallel_s':time.perf_counter()-start},indent=2))
    print('All 150 searches complete.',flush=True)

if __name__=='__main__': main()
