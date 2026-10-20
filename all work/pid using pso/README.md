# Particle Swarm Optimization (PSO) for quadrotor controller tuning

**Author: Mohammad ALbaraj** · [Project overview](../../README.md) · [Shared model and objective](../../docs/METHODOLOGY.md)

## Purpose

Tune eight bounded roll/pitch and yaw-rate controller parameters offline. The optimizer changes gains; it does not change the plant equations, controller structure, or constraints. Lower constrained fitness is better within the same training regime.

## How this implementation works

Global-best PSO moves particles through normalized log-gain space using their own experience and the swarm's best known point.

1. Initialize stratified positions, the original controller, and velocities in [-0.1, 0.1].
2. Evaluate each position and update personal and global bests.
3. Update velocity with `v = w*v + c1*r1*(personal_best-x) + c2*r2*(global_best-x)`.
4. Use c1=c2=1.7 and decrease inertia w from 0.9 to 0.4 over the original iteration-based run.
5. Limit each velocity coordinate to ±0.2. Clip positions to [0, 1] and reverse/damp boundary-hit velocities by 0.5.
6. Repeat 50 updates with 64 particles and return the global best.

PSO has no crossover or mutation. In the separate strict-budget benchmark, inertia follows evaluation-budget progress.

Read [pso.py](pso.py) for the implemented update rules, [config.json](config.json) for settings, and [study.py](study.py) for objective evaluation.

## Original study settings

| Setting | Value |
| --- | --- |
| seeds | `[11, 29, 47]` |
| workers | `4` |
| swarm_size | `64` |
| iterations | `50` |
| inertia_start | `0.9` |
| inertia_end | `0.4` |
| cognitive_coefficient | `1.7` |
| social_coefficient | `1.7` |
| velocity_limit | `0.2` |
| initial_velocity_limit | `0.1` |
| boundary_damping | `0.5` |

The original study uses seeds 11, 29, and 47. Separate robust searches and exploratory sensitivity runs are additional experiments. Their results are not pooled into the nominal main runs.

## Saved original-study results

| Seed | Final training fitness | Unique evaluations |
| --- | --- | --- |
| 11 | 0.052334995 | 3264 |
| 29 | 0.052220983 | 3264 |
| 47 | 0.0518131 | 3264 |

Selected controller: **best training fitness across seeds; seed 47**. Its training fitness is **0.0518131**; the source baseline is **1011.6168**, which includes infeasibility penalties. The difference is not a percentage improvement in settling time.

| Gain | Selected value |
| --- | --- |
| roll_outer_K | 11.410064 |
| roll_inner_Kp_equivalent | 0.068153392 |
| roll_inner_Ki_equivalent | 0.002496343 |
| pitch_outer_K | 16.334872 |
| pitch_inner_Kp_equivalent | 0.14772558 |
| pitch_inner_Ki_equivalent | 0.063413158 |
| yaw_Kp | 0.38660811 |
| yaw_Ki | 0.10347897 |

Exact discrete coefficients are in [best_gains.json](results/best_gains.json) and [SIMULINK_PARAMETER_MAP.txt](results/SIMULINK_PARAMETER_MAP.txt). Roll/pitch equivalent Kp/Ki values must not be substituted blindly into an ideal PI block; retain the exported pole and numerator.

## Separate 30-seed, equal-budget results

These numbers come from the later benchmark: 3,264 unique evaluations per seed, including initialization. They are not the three-seed results above.

| Regime | Best | Median | Mean | Sample SD | Training-feasible runs |
| --- | --- | --- | --- | --- | --- |
| Nominal | 0.051033503 | 0.052025843 | 0.051917325 | 0.00046374851 | 30/30 |
| Robust | 0.065152582 | 0.065736838 | 0.066124861 | 0.00093294274 | 30/30 |

Sources: [nominal benchmark](../../all%20work/30%20seed%20equal%20budget%20study/README.md) and [robustness benchmark](../../all%20work/robustness%2030%20seed%20study/README.md). Nominal and robust fitness use different training scenario sets, so their numerical magnitudes are not directly interchangeable.

## Run and inspect

From this folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m unittest test_study test_pso
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

![Particle Swarm Optimization: 01_step_responses](results/plots/01_step_responses.png)

![Particle Swarm Optimization: 02_pso_iterations](results/plots/02_pso_iterations.png)

![Particle Swarm Optimization: 05_robustness](results/plots/05_robustness.png)

### Complete figure index

- [01 step responses](results/plots/01_step_responses.png)
- [02 pso iterations](results/plots/02_pso_iterations.png)
- [03 coupled and saturation](results/plots/03_coupled_and_saturation.png)
- [04 inner loops](results/plots/04_inner_loops.png)
- [05 robustness](results/plots/05_robustness.png)
- [06 gain sensitivity](results/plots/06_gain_sensitivity.png)
- [07 metric comparison](results/plots/07_metric_comparison.png)
- [08 fitness components](results/plots/08_fitness_components.png)
- [09 robust candidate](results/plots/09_robust_candidate.png)
- [10 ga vs pso](results/plots/10_ga_vs_pso.png)
- [11 ga vs pso convergence](results/plots/11_ga_vs_pso_convergence.png)

## Limits and provenance

The files are saved simulation outputs from the supplied project, not new flight tests. Packaging checks and unit tests do not independently rerun the full optimization campaigns. The six newer methods received a development grid that the original five did not; an eleven-method comparison is exploratory even with equal final budgets. Controller timing is assumed at 1 ms and mixer timing at 4 ms. Negative motor speeds are rejected under the preserved source motor equation. Position/altitude control and hardware robustness are outside this study.

See [shared methodology](../../docs/METHODOLOGY.md) and [data provenance](../../docs/DATA.md). Please cite Mohammad ALbaraj using [CITATION.cff](../../CITATION.cff). No reuse license has yet been selected.
