# Chip Interface Specification — Binary Optical Chip 9×9

**Version:** 1.0
**Last updated:** 2026-02-27

---

## Overview

This document describes how to physically connect to the binary optical chip for testing and operation. The chip has three interface types:

1. **Optical inputs** — 2 fiber arrays (activations + weights)
2. **Optical outputs** — 1 fiber array (775nm SFG results)
3. **Electronic interface** — wire bonds to PCB for MZI control and detector readout

---

## Optical Interface

### Input Fiber Arrays

| Array | Location | Channels | Wavelength | Fiber Type |
|-------|---------|---------|-----------|-----------|
| Activation input | Left edge | 9 channels (rows 0-8) | 1310nm or 1550nm | SMF-28, lensed |
| Weight input | Top edge | 9 channels (cols 0-8) | 1310nm or 1550nm | SMF-28, lensed |

**Coupling method:** V-groove fiber array (9-channel, 127μm pitch) aligned to on-chip facets.
UV-epoxy fixation after alignment optimization (target: <1 dB coupling loss per channel).

**Fiber spec:**
- Type: SMF-28 (Corning) with lensed tip (OZ Optics or Nanonics)
- Lensed tip spot size: 2–4 μm (matched to waveguide mode field)
- MFD of waveguide: ~1.2 μm × 0.8 μm (500nm ridge, 300nm slab)
- Mode mismatch loss: 0.5–2 dB (before coupling optimization)

### Output Fiber Array

| Array | Location | Channels | Wavelength | Notes |
|-------|---------|---------|-----------|-------|
| Output | Right edge | 9 channels (cols 0-8) | 775nm | After WDM demux on chip |

**Note:** The on-chip WDM dichroic coupler separates 775nm from 1310/1550nm pass-through before the output facet. Output fibers carry only 775nm signal.

If WDM coupler is not included on-chip, an external 775nm bandpass filter (>30 dB rejection at 1310/1550nm) must be placed before the detector.

---

## Electronic Interface

### Bond Pad Map

Bond pads are located on the left and right edges of the chip.

**Left edge (activation + weight MZI control):**

| Pad | Signal | Description |
|-----|--------|-------------|
| A0–A8 | MZI_ACT_[0-8]_V | Activation encoder voltage (0V = 1310nm, ~2V = 1550nm) |
| W0–W8 | MZI_WT_[0-8]_V | Weight encoder voltage (same spec) |
| GND | GND | Ground reference |
| VCC | 3.3V | Supply (for on-chip TIA if integrated) |

**Right edge (detector outputs):**

| Pad | Signal | Description |
|-----|--------|-------------|
| D0–D8 | DET_[0-8]_I | Detector photocurrent output (col 0-8) |
| BIAS | BIAS_V | Photodetector reverse bias (1–3V) |
| GND | GND | Ground reference |

**Total wire bonds:** 18 (MZI) + 9 (detector) + 2 (GND) + 1 (VCC) + 1 (bias) = **31 bonds**

### PCB Interface

Mount chip on AlN submount (for thermal conduction), then mount submount on PCB.

PCB requirements:
- SMA RF connectors for MZI drive lines (up to 10 GHz bandwidth)
- Transimpedance amplifier (TIA) for each detector channel
- 18-channel DAC for MZI voltages (resolution ≥12 bit, range 0–3.3V)
- 9-channel ADC for detector currents (resolution ≥12 bit, bandwidth ≥1 GHz)

---

## MZI Encoder Operation

Each MZI encoder is a 2-state Mach-Zehnder interferometer on the chip.

**How it works:**
1. Two laser sources (1310nm CW laser + 1550nm CW laser) are combined in a 2×2 coupler before the MZI input
2. The MZI EO phase shifter (Pockels effect, r₃₃ ≈ 30 pm/V for X-cut LiNbO₃) controls which wavelength exits
3. At V=0: minimum phase shift → 1310nm selected (bit 0)
4. At V=Vπ≈2V: π phase shift → 1550nm selected (bit 1)

**Timing:**
- EO bandwidth: >10 GHz (TFLN Pockels modulators)
- Propagation time through chip: ~7.4 ps (1035μm × n_g/c)
- Minimum encode cycle: >1 ns for safe operation (chip propagation << electrical switching)

**Calibration:**
- Apply V=0, measure output at 1310nm photodetector: should be maximum
- Apply V=Vπ, measure output at 1550nm photodetector: should be maximum
- Scan V from 0 to 5V to find exact Vπ (varies ±0.3V due to fab tolerances)

---

## Power Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| Laser 1 (1310nm) | >1 mW CW per channel | 9 channels: single laser + 9-way splitter |
| Laser 2 (1550nm) | >1 mW CW per channel | 9 channels: single laser + 9-way splitter |
| MZI drive voltage | 0–3.3V, 18 channels | DAC + buffer amplifier |
| Detector bias | 1–3V reverse bias | |
| TIA supply | 3.3V @ <100mA | For all 9 detector TIAs |
| **Total optical** | ~18 mW laser | 2× lasers × 9 channels × 1mW |
| **Total electrical** | <500 mW | MZI switching + TIA |

---

## Test Connector Pinout (Reference Board)

```
┌──────────────────────────────────────────────────────────────┐
│                  BINARY OPTICAL CHIP PCB                      │
│                                                               │
│  [9×SMA]  [1310nm LASER]  [CHIP SOCKET]  [1550nm LASER]  [9×SMA] │
│  Act MZI   → fiber array  1035×660μm   fiber array ←  Wt MZI  │
│                                                               │
│  [18×DAC]  ←wire bonds→   [9×TIA+ADC]                       │
│                                                               │
│  [USB/SPI → FPGA → DAC/ADC interface]                        │
└──────────────────────────────────────────────────────────────┘
```

---

## Binary Chip vs Ternary Interface Comparison

| Interface | Binary | Ternary N-Radix |
|-----------|--------|-----------------|
| Input laser sources | **2** (1310, 1550nm) | 3 (1064, 1310, 1550nm) |
| MZI states | **2** (2-state switch) | 3 (3-state switch) |
| Output wavelength bands | **1** (775nm) | 3 (500-670nm range) |
| Output demux | **Dichroic coupler** | AWG (complex) |
| Wire bonds (MZI) | **18** | 27 |
| Total connectors | **~35** | ~50 |
| Test bench cost (estimate) | **~$8k** | ~$12k |

Binary is simpler at every interface level.
