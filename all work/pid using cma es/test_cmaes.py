import contextlib,io,json,tempfile,unittest
from pathlib import Path
import numpy as np
from cmaes import cma_es
from study import encode

class CMAESTests(unittest.TestCase):
    def test_rotated_ellipsoid_bounds_adaptation_and_reproducibility(self):
        cfg=json.loads((Path(__file__).parent/'config.json').read_text())
        cfg.update(swarm_size=16,iterations=70,workers=1,comparison_evaluation_budget=300)
        rotation,_=np.linalg.qr(np.random.default_rng(3).normal(size=(8,8)))
        def objective(g):
            self.assertTrue(all(p['lower']-1e-12<=z<=p['upper']+1e-12 for p,z in zip(cfg['parameters'],g)))
            z=rotation@(encode(g,cfg)-.4)
            return float(np.sum(np.geomspace(1,100,8)*z*z))
        with tempfile.TemporaryDirectory() as temp,contextlib.redirect_stdout(io.StringIO()):
            a=cma_es(cfg,[],123,temp,objective=objective)
            states=json.loads((Path(temp)/'distribution_main_123.json').read_text())
            b=cma_es(cfg,[],123,temp,objective=objective)
        self.assertEqual(a['fitness'],b['fitness']); np.testing.assert_array_equal(a['gains'],b['gains'])
        self.assertLess(a['fitness'],a['history'][0]['best']*.02)
        self.assertTrue(np.all(np.diff([h['best'] for h in a['history']])<=0))
        self.assertEqual(a['candidate_proposals'],16*71)
        self.assertEqual(a['unique_evaluations'],16*71)
        self.assertEqual(a['evaluations_at_comparison_budget'],300)
        self.assertAlmostEqual(objective(np.array(a['gains'])),a['fitness'])
        cov=np.array(states[-1]['covariance']); self.assertTrue(np.all(np.linalg.eigvalsh(cov)>0))
        self.assertGreater(np.linalg.norm(cov-np.diag(np.diag(cov))),.01)
        self.assertNotEqual(states[0]['sigma'],states[-1]['sigma'])

    def test_diagonal_variant_and_warm_start_archive(self):
        cfg=json.loads((Path(__file__).parent/'config.json').read_text())
        cfg.update(swarm_size=8,iterations=4,workers=1,cma_diagonal=True)
        target=np.array([np.sqrt(p['lower']*p['upper']) for p in cfg['parameters']])
        with tempfile.TemporaryDirectory() as temp,contextlib.redirect_stdout(io.StringIO()):
            result=cma_es(cfg,[],7,temp,initial=target,objective=lambda g:float(np.sum((encode(g,cfg)-.5)**2)))
            states=json.loads((Path(temp)/'distribution_main_7.json').read_text())
        self.assertLess(result['fitness'],1e-20)
        for state in states:
            cov=np.array(state['covariance']); np.testing.assert_allclose(cov,np.diag(np.diag(cov)))

if __name__=='__main__': unittest.main(verbosity=2)
