"""Typed research-result tables for the Excel workbook; analysis stays in Python."""
from pathlib import Path
import csv,json
R=Path(__file__).resolve().parent;O=R/'results'
specs=[('Summary','fitness_summary.csv'),('Selected gains','selected_candidates.csv'),('All gains','exports/all_runs_gains.csv'),
       ('Validation','validation_summary.csv'),('Parameter study','parameter_selection.csv'),('Paired tests','fitness_pairwise.csv'),
       ('Failure counts','failure_categories.csv'),('Integration','integration_checks.csv'),('Eleven methods','exploratory_eleven_comparison.csv')]
def typed(s):
    if s=='':return None
    if s in ['True','False']:return s=='True'
    try:return int(s)
    except ValueError:pass
    try:return float(s)
    except ValueError:return s
tables=[]
for name,file in specs:
    with (O/file).open(encoding='utf-8') as f:
        reader=csv.DictReader(f);headers=reader.fieldnames;data=[[typed(r[k]) for k in headers] for r in reader]
    if name=='Summary':
        keep=[i for i,k in enumerate(headers) if k in ['mode','method','median','mean','std','best','worst','training_feasible_runs','median_ci95_low','median_ci95_high']]
        headers=[headers[i] for i in keep];data=[[row[i] for i in keep] for row in data]
    tables.append({'name':name,'source':file,'headers':headers,'data':data})
(O/'workbook_input.json').write_text(json.dumps(tables,allow_nan=False),encoding='utf-8')
