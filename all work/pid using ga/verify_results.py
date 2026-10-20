"""Independent delivery audit of saved optimization results and reproducibility."""
import hashlib
import json
from pathlib import Path
import unittest
import numpy as np
from PIL import Image
from model import baseline, coefficients
from study import evaluate, training_scenarios

ROOT=Path(__file__).resolve().parent

def main():
    out=ROOT/'results'; cfg=json.loads((out/'configuration.json').read_text())
    best=json.loads((out/'best_gains.json').read_text()); g=np.array(list(best['gains'].values()))
    score=evaluate(g,training_scenarios(),cfg)
    assert abs(score-best['training_fitness'])<1e-11
    assert score<1000, 'Exported main candidate does not meet all training constraints.'
    c=coefficients(g,cfg['controller_dt_s'])
    for axis in ['roll','pitch']:
        np.testing.assert_allclose(c[axis]['numerator'],best[axis+'_transfer_function']['numerator'])
    for path in out.glob('run_*.json'):
        data=json.loads(path.read_text()); curve=[r['best'] for r in data['history']]
        assert np.all(np.diff(curve)<=1e-10), f'Elitism violated: {path.name}'
    figs=list((out/'plots').glob('*.png'))
    assert len(figs)>=9
    for path in figs:
        with Image.open(path) as im: im.verify()
    from test_study import ModelTests
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ModelTests)
    with (out/'test_results.txt').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    assert result.wasSuccessful()
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in ROOT.iterdir() if p.is_file() and p.suffix in ['.py','.json','.md','.txt','.cmd']}
    manifest={'tests_run':result.testsRun,'test_failures':len(result.failures),
              'test_errors':len(result.errors),'recomputed_main_fitness':score,
              'figures_verified':len(figs),'file_hashes':hashes}
    (out/'verification.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({k:v for k,v in manifest.items() if k!='file_hashes'},indent=2))

if __name__=='__main__': main()
