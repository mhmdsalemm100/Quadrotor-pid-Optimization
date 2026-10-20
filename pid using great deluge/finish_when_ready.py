"""Local foreground pipeline helper; run after the search process is started."""
from pathlib import Path
import subprocess,sys,time,json
R=Path(__file__).resolve().parent
while not (R/'results/search_complete.json').exists():
    time.sleep(30)
for script in ['analyze_extension.py','plot_extension.py']:
    print('STARTING '+script,flush=True)
    subprocess.run([sys.executable,'-u',str(R/script)],cwd=R,check=True)
print('ANALYSIS AND FIGURES FINISHED. Reports and final delivery remain.',flush=True)
