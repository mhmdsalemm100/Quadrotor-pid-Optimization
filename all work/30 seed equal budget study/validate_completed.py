"""Validate a snapshot of completed runs; analyze.py reuses these records."""
from concurrent.futures import ThreadPoolExecutor
import json
import numpy as np
from benchmark import ROOT,METHODS,SEEDS
from analyze import uncertainty_cases
from study import evaluate,training_scenarios,validation_scenarios

def main():
    out=ROOT/'results'; cfg=json.loads((out/'contract.json').read_text())['configuration']; dest=out/'validation'; dest.mkdir(exist_ok=True)
    cases=validation_scenarios()+uncertainty_cases()
    paths=[out/'runs'/f'{m}_{s}.json' for m in METHODS for s in SEEDS]
    paths=[p for p in paths if p.exists() and not (dest/p.name).exists()]
    def one(path):
        r=json.loads(path.read_text()); g=np.array(r['gains']); score=evaluate(g,training_scenarios(),cfg)
        assert abs(score-r['fitness'])<1e-11
        _,details=evaluate(g,cases,cfg,True)
        v={'method':r['method'],'seed':r['seed'],'training_fitness':score,
           'held_out_passes':sum(z['feasible'] for z in details[:18]),'single_axis_passes':sum(z['feasible'] for z in details[18:78]),
           'combined_passes':sum(z['feasible'] for z in details[78:]),'details':details}
        (dest/path.name).write_text(json.dumps(v,indent=2)); return path.name
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i,name in enumerate(pool.map(one,paths)):
            if i%10==0: print(f'Validated snapshot {i+1}/{len(paths)}: {name}',flush=True)
    print(f'Completed {len(paths)} validation records.',flush=True)

if __name__=='__main__': main()
