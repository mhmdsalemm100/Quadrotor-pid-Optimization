"""Focused verification of the transcription, metrics, and optimizer mechanics."""
import json
from pathlib import Path
import unittest
import numpy as np
from model import NOMINAL, baseline, coefficients, rc_condition, rhs, full_rhs, run
from study import encode, decode, training_scenarios, evaluate

ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/'config.json').read_text())

class ModelTests(unittest.TestCase):
    def test_source_parameters_and_defaults(self):
        from inspect_source import inventory
        inv=inventory(); p=inv['numeric_initialization_parameters']
        np.testing.assert_allclose(NOMINAL[:3],[p['ModelParam_uavJxx'],p['ModelParam_uavJyy'],p['ModelParam_uavJzz']])
        self.assertEqual(NOMINAL[10],p['ModelParam_motorT'])
        yaw=next(b for b in inv['blocks'] if b['sid']=='5101')['effective_saved_parameters']
        self.assertEqual(float(yaw['UpperLimit']),.5)
        self.assertEqual(float(yaw['LowerLimit']),-.5)

    def test_baseline_coefficients(self):
        for ts in [.001,.004]:
            for value in coefficients(baseline(ts),ts).values():
                np.testing.assert_allclose(value['numerator'],[.03248,-.03223],atol=1e-15)
                np.testing.assert_allclose(value['denominator'],[1.,-.9997])

    def test_rc_limits_and_hover(self):
        np.testing.assert_allclose(rc_condition([1500]*4),[0,0,0,.609])
        np.testing.assert_allclose(rc_condition([2000,1000,2000,2000]),[np.deg2rad(35),np.deg2rad(-35),np.deg2rad(200),1])
        self.assertEqual(rc_condition([1540,1460,1500,1500])[0],0)

    def test_symmetric_motors_have_zero_angular_acceleration(self):
        x=np.zeros(11); x[0]=1; x[7:]=1148*.609-141.4
        out=np.empty(11); rhs(x,np.full(4,.609),NOMINAL,np.zeros(3),out)
        np.testing.assert_allclose(out,0,atol=1e-10)

    def test_roll_torque_sign_and_magnitude(self):
        x=np.zeros(11); x[0]=1; x[7:]=[500,600,600,500]
        out=np.empty(11); rhs(x,np.full(4,.6),NOMINAL,np.zeros(3),out)
        torque=np.sqrt(.5)*NOMINAL[3]*NOMINAL[4]*2*(600**2-500**2)
        self.assertAlmostEqual(out[4],torque/NOMINAL[0],places=10)
        self.assertAlmostEqual(out[5],0,places=10)
        self.assertAlmostEqual(out[6],0,places=10)

    def test_translation_does_not_change_attitude_equations(self):
        x=np.zeros(17); x[0]=1; x[7:11]=560
        a=full_rhs(x,np.full(4,.609)); x[11:]=[8,-5,2,12,24,9]
        b=full_rhs(x,np.full(4,.609))
        np.testing.assert_allclose(a[:11],b[:11])

    def test_source_low_throttle_behavior_is_preserved(self):
        x=np.zeros(11); x[0]=1
        out=np.empty(11); rhs(x,np.zeros(4),NOMINAL,np.zeros(3),out)
        np.testing.assert_allclose(out[7:],-141.4/.02)

    def test_steady_hover_and_quaternions(self):
        _,d,tr=run(baseline(),{'target':[0,0,0]},CFG,True)
        np.testing.assert_allclose(tr[:,1:7],0,atol=1e-10)
        np.testing.assert_allclose(np.linalg.norm(tr[:,32:36],axis=1),1,atol=1e-10)
        self.assertEqual(d[0],0)

    def test_negative_step_symmetry(self):
        a,_,_=run(baseline(),{'target':[5,0,0]},CFG)
        b,_,_=run(baseline(),{'target':[-5,0,0]},CFG)
        np.testing.assert_allclose(a[:,:9],b[:,:9],atol=1e-8)

    def test_rk4_convergence_and_command_metrics(self):
        s={'target':[5,0,0]}
        m,_,t=run(baseline(),s,CFG,True)
        mh,_,th=run(baseline(),{**s,'dt':.0005},CFG,True)
        self.assertLess(np.max(np.abs(t[:,1:7]-th[::2,1:7])),1e-5)
        self.assertGreater(m[0,0],0)
        self.assertTrue(np.isfinite(m).all())

    def test_parameter_mapping_roundtrip(self):
        g=baseline(); np.testing.assert_allclose(decode(encode(g,CFG),CFG),g,rtol=1e-12)

    def test_deterministic_fitness(self):
        a=evaluate(baseline(),training_scenarios()[:1],CFG)
        b=evaluate(baseline(),training_scenarios()[:1],CFG)
        self.assertEqual(a,b)

    def test_controller_recurrence_against_scipy_filter(self):
        from scipy.signal import lfilter
        g=baseline(); _,_,tr=run(g,{'target':[5,0,0]},CFG,True)
        c=coefficients(g)['roll']
        expected=lfilter(c['numerator'],c['denominator'],tr[:,10]-tr[:,4])
        np.testing.assert_allclose(tr[:,13],expected,atol=1e-10)

    def test_negative_motor_speed_is_infeasible(self):
        from study import assess
        s={'target':[0,0,100]}; m,d,_=run(baseline(),s,CFG)
        self.assertLess(d[6],0.)
        self.assertFalse(assess(m,d,s,CFG)['feasible'])

    def test_local_multirate_baseline_stability(self):
        from linear_analysis import local_analysis
        result=local_analysis(baseline(),CFG)
        self.assertTrue(all(v['locally_stable'] for v in result.values()))

if __name__=='__main__': unittest.main(verbosity=2)
