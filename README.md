# Quadrotor PID Optimization Studies

**Mohammad ALbaraj**

Offline controller tuning for a nonlinear quadrotor attitude and motor model,
using eleven optimization methods. This repository provides the implementations,
experiment settings, saved numerical results, validation data, and figures.
Each method has its own explanation and reproducibility guide.

**Papers, manuscripts, and rendered PDF/HTML reports are not published here.**
Results are simulation evidence, not hardware flight certification.

## Start here

- [Model, controller, objective, and experimental design](docs/METHODOLOGY.md)
- [Data formats, provenance, checks, and reproduction limits](docs/DATA.md)
- [Five-method nominal benchmark](all%20work/30%20seed%20equal%20budget%20study/README.md)
- [Five-method robustness benchmark](all%20work/robustness%2030%20seed%20study/README.md)

## Algorithms and saved results

The table summarizes **30-seed runs at 3,264 unique evaluations per run**.
Lower fitness is better within a regime. Nominal and robust objectives use
different training sets and should not be compared as identical scales.
Click a method for its algorithm steps, settings, results, figures, and commands.

| Method and guide | Nominal median | Robust median | Nominal feasible | Robust feasible |
| --- | --- | --- | --- | --- |
| [GA](all%20work/pid%20using%20ga/README.md) | 0.052263125 | 0.066991874 | 30/30 | 30/30 |
| [PSO](all%20work/pid%20using%20pso/README.md) | 0.052025843 | 0.065736838 | 30/30 | 30/30 |
| [CSO](all%20work/pid%20using%20cat%20swarm/README.md) | 0.067147048 | 0.085949108 | 30/30 | 30/30 |
| [DSA](all%20work/pid%20using%20dolphin%20swarm/README.md) | 0.057028331 | 0.070202619 | 30/30 | 30/30 |
| [CMA-ES](all%20work/pid%20using%20cma%20es/README.md) | 0.052958785 | 0.066696075 | 30/30 | 30/30 |
| [GDA](pid%20using%20great%20deluge/README.md) | 0.056975456 | 0.073227065 | 30/30 | 30/30 |
| [TA](pid%20using%20threshold%20accepting/README.md) | 0.055345629 | 0.069379069 | 30/30 | 29/30 |
| [ALNS](pid%20using%20alns/README.md) | 0.052767344 | 0.06685603 | 30/30 | 30/30 |
| [VND](pid%20using%20vnd/README.md) | 0.053073821 | 0.068521437 | 30/30 | 28/30 |
| [SBRS](pid%20using%20shrinking%20ball%20random%20search/README.md) | 0.051609095 | 0.067077749 | 30/30 | 29/30 |
| [PRW](pid%20using%20pure%20random%20walk/README.md) | 0.089606718 | 0.15397958 | 30/30 | 29/30 |

The first five methods form the original equal-budget benchmark. The six newer
methods received an additional four-setting development study before their main
runs. **The eleven-method comparison is exploratory: final budgets match, total
development effort does not.** The earlier three-seed, iteration-based studies
remain available in the individual GA/PSO/CSO/DSA/CMA-ES folders and are documented
separately from this table.

Within the five-method benchmark, PSO has the lowest saved median training fitness
in both regimes. SBRS has the lowest nominal median among the six extensions;
ALNS has the lowest robust median among those six. These observations concern one
model and the stated settings, not universal superiority. Infeasible runs remain
in the summaries: robust TA, SBRS, and PRW each have one; robust VND has two.

![Exploratory eleven-method comparison](pid%20using%20alns/results/plots/07_eleven_methods.png)

The plot shows medians only. Read the feasibility counts above and the per-method
means/standard deviations to see penalties and failed runs.

## What is optimized?

Eight bounded gains govern roll/pitch outer-angle loops, equivalent inner-loop
proportional/integral behavior, and yaw-rate PI control. The code preserves the
source's discrete pole, saturations, mixer, motor lag, and nonlinear rotational
dynamics. It does not optimize translational trajectory or altitude control.

Each optimizer searches normalized logarithmic gain coordinates. Candidates are
evaluated on tracking speed, integrated error, effort, and feasibility constraints.
Nominal training uses six single-axis commands; robust training uses 30 cases
covering nominal and uncertain plants. See the methodology for equations and units.

## Representative response and validation figures

![ALNS representative responses](pid%20using%20alns/results/plots/ALNS/01_responses.png)

These curves compare training-selected best and median representatives against
the original controller. The panel shows the first second after the command;
full-horizon plots are available in each extension's figure index. A good nominal
response does not establish robustness.

![Five-method robustness and tracking tradeoff](all%20work/robustness%2030%20seed%20study/results/plots/03_robustness_speed_tradeoff.png)

Validation separates 300 random single-axis cases, 54 one-factor boundaries, and
90 combined-axis stress cases per controller in the later robustness protocol.
Selected controllers also undergo 1,536 joint-boundary checks. In the saved
five-method robust study, all 150 robust-tuned controllers pass the 300 random
single-axis cases, but all fail the combined-axis stress suite. Robust tuning
therefore does not solve the modeled simultaneous-axis limitation. Finite sampled
passes are not a proof over a continuous uncertainty region.

## Repository layout

```text
all work/
  pid using ga/                 # original three-seed GA study
  pid using pso/                # original three-seed PSO study
  pid using cat swarm/          # original three-seed CSO study
  pid using dolphin swarm/      # original three-seed DSA study
  pid using cma es/             # original three-seed CMA-ES study
  30 seed equal budget study/   # five-method nominal benchmark
  robustness 30 seed study/     # five-method robustness benchmark
pid using alns/                 # six extension methods in separate folders
pid using great deluge/
pid using pure random walk/
pid using shrinking ball random search/
pid using threshold accepting/
pid using vnd/
docs/                          # shared methodology and data documentation
```

Study folders contain `model.py`, `study.py`, optimizer modules, tests,
configuration, requirements, source model files, and `results/`. Results include
CSV/JSON summaries, raw run records, compressed arrays and validation records,
gain exports, and PNG/SVG figures. Frozen reference snapshots support comparisons.

## Installation and first checks

From PowerShell:

```powershell
git clone https://github.com/mhmdsalemm100/Quadrotor-pid-Optimization.git
cd "Quadrotor-pid-Optimization/all work/pid using cat swarm"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m unittest test_study test_cso
```

The existing research environment uses Python 3.13.6, NumPy 2.5.3, SciPy 1.18.1,
Numba 0.68.0, and pycma 4.5.0. Study-specific lock files are supplied. A clean
installation on another machine has not been verified. Python simulations do not
require MATLAB; opening or executing the original SLX models does require the
appropriate MATLAB/Simulink installation.

For a new small simulation run in the selected study:

```powershell
.\.venv\Scripts\python.exe run_study.py --mode quick --output results_quick
```

This command can still take time and creates local outputs. Existing comparison
snapshots are included. Use the method README for its full-run command. For the
extension methods, `run_method.py --processes 4 --search-only` audits/reuses the
supplied method runs; omitting `--search-only` performs additional validation.
Keep archived results intact and use a separate copy for new protocols.

## Verification and limitations

The supplied Python source passes syntax checks. Supplied unit suites and saved
evaluation ledgers were checked during this update; see [DATA.md](docs/DATA.md)
for exact outcomes and scope. Full optimization campaigns were not rerun.

Some report/delivery helpers retain machine-specific Windows paths and fonts.
They are optional local tooling, not a portable publication pipeline. Central
six-method analysis expects all six methods together; each delivered extension
folder holds its own method runs. Source hashes in contracts must match before
reusing an experiment. Controller and mixer timing remain assumed, and negative
motor speeds are rejected under the preserved source model.

## Citation and licensing

If you use this code, numerical results, or figures in research, please cite:

**ALbaraj, Mohammad. _Quadrotor PID Optimization Studies_ [Software and simulation data].**
https://github.com/mhmdsalemm100/Quadrotor-pid-Optimization

[CITATION.cff](CITATION.cff) supplies GitHub's citation metadata. No reuse license
has yet been selected; this citation request does not itself grant permission to
reuse the material. Existing third-party rights remain applicable.
