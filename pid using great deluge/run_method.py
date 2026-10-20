"""Reproduce the one method identified by this delivered folder's METHOD.json.

Default: all 60 main runs, full held-out validation, selected-controller corner
checks, coefficient exports and PNG plots. Existing completed runs are audited
and reused. Remove/move results only yourself if deliberately rerunning from zero.
"""
from concurrent.futures import ProcessPoolExecutor,as_completed
import argparse,hashlib,json
import numpy as np
from methods import SEEDS
from run_extension import worker
from analyze_extension import R,OUT,read,validation,supplemental,export_gains,stability_numeric,selected,additional_diagnostics
from corner_checks import check_corners
from plot_extension import method_figures,P,D
from study import write_csv,decode

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--processes',type=int,default=4);ap.add_argument('--search-only',action='store_true');args=ap.parse_args()
    m=read(R/'METHOD.json')['method'];contract=read(OUT/'contract.json');cfg=contract['configuration']
    for name,h in contract['code_sha256'].items():
        assert hashlib.sha256((R/name).read_bytes()).hexdigest()==h, f'Frozen implementation changed: {name}'
    parameters=read(OUT/'selected_parameters.json')[m]
    tasks=[('main',mode,m,s,parameters,None) for s in SEEDS for mode in ['nominal','robust']]
    with ProcessPoolExecutor(max_workers=args.processes) as pool:
        for i,f in enumerate(as_completed([pool.submit(worker,t) for t in tasks])):
            r=f.result();print(f'{i+1}/60: '+json.dumps(r),flush=True)
    data={mode:{m:[read(OUT/mode/'runs'/f'{m}_{s}.json') for s in SEEDS]} for mode in ['nominal','robust']}
    for mode in data:
        for r in data[mode][m]:
            a=np.load(OUT/mode/'runs'/f'{m}_{r["seed"]}_evaluations.npz')['ledger']
            assert len(a)==r['unique_evaluations']==3264 and np.isfinite(a).all()
            assert len({tuple(np.round(x,13)) for x in a[:,4:]})==3264
            np.testing.assert_allclose(a[:,3],np.minimum.accumulate(a[:,2]),rtol=0,atol=1e-13)
            np.testing.assert_allclose(decode(a[np.argmin(a[:,2]),4:],cfg),r['gains'],rtol=1e-13,atol=1e-15)
    if args.search_only:return
    vv=validation(cfg,args.processes);lookup={(r['mode'],r['method'],r['seed']):r for r in vv}
    supplemental(data);corners=check_corners(data,cfg);export_gains(data,cfg,lookup,corners);stability_numeric(data,cfg);additional_diagnostics(data,cfg)
    P.mkdir(exist_ok=True);D.mkdir(exist_ok=True);method_figures(data,cfg,m)
    print('Method reproduction complete: 60 runs, validation, exports and PNG figures. The delivered report records the original frozen experiment.',flush=True)
if __name__=='__main__':main()
