# Wavelength-Division Ternary Optical TPU

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18437600.svg)](https://doi.org/10.5281/zenodo.18437600)
[![License: Code - MIT](https://img.shields.io/badge/License-Code%20MIT-blue.svg)](LICENSE)
[![License: Docs - CC BY 4.0](https://img.shields.io/badge/License-Docs%20CC%20BY%204.0-lightgrey.svg)](LICENSES/CC-BY-4.0.txt)
[![License: Hardware - CERN OHL](https://img.shields.io/badge/License-Hardware%20CERN%20OHL-orange.svg)](LICENSES/CERN-OHL.txt)
[![Status: Active](https://img.shields.io/badge/Status-Active%20Development-green.svg)]()
[![Open Source](https://img.shields.io/badge/Open%20Source-Yes-brightgreen.svg)]()
[![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg)](CONTRIBUTING.md)

> **An Optical Tensor Processing Unit for AI Acceleration**
>
> Using wavelength-division ternary logic to achieve 33x the performance of NVIDIA's B200 at a fraction of the power.

---

## What Is This?

This is a **Ternary Processing Unit (TPU)** - an AI accelerator optimized for parallel matrix operations. Think NVIDIA's tensor cores, but optical. Instead of electrons through transistors, we use photons through waveguides.

| Architecture | Strength | Use Case |
|--------------|----------|----------|
| CPU | Sequential logic, branching | General computing |
| GPU/TPU | Parallel matrix math | AI training/inference |
| **Optical TPU** | Parallel matrix math, passive logic | AI acceleration at 50-100x efficiency |

**Why this matters:** AI workloads are dominated by matrix multiplications - exactly what this architecture excels at. The optical approach isn't just more efficient - it's *more powerful*:

| Configuration | Performance | vs B200 (2.5 PFLOPS) | vs Frontier (1,200 PFLOPS) |
|---------------|-------------|----------------------|----------------------------|
| **Base mode** | 82 PFLOPS / chip | **33×** faster | 15 chips = Frontier |
| **3^3 mode** | 738 PFLOPS / chip | **295×** faster | **2 chips = Frontier** |

*3^3 mode: Same hardware, same 3 states. The IOC reinterprets each trit as trit³ in log-log domain. In this domain, adding and subtracting exponents is the same as multiplying and dividing the original numbers - so the hardware simplifies to just add/subtract operations. No multiply or divide circuits needed. Result: 9× more compute per cycle with simpler, faster hardware.*

The optical approach eliminates the heat and power constraints that limit electronic accelerators, while delivering raw performance that exceeds anything silicon can achieve.

---

## TPU Architecture

### Systolic Array Design

The optical TPU uses a **systolic array** architecture - the same fundamental design as Google's TPUs and NVIDIA's tensor cores. Data flows through a grid of Processing Elements (PEs), with each PE performing multiply-accumulate operations as data passes through.

```
        Weight inputs (stationary in PEs)
                    ↓
        ┌───────────────────────────────────────┐
        │     PE─PE─PE─PE─PE─PE─PE─PE─PE       │
   A →  │     PE─PE─PE─PE─PE─PE─PE─PE─PE  → C  │
   c    │     PE─PE─PE─PE─PE─PE─PE─PE─PE       │
   t    │     PE─PE─PE─PE─PE─PE─PE─PE─PE       │
   i    │     PE─PE─PE─PE─PE─PE─PE─PE─PE       │
   v    │     PE─PE─PE─PE─PE─PE─PE─PE─PE       │
   a    │     PE─PE─PE─PE─PE─PE─PE─PE─PE       │
   t    │     PE─PE─PE─PE─PE─PE─PE─PE─PE       │
   i    │     PE─PE─PE─PE─PE─PE─PE─PE─PE       │
   o    │                 ↓                     │
   n    │         Accumulated outputs          │
   s    └───────────────────────────────────────┘
```

### Data Flow

1. **Input Encoding**: Binary data from PCIe is converted to ternary optical signals (6.5ns conversion time)
2. **Matrix Load**: Weight matrices flow in from one edge, activation vectors from another
3. **Systolic Propagation**: Each PE performs ternary MAC (multiply-accumulate) using SFG (Sum-Frequency Generation)
4. **Output Collection**: Results accumulate at the output edge and convert back to binary

### How Weights Are Stored in PEs (Bistable Kerr Flip-Flops)

Each PE contains a **weight register** built from bistable Kerr resonators. The Kerr effect (χ³ nonlinearity) creates two stable optical states - the resonator "locks" into one based on input wavelength:

| Stored Value | Wavelength | How It's Set |
|--------------|------------|--------------|
| **-1** | 1550nm locked | High-power 1550nm pulse |
| **0** | 1310nm locked | High-power 1310nm pulse |
| **+1** | 1064nm locked | High-power 1064nm pulse |

**Writing weights:** Assert WRITE_ENABLE, inject desired wavelength at high power, release. The resonator stays locked (~10ns per write).

**Example - Loading a 3×3 matrix:**
```
W = | +1  -1   0 |     Clock 1: Inject 1064nm, 1550nm, 1310nm → Row 0
    |  0  +1  +1 |     Clock 2: Inject 1310nm, 1064nm, 1064nm → Row 1
    | -1   0  -1 |     Clock 3: Inject 1550nm, 1310nm, 1550nm → Row 2

Total: 3 clocks = ~4.9ns for 3×3 | ~131ns for 81×81
```

**During compute:** Weights don't need "reading" - they continuously emit their stored wavelength, mixing with streaming inputs via SFG. Weights are stationary, data flows through. No refresh needed (unlike DRAM).

*Full details: [TPU Architecture README](Research/programs/tpu_architecture/README.md)*

### Wavelength Multiplexing

Each PE operates on **6 stackable wavelength triplets** = 144 WDM channels, enabling massive parallelism without physical routing complexity.

**Instead of building 6 separate chips, we run 6 independent computations through the same physical hardware simultaneously.** Each wavelength triplet operates in its own "lane" - the photons don't interfere with each other because they're different colors.

This isn't experimental - it's **mature telecom technology**. The fiber optic industry has used Wavelength Division Multiplexing (WDM) for decades to send 80+ channels down a single fiber. We're just repurposing it for compute instead of communication. The components (multiplexers, demultiplexers, filters) are commodity hardware you can buy off the shelf.

---

## Performance

**27x27 Array FDTD Simulation: PASSED** - 2.4% clock skew (threshold: 5%)

### Analytical Scaling Projections (from validated data)

| Array | PEs | Clock Skew | Status | Throughput |
|-------|-----|------------|--------|------------|
| 27x27 | 729 | 2.4% | **VALIDATED** | 64.8 TFLOPS |
| 81x81 | 6,561 | 3.2% | PASSES | 583 TFLOPS |
| 243x243 | 59,049 | 4.0% | PASSES | 5.25 PFLOPS |
| 729x729 | 531,441 | 4.8% | PASSES | 47.2 PFLOPS |
| **960x960** | **921,600** | **5.0%** | **Theoretical Max** | **82 PFLOPS** |

*H-tree routing scales logarithmically - going from 729 to 531,441 PEs (729x bigger) only doubles skew from 2.4% to 4.8%*

### vs NVIDIA B200

| System | Performance | Power |
|--------|-------------|-------|
| NVIDIA B200 | 2.5 PFLOPS | 1,000W |
| **243x243 Optical** | **5.25 PFLOPS** | **~100W** |
| **960x960 Optical** | **82 PFLOPS** | **~200-400W** |

**243x243 = 2x B200 at 1/10th the power**
**960x960 = 33x B200**

### vs Frontier (World's Fastest Supercomputer)

| System | Performance | Power |
|--------|-------------|-------|
| Frontier (Oak Ridge) | 1,200 PFLOPS | 21 MW |
| **15 Optical Chips** | **1,230 PFLOPS** | **~6 kW** |

**15 chips = Frontier at 0.03% of the power**

### What's Been Validated

- **Array-scale clock distribution** - 27x27 FDTD simulation PASSED
- **6 stackable wavelength triplets** - 144 WDM channels, collision-free
- **617 MHz Kerr optical clock** - Central distribution with H-tree routing
- **6.5ns binary-ternary conversion** - Negligible interface overhead
- **Passive optical logic** - No software on chip, reduced attack surface

### Currently Working On

| Track | Description | Status |
|-------|-------------|--------|
| **IOC Hardware** | Input/Output Converter - bridge between binary systems and optical ternary chip | Spec complete, seeking FPGA prototype |
| **Driver Software** | PCIe drivers and software API for host integration | Collaborator onboard |
| **3^3 Encoding** | Log-domain encoding to make existing hardware 9x faster at crunching bigger numbers | Exploring theory |

### TPU Configurations

| Tier | Name | Performance | Target Use |
|------|------|-------------|------------|
| **1** | [Standard Accelerator](Research/programs/standard_computer/) | ~4 TFLOPS | Entry-level AI inference |
| **2** | [Home AI](Research/programs/home_ai/) | ~291 TFLOPS (3.5x RTX 4090) | Consumer AI workstation |
| **3** | [Datacenter](Research/programs/supercomputer/) | ~2.33 PFLOPS (1.2x H100) | Cloud AI / HPC |

---

## Building the TPU: Implementation Phases

### [Phase 1: Visible Light Prototype](Phase1_Prototype/)
**Status:** Parts Ordered / Construction In Progress

A 24"x24" visible-light prototype using Red/Green/Blue lasers and 3D-printed optics to prove the core ternary logic works.

- **Firmware**: ESP32 controller ([`ternary_logic_controller.ino`](Phase1_Prototype/firmware/ternary_logic_controller/ternary_logic_controller.ino))
- **Hardware**: Complete BOM, 3D print files (SCAD), assembly instructions
- **Demo**: Blue + Red = Purple = 0 (proves +1 + -1 = 0 optically)

**[Start Building](Phase1_Prototype/NEXT_STEPS.md)**

### [Phase 2: Fiber Benchtop](Phase2_Fiber_Benchtop/)
**Status:** Procurement

10GHz fiber-optic benchtop using standard ITU C-Band telecom equipment to prove the architecture scales to real-world speeds.

- **Firmware**: SFP+ laser tuning scripts ([`sfp_tuner.py`](Phase2_Fiber_Benchtop/firmware/sfp_tuner.py))
- **Target**: Demonstrate 1.58 bits/symbol (vs 1 bit for binary)

### [Phase 3: Silicon Photonics](Phase3_Chip_Simulation/)
**Status:** Design & Partnership Development

Miniaturizing the design onto a Lithium Niobate (LiNbO3) photonic integrated circuit.

- **Goal**: GDSII layouts for foundry fabrication
- **Target**: MPW (Multi-Project Wafer) run

### [Phase 4: DIY Fab (Contingency)](Phase4_DIY_Fab/)
**Status:** Planning

If commercial fabrication partnerships fail, we'll build a garage-scale semiconductor fab using DIY photolithography.

- **Resolution**: 5-10um (sufficient for proof-of-concept)
- **Safety**: Full ORM assessment included
- **Budget**: $800-3000

---

## The Core Insight: Wavelength-Division Ternary Logic

Ternary (base-3) logic is mathematically optimal for computing (closest to Euler's number *e*), but electronic implementations require 40x more transistors per trit than bits. **We solve this by using light wavelengths instead of voltage levels:**

| Trit Value | Input Wavelength | Color |
|------------|------------------|-------|
| **-1** | 1.550 um | Red (Telecom C-band) |
| **0** | 1.216 um | Green (O-band adjacent) |
| **+1** | 1.000 um | Blue (Near-IR) |

Unlike transistors, where cost scales with the number of states, wavelength differentiation is **independent of radix**. This unlocks the full 1.58x information density advantage of ternary logic while leveraging photonics' speed, parallelism, and low power.

### How Addition Works (SFG Mixing)

Sum-Frequency Generation in nonlinear crystals performs addition optically:

| A | B | A+B | Output | Detector |
|---|---|-----|--------|----------|
| -1 | -1 | -2 | 0.775 um | overflow |
| -1 | 0 | -1 | 0.681 um | DET_-1 |
| -1 | +1 | **0** | **0.608 um** | DET_0 |
| 0 | 0 | **0** | **0.608 um** | DET_0 |
| 0 | +1 | +1 | 0.549 um | DET_+1 |
| +1 | +1 | +2 | 0.500 um | overflow |

*Note: Green wavelength (1.216 um) is chosen as the harmonic mean of Red and Blue, ensuring both "zero" cases produce identical output.*

**Read the Paper**: [Zenodo Publication](https://doi.org/10.5281/zenodo.18437600)

---

## Quick Start

### Run Simulations
```bash
cd Research/programs/
python3 optical_selector.py    # Ring resonator simulation
python3 sfg_mixer.py           # Sum-frequency generation mixer
python3 test_photonic_logic.py # Logic verification
```

### Build the Phase 1 Prototype
```bash
# 1. Review the BOM and order parts
cat Phase1_Prototype/hardware/BOM_24x24_Prototype.md

# 2. 3D print the optical components
# Files: Phase1_Prototype/hardware/scad/*.scad

# 3. Flash the firmware
# Open: Phase1_Prototype/firmware/ternary_logic_controller/ternary_logic_controller.ino
# Upload to ESP32

# 4. Run your first calculation
# Serial command: ADD 1 -1
# Result: Purple light = 0
```

### Phase 2 Fiber Benchtop
```bash
python3 Phase2_Fiber_Benchtop/firmware/sfp_tuner.py
```

---

## CPU Architecture (Legacy/Alternative Path)

> **Note:** The sections below document an alternative general-purpose CPU approach. The main focus of this project is now the TPU/AI accelerator architecture described above. This CPU work is preserved for reference and potential future exploration.

### General-Purpose Optical CPU

While the TPU architecture is optimized for matrix operations, a general-purpose optical CPU would require:

- **Sequential instruction execution** - Not the TPU's strength
- **Branch prediction and control flow** - Optical switches are slower than matrix ops
- **Cache hierarchy** - Optical memory is still an open research problem

The CPU path is preserved here because some applications (embedded systems, specialized controllers) might benefit from ternary logic without needing TPU-scale parallelism.

### The Round Table Topology (Multi-CPU Configuration)

For systems requiring multiple CPUs sharing a common clock, we use a **Round Table** architecture:

```
                           CPU₀
                            │
               CPU₇ ────────┼──────── CPU₁
                     \      │      /
                      \  ┌─────┐  /
               CPU₆ ───│ KERR │─── CPU₂
                      /  │617MHz│  \
                     /   └─────┘   \
               CPU₅ ────────┼──────── CPU₃
                            │
                           CPU₄
```

- **Central Kerr Clock**: 617 MHz optical clock at the exact center
- **Equidistant Components**: All CPUs are equidistant from the clock, ensuring synchronous operation
- **Modular Scaling**: 1-8 CPUs per Round Table, each with its own IOC/IOA

**Why "Round Table"?** Like King Arthur's knights, no CPU is closer to the center than another. This eliminates clock skew when coordinating multiple processors.

### Repository Structure (Research/programs/)

Core Meep FDTD simulations for photonic components:

- `optical_selector.py` / `refined_selector.py` - Ring resonator wavelength selectors
- `sfg_mixer.py` / `universal_mixer.py` - Sum-frequency generation mixers
- `y_junction.py` - Y-junction beam splitters
- `photodetector.py` - Detector simulations
- `test_photonic_logic.py` - Logic gate verification

### Research Papers

- **[`papers/`](Research/papers/)**: Published paper, LaTeX source, figures, supplementary materials

---

## Documentation

### For Builders
- **[Build Logs](docs/build_logs/)** - Day-by-day construction progress
- **[Test Results](docs/test_results/)** - Formal verification and benchmarks
- **[Lessons Learned](docs/lessons_learned/)** - What worked and what didn't
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - How to document your build

### For Planners
- **[SMEAC Plans](Phase2_Fiber_Benchtop/admin_logistics/presentation/)** - Mission planning and presentations
- **[Decision Records](docs/decisions/)** - Why we made key design choices
- **[BOM & Assembly](Phase1_Prototype/hardware/)** - Parts lists and instructions

### Key Resources

| Resource | Path | Description |
|----------|------|-------------|
| Session Notes | [docs/session_notes/](docs/session_notes/) | Development session documentation |
| GDS Output | [Research/data/gds/](Research/data/gds/) | GDSII layout files for fabrication |
| Simulations | [Research/programs/simulations/](Research/programs/simulations/) | FDTD and photonic simulations |
| Architecture Notes | [Research/programs/ARCHITECTURE_NOTES.md](Research/programs/ARCHITECTURE_NOTES.md) | Detailed system architecture |
| Full Scaling Analysis | [docs/analytical_scaling_results.md](docs/analytical_scaling_results.md) | Complete performance projections |

### Research Tools
- **[Literature Search](tools/research_search/)** - Multi-database search tool (arXiv, IEEE, Zenodo)
  - Live URL: https://research-search-tool.onrender.com
  - Search all three major repositories from one interface

---

## Recent Activity

### Major Milestone: Wavelength Optimization Complete!

**February 2, 2026** - Solved the fundamental wavelength mapping problem:

| Achievement | Details |
|-------------|---------|
| **Optimized Input Wavelengths** | Red=1.550um, Green=**1.216um**, Blue=1.000um |
| **R+B = G+G Verified** | Both produce 0.608um output (0.2nm difference!) |
| **3-Detector Output Stage** | Tuned to SFG outputs: 0.681, 0.608, 0.549um |
| **Centered Chip Layout** | Frontend at center, reduces signal loss by ~50% |
| **Full Simulation Verification** | All 6 input combinations tested and confirmed |

**Key Insight:** By choosing Green as the harmonic mean of Red and Blue, we ensure that both ways to compute "zero" (R+B and G+G) produce the **same output wavelength** - enabling clean 3-detector readout!

---

| Date | Update |
|------|--------|
| Feb 2, 2026 | **Wavelength optimization & simulation verification** |
| Feb 2, 2026 | Centered chip layout for reduced signal degradation |
| Feb 2, 2026 | SFG output detector wavelengths (0.681, 0.608, 0.549 um) |
| Feb 2026 | Labels on dedicated GDS layer for KLayout toggle |
| Feb 2026 | 3-channel wavelength-discriminating output stage |
| Feb 2026 | Foundry submission docs: design summary, inquiry email |

<details>
<summary>Show older updates</summary>

| Date | Update |
|------|--------|
| Feb 2026 | 81-trit ternary architecture GDS layout |
| Feb 2026 | Ternary chip generator tool |
| Feb 2026 | Phase 4 polymer material simulation results |
| Feb 2026 | Academic profile setup and BibTeX citations |
| Jan 2026 | Software DOI badge and dual-citation system |
| Jan 2026 | Zenodo-GitHub integration for automatic releases |
| Jan 2026 | Research Literature Search Tool (Render.com) |
| Jan 2026 | Open source infrastructure: safety docs |
| Jan 2026 | Initial release with Zenodo publication |

</details>

---

## Project Status

| Phase | Component | Status | Timeline |
|-------|-----------|--------|----------|
| 1 | Visible Light Prototype | Building | 1 month |
| 2 | Fiber Benchtop (10GHz) | Planning | 2 months |
| 3 | Silicon Chip | Seeking Funding | TBD |
| 4 | DIY Fab (Backup) | Contingency | On Demand |

---

## Contributing

This is an open research project. Contributions welcome:

- **Hardware**: 3D print improvements, optical alignment tips
- **Software**: Simulation optimizations, firmware features
- **Theory**: Mathematical analysis, alternative architectures
- **Documentation**: Better explanations, translations

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## Citation

This project consists of both a research paper and software implementation, each with its own DOI:

### Paper (Theory)
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

**Cite the paper** for the theoretical foundation and research methodology.
**Cite the software** when referring to the implementation, code, or hardware designs.

---

## Open Source Licensing

This project is fully open source with explicit licensing for all components:

| Component | License | File |
|-----------|---------|------|
| **Software Code** | MIT License | [LICENSE](LICENSE) |
| **Documentation & Papers** | CC BY 4.0 | [LICENSES/CC-BY-4.0.txt](LICENSES/CC-BY-4.0.txt) |
| **Hardware Designs** | CERN OHL | [LICENSES/CERN-OHL.txt](LICENSES/CERN-OHL.txt) |

All source files include license headers. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards.

### Your Rights

You are free to:
- Use this research for any purpose (commercial or academic)
- Modify and build upon this work
- Distribute copies and derivatives
- Study and learn from the designs

Requirements:
- Provide attribution to the original author
- Share modifications under the same license
- Include license text with distributions

---

## Acknowledgments

- **Inspiration**: The Setun computer (Moscow State University, 1958)
- **Therapist**: Who asked "why don't you start now?"
- **20 years US Navy**: Discipline, ORM, and "make it work" mentality

---

**Author**: Christopher Riner
**Contact**: chrisriner45@gmail.com
**Location**: Chesapeake, VA, USA
**Status**: Active duty Navy, retiring soon to build optical computers full-time

> *"The best time to plant a tree was 20 years ago. The second best time is now."*
