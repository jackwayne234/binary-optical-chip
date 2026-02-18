# N-Radix: Wavelength-Division Ternary Optical Accelerator

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18437600.svg)](https://doi.org/10.5281/zenodo.18437600)
[![License: Code - MIT](https://img.shields.io/badge/License-Code%20MIT-blue.svg)](LICENSE)
[![License: Docs - CC BY 4.0](https://img.shields.io/badge/License-Docs%20CC%20BY%204.0-lightgrey.svg)](LICENSES/CC-BY-4.0.txt)
[![License: Hardware - CERN OHL](https://img.shields.io/badge/License-Hardware%20CERN%20OHL-orange.svg)](LICENSES/CERN-OHL.txt)

> **An optical AI accelerator using wavelength-division ternary logic**
>
> Monolithic photonic chip — passive optical compute at a fraction of the power of electronic GPUs.

---

## What Is This?

**N-Radix** is an optical AI accelerator optimized for parallel matrix operations — the same workloads that dominate AI training and inference. Instead of electrons through transistors, we use photons through waveguides on a monolithic lithium niobate (LiNbO3) chip.

### How It Works

Each Processing Element (PE) uses **sum-frequency generation (SFG)** to mix two optical signals. The chip is entirely passive — no clock, no transistors, no software in the compute path. Light goes in one side, computed results come out the other.

| Trit Value | Wavelength | Band |
|------------|------------|------|
| **-1** | 1550 nm | Telecom C-band |
| **0** | 1310 nm | O-band |
| **+1** | 1064 nm | Near-IR |

All PEs physically just add (via SFG). The external controller (IOC) determines whether each PE performs:
- **ADD/SUB** — straight ternary addition/subtraction
- **MUL/DIV** — log-domain addition, which the IOC interprets as multiplication

The glass never changes. Only the encoding does.

### Performance

| Array Size | PEs | Throughput (617 MHz) | Power | Status |
|------------|-----|---------------------|-------|--------|
| **9x9 MVP** | 81 | ~100 GOPS | <1W | **Fab-ready** (circuit sim 8/8 PASS) |
| 81x81 | 6,561 | ~8.1 TFLOPS | ~5W | FDTD validated |
| 243x243 | 59,049 | ~72.9 TFLOPS | ~20W | Architecture designed |

**Power efficiency comparison (243x243 projected):**

| Chip | Throughput | Power | Efficiency |
|------|-----------|-------|------------|
| N-Radix 243x243 | ~73 TFLOPS | ~20W | **3.6 TFLOPS/W** |
| NVIDIA H100 | ~990 TFLOPS (FP16) | 700W | 1.4 TFLOPS/W |
| NVIDIA B200 | ~2,250 TFLOPS (FP16) | 1,000W | 2.3 TFLOPS/W |

*N-Radix operations are single-trit balanced ternary, not FP16. Direct FLOPS comparison is apples-to-oranges — the advantage is power efficiency and architectural simplicity, not raw throughput vs mature GPUs.*

With 6-triplet WDM (Phase 2): ~438 TFLOPS at the same power — **~22 TFLOPS/W**.

---

## Tape-Out Status

The **9x9 monolithic chip** (1095 x 695 um, X-cut LiNbO3) is ready for foundry submission.

| Milestone | Status |
|-----------|--------|
| Circuit-level simulation (SAX) | **8/8 tests PASS** |
| Monte Carlo process variation (10,000 trials) | **99.82% yield** |
| Thermal sensitivity analysis | **30C passive window (15-45C)** |
| End-to-end functional test plan | **Complete** — 3 test levels, failure diagnosis |
| Post-fab test bench design | **Complete** — 4 budget tiers ($1.8k-$16.5k) |
| Foundry submission package | **Complete** — emails, timeline, risk register |

### Circuit Simulation Results (8/8 PASS)

| Test | Description | Result |
|------|-------------|--------|
| 1 | Single PE multiplication table (all 9 trit combinations) | PASS |
| 2 | Identity matrix (9x9) | PASS |
| 3 | All-ones stress test | PASS |
| 4 | Single nonzero (isolation/crosstalk check) | PASS |
| 5 | Mixed 3x3 values | PASS |
| 6 | Tridiagonal Laplacian pattern | PASS |
| 7 | IOC domain modes (ADD vs MUL equivalence) | PASS |
| 8 | Loss budget (worst-case power margin: 17.6 dB) | PASS |

### FDTD Validation (All Sizes)

| Array | Status |
|-------|--------|
| 3x3 | PASSED |
| 9x9 | PASSED |
| 27x27 (2.4% clock skew) | PASSED |
| 81x81 (6,561 PEs) | **PASSED** |

---

## Repository Structure

```
Optical_computing/
├── NRadix_Accelerator/          # <-- MAIN PROJECT
│   ├── architecture/            # Monolithic chip generators (9x9, 243x243)
│   ├── circuit_sim/             # SAX circuit simulation + interactive demo
│   │   ├── simulate_9x9.py     # Full-chip simulation (8/8 tests)
│   │   ├── simulate_6triplet.py # WDM cross-coupling analysis
│   │   └── demo.py             # Tkinter visual demo
│   ├── driver/                  # NR-IOC driver (C + Python bindings)
│   ├── components/              # Photonic component models
│   ├── simulations/             # Monte Carlo, thermal, FDTD tests
│   ├── docs/                    # Full tape-out documentation package
│   └── papers/                  # Reference papers
│
├── CPU_Phases/                  # Legacy: General-purpose CPU prototypes
├── Research/                    # Shared research, FDTD simulations
└── tools/                       # Research search tool, utilities
```

---

## The Core Insight

Ternary (base-3) logic is mathematically optimal for computing — closest integer to Euler's number *e* (~2.718), which minimizes the radix economy cost function. But electronic ternary requires ~40x more transistors per trit (the Setun problem, known since 1958).

**We bypass this entirely:** use light wavelengths instead of voltage levels. Three wavelengths are as naturally distinct as two — the material science penalty disappears.

This unlocks:
1. **Ternary's 1.58x information density** — each trit carries log₂(3) bits
2. **Photonic parallelism** — wavelength-division multiplexing for 6x parallel channels
3. **Log-domain multiplication** — multiply by adding exponents (hardware just adds)
4. **Passive compute** — no clock, no transistors, no power in the optical path

---

## Key Documentation

| Doc | Description |
|-----|-------------|
| [Tape-Out Readiness](NRadix_Accelerator/docs/TAPEOUT_READINESS.md) | Master checklist — all 5 gaps resolved |
| [Circuit Simulation](NRadix_Accelerator/docs/CIRCUIT_SIMULATION_PLAN.md) | SAX simulation plan & results (8/8 PASS) |
| [Monte Carlo Analysis](NRadix_Accelerator/docs/MONTE_CARLO_ANALYSIS.md) | 10,000 trials, 99.82% yield |
| [Thermal Sensitivity](NRadix_Accelerator/docs/THERMAL_SENSITIVITY.md) | 15-45C passive operating window |
| [Chip Interface](NRadix_Accelerator/docs/CHIP_INTERFACE.md) | How to connect to the chip |
| [Foundry Submission](NRadix_Accelerator/docs/FOUNDRY_SUBMISSION_PACKAGE.md) | Pre-written emails, timeline, budget |
| [Functional Test Plan](NRadix_Accelerator/docs/FUNCTIONAL_TEST_PLAN.md) | Post-fab test procedures |
| [Test Bench Design](NRadix_Accelerator/docs/TEST_BENCH_DESIGN.md) | Equipment BOM, 4 budget tiers |
| [Driver Spec](NRadix_Accelerator/docs/DRIVER_SPEC.md) | NR-IOC driver details |
| [DRC Rules](NRadix_Accelerator/docs/DRC_RULES.md) | Design rules for fabrication |
| [Packaging](NRadix_Accelerator/docs/PACKAGING_SPEC.md) | Fiber coupling, wire bonding |
| [Layer Mapping](NRadix_Accelerator/docs/LAYER_MAPPING.md) | GDS layers per foundry |
| [MPW Plan](NRadix_Accelerator/docs/MPW_RETICLE_PLAN.md) | Multi-project wafer strategy |

---

## Quick Start

```bash
# Run the circuit simulation (8/8 tests)
cd NRadix_Accelerator/circuit_sim/
python simulate_9x9.py

# Launch the interactive demo (Tkinter GUI)
python demo.py

# Run Monte Carlo yield analysis
cd NRadix_Accelerator/simulations/
python monte_carlo_9x9.py
```

---

## Architecture

The chip is **monolithic** — one substrate with two regions:

1. **IOC Region** (active): Kerr self-pulsing clock (617 MHz), input encoding, output decoding
2. **Accelerator Region** (passive): Systolic array of PEs — waveguides, SFG mixers, ring resonators

Photon arrival at each PE is synchronized by **matched waveguide path lengths** (validated: 0.000 ps spread). No clock distribution needed in the passive region — timing is geometry.

Weights are **streamed from optical RAM**, not stored per-PE. Each PE is just a mixer + routing — simple, high-yield passive optics.

---

## CPU Phases (Legacy)

The [`CPU_Phases/`](CPU_Phases/) directory contains earlier prototyping work for a general-purpose optical CPU. This work is preserved but not the current focus.

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Visible light RGB prototype (24"x24") | Parts ordered |
| Phase 2 | 10GHz fiber benchtop | Planning |
| Phase 3 | Silicon photonics chip | Seeking funding |
| Phase 4 | DIY fab (contingency) | On demand |

---

## Contributing

This is an open research project. Contributions welcome:

- **Hardware**: Optical alignment, component testing
- **Software**: Driver development, simulation optimization
- **Theory**: Architecture analysis, encoding schemes
- **Documentation**: Technical writing, diagrams

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## Citation

### Paper v2 (Architecture)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18501296.svg)](https://doi.org/10.5281/zenodo.18501296)

```bibtex
@misc{riner2026nradix,
  author = {Riner, Christopher},
  title = {Wavelength-Division Ternary Computing II: The N-Radix Optical AI Accelerator},
  year = {2026},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.18501296},
  url = {https://doi.org/10.5281/zenodo.18501296}
}
```

### Paper v1 (Theory)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18437600.svg)](https://doi.org/10.5281/zenodo.18437600)

```bibtex
@misc{riner2026wavelength,
  author = {Riner, Christopher},
  title = {Wavelength-Division Ternary Logic: Bypassing the Radix Economy Penalty in Optical Computing},
  year = {2026},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.18437600},
  url = {https://doi.org/10.5281/zenodo.18437600}
}
```

### Software (Implementation)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18450479.svg)](https://doi.org/10.5281/zenodo.18450479)

```bibtex
@software{riner2026wavelengthsoftware,
  author = {Riner, Christopher},
  title = {Wavelength-Division Ternary Optical Computer},
  year = {2026},
  publisher = {Zenodo},
  version = {v1.0.1},
  doi = {10.5281/zenodo.18450479},
  url = {https://doi.org/10.5281/zenodo.18450479}
}
```

---

## License

| Component | License |
|-----------|---------|
| Software Code | MIT License |
| Documentation | CC BY 4.0 |
| Hardware Designs | CERN OHL |

---

**Author:** Christopher Riner
**Contact:** chrisriner45@gmail.com
**Location:** Chesapeake, VA, USA
