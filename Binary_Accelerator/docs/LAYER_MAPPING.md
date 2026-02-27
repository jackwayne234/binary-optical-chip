# GDS Layer Mapping — Binary Optical Chip 9×9

**Version:** 1.0
**Last updated:** 2026-02-27

---

## Overview

Maps the binary chip's internal GDS layer numbers to each target foundry's naming convention. When submitting GDS for fabrication, rename layers according to the target foundry column.

---

## Internal Layer Definitions

| Internal Layer | Purpose | Description |
|---------------|---------|-------------|
| (1, 0) | WAVEGUIDE | LiNbO₃ ridge waveguides (500nm wide) |
| (2, 0) | CHI2_SFG | PPLN SFG/SHG mixer regions |
| (2, 1) | PPLN_STRIPES | PPLN periodic poling electrode stripes |
| (3, 0) | PHOTODET | Photodetector active areas (Ge or InGaAs) |
| (10, 0) | HEATER | TiN heaters / MZI EO electrodes |
| (12, 0) | METAL_PAD | Wire-bond pads (Ti/Au) |
| (12, 1) | METAL_INT | Internal metal (MZI push-pull electrodes) |
| (15, 0) | WDM_COUPLER | WDM dichroic directional coupler regions |
| (18, 0) | WEIGHT_BUS | Weight streaming bus waveguides |
| (20, 0) | REGION | Region boundary markers (non-physical) |
| (21, 0) | MEANDER | Path equalization meander waveguides |
| (99, 0) | CHIP_BORDER | Chip boundary (for dicing guide) |
| (100, 0) | TEXT | Labels and annotations (non-physical) |

---

## Foundry Layer Mapping

### HyperLight (TFLN Platform) — Recommended Primary Foundry

| Internal | HyperLight Layer Name | GDS (L,D) | Notes |
|----------|-----------------------|-----------|-------|
| (1, 0) | WG_CORE | (10, 0) | TFLN ridge waveguide |
| (2, 0) | PPLN_REGION | (20, 0) | Periodic poling zone |
| (2, 1) | PPLN_ELECTRODE | (21, 0) | Poling electrode stripes |
| (3, 0) | PD_ACTIVE | (30, 0) | Detector material |
| (10, 0) | TIN_HEATER | (40, 0) | Resistive heater / EO electrode |
| (12, 0) | BOND_PAD | (50, 0) | Wire-bond landing |
| (12, 1) | RF_METAL | (51, 0) | RF electrode |
| (15, 0) | WDM_DC | (60, 0) | Directional coupler |
| (99, 0) | CHIP_OUTLINE | (99, 0) | Dicing boundary |
| (100, 0) | TEXT | (100, 0) | Labels |

*Confirm layer names against HyperLight PDK release. Contact: foundry@hyperlight.com*

---

### AIM Photonics (Silicon Photonics + TFLN)

| Internal | AIM Layer Name | GDS (L,D) | Notes |
|----------|---------------|-----------|-------|
| (1, 0) | LNOI_WG | (1, 0) | LiNbO₃-on-insulator waveguide |
| (2, 0) | PPLN | (5, 0) | Poling region |
| (2, 1) | PPLN_STRIPE | (5, 1) | Poling stripes |
| (3, 0) | GEDET | (10, 0) | Ge photodetector |
| (10, 0) | METAL1 | (20, 0) | First metal layer (heater/electrode) |
| (12, 0) | METALPAD | (30, 0) | Bond pad |
| (12, 1) | METAL2 | (31, 0) | Second metal layer |
| (15, 0) | DIRCOUP | (40, 0) | Directional coupler |
| (99, 0) | CHIPBDRY | (99, 0) | Chip boundary |

*AIM offers MPW runs (multi-project wafer). TFLN module availability — confirm with AIM.*

---

### Applied Nanotools (ANT) — TFLN Process

| Internal | ANT Layer Name | GDS (L,D) | Notes |
|----------|---------------|-----------|-------|
| (1, 0) | LN_WAVEGUIDE | (1, 0) | Ridge waveguide |
| (2, 0) | PPLN | (2, 0) | Poling region |
| (2, 1) | PPLN_STRIPE | (2, 1) | Electrode stripes |
| (3, 0) | DETECTOR | (3, 0) | Photodetector |
| (10, 0) | HEATER | (10, 0) | TiN heater |
| (12, 0) | BOND_PAD | (12, 0) | Au wire-bond pad |
| (12, 1) | ELECTRODE | (12, 1) | EO electrode |
| (15, 0) | COUPLER | (15, 0) | WDM coupler |
| (99, 0) | CHIP | (99, 0) | Chip outline |

*ANT offers fast turnaround (4-6 months). Good option for first prototype.*

---

### NIST Center for Nanoscale Science and Technology

| Internal | NIST Layer | GDS (L,D) | Notes |
|----------|-----------|-----------|-------|
| (1, 0) | WG | (1, 0) | Waveguide |
| (2, 0) | PPLN | (2, 0) | PPLN |
| (2, 1) | POLING | (2, 1) | Poling electrodes |
| (10, 0) | METAL | (10, 0) | Metal |
| (12, 0) | PAD | (12, 0) | Bond pad |
| (99, 0) | OUTLINE | (99, 0) | Chip outline |

*NIST: research collaboration, not commercial MPW. Contact for CRADA.*

---

### Generic TFLN Process (Fallback)

| Internal | Generic Name | GDS (L,D) | Description |
|----------|-------------|-----------|-------------|
| (1, 0) | LN_RIB | (1, 0) | LN rib/ridge waveguide |
| (2, 0) | PPLN | (2, 0) | Nonlinear region |
| (2, 1) | PPLN_STRIPE | (2, 1) | Periodic electrode |
| (3, 0) | DETECTOR | (3, 0) | PD active |
| (10, 0) | HEATER | (10, 0) | Heater/electrode |
| (12, 0) | BOND_PAD | (12, 0) | Wire bond pad |
| (12, 1) | RF_ELECTRODE | (12, 1) | RF/DC electrode |
| (15, 0) | COUPLER | (15, 0) | WDM coupler |
| (18, 0) | WG_BUS | (18, 0) | Bus waveguide |
| (99, 0) | CHIP_BORDER | (99, 0) | Chip outline |
| (100, 0) | LABEL | (100, 0) | Text (non-physical) |

---

## Layer Remapping Script

To remap layers for a specific foundry, edit `monolithic_chip_binary_9x9.py`:

```python
# Replace layer constants with foundry-specific values
# Example: HyperLight remapping
LAYER_WAVEGUIDE    = (10, 0)  # was (1, 0)
LAYER_CHI2_SFG     = (20, 0)  # was (2, 0)
LAYER_PPLN_STRIPES = (21, 0)  # was (2, 1)
# ... etc
```

Or use gdsfactory layer mapping:
```python
from gdsfactory.technology import LayerMap

HYPERLIGHT_LAYERS = LayerMap(
    WG_CORE=(10, 0),
    PPLN_REGION=(20, 0),
    # ...
)
```

---

## Non-Physical Layers (Not Sent to Foundry)

These layers are for design reference only and must be **excluded from fabrication GDS**:

| Layer | Purpose |
|-------|---------|
| (20, 0) REGION | Region boundary visualization |
| (21, 0) MEANDER | Path equalization guides |
| (100, 0) TEXT | Labels and annotations |

Strip these before submission:
```bash
# KLayout: Remove non-physical layers before export
klayout -zz -rd gds_in=chip.gds -rd gds_out=chip_fab.gds \
  -r strip_labels.drc
```
