"""Read-only study exploration and isolated, opt-in experiment helpers."""
from pathlib import Path
import ast
import csv
import gzip
import html
import json
import os
import subprocess
import sys
from urllib.parse import quote

import numpy as np
import matplotlib.pyplot as plt
from IPython.display import Code, HTML, Image, Markdown, display

ROOT = Path(__file__).resolve().parents[1]
METHODS = {
    'GA': ('all work/pid using ga', 'Genetic Algorithm', 'study.py'),
    'PSO': ('all work/pid using pso', 'Particle Swarm Optimization', 'pso.py'),
    'CSO': ('all work/pid using cat swarm', 'Cat Swarm Optimization', 'cso.py'),
    'DSA': ('all work/pid using dolphin swarm', 'Dolphin Swarm Algorithm', 'dsa.py'),
    'CMA-ES': ('all work/pid using cma es', 'Covariance Matrix Adaptation Evolution Strategy', 'cmaes.py'),
    'GDA': ('pid using great deluge', 'Great Deluge Algorithm', 'methods.py'),
    'TA': ('pid using threshold accepting', 'Threshold Accepting', 'methods.py'),
    'ALNS': ('pid using alns', 'Adaptive Large Neighborhood Search', 'methods.py'),
    'VND': ('pid using vnd', 'Variable Neighborhood Descent', 'methods.py'),
    'SBRS': ('pid using shrinking ball random search', 'Shrinking Ball Random Search', 'methods.py'),
    'PRW': ('pid using pure random walk', 'Pure Random Walk', 'methods.py'),
}
ORIGINAL = list(METHODS)[:5]
NOMINAL = ROOT / 'all work/30 seed equal budget study'
ROBUST = ROOT / 'all work/robustness 30 seed study'


def study(method):
    return ROOT / METHODS[method][0]


def load_json(path):
    path = Path(path)
    if path.name.endswith('.json.gz'):
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            return json.load(stream)
    return json.loads(path.read_text(encoding='utf-8-sig'))


def load_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def show_table(rows, columns=None, limit=40):
    rows = list(rows)
    if not rows:
        display(Markdown('*No matching rows.*'))
        return
    columns = columns or list(rows[0])
    def cell(v):
        if isinstance(v, (dict, list, tuple)):
            v = json.dumps(v, ensure_ascii=False)
        return html.escape(str(v))
    text = '<table><thead><tr>' + ''.join('<th>'+cell(c)+'</th>' for c in columns) + '</tr></thead><tbody>'
    for row in rows[:limit]:
        text += '<tr>' + ''.join('<td>'+cell(row.get(c, ''))+'</td>' for c in columns) + '</tr>'
    display(HTML(text+'</tbody></table>'))
    if len(rows) > limit:
        print(f'Showing {limit} of {len(rows)} rows. Increase limit to inspect more.')


def show_source(path, symbol=None):
    path = Path(path)
    source = path.read_text(encoding='utf-8-sig')
    if symbol:
        tree = ast.parse(source)
        node = next(n for n in tree.body if getattr(n, 'name', None) == symbol)
        source = '\n'.join(source.splitlines()[node.lineno-1:node.end_lineno])
    display(Code(source, language='python' if path.suffix == '.py' else 'text'))


def source_index():
    result = []
    for p in sorted(ROOT.rglob('*.py')):
        if any(part in {'.git', '.venv', '.venv-notebooks', 'notebook_outputs'} for part in p.parts) or p.is_relative_to(ROOT/'notebooks'):
            continue
        tree = ast.parse(p.read_text(encoding='utf-8-sig'))
        names = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        result.append({'file': p.relative_to(ROOT).as_posix(), 'definitions': ', '.join(names)})
    return result


def load_runs(method, mode='nominal'):
    if mode not in {'nominal', 'robust'}:
        raise ValueError('mode must be nominal or robust')
    folder = (NOMINAL if mode == 'nominal' else ROBUST)/'results/runs' if method in ORIGINAL else study(method)/'results'/mode/'runs'
    runs = [(p, load_json(p)) for p in sorted(folder.glob(f'{method}_*.json'))
            if p.stem.removeprefix(method + '_').isdigit()]
    assert len(runs) == 30, (method, mode, len(runs))
    return sorted(runs, key=lambda pair: pair[1]['seed'])


def fitness_summary(methods=None):
    result = []
    for method in methods or METHODS:
        for mode in ['nominal', 'robust']:
            values = np.array([r['fitness'] for _, r in load_runs(method, mode)])
            result.append({'method': method, 'regime': mode, 'runs': len(values),
                           'best': float(values.min()), 'median': float(np.median(values)),
                           'mean': float(values.mean()), 'sample_sd': float(values.std(ddof=1)),
                           'feasible': int((values < 1000).sum())})
    return result


def convergence_plot(method, mode='nominal'):
    histories = []
    for path, record in load_runs(method, mode):
        with np.load(path.with_name(path.stem+'_evaluations.npz'), allow_pickle=False) as data:
            ledger = data['ledger']
            assert ledger.shape == (3264, 12)
            np.testing.assert_allclose(ledger[:, 3], np.minimum.accumulate(ledger[:, 2]), atol=1e-13, rtol=0)
            histories.append(ledger[:, 3].copy())
    histories = np.array(histories)
    low, med, high = np.quantile(histories, [0.25, 0.5, 0.75], axis=0)
    fig, ax = plt.subplots(figsize=(8, 3.5))
    evaluations = np.arange(1, 3265)
    ax.fill_between(evaluations, low, high, alpha=.2, label='Across-seed IQR')
    ax.plot(evaluations, med, label='Across-seed median')
    ax.set(xlabel='Unique objective evaluations (initialization included)', ylabel='Best constrained fitness',
           title=f'{method}: {mode}, 30 seeds', yscale='log')
    ax.legend(); ax.grid(alpha=.2); fig.tight_layout(); plt.show(); plt.close(fig)


def validation_rows(method):
    folder = ROBUST if method in ORIGINAL else study(method)
    return [r for r in load_csv(folder/'results/validation_summary.csv') if r['method'] == method]


def validation_summary(method):
    result = []
    for mode in ['nominal', 'robust']:
        data = [r for r in validation_rows(method) if r['mode'] == mode]
        for field, suite, total in [('single_axis_mc_passes','Random single-axis',300),
                                     ('one_at_a_time_passes','One-factor boundaries',54),
                                     ('combined_stress_passes','Combined-axis stress',90)]:
            values = np.array([int(r[field]) for r in data])
            result.append({'method': method, 'training': mode, 'suite': suite, 'cases_per_controller': total,
                           'minimum_passes': int(values.min()), 'median_passes': float(np.median(values)),
                           'maximum_passes': int(values.max())})
    return result


def figures(method=None):
    folders = [study(method)/'results/plots'] if method else [p for p in ROOT.rglob('plots') if p.parent.name == 'results']
    return sorted(p for folder in folders for p in folder.rglob('*.png'))


def file_links(paths, title='Files'):
    lines = [f'### {title}']
    for p in paths:
        rel = Path(p).relative_to(ROOT).as_posix()
        lines.append(f'- [{rel}](../{quote(rel, safe="/._-")})')
    display(Markdown('\n'.join(lines)))


def show_figures(paths, limit=3):
    for p in list(paths)[:limit]:
        display(Markdown('**'+p.relative_to(ROOT).as_posix()+'**'))
        display(Image(filename=str(p), width=850))


def gallery(paths, page_size=12):
    paths = list(paths)
    for start in range(0, len(paths), page_size):
        batch = paths[start:start+page_size]
        fig, axes = plt.subplots(int(np.ceil(len(batch)/3)), 3, figsize=(15, 3.1*np.ceil(len(batch)/3)), squeeze=False)
        for ax in axes.flat:
            ax.axis('off')
        for ax, p in zip(axes.flat, batch):
            ax.imshow(plt.imread(p)); ax.set_title(p.parent.parent.parent.name+'\n'+p.name, fontsize=7)
        fig.suptitle(f'Figure index {start+1}–{start+len(batch)} of {len(paths)}; open linked originals for detail', fontsize=10)
        fig.tight_layout(); plt.show(); plt.close(fig)


def isolated_python(method, source, timeout=180):
    """Use a fresh process so different studies' model/study imports cannot collide."""
    out = ROOT/'notebook_outputs'/method
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy(); env['PID_NOTEBOOK_OUTPUT'] = str(out)
    env['PYTHONIOENCODING'] = 'utf-8'
    process = subprocess.run([sys.executable, '-c', source], cwd=study(method),
                             env=env, capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    if process.returncode:
        raise RuntimeError(process.stderr or process.stdout)
    if process.stdout.strip():
        print(process.stdout.strip())
    return out


def demo_source(method):
    """Small fresh optimization, not a reproduction of the published budget."""
    prefix = '''from pathlib import Path
import json, os
cfg=json.loads(Path('config.json').read_text())
out=Path(os.environ['PID_NOTEBOOK_OUTPUT'])/'small_search'
out.mkdir(exist_ok=True)
from study import training_scenarios
'''
    if method in ORIGINAL:
        name, module = {'GA':('genetic_algorithm','study'), 'PSO':('particle_swarm','pso'),
                        'CSO':('cat_swarm','cso'), 'DSA':('dolphin_swarm','dsa'), 'CMA-ES':('cma_es','cmaes')}[method]
        return prefix + f"from {module} import {name}\ncfg.update(population=8,swarm_size=8,generations=2,iterations=2,workers=1)\nresult={name}(cfg,training_scenarios(),2026,out)\nprint('Fresh small-search fitness:',result['fitness'])\n"
    return prefix + f"from methods import optimize\nparams=json.loads(Path('results/selected_parameters.json').read_text())[{method!r}]\nresult=optimize({method!r},2026,cfg,params,out=out,limit=96)\nprint('Fresh 96-evaluation nominal fitness:',result['fitness'])\n"
