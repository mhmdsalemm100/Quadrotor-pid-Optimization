"""Optimizer-specific deterministic, bound and memory checks on a known objective."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from pso import particle_swarm
from study import encode

class PSOTests(unittest.TestCase):
    def test_pso_known_optimum_and_reproducibility(self):
        cfg=json.loads((Path(__file__).parent/'config.json').read_text())
        cfg.update(swarm_size=32,iterations=60,workers=1)
        seen=[]
        def sphere(g):
            self.assertTrue(all(p['lower']-1e-12 <= v <= p['upper']+1e-12 for p,v in zip(cfg['parameters'],g)))
            x=encode(g,cfg); seen.append(x)
            return float(np.sum((x-.35)**2))
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            a=particle_swarm(cfg,[],123,temp,objective=sphere)
            b=particle_swarm(cfg,[],123,temp,objective=sphere)
        self.assertEqual(a['fitness'],b['fitness'])
        np.testing.assert_array_equal(a['gains'],b['gains'])
        self.assertLess(a['fitness'],1e-4)
        self.assertTrue(np.all(np.diff([r['best'] for r in a['history']])<=0))
        self.assertTrue(np.all(np.asarray(seen)>=0) and np.all(np.asarray(seen)<=1))
        self.assertEqual(a['candidate_proposals'],32*61)
        self.assertAlmostEqual(a['history'][0]['inertia_for_next_update'],.9)
        self.assertAlmostEqual(a['history'][-2]['inertia_for_next_update'],.4)

if __name__=='__main__': unittest.main(verbosity=2)
