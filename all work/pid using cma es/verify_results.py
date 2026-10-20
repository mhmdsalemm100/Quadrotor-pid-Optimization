"""Independent delivery audit of saved optimization results and reproducibility."""
import hashlib
import csv
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
        assert np.all(np.diff(curve)<=1e-10), f'Global-best memory violated: {path.name}'
        suffix=path.stem.removeprefix('run_')
        ledger=list(csv.DictReader((out/f'evaluations_{suffix}.csv').open()))
        assert len(ledger)==data['unique_evaluations']
        assert abs(min(float(r['fitness']) for r in ledger)-data['fitness'])<1e-11
        states=json.loads((out/f'distribution_{suffix}.json').read_text())
        assert len(states)==len(data['history'])
        for state in states:
            eigenvalues=np.linalg.eigvalsh(np.array(state['covariance']))
            assert np.all(eigenvalues>0) and state['sigma']>0
        for row in ledger:
            assert all(p['lower']-1e-12<=float(row[p['name']])<=p['upper']+1e-12 for p in cfg['parameters'])
    figs=list((out/'plots').glob('*.png'))
    assert len(figs)>=9
    for path in figs:
        with Image.open(path) as im: im.verify()
    from test_study import ModelTests
    from test_cmaes import CMAESTests
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(ModelTests), unittest.defaultTestLoader.loadTestsFromTestCase(CMAESTests)])
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
