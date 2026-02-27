# Packaging Specification — Binary Optical Chip 9×9

**Version:** 1.0
**Last updated:** 2026-02-27

---

## Overview

The binary optical chip requires packaging that provides:
1. Mechanical support (chip-to-PCB)
2. Optical I/O (fiber array coupling at 3 edges)
3. Electrical I/O (wire bonds for MZI + detector)
4. Thermal management (heatsink or passive thermal path)

---

## Section 1: Die Attach

**Submount:** Aluminum nitride (AlN)
- AlN thermal conductivity: 150–220 W/m·K (excellent thermal conduction)
- Low thermal expansion: 4.5 ppm/°C (well-matched to LiNbO₃: 15 ppm/°C)
- Size: 3mm × 3mm × 0.5mm

**Bond method:** AuSn eutectic solder (Au80/Sn20, melting point 280°C)
- Preferred over epoxy for thermal performance
- Process: Apply solder preform, place chip under N₂ atmosphere, reflow at 300°C
- Alignment tolerance: ±10 μm (not critical — chip facets are at fixed locations)

**Epoxy alternative:** Epo-Tek H20E (silver-filled, Tg 90°C)
- Lower cost and equipment compared to eutectic
- Acceptable for initial prototype testing

---

## Section 2: Wire Bonding

**Wire spec:**
- Material: 25 μm diameter gold (Au) wire
- Ball bond at chip pads, wedge bond at PCB pads
- Loop height: 150–200 μm (for fiber clearance above chip)
- Pitch: 120 μm (pad pitch from DRC_RULES.md PAD.S.1)

**Bond sequence (left edge — activation MZI):**
1. GND first (ground reference)
2. MZI_ACT_0 through MZI_ACT_8 (rows 0–8)
3. MZI_WT_0 through MZI_WT_8 (weight encoders)
4. VCC (last)

**Bond sequence (right edge — detectors):**
1. GND
2. DET_BIAS (reverse bias for PDs)
3. DET_0 through DET_8 (columns 0–8)

**Total bonds:** ~31 wires
**Equipment:** Manual wedge bonder (West Bond 7476D) or automated (Kulicke & Soffa 4526)

---

## Section 3: Fiber Coupling

**Fiber type:** SMF-28 with lensed tip (OZ Optics LPF series)
- Lensed tip spot size: 2.5 μm ± 0.5 μm
- Lensed tip NA: 0.3–0.4
- Working distance: 3–5 μm from facet

**Array specification:**
- 9-channel V-groove fiber array (127 μm pitch — matches PE pitch of 55μm via fanout)
  - Or: 55 μm pitch V-groove (direct match, less common)
  - Or: Individual fibers on 6-axis stages for initial testing
- V-groove substrate: Silicon or glass
- Array width: ~1.1 mm (9 channels × 127 μm)

**Three fiber arrays needed:**

| Array | Location | Channels | Wavelength | Purpose |
|-------|---------|---------|-----------|---------|
| FA-1 | Left edge | 9 | 1310/1550nm | Activation input |
| FA-2 | Top edge | 9 | 1310/1550nm | Weight input |
| FA-3 | Right edge | 9 | 775nm | SFG output |

**Alignment and fixation:**
1. Mount chip in alignment jig
2. Active alignment: inject 1310nm CW laser, monitor output TIA while adjusting
3. Target: coupling loss < 1 dB per channel
4. Apply UV-epoxy (Norland NOA61 or OG142) to V-groove
5. UV cure: 365nm, 60 seconds, 500 mW/cm²
6. Post-cure: bake 60°C for 30 minutes

---

## Section 4: Package Housing

**Custom aluminum package:**

```
     ┌──────────────────────────────────────────────────┐
     │  [9×SMA connectors]   [chip window]  [fiber FC/APC]│
     │  Left panel           Top view       Right panel   │
     │                                                    │
     │                   [CHIP]                          │
     │  [FA-1 input]  ←  on AlN  → [FA-3 output]        │
     │                  submount                          │
     │              [FA-2 weights (top)]                  │
     │                                                    │
     │  [PCB with TIA]    [DAC/ADC]    [USB/SPI conn]     │
     └──────────────────────────────────────────────────┘
```

**Dimensions:** 60mm × 40mm × 20mm (L×W×H) aluminum
**Lid:** Removable for fiber adjustment access
**RF connectors:** 18× SMA (for MZI drive lines)
**Optical connectors:** 3× FC/APC fiber pigtail bulkhead

---

## Section 5: Thermal Management

**Heat sources:**
- Chip: optical losses heat waveguides (~1–5 mW)
- MZI drivers: ~100–200 mW total
- TIAs: ~50 mW total

**Passive cooling:**
- AlN submount conducts heat to aluminum package lid
- Natural convection: sufficient for <500 mW total dissipation
- Expected chip temperature rise above ambient: <5°C

**Optional TEC:**
- For PPLN phase-match optimization or colder environments
- Thermoelectric module (Laird HiTemp ETX series, 3W)
- Maintains chip at 25°C ± 0.1°C if needed

---

## Section 6: Operating Limits

| Parameter | Min | Max | Notes |
|-----------|-----|-----|-------|
| Operating temperature | 15°C | 55°C | Passive, no TEC |
| Storage temperature | −20°C | 70°C | |
| Relative humidity | 10% | 85% | Non-condensing |
| Chip supply voltage | 0V | 5V | MZI drive |
| Detector bias voltage | 0V | 5V | Reverse bias |
| Optical input power (per channel) | 0.1 mW | 50 mW | Max to avoid waveguide damage |
| Fiber pull force (on bonded array) | — | 0.5 N | Don't yank fibers |
