import contextlib,io,json,tempfile,unittest
from pathlib import Path
import numpy as np
from cso import cat_swarm,selection_probabilities
from study import encode

class CSOTests(unittest.TestCase):
    def test_seeking_selection(self):
        np.testing.assert_allclose(selection_probabilities([1,2,3]),[2/3,1/3,0])
        np.testing.assert_allclose(selection_probabilities([7,7,7]),[1/3]*3)

    def test_modes_bounds_memory_and_reproducibility(self):
        cfg=json.loads((Path(__file__).parent/'config.json').read_text())
        cfg.update(swarm_size=24,iterations=40,workers=1,comparison_evaluation_budget=300)
        def sphere(g):
            self.assertTrue(all(p['lower']-1e-12<=z<=p['upper']+1e-12 for p,z in zip(cfg['parameters'],g)))
            return float(np.sum((encode(g,cfg)-.35)**2))
        with tempfile.TemporaryDirectory() as temp,contextlib.redirect_stdout(io.StringIO()):
            a=cat_swarm(cfg,[],123,temp,objective=sphere)
            b=cat_swarm(cfg,[],123,temp,objective=sphere)
        self.assertEqual(a['fitness'],b['fitness'])
        np.testing.assert_array_equal(a['gains'],b['gains'])
        self.assertLess(a['fitness'],a['history'][0]['best']*.5)
        self.assertTrue(np.all(np.diff([h['best'] for h in a['history']])<=0))
        self.assertEqual(a['history'][1]['tracing_cats'],5)
        self.assertEqual(a['history'][1]['seeking_cats'],19)
        self.assertGreater(a['unique_evaluations'],24*41)
        self.assertEqual(a['evaluations_at_comparison_budget'],300)
        self.assertLessEqual(a['fitness'],a['fitness_at_comparison_budget'])
        self.assertAlmostEqual(sphere(np.array(a['gains'])),a['fitness'])

if __name__=='__main__': unittest.main(verbosity=2)
