"""Copy audited packages to the six requested Desktop folders and verify them.

Requires permission to write outside the workspace. Does not delete files.
"""
from pathlib import Path
import hashlib
import json
import shutil
from datetime import datetime, timezone
from prepare_delivery import FOLDERS

ROOT = Path(__file__).resolve().parent
DESKTOP = Path(r'C:\Users\asus\Desktop')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    audit = read(ROOT / 'results/final_audit.json')
    assert audit['passed'] and read(ROOT / 'results/visual_qa.json')['passed']
    deliveries = []
    for method, name in FOLDERS.items():
        source = (ROOT / 'delivery' / name).resolve()
        target = (DESKTOP / name).resolve()
        assert source.parent == (ROOT / 'delivery').resolve()
        assert target.parent == DESKTOP.resolve()
        manifest_path = source / 'DELIVERY_MANIFEST.json'
        manifest = read(manifest_path)
        assert manifest['method'] == method
        if target.exists():
            assert read(target / 'METHOD.json')['method'] == method
        target.mkdir(parents=True, exist_ok=True)
        for relative, expected in manifest['files'].items():
            src = (source / relative).resolve()
            dst = (target / relative).resolve()
            assert src.is_relative_to(source) and dst.is_relative_to(target)
            assert digest(src) == expected, f'Package changed: {src}'
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        shutil.copy2(manifest_path, target / manifest_path.name)
        for relative, expected in manifest['files'].items():
            assert digest(target / relative) == expected, relative
        main_runs = list((target / 'results/nominal/runs').glob(f'{method}_*.json'))
        main_runs += list((target / 'results/robust/runs').glob(f'{method}_*.json'))
        pilot_runs = list((target / 'results/pilot').rglob(f'{method}_*.json'))
        assert len(main_runs) == 60 and len(pilot_runs) == 24
        record = {
            'complete': True, 'method': method,
            'verified_utc': datetime.now(timezone.utc).isoformat(),
            'directory': str(target), 'files_verified': len(manifest['files']),
            'main_runs': 60, 'development_runs': 24,
            'manifest_sha256': digest(target / manifest_path.name),
            'central_audit_sha256': digest(ROOT / 'results/final_audit.json'),
            'scope': 'Offline Python simulation; no Simulink, HIL or flight validation.'
        }
        (target / 'VERIFIED_COMPLETE.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
        deliveries.append(record)
        print(f'{method}: verified {len(manifest["files"])} files, 60 final runs and 24 pilot runs.', flush=True)
    summary = {'complete': True, 'deliveries': deliveries, 'main_runs': 360, 'development_runs': 144}
    (ROOT / 'results/VERIFIED_COMPLETE.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
