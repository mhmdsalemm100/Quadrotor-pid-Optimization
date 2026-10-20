# Variable Neighborhood Descent (VND) for quadrotor controller tuning

**Author: Mohammad ALbaraj** · [Project overview](../README.md) · [Shared model and objective](../docs/METHODOLOGY.md)

## Purpose

Tune eight bounded roll/pitch and yaw-rate controller parameters offline. The optimizer changes gains; it does not change the plant equations, controller structure, or constraints. Lower constrained fitness is better within the same training regime.

## How this implementation works

This is budgeted multistart VND with first-improvement coordinate neighborhoods.

1. Start from the best of the common initial candidates.
2. Explore positive and negative moves along all eight coordinates at the current radius.
3. Use four radii: r, r/2, r/10, and r/50, in the selected order. Reflect proposals at the bounds.
4. Accept the first strict improvement and restart from the first neighborhood.
5. If all 16 directions fail, advance to the next radius.
6. If all radii fail, restart at a new uniform random point and charge its evaluation to the same budget.

Restarts prevent a local stationary point from ending the run before the fixed budget. The returned solution is the best archive point, not necessarily the current restart point.

Read [methods.py](methods.py) for the implemented update rules, [config.json](config.json) for settings, and [study.py](study.py) for objective evaluation.

## Protocol and selected settings

Each regime has 30 main seeds: 11, 29, 47, and 101–127. Every run receives 3,264 unique objective evaluations, including the same 64 initial points. Duplicate normalized coordinates rounded to 13 decimals are cached and do not spend the budget. The best evaluated point remains valid even when the budget interrupts a final state update.

Four candidate settings were compared on development seeds 5011, 5021, and 5039 under both nominal and robust training (24 development runs per method). The lowest average within-block rank selected one setting for both regimes. Main-seed and held-out validation results were not used for that selection.

| Selected parameter | Value |
| --- | --- |
| radius | 0.05 |
| neighborhood_order | large_to_small |

## Saved 30-seed results

| Regime | Best | Median | Mean | Sample SD | Training-feasible runs |
| --- | --- | --- | --- | --- | --- |
| nominal | 0.051476184 | 0.053073821 | 0.054450461 | 0.0040880055 | 30/30 |
| robust | 0.065131041 | 0.068521437 | 68.095361 | 258.831 | 28/30 |

Source: [fitness_summary.csv](results/fitness_summary.csv). Infeasible runs have penalized scores above 1,000 and remain in means and standard deviations. A low median does not imply every run found a feasible controller.

### Held-out validation

| Training regime | Suite | Pass range across 30 runs | Median passes |
| --- | --- | --- | --- |
| nominal | Random single-axis | 292–299 / 300 | 297 / 300 |
| nominal | One-factor boundaries | 48–53 / 54 | 50 / 54 |
| nominal | Combined-axis stress | 0–0 / 90 | 0 / 90 |
| robust | Random single-axis | 295–300 / 300 | 300 / 300 |
| robust | One-factor boundaries | 39–54 / 54 | 53 / 54 |
| robust | Combined-axis stress | 0–0 / 90 | 0 / 90 |

Source: [validation_summary.csv](results/validation_summary.csv). These are repeated checks on fixed test suites, not independent hardware success probabilities. Combined-axis failures remain visible.

### Training-selected representatives

| Regime | Selection | Seed | Fitness | Joint-boundary passes / 1,536 |
| --- | --- | --- | --- | --- |
| nominal | best | 119 | 0.051476184 | 1024 |
| nominal | median | 110 | 0.053059135 | 1056 |
| robust | best | 111 | 0.065131041 | 1344 |
| robust | median | 106 | 0.068575438 | 1344 |

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

![Variable Neighborhood Descent: 01_responses](results/plots/VND/01_responses.png)

![Variable Neighborhood Descent: 02_convergence](results/plots/VND/02_convergence.png)

![Variable Neighborhood Descent: 05_validation](results/plots/VND/05_validation.png)

### Complete figure index

- [01 fitness distributions](results/plots/01_fitness_distributions.png)
- [02 convergence](results/plots/02_convergence.png)
- [03 validation passes](results/plots/03_validation_passes.png)
- [04 speed robustness](results/plots/04_speed_robustness.png)
- [05 parameter study](results/plots/05_parameter_study.png)
- [06 joint boundaries](results/plots/06_joint_boundaries.png)
- [07 eleven methods](results/plots/07_eleven_methods.png)
- [controller](results/plots/equations/controller.png)
- [fitness](results/plots/equations/fitness.png)
- [plant](results/plots/equations/plant.png)
- [01 responses](results/plots/VND/01_responses.png)
- [02 convergence](results/plots/VND/02_convergence.png)
- [03 uncertain responses](results/plots/VND/03_uncertain_responses.png)
- [04 actuation](results/plots/VND/04_actuation.png)
- [05 validation](results/plots/VND/05_validation.png)
- [06 sensitivity](results/plots/VND/06_sensitivity.png)
- [07 full responses](results/plots/VND/07_full_responses.png)

## Limits and provenance

The files are saved simulation outputs from the supplied project, not new flight tests. Packaging checks and unit tests do not independently rerun the full optimization campaigns. The six newer methods received a development grid that the original five did not; an eleven-method comparison is exploratory even with equal final budgets. Controller timing is assumed at 1 ms and mixer timing at 4 ms. Negative motor speeds are rejected under the preserved source motor equation. Position/altitude control and hardware robustness are outside this study.

See [shared methodology](../docs/METHODOLOGY.md) and [data provenance](../docs/DATA.md). Please cite Mohammad ALbaraj using [CITATION.cff](../CITATION.cff). No reuse license has yet been selected.
