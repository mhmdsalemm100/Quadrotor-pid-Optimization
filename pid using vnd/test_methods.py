"""Meaningful behavioral and accounting tests before scientific runs."""
import unittest,json
from pathlib import Path
import numpy as np
from methods import optimize,parameter_grid,METHODS,reflect,accept
from benchmark import initial_population
from study import encode
R=Path(__file__).resolve().parent;cfg=json.loads((R/'config.json').read_text())
def sphere(g):return float(np.sum((encode(g,cfg)-.5)**2))
class Tests(unittest.TestCase):
 def test_acceptance(self):
  self.assertTrue(accept('PRW',1,10,0));self.assertFalse(accept('SBRS',1,2,0));self.assertTrue(accept('TA',1,1.1,.1));self.assertFalse(accept('TA',1,1.1,0));self.assertTrue(accept('GDA',2,1,0));self.assertFalse(accept('GDA',1,2,0))
 def test_reflection(self):
  np.testing.assert_allclose(reflect(np.array([-.2,1.2,2.3,-2.3])),[.2,.8,.3,.3])
 def test_seed_budget_and_reproducibility(self):
  for m in METHODS:
   p=parameter_grid(m)[0];a=optimize(m,5011,cfg,p,limit=180,objective=sphere);b=optimize(m,5011,cfg,p,limit=180,objective=sphere)
   self.assertEqual(a['unique_evaluations'],180);self.assertEqual(a['fitness'],b['fitness']);self.assertEqual(a['gains'],b['gains']);self.assertTrue(np.all(np.diff([x['best'] for x in a['history']])<=0))
 def test_all_parameter_candidates(self):
  for m in METHODS:
   for p in parameter_grid(m):self.assertEqual(optimize(m,5021,cfg,p,limit=256,objective=sphere)['unique_evaluations'],256)
if __name__=='__main__':unittest.main()
