# Adaptive Large Neighborhood Search (ALNS) for quadrotor controller tuning

**Author: Mohammad ALbaraj** · [Project overview](../README.md) · [Shared model and objective](../docs/METHODOLOGY.md)

## Purpose

Tune eight bounded roll/pitch and yaw-rate controller parameters offline. The optimizer changes gains; it does not change the plant equations, controller structure, or constraints. Lower constrained fitness is better within the same training regime.

## How this implementation works

This is a continuous gain-tuning adaptation of ALNS, not a vehicle-routing implementation.

1. Start at the best shared initial candidate.
2. Select a destroy size of 1, 2, 4, or 8 coordinates by adaptive roulette weights.
3. Select a repair operator: uniform replacement, Gaussian perturbation, or an elite-difference proposal `a + 0.5*(b-c)` using three points from the best 16 evaluated candidates.
4. Reflect the repaired coordinates into the allowed domain.
5. Accept using a decreasing threshold on log(1+fitness), initially 0.05.
6. Reward operators by 5 for a new archive best, 3 for an improvement, 1 for an accepted move, and 0.1 otherwise. Every 64 moves, smooth weights toward average reward using the selected reaction factor.
7. Stop at 3,264 unique evaluations and export the archive best.

Destroy and repair choices adapt separately. The reward scheme, coordinate neighborhoods, and threshold rule are explicit problem-specific design choices.

Read [methods.py](methods.py) for the implemented update rules, [config.json](config.json) for settings, and [study.py](study.py) for objective evaluation.

## Protocol and selected settings

Each regime has 30 main seeds: 11, 29, 47, and 101–127. Every run receives 3,264 unique objective evaluations, including the same 64 initial points. Duplicate normalized coordinates rounded to 13 decimals are cached and do not spend the budget. The best evaluated point remains valid even when the budget interrupts a final state update.

Four candidate settings were compared on development seeds 5011, 5021, and 5039 under both nominal and robust training (24 development runs per method). The lowest average within-block rank selected one setting for both regimes. Main-seed and held-out validation results were not used for that selection.

| Selected parameter | Value |
| --- | --- |
| repair_sigma | 0.16 |
| reaction | 0.1 |
| threshold0 | 0.05 |
| segment | 64 |

## Saved 30-seed results

| Regime | Best | Median | Mean | Sample SD | Training-feasible runs |
| --- | --- | --- | --- | --- | --- |
| nominal | 0.051122045 | 0.052767344 | 0.053167346 | 0.0015660325 | 30/30 |
| robust | 0.065002597 | 0.06685603 | 0.067214715 | 0.0018699537 | 30/30 |

Source: [fitness_summary.csv](results/fitness_summary.csv). Infeasible runs have penalized scores above 1,000 and remain in means and standard deviations. A low median does not imply every run found a feasible controller.

### Held-out validation

| Training regime | Suite | Pass range across 30 runs | Median passes |
| --- | --- | --- | --- |
| nominal | Random single-axis | 295–300 / 300 | 298 / 300 |
| nominal | One-factor boundaries | 48–53 / 54 | 50 / 54 |
| nominal | Combined-axis stress | 0–0 / 90 | 0 / 90 |
| robust | Random single-axis | 300–300 / 300 | 300 / 300 |
| robust | One-factor boundaries | 53–54 / 54 | 53 / 54 |
| robust | Combined-axis stress | 0–0 / 90 | 0 / 90 |

Source: [validation_summary.csv](results/validation_summary.csv). These are repeated checks on fixed test suites, not independent hardware success probabilities. Combined-axis failures remain visible.

### Training-selected representatives

| Regime | Selection | Seed | Fitness | Joint-boundary passes / 1,536 |
| --- | --- | --- | --- | --- |
| nominal | best | 105 | 0.051122045 | 1152 |
| nominal | median | 122 | 0.052775571 | 832 |
| robust | best | 110 | 0.065002597 | 1344 |
| robust | median | 104 | 0.066826823 | 1408 |

The median representative is an actual run nearest the method median (seed breaks ties), not the median of gain coordinates. Exact gains and coefficients: [selected_candidates.csv](results/selected_candidates.csv) and [exports/](results/exports/). Boundary audits concern these selected representatives, not all seeds.

## Run and inspect

From this folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m unittest test_methods test_budget test_study test_robust
.\.venv\Scripts\python.exe run_method.py --processes 4 --search-only
```

The last command reuses and audits the supplied 60 completed main runs. Omit `--search-only` to execute held-out validation and regenerate method figures; this can be expensive. The runner reads [METHOD.json](METHOD.json), [results/contract.json](results/contract.json), and [results/selected_parameters.json](results/selected_parameters.json).

For an entirely new six-method experiment, use `run_extension.py --processes 6` in a separate clean copy; it runs development selection and main searches for all six methods. Central analysis scripts expect all six methods together, whereas this delivered folder contains only its own method runs. Do not confuse the central 360-run audit metadata with the 60 runs packaged in this folder.

## Result files

| Path | Meaning |
| --- | --- |
| [fitness_summary.csv](results/fitness_summary.csv) | Fitness distribution and confidence intervals |
| [parameter_selection.csv](results/parameter_selection.csv) | Development-grid selection |
| [nominal/runs/](results/nominal/runs/) | 30 nominal run records and evaluation ledgers |
| [robust/runs/](results/robust/runs/) | 30 robust run records and evaluation ledgers |
| [validation/](results/validation/) | Compressed scenario-level validation data |
| [plot_data/](results/plot_data/) | Numerical inputs behind the figures |
| [statistics.json](results/statistics.json) | Statistical design and comparison caveats |
| [reference_benchmark/](reference_benchmark/) | Frozen five-method comparison inputs |

## Figures

![Adaptive Large Neighborhood Search: 01_responses](results/plots/ALNS/01_responses.png)

![Adaptive Large Neighborhood Search: 02_convergence](results/plots/ALNS/02_convergence.png)

![Adaptive Large Neighborhood Search: 05_validation](results/plots/ALNS/05_validation.png)

### Complete figure index

- [01 fitness distributions](results/plots/01_fitness_distributions.png)
- [02 convergence](results/plots/02_convergence.png)
- [03 validation passes](results/plots/03_validation_passes.png)
- [04 speed robustness](results/plots/04_speed_robustness.png)
- [05 parameter study](results/plots/05_parameter_study.png)
- [06 joint boundaries](results/plots/06_joint_boundaries.png)
- [07 eleven methods](results/plots/07_eleven_methods.png)
- [01 responses](results/plots/ALNS/01_responses.png)
- [02 convergence](results/plots/ALNS/02_convergence.png)
- [03 uncertain responses](results/plots/ALNS/03_uncertain_responses.png)
- [04 actuation](results/plots/ALNS/04_actuation.png)
- [05 validation](results/plots/ALNS/05_validation.png)
- [06 sensitivity](results/plots/ALNS/06_sensitivity.png)
- [07 full responses](results/plots/ALNS/07_full_responses.png)
- [controller](results/plots/equations/controller.png)
- [fitness](results/plots/equations/fitness.png)
- [plant](results/plots/equations/plant.png)

## Limits and provenance

The files are saved simulation outputs from the supplied project, not new flight tests. Packaging checks and unit tests do not independently rerun the full optimization campaigns. The six newer methods received a development grid that the original five did not; an eleven-method comparison is exploratory even with equal final budgets. Controller timing is assumed at 1 ms and mixer timing at 4 ms. Negative motor speeds are rejected under the preserved source motor equation. Position/altitude control and hardware robustness are outside this study.

See [shared methodology](../docs/METHODOLOGY.md) and [data provenance](../docs/DATA.md). Please cite Mohammad ALbaraj using [CITATION.cff](../CITATION.cff). No reuse license has yet been selected.
