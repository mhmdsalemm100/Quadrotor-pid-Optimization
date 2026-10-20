"""Prepare six complete, independent Desktop deliveries inside the workspace.

This script does not write outside the workspace. Copying to Desktop is separate.
"""
from pathlib import Path
import csv,json,shutil,hashlib
from prepare_delivery import FOLDERS
R=Path(__file__).resolve().parent;O=R/'results';D=R/'delivery'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2),encoding='utf-8')
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def filtered_csv(src,dst,m):
    with src.open(encoding='utf-8') as f:
        rr=csv.DictReader(f);headers=rr.fieldnames;allrows=list(rr)
    if 'method' in headers:data=[r for r in allrows if r['method'] in [m,'baseline','source']]
    elif 'A' in headers and 'B' in headers:data=[r for r in allrows if m in [r['A'],r['B']]]
    elif 'controller' in headers:data=[r for r in allrows if f'_{m}_' in r['controller']]
    else:data=allrows
    dst.parent.mkdir(parents=True,exist_ok=True)
    with dst.open('w',newline='',encoding='utf-8') as f:
        wr=csv.DictWriter(f,fieldnames=headers);wr.writeheader();wr.writerows(data)
def main():
    assert read(O/'final_audit.json')['passed'] and read(O/'visual_qa.json')['passed']
    for m,folder in FOLDERS.items():
        target=D/folder;target.mkdir(parents=True,exist_ok=True)
        for src in R.glob('*.py'):copy(src,target/src.name)
        for name in ['README.md','HYPERPARAMETERS.md','STATISTICS.md','SIMULINK_TRANSFER_NOTES.md','config.json','requirements-lock.txt','environment.json','tests_final.log']:
            copy(R/name,target/name)
        for name in ['source','references','reference_benchmark']:
            shutil.copytree(R/name,target/name,dirs_exist_ok=True)
        result=target/'results';result.mkdir(exist_ok=True)
        for src in O.glob('*.json'):
            if src.name not in ['workbook_input.json','progress.json']:copy(src,result/src.name)
        for src in O.glob('*.csv'):filtered_csv(src,result/src.name,m)
        for mode in ['nominal','robust']:
            for src in (O/mode/'runs').glob(f'{m}_*'):copy(src,result/mode/'runs'/src.name)
        for src in (O/'pilot').rglob(f'{m}_*'):
            if src.is_file():copy(src,result/src.relative_to(O))
        for name in ['validation','corner_validation','additional_diagnostics']:
            for src in (O/name).glob('*.gz'):
                if f'_{m}_' in src.name or src.name.startswith('baseline_'):copy(src,result/name/src.name)
        for src in (O/'exports').glob('*'):
            if f'_{m}_' in src.name:copy(src,result/'exports'/src.name)
            elif src.suffix=='.csv':filtered_csv(src,result/'exports'/src.name,m)
        for name in ['plots','plot_data']:
            for src in (O/name).glob('*'):
                if src.is_file():copy(src,result/name/src.name)
                elif src.name in [m,'equations']:shutil.copytree(src,result/name/src.name,dirs_exist_ok=True)
        copy(R/'output/pdf'/f'{m}_complete_study.pdf',target/f'{m}_complete_study.pdf')
        copy(R/'output/pdf/Six_methods_comparison.pdf',target/'Six_methods_comparison.pdf')
        copy(R/'output/Six_methods_results.xlsx',target/'Six_methods_results.xlsx')
        dump(target/'METHOD.json',{'method':m,'central_project':str(R),'stage':'complete; see VERIFIED_COMPLETE.json after Desktop delivery verification',
             'local_main_runs':60,'local_development_runs':24,'central_main_runs':360,'central_development_runs':144})
        (target/'START_HERE.md').write_text(f'''# {folder}

Open **{m}_complete_study.pdf** for this method and **Six_methods_comparison.pdf** for the comparison. The Excel workbook contains all six methods for filtering and comparison. Local CSV files and raw histories contain this method's results.

## What is included
- 30 nominal and 30 robust main runs, each with 3264 unique evaluations.
- 24 development runs comparing four settings on three independent seeds in both regimes.
- Validation on 444 cases per controller; best and median representatives also receive 1536 joint-boundary cases.
- Full-precision gains, exact discrete coefficients, evaluation histories, iteration and acceptance records, PNG figures, figure data, local stability and integration checks.
- Complete Python implementation and the unchanged reference model extracts.

## Run this method
Double-click RUN_THIS_METHOD.cmd, or use `python run_method.py --processes 4` in a Python environment installed from requirements-lock.txt. Completed runs are checked and reused. The supplied code refuses a changed frozen implementation. Use a separate project for a changed protocol.

`run_extension.py` and `analyze_extension.py` are central comparison drivers. For this individual folder, use **run_method.py**. `plot_extension.py` and `build_reports.py` detect METHOD.json and work on this method. PDF rebuilding also needs ReportLab; the delivered numerical results do not depend on ReportLab or Excel.

The central audit JSON describes the complete 360-run experiment. This folder contains the 60-run subset named above. DELIVERY_MANIFEST.json records the local files and their hashes.

All tuning is offline. Parameters are best among the tested settings, not proven globally best. Results are Python simulation candidates, not Simulink, HIL or flight validation. The previous five optimizers had no matching new parameter-selection pilot, so the eleven-method comparison is exploratory.
''',encoding='utf-8')
        python=str(R.parent/'.venv/Scripts/python.exe')
        (target/'RUN_THIS_METHOD.cmd').write_text('@echo off\r\ncd /d "%~dp0"\r\nif exist "'+python+'" (\r\n  "'+python+'" -u run_method.py --processes 4\r\n) else (\r\n  python -u run_method.py --processes 4\r\n)\r\npause\r\n',encoding='utf-8')
        files=[p for p in target.rglob('*') if p.is_file() and p.name not in ['DELIVERY_MANIFEST.json','VERIFIED_COMPLETE.json'] and '__pycache__' not in p.parts]
        manifest={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        dump(target/'DELIVERY_MANIFEST.json',{'method':m,'files':manifest,'file_count':len(files),'main_runs':60,'development_runs':24})
        print(f'Prepared {m}: {len(files)} files',flush=True)
if __name__=='__main__':main()
