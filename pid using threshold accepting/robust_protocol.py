"""Frozen sampled-robustness design; physical equations are unchanged."""
from pathlib import Path
import json
import numpy as np
from scipy.stats import qmc
from model import NOMINAL
from study import training_scenarios, evaluate

ROOT=Path(__file__).resolve().parent
# Independent factors in validation; coefficients already present in source model.
FACTORS=[('Jxx',0,.15),('Jyy',1,.15),('Jzz',2,.15),('motor_tau',10,.30),
         ('Ct',4,.10),('Cm',5,.10),('damping_x',6,.30),('damping_y',7,.30),('damping_z',8,.30)]
TRAIN_SEED=20261005
TEST_SEED=20261006

def plant_from_unit(unit):
    p=NOMINAL.copy()
    for u,(_,idx,width) in zip(unit,FACTORS): p[idx]*=1+width*(2*u-1)
    return p

def training_cases():
    cases=training_scenarios()
    # Six independent Latin-hypercube plants plus two directed boundary plants.
    units=qmc.LatinHypercube(d=9,seed=TRAIN_SEED).random(6).tolist()
    units += [[1,1,1,1,0,0,0,0,0],[0,0,0,0,1,1,1,1,1]]
    for i,u in enumerate(units):
        for axis,amp in enumerate([20,20,100]):
            target=[0,0,0]; target[axis]=amp
            cases.append({'name':f'train_plant{i}_axis{axis}','target':target,
                          'plant':plant_from_unit(u).tolist(),'group':'uncertain_training'})
    return cases

def validation_cases():
    rng=np.random.default_rng(TEST_SEED); cases=[]
    # Uniform independent draws, with 100 unseen commands for each single axis.
    for i in range(300):
        j=i%3; target=[0.,0.,0.]
        target[j]=float(rng.choice([-1,1])*rng.uniform(5 if j<2 else 20,20 if j<2 else 100))
        cases.append({'name':f'mc_{i:03d}','target':target,'plant':plant_from_unit(rng.random(9)).tolist(),
                      'group':'single_axis_mc'})
    # Independent one-at-a-time limits isolate the sensitivity to each coefficient.
    for factor,(_,_,_) in enumerate(FACTORS):
        for edge in [0.,1.]:
            u=np.full(9,.5); u[factor]=edge
            for j,amp in enumerate([20,20,100]):
                target=[0,0,0]; target[j]=amp
                cases.append({'name':f'oat_{FACTORS[factor][0]}_{int(edge)}_{j}',
                              'target':target,'plant':plant_from_unit(u).tolist(),'group':'one_at_a_time'})
    # Separate structural stress test: NOT mixed with the primary robustness score.
    for i in range(90):
        target=(rng.choice([-1,1],3)*rng.uniform([5,5,20],[18,15,70])).tolist()
        cases.append({'name':f'combined_{i:03d}','target':target,'plant':plant_from_unit(rng.random(9)).tolist(),
                      'throttle':float(rng.uniform(.54,.68)),'group':'combined_stress'})
    return cases

class RobustObjective:
    def __init__(self,cfg): self.cfg=cfg; self.cases=training_cases()
    def __call__(self,gains): return evaluate(gains,self.cases,self.cfg)

def configuration():
    return json.loads((ROOT/'config.json').read_text())
