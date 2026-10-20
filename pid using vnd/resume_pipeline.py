"""Resumable local pipeline. Numerical design and completed results are immutable."""
from pathlib import Path
import subprocess,sys,json,time,traceback
R=Path(__file__).resolve().parent
B=Path(r'C:\Users\asus\.cache\codex-runtimes\codex-primary-runtime\dependencies')
steps=[('search',[sys.executable,'-u','run_extension.py','--processes','10']),
       ('validation',[sys.executable,'-u','analyze_extension.py']),
       ('figures',[sys.executable,'-u','plot_extension.py']),
       ('equations',[sys.executable,'equation_figures.py']),
       ('reports',[str(B/'python/python.exe'),'-u','build_reports.py']),
       ('workbook_data',[sys.executable,'prepare_workbook.py']),
       ('workbook',[str(B/'node/bin/node.exe'),'build_workbook.mjs'])]
status=R/'results/pipeline_status.json'
try:
    for stage,args in steps:
        status.write_text(json.dumps({'stage':stage,'state':'running','unix':time.time()},indent=2),encoding='utf-8')
        print('PIPELINE '+stage,flush=True)
        with (R/f'pipeline_{stage}.log').open('a',encoding='utf-8') as f:
            subprocess.run(args,cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True)
    status.write_text(json.dumps({'stage':'visual_quality_review','state':'awaiting review','unix':time.time()},indent=2),encoding='utf-8')
    print('Numerical work and artifacts generated. Visual QA and Desktop delivery remain.',flush=True)
except Exception as error:
    status.write_text(json.dumps({'stage':stage,'state':'failed','error':str(error),'unix':time.time()},indent=2),encoding='utf-8')
    traceback.print_exc();raise
