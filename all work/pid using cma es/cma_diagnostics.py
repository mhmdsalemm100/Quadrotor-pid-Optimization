"""Inspect saved distribution adaptation, without changing search results."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def build_diagnostics(out):
    out=Path(out); fig,axs=plt.subplots(1,3,figsize=(14,4.5),layout='constrained')
    runs=[json.loads(p.read_text()) for p in sorted(out.glob('run_main_*.json'))]
    for r in runs:
        h=r['history']; t=[a['iteration'] for a in h]
        axs[0].plot(t,[a['sigma'] for a in h],label=f"Seed {r['seed']}")
        axs[1].plot(t,[a['covariance_axis_ratio'] for a in h],label=f"Seed {r['seed']}")
    best=min(runs,key=lambda r:r['fitness'])
    st=json.loads((out/f"distribution_main_{best['seed']}.json").read_text())[-1]
    matrix=np.array(st['covariance']); scale=np.sqrt(np.diag(matrix)); corr=matrix/scale[:,None]/scale[None,:]
    im=axs[2].imshow(corr,vmin=-1,vmax=1,cmap='RdBu_r'); fig.colorbar(im,ax=axs[2],shrink=.8)
    axs[0].set(title='Global step-size adaptation',xlabel='Update',ylabel='Sigma',yscale='log'); axs[0].legend()
    axs[1].set(title='Covariance axis ratio',xlabel='Update',ylabel='sqrt(max eigenvalue / min)',yscale='log')
    axs[2].set(title=f"Final genotype correlation | seed {best['seed']}",xticks=range(8),yticks=range(8))
    for ext in ['png','svg']: fig.savefig(out/f'plots/12_cma_adaptation.{ext}',dpi=170,bbox_inches='tight')
    plt.close(fig)
