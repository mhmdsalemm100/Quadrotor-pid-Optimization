"""Read-only snapshot of prior results used by the exploratory comparisons."""
from pathlib import Path
import shutil,json,hashlib
R=Path(__file__).resolve().parent;manifest=[]
for mode,folder in [('nominal','30 seed equal budget study'),('robust','robustness 30 seed study')]:
    src=R.parent/folder;dst=R/'reference_benchmark'/mode/'runs';dst.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256((src/'model.py').read_bytes()).hexdigest()==hashlib.sha256((R/'model.py').read_bytes()).hexdigest()
    for p in (src/'results/runs').glob('*.json'):
        target=dst/p.name;shutil.copy2(p,target)
        manifest.append({'original_path':str(p),'snapshot':str(target.relative_to(R)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
src=R.parent/'robustness 30 seed study/results';dst=R/'reference_benchmark';
for name in ['nominal_vs_robust.csv','corner_validation_summary.csv','validation_summary.csv','selected_candidates.csv']:
    target=dst/name;shutil.copy2(src/name,target)
    manifest.append({'original_path':str(src/name),'snapshot':str(target.relative_to(R)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
(dst/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(f'Snapshotted {len(manifest)} reference files; original plant hash matches.')
