"""Read, never execute, the supplied Simulink source; build an auditable inventory."""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent

def inventory():
    src = ROOT / 'source'
    doc = ET.parse(src / 'blockdiagram.xml')
    defaults = {b.get('BlockType'): {p.get('Name'): p.text for p in b.findall('P')}
                for b in ET.parse(src / 'bddefaults.xml').findall('.//Block')}
    rows = []
    def walk(system, prefix):
        for b in system.findall('Block'):
            path = prefix + '/' + b.get('Name', '')
            values = dict(defaults.get(b.get('BlockType'), {}))
            values.update({p.get('Name'): p.text for p in b.findall('P')})
            rows.append({'path': path, 'sid': b.get('SID'), 'type': b.get('BlockType'),
                         'effective_saved_parameters': values})
            if b.find('System') is not None:
                walk(b.find('System'), path)
    walk(doc.find('.//Model/System'), 'AttitudeControl_Sim')
    functions = [p.text for p in ET.parse(src / 'stateflow.xml').findall('.//P')
                 if p.get('Name') == 'script']
    params = {}
    for f in ['Init.m', 'Init_control.m']:
        for line in (src / f).read_text(encoding='gbk', errors='replace').splitlines():
            m = re.match(r'^\s*(\w+)\s*=\s*([-+\d.eE]+)\s*;', line)
            if m:
                params[m[1]] = float(m[2])
    result = {'sha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                        for f in src.iterdir() if f.is_file() and f.suffix != '.json'},
              'numeric_initialization_parameters': params,
              'blocks': rows, 'embedded_functions': functions,
              'warning': 'Saved inherited sample times cannot determine compiled execution rates.'}
    (src / 'inventory.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result

if __name__ == '__main__':
    data = inventory()
    print(f"Inventoried {len(data['blocks'])} blocks and {len(data['embedded_functions'])} functions.")
