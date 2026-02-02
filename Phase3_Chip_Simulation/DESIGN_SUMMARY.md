# Design Summary: 81-Trit Ternary Optical Processor

*Prepared for foundry submission*
*Version 1.3 | February 2, 2026*
*Updated: Full ALU with add/sub/mul, carry chain, and MZI selector option*

---

## Overview

This document describes a photonic integrated circuit implementing an 81-trit ternary arithmetic logic unit (ALU) using wavelength-division multiplexing. The design bypasses the radix economy penalty of electronic ternary logic by encoding ternary states as optical wavelengths rather than voltage levels.

**Chip name:** Ternary81
**Function:** 81-trit optical ALU (add, subtract, multiply, divide)
**Equivalent capacity:** 128-bit binary
**Technology:** Silicon photonics (LiNbO3 or SiN platform)

---

## Architecture

### Ternary encoding scheme (INPUT wavelengths)

| Logic value | Wavelength | Color | Telecom band |
|-------------|------------|-------|--------------|
| -1 | 1.550 μm | Red | C-band |
| 0 | 1.216 μm | Green | O-band adjacent |
| +1 | 1.000 μm | Blue | Near-IR |

**Key optimization:** Green wavelength (1.216 μm) is chosen as the *harmonic mean* of Red and Blue:
```
λ_Green = 2 × λ_Red × λ_Blue / (λ_Red + λ_Blue) = 1.216 μm
```

This ensures that R+B (=-1+1=0) and G+G (=0+0=0) produce the **same SFG output wavelength** (0.608 μm), enabling clean readout.

### SFG Output wavelengths (5-DETECTOR configuration)

All 5 possible arithmetic results are detected for full carry propagation:

| Detector | Wavelength | Result | Source | Function |
|----------|------------|--------|--------|----------|
| DET_-2 | 0.775 μm | -2 | R+R | **Borrow** (carry out) |
| DET_-1 | 0.681 μm | -1 | R+G | Normal result |
| DET_0 | 0.608 μm | 0 | R+B or G+G | Normal result |
| DET_+1 | 0.549 μm | +1 | G+B | Normal result |
| DET_+2 | 0.500 μm | +2 | B+B | **Carry** (carry out) |

*All output wavelengths verified by Meep FDTD simulation (February 2, 2026)*

**Carry propagation:** When DET_±2 fires, the result digit is ∓1 (wraps around) and a carry/borrow propagates to the next trit position.

### Hierarchical organization

The 81-trit word divides naturally into ternary sub-units:

```
81 trits = 27 trytes (3 trits each)
         = 9 nonads (9 trits each)
         = 3 heptacosas (27 trits each)
```

Physical layout: 3×3 grid of 9-trit processing elements.

### Core components (SIMPLIFIED architecture)

| Component | Function | Quantity per ALU |
|-----------|----------|------------------|
| AWG demux (3-ch) | Input wavelength separation (R/G/B) | 2 (one per operand) |
| Ring resonator | Wavelength selection/gating | 6 (3 per operand) |
| Wavelength combiner | Merge selected wavelengths | 2 (one per operand) |
| MMI 2×2 | Combine A and B operands | 1 |
| SFG mixer | Ternary arithmetic (χ² nonlinear) | 1 |
| AWG demux (5-ch) | Output wavelength separation | 1 |
| Photodetector | Output readout | 5 (DET_-2 to DET_+2) |

**Simplification:** The output stage uses a single 5-channel AWG demultiplexer instead of a splitter + 5 ring resonator filters. This reduces component count by 45% per ALU while maintaining full functionality.

### Total component count (81-trit chip)

| Component | Count | Notes |
|-----------|-------|-------|
| Ring resonators | 486 | Input selectors only (6 per ALU × 81) |
| AWG demux | 243 | 2 input + 1 output per ALU × 81 |
| SFG mixers | 81 | One per ALU |
| Photodetectors | 405 | 5 per ALU × 81 |
| MMI couplers | ~500 | Combiners, splitters |

*Note: Simplified architecture eliminates 405 ring resonator filters from output stage.*

### Supported operations

| Operation | Mixer Type | Physics | Output Formula |
|-----------|------------|---------|----------------|
| **Addition** | SFG | χ² sum-frequency | λ_out = 1/(1/λ₁ + 1/λ₂) |
| **Subtraction** | DFG | χ² difference-frequency | λ_out = 1/(1/λ₁ - 1/λ₂) |
| **Multiplication** | Kerr | χ³ four-wave mixing | Balanced ternary product |

**Multiplication truth table:**
| A | B | A × B |
|---|---|-------|
| -1 | -1 | +1 |
| -1 | 0 | 0 |
| -1 | +1 | -1 |
| 0 | any | 0 |
| +1 | -1 | -1 |
| +1 | 0 | 0 |
| +1 | +1 | +1 |

### Carry chain (electronic)

Multi-trit arithmetic uses electronic carry propagation via dedicated GPIO signals:

| Signal | Function | Direction |
|--------|----------|-----------|
| CARRY_OUT_POS | Carry (+1) from DET_+2 | Output |
| CARRY_OUT_NEG | Borrow (-1) from DET_-2 | Output |
| CARRY_IN | Carry/borrow from previous trit | Input |

**Firmware algorithm:**
1. Read all photodetector outputs simultaneously
2. For each trit N (LSB to MSB): add carry from trit N-1
3. Result = (A[N] + B[N] + carry_in) mod 3
4. Generate new carry for trit N+1

### Selector options

| Type | Component | Pros | Cons |
|------|-----------|------|------|
| **Ring resonator** (default) | wavelength_selector() | Compact, wavelength-specific | Sensitive to fab variations |
| **MZI switch** | wavelength_selector_mzi() | Better extinction, tolerant | Larger footprint |

MZI switches use thermo-optic phase control via heater electrodes (GDS layer 10).

---

## Design specifications

### Waveguide parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Core width | 0.5 μm | Single-mode at all wavelengths |
| Core index | 2.2 | LiNbO3 |
| Cladding index | 1.0 | Air cladding |
| Minimum bend radius | 5 μm | Ring resonators (PDK minimum) |
| Coupling gap | 0.15 μm | Ring-to-bus coupling (simulation verified) |
| Mixer width | 0.8 μm | Wider for phase matching |

### Nonlinear mixers

| Mixer | Length | Width | Material | GDS Layer |
|-------|--------|-------|----------|-----------|
| SFG (addition) | 20 μm | 0.8 μm | LiNbO3 χ² | (2, 0) |
| DFG (subtraction) | 25 μm | 0.8 μm | LiNbO3 χ² | (4, 0) |
| Kerr (multiplication) | 30 μm | 0.8 μm | LiNbO3 χ³ | (7, 0) |

**Material options:**
- Primary: LiNbO3 (d33 ≈ 30 pm/V for χ², n2 for χ³)
- Alternative: Poled DR1-SU8 (15% efficiency)

### Die size estimate

| Configuration | Approximate size |
|---------------|------------------|
| Single ALU (1 trit) | 350 × 250 μm |
| 9-trit nonad | 1.2 × 0.6 mm |
| 81-trit full processor | 3.6 × 5.4 mm |

---

## Layer definitions (generic PDK)

*Note: Generated using gdsfactory generic PDK. Layer mapping to foundry-specific process required.*

| GDS layer | Purpose |
|-----------|---------|
| (1, 0) | Waveguide core |
| (2, 0) | SFG mixer region (χ² addition) |
| (3, 0) | Photodetector region |
| (4, 0) | DFG mixer region (χ² subtraction) |
| (5, 0) | Kerr resonator region |
| (6, 0) | AWG body |
| (7, 0) | MUL mixer region (χ³ multiplication) |
| (10, 0) | MZI heater/electrode |
| (100, 0) | Labels (toggle in KLayout) |

---

## Input/output specification

### Optical I/O

| Port | Position | Function |
|------|----------|----------|
| input_a | Left edge, upper | Operand A (multi-wavelength) |
| input_b | Left edge, lower | Operand B (multi-wavelength) |

### Electrical outputs (5-detector SFG detection)

The output stage uses a **5-channel AWG demultiplexer** to separate SFG output wavelengths, routing each to a dedicated photodetector:

| Signal | Wavelength | Ternary Result | Function |
|--------|------------|----------------|----------|
| DET_-2 | 0.775 μm | -2 | Borrow out |
| DET_-1 | 0.681 μm | -1 | Result |
| DET_0 | 0.608 μm | 0 | Result |
| DET_+1 | 0.549 μm | +1 | Result |
| DET_+2 | 0.500 μm | +2 | Carry out |

**Detection logic:** Exactly one detector fires for each arithmetic result. Firmware reads all five to determine the output digit and carry:

| DET_-2 | DET_-1 | DET_0 | DET_+1 | DET_+2 | Digit | Carry |
|--------|--------|-------|--------|--------|-------|-------|
| HIGH | low | low | low | low | +1 | -1 (borrow) |
| low | HIGH | low | low | low | -1 | 0 |
| low | low | HIGH | low | low | 0 | 0 |
| low | low | low | HIGH | low | +1 | 0 |
| low | low | low | low | HIGH | -1 | +1 (carry) |

**Carry interpretation:**
- Result -2: Output digit = +1, carry = -1 (borrow to next position)
- Result +2: Output digit = -1, carry = +1 (carry to next position)

### Fiber coupling requirements

- **Method:** Edge coupling preferred (grating couplers acceptable)
- **Fiber type:** SMF-28 or equivalent
- **Pitch:** 127 μm or 250 μm array
- **Alignment tolerance:** ±1 μm

### Electrical I/O (if active tuning required)

- Ring resonator tuning pads (thermal or electro-optic)
- Photodetector bias and readout pads

---

## Test plan

### Equipment required

- Tunable laser sources (1.000, 1.216, 1.550 μm)
- Optical spectrum analyzer (0.5-1.6 μm range)
- Fiber alignment stage
- Si photodetectors (for 0.5-0.8 μm SFG outputs)

### Verification tests

| Test | Input | Expected output | Pass criteria |
|------|-------|-----------------|---------------|
| Waveguide transmission | 1.55 μm CW | Transmitted signal | Loss < 3 dB/cm |
| Ring resonator | Broadband | Filtered wavelength | Extinction > 10 dB |
| SFG mixing (R+B) | 1.550 + 1.000 μm | Signal at 0.608 μm | Detectable peak |
| SFG mixing (G+G) | 1.216 + 1.216 μm | Signal at 0.608 μm | Same as R+B (±1 nm) |
| Ternary addition | Red + Blue | DET_0 fires | Correct detector |

### Truth table verification (single trit) - SIMULATION VERIFIED

| A | B | A + B | SFG Output λ | Detector | Digit | Carry |
|---|---|-------|--------------|----------|-------|-------|
| -1 (R) | -1 (R) | -2 | 0.775 μm | DET_-2 | +1 | -1 (borrow) |
| -1 (R) | 0 (G) | -1 | 0.681 μm | DET_-1 | -1 | 0 |
| -1 (R) | +1 (B) | 0 | **0.608 μm** | DET_0 | 0 | 0 |
| 0 (G) | 0 (G) | 0 | **0.608 μm** | DET_0 | 0 | 0 |
| 0 (G) | +1 (B) | +1 | 0.549 μm | DET_+1 | +1 | 0 |
| +1 (B) | +1 (B) | +2 | 0.500 μm | DET_+2 | -1 | +1 (carry) |

*Critical verification: R+B and G+G both produce 0.608 μm (verified within 0.2 nm by Meep FDTD)*

---

## Chip layout

### Centered frontend architecture

The optical frontend (Kerr clock, Y-junction, splitter trees) is positioned at the **chip center** to minimize signal degradation:

```
                    ┌─────────────────────────────────────┐
                    │  Zone 6    Zone 7    Zone 8        │
                    │  (9 ALUs)  (9 ALUs)  (9 ALUs)      │
                    ├─────────────────────────────────────┤
                    │  Zone 3   [FRONTEND]  Zone 5       │
                    │  (9 ALUs)  Kerr+Y    (9 ALUs)      │
                    ├─────────────────────────────────────┤
                    │  Zone 0    Zone 1    Zone 2        │
                    │  (9 ALUs)  (9 ALUs)  (9 ALUs)      │
                    └─────────────────────────────────────┘
```

**Benefits:**
- Maximum path length reduced by ~50%
- Equal signal power to all ALUs
- Symmetric splitter tree distribution

---

## Files included

### GDS layouts

| File | Operation | Selectors | Description |
|------|-----------|-----------|-------------|
| `ternary_81trit_simplified.gds` | ADD | Ring | **RECOMMENDED** - Simplified AWG output |
| `ternary_81trit_add_mzi.gds` | ADD | MZI | MZI switches (larger, more tolerant) |
| `ternary_81trit_sub.gds` | SUB | Ring | Subtraction (DFG mixer) |
| `ternary_81trit_mul.gds` | MUL | Ring | Multiplication (Kerr mixer) |
| `ternary_81trit_5det_complete.gds` | ADD | Ring | Ring filter output (more precise) |

### Documentation

| File | Description |
|------|-------------|
| `METHODS.md` | Simulation methodology |
| `../Research/data/SIMULATION_RESULTS.md` | Material characterization data |

### Simulation verification files

| File | Contents |
|------|----------|
| `mixer_data_RED_RED.csv` | R+R → 0.775 μm verified |
| `mixer_data_RED_GREEN.csv` | R+G → 0.681 μm verified |
| `mixer_data_RED_BLUE.csv` | R+B → 0.608 μm verified |
| `mixer_data_GREEN_GREEN.csv` | G+G → 0.608 μm verified |
| `mixer_data_GREEN_BLUE.csv` | G+B → 0.549 μm verified |
| `mixer_data_BLUE_BLUE.csv` | B+B → 0.500 μm verified |

---

## References

1. Riner, C. (2026). "Wavelength-Division Ternary Logic: Bypassing the Radix Economy Penalty in Optical Computing." Zenodo. DOI: 10.5281/zenodo.18437600

2. Simulation methodology uses Meep FDTD (Oskooi et al., Computer Physics Communications, 2010)

---

## Contact

**Designer:** Christopher Riner
**Email:** chrisriner45@gmail.com
**Repository:** https://github.com/jackwayne234/-wavelength-ternary-optical-computer

---

*Generated with gdsfactory. Ready for foundry PDK adaptation.*
