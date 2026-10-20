"""Workbook API smoke check on actual development settings, never final results."""
from pathlib import Path
import csv,json
R=Path(__file__).resolve().parent
with (R/'results/parameter_selection.csv').open(encoding='utf-8') as f:
    rd=csv.DictReader(f);h=rd.fieldnames;data=[]
    for r in rd:
        data.append([r['method'],int(r['candidate']),float(r['mean_rank']),r['selected']=='True',r['parameters'],float(r['nominal_median_fitness']),float(r['robust_median_fitness'])])
t=[{'name':'Summary','headers':h,'source':'Development parameter selection only; temporary API check','data':data}]
p=R/'tmp/workbook_smoke_input.json';p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(t),encoding='utf-8')
