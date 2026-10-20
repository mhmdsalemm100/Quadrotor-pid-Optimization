import contextlib,io,json,tempfile,unittest
from pathlib import Path
import numpy as np
from dsa import dolphin_swarm,communicate,predation_radius
from study import encode

class DSATests(unittest.TestCase):
    def test_delayed_reception(self):
        x=np.array([[0.],[1.]])
        k=x.copy(); f=np.array([1.,.1]); ts=np.full((2,2),100)
        k,f,ts,count=communicate(x,k,f,ts,.25,1,100)
        self.assertEqual(count,0); self.assertEqual(ts[0,1],3)
        for _ in range(3): k,f,ts,count=communicate(x,k,f,ts,.25,1,100)
        self.assertEqual(count,1); self.assertEqual(f[0],.1); self.assertEqual(k[0,0],1.)

    def test_predation_equations(self):
        self.assertAlmostEqual(predation_radius(2,1,1,2,3),2-2.5/3)
        self.assertAlmostEqual(predation_radius(1,2,1,2,3),1-.5/3)
        self.assertTrue(np.isfinite(predation_radius(1,1,0,0,3)))

    def test_bounds_archive_and_reproducibility(self):
        cfg=json.loads((Path(__file__).parent/'config.json').read_text())
        cfg.update(swarm_size=16,iterations=35,workers=1,comparison_evaluation_budget=300)
        def sphere(g):
            self.assertTrue(all(p['lower']-1e-12<=z<=p['upper']+1e-12 for p,z in zip(cfg['parameters'],g)))
            return float(np.sum((encode(g,cfg)-.35)**2))
        with tempfile.TemporaryDirectory() as temp,contextlib.redirect_stdout(io.StringIO()):
            a=dolphin_swarm(cfg,[],123,temp,objective=sphere)
            b=dolphin_swarm(cfg,[],123,temp,objective=sphere)
        self.assertEqual(a['fitness'],b['fitness']); np.testing.assert_array_equal(a['gains'],b['gains'])
        self.assertLess(a['fitness'],a['history'][0]['best']*.5)
        self.assertTrue(np.all(np.diff([h['best'] for h in a['history']])<=0))
        self.assertEqual(a['candidate_proposals'],16+35*16*5)
        self.assertEqual(a['evaluations_at_comparison_budget'],300)
        self.assertLessEqual(a['fitness'],a['fitness_at_comparison_budget'])
        self.assertAlmostEqual(sphere(np.array(a['gains'])),a['fitness'])

if __name__=='__main__': unittest.main(verbosity=2)
