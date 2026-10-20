# Data, provenance, and reproduction checks

[Project overview](../README.md)

## What is included

The numerical outputs and figures were copied from the supplied research archive.
They are saved experiments, not newly generated optimization results. The
[results_manifest.csv](results_manifest.csv) lists every copied data/figure file,
its size, and its SHA-256 digest. Scientific source files were preserved.

Included formats are CSV tables, JSON configuration/run/validation records,
NPZ arrays, JSON.GZ compressed validation records, PNG/SVG figures, and controller
parameter maps in TXT. Frozen `*_reference/` and `reference_benchmark/` snapshots
are numerical comparison inputs. No paper library, manuscript, PDF/HTML report,
ZIP package, or workbook is part of this publication.

## Reading the data

| Data | Interpretation |
| --- | --- |
| `run_main_*.json` | Original three-seed method runs; include seed, gains, fitness and history |
| `runs/METHOD_SEED.json` | Later fixed-budget run, paired by seed |
| `*_evaluations.npz` | Array `ledger`: evaluation index, iteration, fitness, best-so-far, then eight normalized gain coordinates |
| Extension NPZ `transitions` | Evaluation count, old fitness, trial fitness, resulting current fitness, acceptance flag, threshold/radius, destroy/repair indices, restart flag |
| `metrics.csv` | Commanded-channel response metrics, units in column names |
| `validation_summary.csv` | Per-controller pass counts and response summaries by suite |
| `fitness_summary.csv` / `summary.csv` | Across-seed descriptive statistics and confidence intervals |
| `selected_candidates.csv`, `exports/` | Training-selected best/median representatives and discrete controller coefficients |
| `plot_data/`, `traces/` | Figure inputs and trajectories; consult column names and companion JSON metadata |
| `contract.json` | Frozen cases, configuration, budgets, seeds and source hashes |

NPZ files can be loaded with `numpy.load(path, allow_pickle=False)`; JSON.GZ files
can be read with `gzip.open(path, 'rt')` and `json.load`. No pickle loading is
needed. Keep original units: roll/pitch targets are degrees, yaw targets degrees/s;
internal dynamics often use radians. Fitness is dimensionless, not a time.

The extension's shared metadata may describe the central six-method experiment
(360 main and 144 development runs), while each method folder contains 60 main
and 24 development runs. Summary files named `all_eleven_*` in a delivered folder
may be filtered to that folder's method; their filename alone does not establish
coverage. The main README combines the appropriate per-method summaries.

## Current saved-data checks

Checked **804 fixed-budget run ledgers** and **46 frozen source hashes**. No source-hash mismatches were found.

Checks covered exact 3,264-evaluation budgets, uniqueness of rounded coordinates,
finite values and gain bounds, monotone best archives, exported fitness/gain
agreement with the best ledger point, and agreement between run records and
summary minima, medians, means, sample deviations, maxima, and feasible counts.
See [data_checks.json](data_checks.json) for counts by folder. This is a consistency
audit, not a recomputation of every objective value or validation trajectory.
Historical `verification.json` files describe prior checks and may mention
reports which are intentionally not distributed.

## Current unit-test checks

Existing environment: Python 3.13.6, NumPy 2.5.3, SciPy 1.18.1, Numba 0.68.0,
pycma 4.5.0 on Windows. The following outcomes are from the packaging review:

| Study | Tests attempted | Outcome |
| --- | --- | --- |
| all work/30 seed equal budget study | 17 | Passed |
| all work/pid using cat swarm | 17 | Blocked by Windows temporary-file permissions |
| all work/pid using cma es | 17 | Blocked by Windows temporary-file permissions |
| all work/pid using dolphin swarm | 18 | Blocked by Windows temporary-file permissions |
| all work/pid using ga | 15 | Passed |
| all work/pid using pso | 16 | Blocked by Windows temporary-file permissions |
| all work/robustness 30 seed study | 19 | Passed |
| pid using alns | 23 | Passed |
| pid using great deluge | 23 | Passed |
| pid using pure random walk | 23 | Passed |
| pid using shrinking ball random search | 23 | Passed |
| pid using threshold accepting | 23 | Passed |
| pid using vnd | 23 | Passed |

The four blocked suites encountered PermissionError when their temporary
directories were accessed; those outcomes are not counted as passes. The other
nine suites passed. A fresh dependency installation, complete optimization rerun,
and hardware validation were not performed.

## Reproducing without mixing experiments

Use the appropriate study's requirements and test commands. Preserve existing
results when changing configuration or code; use a fresh working copy/output
directory. Frozen-source checks are meaningful only when the exact original
source bytes and experiment contract are preserved. Some local report/delivery
helpers still contain Windows paths and font requirements.

Method-specific extension runners can reuse their 60 supplied main runs.
Central six-method scripts require all six datasets together and are not
equivalent to the per-method runner. Shared validation and initialization explain
pairing across methods; they do not make every search path identical.

Finite simulations, particularly with failed combined-axis stress tests, do not
certify safe deployment. Keep infeasible runs in statistical summaries rather
than dropping them to improve a mean or ranking.
