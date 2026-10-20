from urllib.request import Request,urlopen
import json
from pathlib import Path
queries={'GDA':'10.1006/jcph.1993.1010','TA':'10.1016/0021-9991(90)90201-B','ALNS':'10.1287/trsc.1050.0135','VND':'10.1016/S0305-0548(97)00031-2'}
R=Path(__file__).resolve().parent/'references';R.mkdir(exist_ok=True)
for key,doi in queries.items():
 try:
  req=Request('https://api.crossref.org/works/'+doi,headers={'User-Agent':'QuadrotorResearch/1.0'})
  with urlopen(req,timeout=25) as f:data=json.load(f)['message']
  (R/(key+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8');print(key,data.get('title'),flush=True)
 except Exception as e:print(key,type(e).__name__,str(e),flush=True)
