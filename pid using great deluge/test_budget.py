import unittest,json,contextlib,io
from pathlib import Path
import numpy as np
from benchmark import METHODS,optimize,Budget,BudgetExhausted
from study import encode

class BudgetTests(unittest.TestCase):
    def test_partial_batches_all_methods_repeat_and_bounds(self):
        cfg=json.loads((Path(__file__).parent/'config.json').read_text()); calls=0
        def objective(g):
            nonlocal calls
            calls+=1
            self.assertTrue(all(p['lower']-1e-12<=v<=p['upper']+1e-12 for p,v in zip(cfg['parameters'],g)))
            return float(np.sum((encode(g,cfg)-.37)**2))
        hashes=[]
        for method in METHODS:
            calls=0; a=optimize(method,17,cfg,None,197,None,objective)
            self.assertEqual(calls,197); self.assertEqual(a['unique_evaluations'],197)
            b=optimize(method,17,cfg,None,197,None,objective)
            self.assertEqual(a['fitness'],b['fitness']); self.assertEqual(a['gains'],b['gains'])
            self.assertTrue(np.all(np.diff([h['best'] for h in a['history']])<=0))
            hashes.append(a['initial_population_sha256'])
        self.assertEqual(len(set(hashes)),1)
    def test_duplicates_do_not_consume_budget(self):
        cfg=json.loads((Path(__file__).parent/'config.json').read_text()); calls=[]
        b=Budget(cfg,2,None,lambda g:calls.append(g) or 1.)
        b.score(np.full((5,8),.5)); self.assertEqual(len(calls),1)
        with self.assertRaises(BudgetExhausted): b.score(np.array([[.5]*8,[.6]*8,[.7]*8]))
        self.assertEqual(len(calls),2); self.assertEqual(len(b.cache),2)

if __name__=='__main__': unittest.main(verbosity=2)
