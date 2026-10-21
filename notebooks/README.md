# Jupyter notebook collection

**Mohammad ALbaraj**

Start with [00_Start_Here.ipynb](00_Start_Here.ipynb). Download or clone the **whole repository**; notebooks read the included source and result files using relative paths. Each notebook can be run independently from top to bottom.

## Contents

- [Complete project walkthrough](00_Start_Here.ipynb)
- [System model, controller, and a fresh simulation](01_System_Model_and_Controller.ipynb)
- [Gain coordinates, objective, and feasibility](02_Gains_Objective_and_Constraints.ipynb)
- [Genetic Algorithm (GA) for quadrotor controller tuning](03_GA.ipynb)
- [Particle Swarm Optimization (PSO) for quadrotor controller tuning](04_PSO.ipynb)
- [Cat Swarm Optimization (CSO) for quadrotor controller tuning](05_CSO.ipynb)
- [Dolphin Swarm Algorithm (DSA) for quadrotor controller tuning](06_DSA.ipynb)
- [Covariance Matrix Adaptation Evolution Strategy (CMA-ES) for quadrotor controller tuning](07_CMA_ES.ipynb)
- [Great Deluge Algorithm (GDA) for quadrotor controller tuning](08_GDA.ipynb)
- [Threshold Accepting (TA) for quadrotor controller tuning](09_TA.ipynb)
- [Adaptive Large Neighborhood Search (ALNS) for quadrotor controller tuning](10_ALNS.ipynb)
- [Variable Neighborhood Descent (VND) for quadrotor controller tuning](11_VND.ipynb)
- [Shrinking Ball Random Search (SBRS) for quadrotor controller tuning](12_SBRS.ipynb)
- [Pure Random Walk (PRW) for quadrotor controller tuning](13_PRW.ipynb)
- [Five-method nominal benchmark](14_Nominal_Benchmark.ipynb)
- [Five-method robust benchmark](15_Robust_Benchmark.ipynb)
- [Exploratory comparison of all eleven methods](16_Eleven_Method_Comparison.ipynb)
- [Uncertainty, held-out validation, and failure cases](17_Robustness_and_Validation.ipynb)
- [Complete figure gallery](18_All_Figures_Gallery.ipynb)
- [All source code and data explorer](19_All_Source_and_Data_Explorer.ipynb)
- [Reproducibility and archive consistency checks](20_Reproducibility_and_Archive_Checks.ipynb)

## Install and launch

From the repository root in PowerShell:

```powershell
python -m venv .venv-notebooks
.\.venv-notebooks\Scripts\python.exe -m pip install -r notebooks/requirements-notebooks.txt
.\.venv-notebooks\Scripts\python.exe -m jupyterlab notebooks/00_Start_Here.ipynb
```

Choose the Python kernel from that environment. Saved cell outputs provide a
readable preview on GitHub; Jupyter is needed to edit parameters and rerun cells.
Use **Restart Kernel and Run All Cells** for a clean execution.

The notebooks use Python 3.13 and the scientific versions recorded in the project.
The dependency file pins the core simulation stack to the archived versions.
Installation availability can depend on Python version and platform.

## Execution behavior

- Overview, methods, benchmarks, validation, figures, and data explorers primarily read saved data.
- The system notebook runs two fresh single-scenario simulations. First-time Numba compilation can take several seconds.
- Each algorithm notebook shows executable small-search code behind `RUN_SMALL_SEARCH=False`. It is not the full published experiment.
- The archive-check notebook checks 22 raw ledgers by default; `CHECK_ALL_RUNS=True` checks all 660 main runs.
- The figure gallery previews every PNG in contact sheets and links all PNG/SVG originals.
- New example outputs go to ignored `notebook_outputs/`. Archived results are not rewritten.
- Identically named scientific modules are run in separate Python processes so imports cannot leak between study folders.

The collection is a notebook interface to the existing scientific code, not a
second implementation. Papers, manuscripts, PDF/HTML reports, environments,
checkpoints, and notebook-generated data remain excluded from publication.
Please cite the project using [CITATION.cff](../CITATION.cff).

## Verification

On 21 October 2026, all 21 notebooks were executed from fresh Python kernels
with no cell errors. All eleven opt-in small-search examples were also run
successfully. The system example ran fresh baseline and saved-CSO simulations;
the archive notebook verified 46 source hashes and 22 main-run ledgers.
These checks do not rerun the full optimization campaigns or establish hardware
performance. Saved figures and new simulation plots were inspected for readable
labels. The gallery includes 166 PNG previews and links to the SVG originals.

Verified notebook tools: JupyterLab 4.6.4, ipykernel 7.4.0, nbformat 5.11.1,
and nbclient 0.11.0, with the scientific dependencies in
`requirements-notebooks.txt`.
