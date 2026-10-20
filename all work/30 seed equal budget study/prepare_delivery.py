"""Add separate 30-seed result bundles to the five workspace projects."""
from pathlib import Path
import json,csv,shutil,hashlib
from benchmark import ROOT,METHODS,FOLDERS,SEEDS
from study import write_csv

def main():
    out=ROOT/'results'; verification=json.loads((out/'verification.json').read_text())
    assert verification['runs']==150 and verification['unique_evaluations_per_run']==3264
    for method,folder in zip(METHODS,FOLDERS):
        dest=ROOT.parent/folder/'30_seed_equal_budget'
        dest.mkdir(exist_ok=True); runs=dest/'runs'; runs.mkdir(exist_ok=True)
        for seed in SEEDS:
            for suffix in ['.json','_evaluations.npz']:
                shutil.copy2(out/'runs'/f'{method}_{seed}{suffix}',runs)
        for p in (out/'exports').glob(method+'_*'): shutil.copy2(p,dest/p.name)
        for name in ['summary.csv','all_runs.csv','validation_summary.csv','robustness_summary.csv','selected_candidates.csv','best_metrics.csv','numerical_checks.csv']:
            rr=list(csv.DictReader((out/name).open(encoding='utf-8')))
            filtered=[r for r in rr if r.get('method',r.get('controller'))==method]
            write_csv(dest/name,filtered)
        (dest/'README.md').write_text(f'''# {method}: updated 30-seed results

These new results use exactly 3264 unique training evaluations per seed.
Original results/ is preserved as the earlier small-seed study.

Open START_HERE.html for the complete five-method report. The shared project
is ../../30 seed equal budget study/ and contains the full source, protocol,
PDF, statistical analysis, all 150 ledgers and full validation details.

This bundle contains all 30 {method} run ledgers, method summary tables and
best/median-representative gains. Do not mix them with earlier iteration-based
results. Gains require matching Simulink timing and trace validation.
''',encoding='utf-8')
        (dest/'START_HERE.html').write_text(f'''<!doctype html><html><meta charset="utf-8"><title>{method}: 30-seed update</title><body style="font:20px Segoe UI;margin:50px"><h1>{method}: 30-seed equal-budget update</h1><p><a href="../../30%20seed%20equal%20budget%20study/results/REPORT.html">Open complete five-method report</a></p><p><a href="../../30%20seed%20equal%20budget%20study/results/Thirty_Seed_Equal_Budget_Comparison.pdf">Open updated presentation PDF</a></p><p>Earlier results remain in the original results folder. Updated gain files and all 30 run ledgers are here.</p></body></html>''',encoding='utf-8')
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='delivery_manifest.json'}
    (ROOT/'delivery_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(f'Prepared all five updated bundles; {len(manifest)} shared project files hashed.')

if __name__=='__main__': main()
