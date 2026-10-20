from pathlib import Path
import json,shutil,hashlib
R=Path(__file__).resolve().parent
FOLDERS={'GDA':'pid using great deluge','TA':'pid using threshold accepting','ALNS':'pid using alns','VND':'pid using vnd','SBRS':'pid using shrinking ball random search','PRW':'pid using pure random walk'}
def prepare():
 dstroot=R/'delivery';dstroot.mkdir(exist_ok=True)
 for m,name in FOLDERS.items():
  dst=dstroot/name;dst.mkdir(exist_ok=True)
  for f in R.glob('*.py'):shutil.copy2(f,dst/f.name)
  for name0 in ['config.json','README.md','requirements-lock.txt','environment.json']:
   shutil.copy2(R/name0,dst/name0)
  for name0 in ['source','references']:
   if (R/name0).exists():shutil.copytree(R/name0,dst/name0,dirs_exist_ok=True)
  (dst/'METHOD.json').write_text(json.dumps({'method':m,'central_project':str(R),'stage':'development and main runs in progress; not final results'},indent=2))
  (dst/'START_HERE.md').write_text('# '+name+'\n\nThis is the separate project for '+m+'. The initial delivery contains verified code and the frozen study design. Numerical results are still being generated. Do not describe this folder as a completed study until VERIFIED_COMPLETE.json is present. The central workspace progress is recorded in '+str(R/'results/progress.json')+'.\n')
 print('Prepared six method-specific Desktop project folders.')
if __name__=='__main__':prepare()
