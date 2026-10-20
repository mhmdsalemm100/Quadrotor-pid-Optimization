"""Local hover analysis retaining controller sampling and the mixer hold."""
import numpy as np
from scipy.linalg import expm
from model import NOMINAL, coefficients

def local_analysis(gains,cfg):
    p=NOMINAL; tc=cfg['controller_dt_s']; tm=cfg['mixer_dt_s']
    ratio=int(round(tm/tc))
    if ratio<1 or abs(ratio*tc-tm)>1e-10:
        raise ValueError('This lifted local analysis requires mixer_dt / controller_dt to be an integer >= 1.')
    w=p[11]*.609+p[12]; coeff=coefficients(gains,tc,cfg['fixed_discrete_pole'])
    result={}
    for axis,j,idx in [('roll',0,0),('pitch',1,3),('yaw',2,6)]:
        k_moment=8*(np.sqrt(.5)*p[3]*p[4] if j<2 else p[5])*w
        if j<2:
            A=np.array([[0.,1.,0.],[0.,0.,k_moment/p[j]],[0.,0.,-1/p[10]]])
            B=np.array([0.,0.,p[11]/p[10]])
        else:
            A=np.array([[0.,k_moment/p[j]],[0.,-1/p[10]]])
            B=np.array([0.,p[11]/p[10]])
        n=len(B); augmented=np.zeros((n+1,n+1)); augmented[:n,:n]=A; augmented[:n,n]=B
        zoh=expm(augmented*tc); Ad=zoh[:n,:n]; Bd=zoh[:n,n]
        size=6 if j<2 else 4
        def period(state):
            state=state.copy()
            for phase in range(ratio):
                if j<2:
                    e=-gains[idx]*state[0]-state[1]
                    b0,b1=coeff[axis]['numerator']; pole=cfg['fixed_discrete_pole']
                    u=pole*state[4]+b0*e+b1*state[3]
                    state[3]=e; state[4]=u
                    if phase==0: state[5]=u
                    state[:3]=Ad@state[:3]+Bd*state[5]
                else:
                    e=-state[0]; u=gains[6]*e+state[2]
                    state[2]+=tc*gains[7]*e
                    if phase==0: state[3]=u
                    state[:2]=Ad@state[:2]+Bd*state[3]
            return state
        transition=np.column_stack([period(np.eye(size)[:,k]) for k in range(size)])
        eig=np.linalg.eigvals(transition)
        result[axis]={'motor_command_to_torque_gain':float(k_moment*p[11]),
                      'rate_plant_numerator':float(k_moment*p[11]/p[j]),
                      'rate_plant_denominator_s': [.02,1.,0.],
                      'lifted_period_s':tm,
                      'closed_loop_eigenvalues':[{'real':float(v.real),'imag':float(v.imag)} for v in eig],
                      'spectral_radius':float(np.max(np.abs(eig))),
                      'locally_stable':bool(np.max(np.abs(eig))<1)}
    return result
