# Design Rule Check (DRC) Rules — Binary Optical Chip 9×9

**Version:** 1.0
**Foundry target:** HyperLight (TFLN), AIM Photonics, Applied Nanotools
**Last updated:** 2026-02-27

---

## Overview

These design rules ensure the binary optical chip layout is manufacturable on thin-film lithium niobate (TFLN) foundry processes. Rules are organized by layer. Violations will cause KLayout DRC to flag errors.

All dimensions in **micrometers (μm)** unless noted.

---

## Section 1: Waveguide Rules (Layer 1,0)

| Rule ID | Description | Min | Max | Nominal | Notes |
|---------|-------------|-----|-----|---------|-------|
| WG.W.1 | Waveguide width | 0.4 | 0.7 | **0.5** | Single-mode for 775/1310/1550nm |
| WG.W.2 | Width tolerance (fab) | — | — | ±0.02 | 3σ fab spec |
| WG.B.1 | Bend radius (inner) | 5.0 | — | 10.0 | Minimum for <0.1 dB bend loss |
| WG.S.1 | Waveguide-to-waveguide spacing | 2.0 | — | 5.0 | Avoid evanescent coupling |
| WG.S.2 | Waveguide-to-PPLN region spacing | 1.0 | — | 2.0 | |
| WG.E.1 | End-facet to chip edge | 5.0 | — | 10.0 | Dicing clearance |
| WG.E.2 | Waveguide-to-chip-border | 10.0 | — | 20.0 | |
| WG.C.1 | Crossing angle (waveguide crossings) | 80° | 90° | 90° | Orthogonal preferred |
| WG.L.1 | Minimum straight length (before bend) | 2.0 | — | 5.0 | |

---

## Section 2: PPLN Rules (Layer 2,0 and 2,1)

| Rule ID | Description | Min | Max | Nominal | Notes |
|---------|-------------|-----|-----|---------|-------|
| PPLN.P.1 | Poling period (Λ) | 18.9 | 19.3 | **19.1** | μm, for 1550→775nm SHG |
| PPLN.P.2 | Period tolerance (fab) | — | — | ±0.2 | μm at 3σ |
| PPLN.W.1 | Electrode stripe width | 8.5 | 10.5 | **9.55** | μm (= Λ/2) |
| PPLN.W.2 | Stripe width tolerance | — | — | ±0.5 | μm |
| PPLN.D.1 | PPLN region width | 1.0 | 4.0 | **2.0** | μm (covers waveguide) |
| PPLN.D.2 | Lateral alignment to waveguide | — | 0.5 | 0.1 | μm |
| PPLN.S.1 | PPLN-to-PPLN spacing | 5.0 | — | 10.0 | Between adjacent PE PPLN regions |
| PPLN.L.1 | Minimum PPLN length | 100 | — | 800 | μm |
| PPLN.E.1 | PPLN contact (electrode) to edge | 50 | — | 100 | μm |

**Note:** Binary chip requires ONLY ONE QPM period (Λ = 19.1μm for 1550→775nm SHG). This is a standard commercial PPLN process. No chirped or aperiodic grating needed.

---

## Section 3: Metal / Heater Rules (Layers 10,0 and 12,x)

| Rule ID | Description | Min | Max | Nominal |
|---------|-------------|-----|-----|---------|
| HT.W.1 | Heater/electrode width | 5.0 | — | 10.0 |
| HT.S.1 | Heater spacing | 5.0 | — | 10.0 |
| HT.G.1 | Gap between heater and waveguide | 2.0 | — | 5.0 |
| PAD.W.1 | Bond pad minimum width | 60.0 | — | 80.0 |
| PAD.H.1 | Bond pad minimum height | 50.0 | — | 60.0 |
| PAD.S.1 | Bond pad pitch (center-to-center) | 100.0 | — | 120.0 |
| PAD.E.1 | Bond pad to chip edge (clearance) | 20.0 | — | 30.0 |
| PAD.M.1 | Metal-to-waveguide clearance | 5.0 | — | 10.0 |

---

## Section 4: Photodetector Rules (Layer 3,0)

| Rule ID | Description | Value |
|---------|-------------|-------|
| PD.W.1 | Detector width (waveguide-coupled) | 2.0 μm |
| PD.L.1 | Detector length | 50.0 μm (minimum for >90% absorption) |
| PD.S.1 | Detector to waveguide alignment | ±0.2 μm |
| PD.C.1 | Detector contact pad size | 30×30 μm |

---

## Section 5: WDM Coupler Rules (Layer 15,0)

| Rule ID | Description | Value |
|---------|-------------|-------|
| WDM.G.1 | Directional coupler gap (775nm coupler) | 200 nm |
| WDM.L.1 | Coupling length for 775nm | 5.0–8.0 μm (foundry-specific) |
| WDM.S.1 | WDM region to waveguide crossing | 10.0 μm minimum |

---

## Section 6: Chip Boundary Rules (Layer 99,0)

| Rule ID | Description | Value |
|---------|-------------|-------|
| CB.W.1 | Chip width | 1035 μm ±5 μm |
| CB.H.1 | Chip height | 660 μm ±5 μm |
| CB.D.1 | Dicing lane width (around chip) | ≥50 μm |
| CB.A.1 | Alignment mark size | 20×20 μm |
| CB.A.2 | Alignment mark location | 4 corners, 100 μm from edge |

---

## Section 7: Layer Density Rules

| Rule | Description | Requirement |
|------|-------------|-------------|
| DEN.1 | Waveguide density in array region | Nominally uniform (systolic array) |
| DEN.2 | PPLN coverage in array region | One PPLN per PE (81 total) |
| DEN.3 | Metal density over chip | <30% (to avoid stress deformation) |

---

## Section 8: Critical Dimension Summary

| Feature | Nominal | Tolerance | Layer |
|---------|---------|-----------|-------|
| Waveguide width | 500 nm | ±20 nm | (1,0) |
| Bend radius | 10 μm | ≥5 μm | (1,0) |
| PPLN period | 19.1 μm | ±0.2 μm | (2,0) |
| PPLN stripe | 9.55 μm | ±0.5 μm | (2,1) |
| Bond pad | 80×60 μm | ±5 μm | (12,0) |
| Chip size | 1035×660 μm | ±5 μm | (99,0) |

---

## Section 9: KLayout DRC Script

A KLayout DRC runset (`binary_chip_9x9.drc`) should check:

```python
# binary_chip_9x9.drc — KLayout DRC
# Layer definitions
wg    = input(1, 0)
ppln  = input(2, 0)
ppln_s = input(2, 1)
pad   = input(12, 0)
border = input(99, 0)

# WG rules
wg.width < 0.4.um  # WG.W.1 minimum
wg.space < 2.0.um  # WG.S.1 minimum spacing
wg.separation(ppln, 0.5.um)  # PPLN alignment

# PPLN rules
ppln.width < 1.0.um  # PPLN.D.1 minimum
ppln.space < 5.0.um  # PPLN.S.1 minimum

# Pad rules
pad.width < 60.um   # PAD.W.1
pad.height < 50.um  # PAD.H.1
pad.space < 100.um  # PAD.S.1
```

---

## Section 10: Process Tolerances (Foundry Reference)

These are typical values for TFLN foundry (HyperLight). Confirm with foundry PDK.

| Parameter | Typical | Range |
|-----------|---------|-------|
| Waveguide width | 500 nm | ±20 nm |
| Etch depth | 400 nm | ±10 nm |
| PPLN poling period | 19.1 μm | ±0.2 μm |
| Propagation loss | 2.0 dB/cm | 0.5–5.0 dB/cm |
| Edge coupling (lensed fiber) | 1.0 dB | 0.5–3.0 dB |
| Surface roughness (RMS) | <1 nm | — |

---

*Review against foundry PDK before GDS submission. Some rules may need adjustment per specific foundry process.*
