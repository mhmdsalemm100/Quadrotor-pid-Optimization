"""Early audit of all development runs and the first three complete main seeds."""
from pathlib import Path
import analyze_extension as a
R=Path(__file__).resolve().parent;T=R/'tmp/archive_check';T.mkdir(parents=True,exist_ok=True)
data={mode:{m:[a.read(R/'results'/mode/'runs'/f'{m}_{s}.json') for s in [11,29,47]] for m in a.METHODS} for mode in a.MODES}
original_dump=a.dump;original_csv=a.write_csv
a.dump=lambda p,x:original_dump(T/Path(p).name,x)
a.write_csv=lambda p,x:original_csv(T/Path(p).name,x)
a.audit(data,a.read(R/'results/contract.json')['configuration'])
result=a.read(T/'audit.json');assert result['runs']==36 and result['pilot_runs']==144
print('Archive check passed: all 144 development runs and 36 main runs. Final all-run audit remains required.')
