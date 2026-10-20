"""Typeset equation figures directly from the documented implemented model."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent/'results/plots/equations'
R.mkdir(parents=True,exist_ok=True)
E={
'plant':[
r'$\mathbf{J}\dot{\boldsymbol{\Omega}}+\boldsymbol{\Omega}\times(\mathbf{J}\boldsymbol{\Omega})=\boldsymbol{\tau}_{prop}+\boldsymbol{\tau}_{damp}+\boldsymbol{\tau}_{gyro}$',
r'$\tau_m\dot{\omega}_i+\omega_i=1148u_i-141.4,\qquad 0\leq u_i\leq 1$',
r'$\tau_x=\frac{R C_t}{\sqrt{2}}(-\omega_1^2+\omega_2^2+\omega_3^2-\omega_4^2)$',
r'$\tau_y=\frac{R C_t}{\sqrt{2}}(\omega_1^2-\omega_2^2+\omega_3^2-\omega_4^2),\quad \tau_z=C_m(\omega_1^2+\omega_2^2-\omega_3^2-\omega_4^2)$',
r'$\boldsymbol{\tau}_{damp}=(-D_xp|p|,-D_yq|q|,-D_zr|r|),\quad\boldsymbol{\tau}_{gyro}=J_r(\omega_1+\omega_2-\omega_3-\omega_4)(q,-p,0)$'],
'controller':[
r'$p_{ref}=\operatorname{sat}_{220}[K_{\phi}(\phi_{ref}-\phi)],\quad q_{ref}=\operatorname{sat}_{220}[K_{\theta}(\theta_{ref}-\theta)]$',
r'$C_j(z)=\frac{(K_{p,j}+K_{i,j}T_s)-aK_{p,j}z^{-1}}{1-az^{-1}},\quad a=0.9997,\quad T_s=0.001\ {\rm s}$',
r'$v_r[k]=\operatorname{sat}_{0.5}(K_{p,r}e_r[k]+I_r[k]),\quad I_r[k+1]=\operatorname{sat}_{0.2}(I_r[k]+T_sK_{i,r}e_r[k])$',
r'$\mathbf{u}=\operatorname{clip}_{[0,1]}(h-v_p+v_q+v_r,\ h+v_p-v_q+v_r,\ h+v_p+v_q-v_r,\ h-v_p-v_q-v_r)$',
r'$G_{rate,j}(s)=\frac{k_j\,1148/J_j}{s(\tau_m s+1)},\qquad G_{angle,j}(s)=\frac{G_{rate,j}(s)}{s}$'],
'fitness':[
r'$\epsilon_j(t)=\frac{y_{ref,j}-y_j(t)}{|y_{ref,j}|},\quad {\rm IAE}_j=\int_0^T|\epsilon_j(t)|dt,\quad {\rm ITAE}_j=\int_0^Tt|\epsilon_j(t)|dt$',
r'$S_c=\operatorname{mean}_{j\in A_c}\left[0.45\frac{t_{s,j}}{T}+0.20\frac{t_{r,j}}{T}+0.25\frac{2{\rm ITAE}_j}{T^2}+0.10\frac{{\rm IAE}_j}{T}\right]$',
r'$Q=0.7\operatorname{mean}_c S_c+0.3\max_c S_c+0.01\operatorname{mean}_c E_c$',
r'$F=Q\quad (V\leq10^{-10});\qquad F=1000+100V+\frac{2}{\pi}\arctan Q\quad (V>10^{-10})$',
r'$g_j=\exp[\log L_j+x_j\log(U_j/L_j)],\quad 0\leq x_j\leq1,\qquad M(F)=\log(1+F)$']}
for name,lines in E.items():
    fig=plt.figure(figsize=(12,3.6));fig.patch.set_facecolor('white')
    for i,line in enumerate(lines):fig.text(.015,.88-i*.18,line,fontsize=13,va='center')
    fig.savefig(R/f'{name}.png',dpi=250,bbox_inches='tight');plt.close(fig)
