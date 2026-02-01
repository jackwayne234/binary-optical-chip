# Optical Computing / Meep FDTD - Agent Guidelines

This document outlines the development workflows, code standards, and project structure for the Optical Computing repository. All AI agents and developers must adhere to these guidelines.

## 1. Project Structure & Standard Locations

The project follows a strict directory structure to separate code, data, and documentation.

- **`/scripts`**: Primary location for `.py` (PyMeep) and `.ctl` (libctl) files.
    - *Convention*: Naming should be descriptive, e.g., `simulate_waveguide.py`.
- **`/data`**: Store all `.h5` simulation outputs here.
    - *Rule*: **Never attempt to read raw `.h5` files directly; use metadata tools only.**
    - *Rule*: This directory is `.gitignore`'d. Do not commit large data files.
- **`/docs`**: Store research notes, physical parameters, and Markdown logs.
- **`/analysis`**: Use this for Python notebooks and matplotlib scripts for post-processing.
- **`/logs`**: Runtime logs, standard output captures, and error reports.
    - *Rule*: This directory is `.gitignore`'d.

## 2. Environment & Build

This project uses Python (3.12+). Dependencies are managed via `requirements.txt` (or Conda).

### Dependencies
- **Core**: `numpy`, `scipy`, `matplotlib`, `h5py`
- **Simulation**: `meep` (assumed installed via Conda/System)

### Installation
```bash
# Recommended: Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Testing & Verification

We use **pytest** for testing logic and simulation setups.

### Running Tests
- **Run all tests**:
  ```bash
  pytest
  ```
- **Run a single test file**:
  ```bash
  pytest scripts/test_simulation.py
  ```
- **Run a single test function** (Critical for debugging):
  ```bash
  pytest scripts/test_simulation.py::test_energy_conservation -v
  ```
- **Run with stdout visible** (useful for debugging simulations):
  ```bash
  pytest -s
  ```

### Linting & Formatting
We use `ruff` (or `flake8` + `black`) for enforcing code style.

- **Check code quality**:
  ```bash
  ruff check .
  ```
- **Format code**:
  ```bash
  ruff format .
  ```

## 4. Code Style Guidelines

### Imports
- **Order**: Standard library -> Third-party (numpy, meep) -> Local imports.
- **Convention**:
  ```python
  import sys
  import os
  
  import numpy as np
  import meep as mp
  import matplotlib.pyplot as plt
  
  from scripts import utils
  ```

### Formatting
- Follow **PEP 8**.
- **Line Length**: 88 characters (Black default) or 100 is acceptable for complex scientific formulas.
- **Indentation**: 4 spaces.

### Naming Conventions
- **Variables/Functions**: `snake_case` (e.g., `calculate_flux`, `wavelength_um`).
- **Classes**: `PascalCase` (e.g., `WaveguideSimulation`).
- **Constants**: `UPPER_CASE` (e.g., `SPEED_OF_LIGHT`, `RESOLUTION`).
- **Physics Units**: explicit in variable names where ambiguous (e.g., `width_um`, `freq_hz`).

### Type Hinting
- Use Python type hints for function arguments and return values.
  ```python
  def calculate_transmission(flux: np.ndarray, incident: float) -> float:
      ...
  ```

### Error Handling
- Use specific exceptions (e.g., `ValueError` for invalid physics parameters).
- Log errors to `logs/` files or stderr, do not silently fail.
- Ensure simulation resources (contexts) are cleaned up in `finally` blocks if not using context managers.

## 5. Simulation Best Practices (Meep)
- **Resolution**: Define `resolution` as a global variable or parameter.
- **Units**: Always comment the units being used (Meep defaults to dimensionless units where $c=1$, $a=1$).
- **Symmetry**: Explicitly state if symmetry is being used to speed up calculations.
- **Output**: Always save heavy data to `/data` using `h5py` or Meep's built-in HDF5 output functions. Avoid printing massive arrays to stdout.

