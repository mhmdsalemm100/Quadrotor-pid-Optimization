# Covariance Matrix Adaptation Evolution Strategy (CMA-ES) for quadrotor controller tuning

**Author: Mohammad ALbaraj** · [Project overview](../../README.md) · [Shared model and objective](../../docs/METHODOLOGY.md)

## Purpose

Tune eight bounded roll/pitch and yaw-rate controller parameters offline. The optimizer changes gains; it does not change the plant equations, controller structure, or constraints. Lower constrained fitness is better within the same training regime.

## How this implementation works

This method uses pycma's active, full-covariance CMA-ES in normalized log-gain coordinates.

1. Evaluate 64 shared stratified initial candidates, including the original controller.
2. Initialize the search mean at the best initial point with sigma0=0.25.
3. Ask the library for a population of 64 samples, mapped into [0, 1] using BoundTransform.
4. Evaluate candidates and tell the library their fitness values; update the mean, covariance, and global step size.
5. Record sigma, covariance eigenvalues, and axis ratio, and retain the best point across all evaluations.
6. Complete 50 updates in the original study. Library stop flags are recorded rather than used to shorten this fixed experiment.

The full covariance learns correlations between controller gains. Active covariance updates use information from poorer samples as well as successful ones. The separate benchmark instead stops at the exact unique-evaluation budget.

Read [cmaes.py](cmaes.py) for the implemented update rules, [config.json](config.json) for settings, and [study.py](study.py) for objective evaluation.

## Original study settings

| Setting | Value |
| --- | --- |
| seeds | `[11, 29, 47]` |
| workers | `4` |
| swarm_size | `64` |
| iterations | `50` |
| comparison_evaluation_budget | `3264` |
| sigma0 | `0.25` |
| cma_active | `true` |
| cma_diagonal | `false` |
| cma_initialization | `"best of shared stratified initial population"` |

The original study uses seeds 11, 29, and 47. Separate robust searches and exploratory sensitivity runs are additional experiments. Their results are not pooled into the nominal main runs.

## Saved original-study results

| Seed | Final training fitness | Unique evaluations |
| --- | --- | --- |
| 11 | 0.053226156 | 3264 |
| 29 | 0.053677229 | 3264 |
| 47 | 0.05226415 | 3264 |

Selected controller: **best training fitness across seeds; seed 47**. Its training fitness is **0.05226415**; the source baseline is **1011.6168**, which includes infeasibility penalties. The difference is not a percentage improvement in settling time.

| Gain | Selected value |
| --- | --- |
| roll_outer_K | 15.92718 |
| roll_inner_Kp_equivalent | 0.15782826 |
| roll_inner_Ki_equivalent | 0.002889811 |
| pitch_outer_K | 16.219622 |
| pitch_inner_Kp_equivalent | 0.16060491 |
| pitch_inner_Ki_equivalent | 0.00041475661 |
| yaw_Kp | 0.38840111 |
| yaw_Ki | 0.091676592 |

Exact discrete coefficients are in [best_gains.json](results/best_gains.json) and [SIMULINK_PARAMETER_MAP.txt](results/SIMULINK_PARAMETER_MAP.txt). Roll/pitch equivalent Kp/Ki values must not be substituted blindly into an ideal PI block; retain the exported pole and numerator.

## Separate 30-seed, equal-budget results

These numbers come from the later benchmark: 3,264 unique evaluations per seed, including initialization. They are not the three-seed results above.

| Regime | Best | Median | Mean | Sample SD | Training-feasible runs |
| --- | --- | --- | --- | --- | --- |
| Nominal | 0.05226415 | 0.052958785 | 0.053037539 | 0.00056362 | 30/30 |
| Robust | 0.065400499 | 0.066696075 | 0.06679798 | 0.0011446262 | 30/30 |

Sources: [nominal benchmark](../../all%20work/30%20seed%20equal%20budget%20study/README.md) and [robustness benchmark](../../all%20work/robustness%2030%20seed%20study/README.md). Nominal and robust fitness use different training scenario sets, so their numerical magnitudes are not directly interchangeable.

## Run and inspect

From this folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m unittest test_study test_cmaes
.\.venv\Scripts\python.exe run_study.py --mode quick --output results_quick
```

Use `--mode full --output results_new` for a fresh full run. Keep the distributed `results/` as the archived experiment. Quick mode is still a simulation study, not an instant test. Comparison reference snapshots are included where required. Report-generation code may create local HTML; rendered reports are excluded from version control.

## Result files

| Path | Meaning |
| --- | --- |
| [results/metrics.csv](results/metrics.csv) | Per-controller, per-scenario response metrics and feasibility |
| [results/monte_carlo.csv](results/monte_carlo.csv) | Single-axis uncertainty and combined-axis stress cases |
| [results/robust_gains.json](results/robust_gains.json) | Separate uncertainty-focused candidate |
| [results/numerical_convergence.csv](results/numerical_convergence.csv) | Integration-step sensitivity |
| [results/gain_sensitivity.csv](results/gain_sensitivity.csv) | One-gain-at-a-time perturbations |
| [results/](results/) | Run JSON, iteration histories, candidate data, traces, and historical verification |

## Figures

![Covariance Matrix Adaptation Evolution Strategy: 01_step_responses](results/plots/01_step_responses.png)

![Covariance Matrix Adaptation Evolution Strategy: 02_cmaes_iterations](results/plots/02_cmaes_iterations.png)

![Covariance Matrix Adaptation Evolution Strategy: 05_robustness](results/plots/05_robustness.png)

### Complete figure index

- [01 step responses](results/plots/01_step_responses.png)
- [02 cmaes iterations](results/plots/02_cmaes_iterations.png)
- [03 coupled and saturation](results/plots/03_coupled_and_saturation.png)
- [04 inner loops](results/plots/04_inner_loops.png)
- [05 robustness](results/plots/05_robustness.png)
- [06 gain sensitivity](results/plots/06_gain_sensitivity.png)
- [07 metric comparison](results/plots/07_metric_comparison.png)
- [08 fitness components](results/plots/08_fitness_components.png)
- [09 robust candidate](results/plots/09_robust_candidate.png)
- [10 method responses](results/plots/10_method_responses.png)
- [11 evaluation comparison](results/plots/11_evaluation_comparison.png)
- [12 cma adaptation](results/plots/12_cma_adaptation.png)

## Limits and provenance

The files are saved simulation outputs from the supplied project, not new flight tests. Packaging checks and unit tests do not independently rerun the full optimization campaigns. The six newer methods received a development grid that the original five did not; an eleven-method comparison is exploratory even with equal final budgets. Controller timing is assumed at 1 ms and mixer timing at 4 ms. Negative motor speeds are rejected under the preserved source motor equation. Position/altitude control and hardware robustness are outside this study.

See [shared methodology](../../docs/METHODOLOGY.md) and [data provenance](../../docs/DATA.md). Please cite Mohammad ALbaraj using [CITATION.cff](../../CITATION.cff). No reuse license has yet been selected.
