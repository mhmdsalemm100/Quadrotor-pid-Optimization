"""Integration check using actual completed seed 11; outputs only in tmp/."""
from pathlib import Path
import shutil,json
import analyze_extension as a
import analyze_robust as v
import corner_checks as c
import plot_extension as p
from model import baseline
R=Path(__file__).resolve().parent;T=R/'tmp/analysis_smoke';O=T/'results';O.mkdir(parents=True,exist_ok=True)
cfg=a.read(R/'results/contract.json')['configuration'];m='ALNS'
data={mode:{m:[a.read(R/'results'/mode/'runs'/f'{m}_11.json')]} for mode in ['nominal','robust']}
for mode in data:
    dst=O/mode/'runs';dst.mkdir(parents=True,exist_ok=True)
    for name in [f'{m}_11.json',f'{m}_11_evaluations.npz']:shutil.copy2(R/'results'/mode/'runs'/name,dst/name)
a.OUT=O;v.OUT=O;c.ROOT=T;p.OUT=O;p.P=O/'plots';p.D=O/'plot_data'
(O/'validation').mkdir(exist_ok=True);p.P.mkdir(exist_ok=True);p.D.mkdir(exist_ok=True)
rows=[v.validate_one((mode,m,data[mode][m][0],cfg)) for mode in data]
rows.append(v.validate_one(('baseline','baseline',{'seed':0,'gains':baseline().tolist()},cfg)))
a.write_csv(O/'validation_summary.csv',rows);lookup={(r['mode'],r['method'],r['seed']):r for r in rows}
a.supplemental(data);corners=c.check_corners(data,cfg);a.export_gains(data,cfg,lookup,corners);a.stability_numeric(data,cfg);a.additional_diagnostics(data,cfg)
p.method_figures(data,cfg,m)
assert len(list((p.P/m).glob('*.png')))==7
(T/'SMOKE_CHECK.json').write_text(json.dumps({'passed':True,'real_seed':11,'method':m,'note':'One-seed integration check only. Not final study results.'},indent=2),encoding='utf-8')
print('Analysis integration check passed. Outputs are temporary and excluded from delivery.',flush=True)
