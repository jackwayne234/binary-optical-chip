# Multi-Project Wafer (MPW) Reticle Plan — Binary Optical Chip 9×9

**Version:** 1.0
**Last updated:** 2026-02-27

---

## Overview

MPW (multi-project wafer) allows multiple chip designs to share one fabrication run, dramatically reducing cost. This document describes the binary chip's MPW strategy across three phases.

---

## Phase 1: Single 9×9 Chip + PCM Test Structures

**Die size:** ~2mm × 2mm (including test structures and dicing lanes)
**Main chip:** 1035 × 660 μm (binary 9×9 AND array)
**Test structures:** 4× PCM (process control monitor) structures

### PCM Test Structure Layout

| Structure | Size | Purpose |
|-----------|------|---------|
| WG_LOSS strip | 100 × 100 μm | Straight waveguide for propagation loss measurement |
| PPLN_STANDALONE | 200 × 100 μm | Isolated PPLN for conversion efficiency measurement |
| MZI_STANDALONE | 200 × 100 μm | Single MZI for Vπ measurement |
| RING_RESONATOR | 100 × 100 μm | (Optional) Ring for index characterization |
| GRATING_COUPLER | 100 × 100 μm | Top-surface coupling option |

### Phase 1 Die Map (2mm × 2mm)

```
┌────────────────────────────────────────────────────────┐
│   [dicing lane 50μm]                                   │
│                                                        │
│   ┌─────────────────────────────┐  ┌──────────────┐   │
│   │                             │  │  WG_LOSS     │   │
│   │   BINARY 9×9 CHIP           │  │  PPLN_ALONE  │   │
│   │   1035 × 660 μm             │  │  MZI_ALONE   │   │
│   │                             │  │  GRATING     │   │
│   └─────────────────────────────┘  └──────────────┘   │
│   [dicing lane 50μm]                                   │
└────────────────────────────────────────────────────────┘
```

**Target foundries for Phase 1:**
- AIM Photonics MPW (LNOI module)
- Applied Nanotools custom run
- HyperLight custom TFLN

**Estimated cost:** $8k–$20k

---

## Phase 2: 3×3 Tiling on One Reticle

After Phase 1 confirms the basic chip works, run 9 copies on one reticle.

**Reticle size:** 6mm × 6mm (typical MPW reticle slot)
**Chips per reticle:** 9 (3×3 tiling, ~2mm die size with lanes)
**Purpose:**
- Statistical yield measurement across 9 identical chips
- One chip for packaging, rest for experiments
- Variation study: compare chips at different reticle positions

---

## Phase 3: 27×27 Full Array Chip

Scale up from 9×9 to 27×27 (729 PEs) once 9×9 is validated.

| Parameter | 9×9 | 27×27 |
|-----------|-----|-------|
| PEs | 81 | 729 |
| Array area | 495×495 μm | 1485×1485 μm |
| Chip size | ~1035×660 μm | ~2100×2100 μm |
| Throughput | ~50 GOPS | ~450 GOPS |
| Power | <1W | <8W |

**Phase 3 design note:** Same PPLN period (19.1μm), same waveguide spec. Just larger array — identical PE design, more rows and columns.

---

## MPW Programs Reference

| Program | Foundry | Platform | Typical Cost | Schedule |
|---------|---------|---------|-------------|---------|
| AIM Photonics MPW | AIM | SiPh + TFLN | $5k–$15k/die | 2× per year |
| Europractice TFLN | Various | TFLN | €5k–€15k | 2× per year |
| Applied Nanotools | ANT | TFLN | $15k–$30k | Rolling |
| HyperLight custom | HyperLight | TFLN | $20k–$40k | Rolling |

**Recommendation:** Start with AIM or ANT MPW for Phase 1 (lower cost, proven MPW infrastructure). Use HyperLight for Phase 2/3 (best TFLN quality for production-ready chip).

---

## Test Structure Design Notes

### WG_LOSS Test Structure
Purpose: Measure propagation loss in dB/cm using cut-back method or Fabry-Perot method.
Design: 3× different lengths (100μm, 500μm, 1000μm), same cross-section as main chip waveguide.
Measurement: Insert loss vs. length → slope = propagation loss.
Target: <3 dB/cm. Flag if >5 dB/cm (waveguide process issue).

### PPLN_STANDALONE Test Structure
Purpose: Measure SHG conversion efficiency independently from main chip.
Design: 800μm PPLN on straight waveguide, input/output grating couplers.
Measurement: Inject 1550nm CW, measure 775nm output power.
Target: ≥5% conversion efficiency at 10mW pump.
This is the most critical PCM structure — confirms PPLN fabrication quality before testing main chip.

### MZI_STANDALONE Test Structure
Purpose: Measure Vπ and extinction ratio for typical MZI design.
Design: Standard 2-electrode push-pull MZI, same electrode length as main chip.
Measurement: Scan voltage, measure transmission ratio.
Target: Vπ = 1.5–3.0V, extinction ratio > 20 dB.
