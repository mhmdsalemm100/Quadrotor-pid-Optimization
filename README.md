# Quadrotor PID Optimization Studies

**Author and maintainer: Mohammad ALbaraj**

Python source code for offline tuning of eight quadrotor attitude-controller
parameters using optimization algorithms. The project models rotational and
motor dynamics, evaluates candidate controller gains, and provides code for
nominal and uncertain-plant experiments.

This distribution contains code, experiment configuration, dependency files,
tests, and MATLAB/Simulink source models. Papers, manuscripts, saved experiment
results, optimized gain datasets, figures, spreadsheets, and rendered reports
are not included.

## Methods and folders

| Folder | Purpose |
| --- | --- |
| `all work/pid using ga` | Genetic algorithm |
| `all work/pid using pso` | Particle swarm optimization |
| `all work/pid using cat swarm` | Cat swarm optimization |
| `all work/pid using dolphin swarm` | Dolphin swarm optimization |
| `all work/pid using cma es` | CMA-ES |
| `all work/30 seed equal budget study` | Five-method nominal benchmark code |
| `all work/robustness 30 seed study` | Five-method robustness benchmark code |
| `pid using alns` | Continuous adaptive large neighborhood search |
| `pid using great deluge` | Great deluge |
| `pid using pure random walk` | Pure random walk |
| `pid using shrinking ball random search` | Shrinking ball random search |
| `pid using threshold accepting` | Threshold accepting |
| `pid using vnd` | Variable neighborhood descent |

The six extension folders contain shared experiment machinery alongside their
method identifier. They are not six unrelated plant models. Source folder names
are preserved so local imports and relative paths retain their original layout.

## How the code works

1. `model.py` implements the plant and controller simulation.
2. `config.json` specifies gain bounds, simulation settings, and search settings.
3. `study.py` defines scenarios and evaluates performance and constraint penalties.
4. Optimizer modules propose gain vectors and retain evaluated candidates.
5. Runners execute experiments; analysis and plotting scripts consume generated
   files. Those scripts are included as code, not as completed reports.

Tuning uses logarithmically scaled gain coordinates. The modeled controller
includes roll/pitch angle control and yaw-rate control. Source assumptions such
as controller/mixer timing, saturation, and the motor model must be checked
before applying any generated gains outside this simulation.

## Set up and test one study

Install Python, clone the repository, and run these commands in PowerShell:

```powershell
git clone https://github.com/mhmdsalemm100/Quadrotor-pid-Optimization.git
cd "Quadrotor-pid-Optimization/all work/pid using cat swarm"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m unittest test_study test_cso
```

Each study has its own dependency files. A tested Python-version range and a
fresh-environment installation check are still pending. All 278 supplied Python
files passed a syntax check during packaging; this is not runtime validation.

## Generating your own outputs

Read the entry point and configuration before launching a full experiment;
large searches and uncertainty sweeps can take substantial time.

For example, the cat swarm runner supports:

```powershell
.\.venv\Scripts\python.exe run_study.py --mode quick --output results_quick
```

**This is not yet a fully self-contained end-to-end quick start.** The original
runner performs a final comparison against archived GA/PSO data, which this
code-only distribution intentionally omits. That comparison can fail after
local optimization outputs have been generated. Use the optimizer modules and
tests independently, or supply your own comparison inputs before running the
complete reporting pipeline.

Other archived-data dependencies include:

- `run_method.py` expects locally generated `results/contract.json` and
  `results/selected_parameters.json`. A fresh extension experiment starts with
  `run_extension.py`, which performs development and main searches.
- Analysis, report, comparison, and verification scripts require the relevant
  local experiment outputs and sometimes reference-benchmark datasets.
- Some delivery/report helpers retain original Windows-specific paths and font
  requirements. Review these helpers before executing them on another machine.

Generated outputs are ignored by Git. Do not force-add research results,
papers, figures, or archives. Experiment source is preserved; do not reuse old
frozen contracts after changing scientific code or configuration.

## Interpretation

This repository supplies research simulation code. It does not establish
hardware readiness, global optimality, or verified equivalence to a compiled
Simulink model. No numerical results or algorithm rankings are published here.
Algorithm references remain in source comments/docstrings where supplied.

## Citation and licensing

If you use this software in research, please cite:

ALbaraj, Mohammad. *Quadrotor PID Optimization Studies* [Computer software].
https://github.com/mhmdsalemm100/Quadrotor-pid-Optimization

Machine-readable metadata is in [CITATION.cff](CITATION.cff).
No reuse license has been selected yet; this citation request does not itself
grant a software license. Existing third-party rights remain applicable.
