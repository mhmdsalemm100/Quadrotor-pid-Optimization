import unittest
import numpy as np
from robust_protocol import *
from model import baseline
from study import evaluate

class RobustTests(unittest.TestCase):
    def test_cases_and_ranges(self):
        a=training_cases(); b=validation_cases()
        self.assertEqual(len(a),30); self.assertEqual(len(b),444)
        self.assertEqual(a,training_cases()); self.assertEqual(b,validation_cases())
        self.assertEqual(sum(s['group']=='single_axis_mc' for s in b),300)
        self.assertEqual(sum(s['group']=='one_at_a_time' for s in b),54)
        trainplants={tuple(s['plant']) for s in a if 'plant' in s}
        self.assertEqual(len(trainplants),8)
        self.assertTrue(all(tuple(s['plant']) not in trainplants for s in b))
        for s in a+b:
            p=np.asarray(s.get('plant',NOMINAL))
            for _,idx,width in FACTORS:
                self.assertGreaterEqual(p[idx]/NOMINAL[idx],1-width-1e-12)
                self.assertLessEqual(p[idx]/NOMINAL[idx],1+width+1e-12)
            fixed=[j for j in range(13) if j not in [f[1] for f in FACTORS]]
            np.testing.assert_array_equal(p[fixed],NOMINAL[fixed])
    def test_robust_objective_matches_shared_and_constraints(self):
        cfg=configuration(); g=baseline(); obj=RobustObjective(cfg)
        f,cases=evaluate(g,training_cases(),cfg,True)
        self.assertEqual(f,obj(g))
        self.assertEqual(f<1000,all(c['feasible'] for c in cases))
        # Inertia, lag, actuator coefficient and quadratic damping really change dynamics.
        from model import rhs
        x=np.array([1.,0,0,0,1.,2.,3.,450.,470.,490.,510.]); u=np.array([.4,.5,.6,.7])
        z=np.zeros(3); nominal=np.empty(11); changed=np.empty(11)
        rhs(x,u,NOMINAL,z,nominal)
        for _,idx,width in FACTORS:
            p=NOMINAL.copy(); p[idx]*=1+width; rhs(x,u,p,z,changed)
            self.assertGreater(np.max(abs(changed-nominal)),1e-10)

if __name__=='__main__': unittest.main(verbosity=2)
