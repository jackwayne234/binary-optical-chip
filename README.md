# Binary Optical Chip

[![License: Code - MIT](https://img.shields.io/badge/License-Code%20MIT-blue.svg)](LICENSE)
[![License: Docs - CC BY 4.0](https://img.shields.io/badge/License-Docs%20CC%20BY%204.0-lightgrey.svg)](LICENSES/CC-BY-4.0.txt)
[![License: Hardware - CERN OHL](https://img.shields.io/badge/License-Hardware%20CERN%20OHL-orange.svg)](LICENSES/CERN-OHL.txt)

> **2-Wavelength photonic AND array on lithium niobate — binary baseline for wavelength-division optical computing**
>
> Companion project to [N-Radix (ternary)](https://github.com/jackwayne234/optical-computing-workspace). Same glass. Same SFG physics. Two wavelengths instead of three.

---

## What Is This?

**Binary Optical Chip** is a photonic AND array accelerator implemented on a monolithic lithium niobate (LiNbO₃) chip. It uses **sum-frequency generation (SFG)** to compute binary AND operations in hardware — no transistors, no clock in the optical path, no software in the compute path.

This project serves two purposes:

1. **Near-term fabrication target** — binary needs only ONE SFG phase-matching condition, making it compatible with standard commercial PPLN. No custom nonlinear material required.
2. **Proof of concept** — a working binary chip demonstrates the optical computing platform before tackling the more complex ternary multi-triplet SFG.

### How It Works

Each Processing Element (PE) mixes two optical signals via SFG. Binary logic is encoded by wavelength selection:

| Bit Value | Wavelength | Band |
|-----------|------------|------|
| **0** | 1310 nm | O-band |
| **1** | 1550 nm | Telecom C-band |

SFG acts as a **hardware AND gate**:

| Input A | Input B | SFG Output | Logic |
|---------|---------|------------|-------|
| 1550 nm | 1550 nm | **775 nm** | **1 AND 1 = 1** |
| 1310 nm | 1550 nm | 711 nm | 0 AND 1 = 0 |
| 1550 nm | 1310 nm | 711 nm | 1 AND 0 = 0 |
| 1310 nm | 1310 nm | 655 nm | 0 AND 0 = 0 |

Only the 775 nm SFG product (from 1550+1550) is detected as bit 1. All other SFG products are rejected by the WDM demux.

### Why Binary Before Ternary?

The ternary N-Radix chip mixes **six wavelength triplets**, requiring a chirped or aperiodic PPLN grating with multiple simultaneous phase-matching conditions. This is an advanced nonlinear photonics fabrication challenge.

The binary chip requires **exactly one QPM condition** (1550 nm SHG → 775 nm, Λ ≈ 19.1 μm). This is a standard commercial PPLN product available from Covesion, HC Photonics, and others.

Binary first → validate the optical computing platform → then ternary.

### Array Architecture

The 9×9 systolic array computes binary inner products:

```
y[j] = OR_i ( input[i] AND weight[i][j] )
```

- **Rows** carry activation signals (horizontal waveguides)
- **Columns** carry weight signals (vertical waveguides)
- **Each PE** produces a 775 nm photon if and only if both activation AND weight are 1
- **Column output** is the logical OR of all PE products — any 775 nm detected → output = 1

The chip is entirely passive in the accelerator region. No clock, no transistors, no software in the optical path.

---

## Fabrication Advantage

| Criterion | Binary (This Chip) | Ternary N-Radix |
|-----------|-------------------|-----------------|
| SFG phase-match conditions | **1** (1550→775 nm SHG) | 6+ (6-triplet mixer) |
| PPLN type | **Standard commercial** (Λ ≈ 19.1 μm) | Custom chirped/aperiodic |
| Wavelengths | **2** (1310 nm, 1550 nm) | 3 (1064, 1310, 1550 nm) |
| Laser sources | **2** | 3 |
| Ring resonators | **Not required** | Required |
| IOC complexity | **2-state MZI** | 3-state MZI |
| Foundry risk | **Low** — proven PPLN process | Higher — multi-QPM nonlinear |

---

## Simulation Status

The 9×9 binary optical chip circuit simulation is complete.

| Test | Description | Result |
|------|-------------|--------|
| 1 | Single PE — all 4 binary AND combinations | **PASS** |
| 2 | Identity matrix (9×9) | **PASS** |
| 3 | All-ones stress test | **PASS** |
| 4 | All-zeros baseline | **PASS** |
| 5 | Single nonzero (PE isolation check) | **PASS** |
| 6 | Mixed 3×3 binary pattern | **PASS** |
| 7 | IOC domain modes (AND / OR / XOR equivalence) | **PASS** |
| 8 | Loss budget (worst-case power margin) | **PASS — 18.9 dB** |
| 9 | Binary vs ternary radix economy analysis | **PASS** |

**9/9 tests PASS.** Power margin: 18.9 dB at worst-case PE[0,8].

---

## Performance

| Array Size | PEs | Throughput | Power | Status |
|------------|-----|-----------|-------|--------|
| **9×9 MVP** | 81 | ~50 GOPS | <1W | **Simulation complete** |
| 81×81 | 6,561 | ~4 TOPS | ~4W | Architecture designed |
| 243×243 | 59,049 | ~36 TOPS | ~16W | Architecture designed |

*Binary operations carry 1 bit/symbol vs ternary's 1.585 bits/symbol. Binary chip provides the practical near-term fabrication path.*

---

## Repository Structure

```
binary-optical-chip/
├── Binary_Accelerator/          # <-- MAIN PROJECT
│   ├── architecture/            # Monolithic chip GDS generators
│   │   └── monolithic_chip_binary_9x9.py
│   ├── circuit_sim/             # Circuit simulation
│   │   └── simulate_binary_9x9.py   # Full-chip sim (9/9 tests PASS)
│   ├── simulations/             # Monte Carlo, thermal, yield analysis
│   │   ├── monte_carlo_binary_9x9.py
│   │   └── thermal_sweep_binary_9x9.py
│   └── docs/                    # Full tape-out documentation
│       ├── TAPEOUT_READINESS.md
│       ├── CIRCUIT_SIMULATION_PLAN.md
│       ├── MONTE_CARLO_ANALYSIS.md
│       ├── THERMAL_SENSITIVITY.md
│       ├── FOUNDRY_SUBMISSION_PACKAGE.md
│       ├── FUNCTIONAL_TEST_PLAN.md
│       ├── TEST_BENCH_DESIGN.md
│       ├── DRC_RULES.md
│       ├── LAYER_MAPPING.md
│       ├── CHIP_INTERFACE.md
│       ├── PACKAGING_SPEC.md
│       ├── MPW_RETICLE_PLAN.md
│       └── DRIVER_SPEC.md
│
├── NRadix_Accelerator/          # Ternary companion (reference)
└── CPU_Phases/                  # Legacy optical CPU prototypes
```

---

## Quick Start

```bash
# Run the circuit simulation (9/9 tests)
cd Binary_Accelerator/circuit_sim/
python simulate_binary_9x9.py

# Run Monte Carlo yield analysis
cd Binary_Accelerator/simulations/
python monte_carlo_binary_9x9.py

# Run thermal sensitivity sweep
python thermal_sweep_binary_9x9.py
```

Dependencies: `numpy`, `matplotlib` (standard scientific Python).

```bash
python3 -m venv .venv && .venv/bin/pip install numpy matplotlib
```

---

## Architecture

The chip is **monolithic** — one X-cut LiNbO₃ (TFLN) substrate with two regions:

1. **IOC Region** (active): 2-state MZI modulators for input encoding, WDM demux for output decoding
2. **Accelerator Region** (passive): 9×9 systolic array of SFG AND gates

Photon arrival at each PE is synchronized by **matched waveguide path lengths** (validated: 0.000 ps spread). No clock distribution needed in the passive region — timing is geometry.

### PPLN Specification

Single phase-matching condition only:

| Parameter | Value |
|-----------|-------|
| Process | SHG (second harmonic generation) |
| Pump wavelength | 1550 nm (C-band) |
| Output wavelength | 775 nm (near-IR) |
| QPM period (Λ) | ~19.1 μm |
| PPLN type | Periodic poling, uniform grating |
| Temperature sensitivity | ~0.05 nm/°C (well within 15-45°C window) |

This is a **standard commercial PPLN configuration**, available from Covesion (MSHG1550-0.5), HC Photonics, and Stratophase. No custom aperiodic grating required.

---

## Binary vs Ternary: The Trade-Off

| Metric | Binary | Ternary (N-Radix) |
|--------|--------|-------------------|
| Information density | 1.000 bit/symbol | **1.585 bits/trit** (+58.5%) |
| PPLN complexity | **1 QPM condition** | 6 QPM conditions |
| Fab risk | **Low** | Higher |
| Time to first chip | **Shorter** | Longer |
| Long-term efficiency | Baseline | **+58.5% vs binary** |

**Conclusion:** Binary gets silicon on the table first. Ternary is the long-term target.

The wavelength cost of adding a third state (one more laser source) is O(1). The transistor cost of ternary electronics is O(N). Optical ternary wins at scale — but binary proves the concept.

---

## Key Documentation

| Doc | Description |
|-----|-------------|
| [Tape-Out Readiness](Binary_Accelerator/docs/TAPEOUT_READINESS.md) | Master checklist — simulation complete |
| [Circuit Simulation](Binary_Accelerator/docs/CIRCUIT_SIMULATION_PLAN.md) | 9/9 tests PASS |
| [Monte Carlo Analysis](Binary_Accelerator/docs/MONTE_CARLO_ANALYSIS.md) | Process variation yield |
| [Thermal Sensitivity](Binary_Accelerator/docs/THERMAL_SENSITIVITY.md) | Operating temperature window |
| [Foundry Submission](Binary_Accelerator/docs/FOUNDRY_SUBMISSION_PACKAGE.md) | Pre-written emails, timeline, budget |
| [Functional Test Plan](Binary_Accelerator/docs/FUNCTIONAL_TEST_PLAN.md) | Post-fab test procedures |
| [Test Bench Design](Binary_Accelerator/docs/TEST_BENCH_DESIGN.md) | Equipment BOM, 4 budget tiers |
| [DRC Rules](Binary_Accelerator/docs/DRC_RULES.md) | Design rules for fabrication |
| [Layer Mapping](Binary_Accelerator/docs/LAYER_MAPPING.md) | GDS layers per foundry |
| [Chip Interface](Binary_Accelerator/docs/CHIP_INTERFACE.md) | How to connect to the chip |
| [Packaging](Binary_Accelerator/docs/PACKAGING_SPEC.md) | Fiber coupling, wire bonding |
| [MPW Plan](Binary_Accelerator/docs/MPW_RETICLE_PLAN.md) | Multi-project wafer strategy |
| [Driver Spec](Binary_Accelerator/docs/DRIVER_SPEC.md) | Binary IOC driver details |

---

## Contributing

This is an open research project. Contributions welcome:

- **Hardware**: Optical alignment, component testing
- **Software**: Driver development, simulation optimization
- **Theory**: Architecture analysis, encoding schemes
- **Documentation**: Technical writing, diagrams

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
**GitHub:** jackwayne234
**Location:** Chesapeake, VA, USA
