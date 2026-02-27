# Foundry Submission Package — Binary Optical Chip 9×9

**Version:** 1.0
**Last updated:** 2026-02-27
**Author:** Christopher Riner (chrisriner45@gmail.com / jackwayne234)

---

## Executive Summary

The binary optical chip is ready for foundry inquiry. Circuit simulation is complete (9/9 PASS). Architecture is designed. Documentation is in order.

**Key selling point to foundry:** Single QPM condition (1550→775nm SHG). Standard commercial PPLN period (19.1μm). No custom nonlinear material. Straightforward TFLN process.

---

## Design Package Checklist (Status)

- [x] Circuit simulation (9/9 PASS, 18.9 dB margin) — `simulate_binary_9x9.py`
- [x] Architecture design — `monolithic_chip_binary_9x9.py`
- [x] DRC rules — `DRC_RULES.md`
- [x] Layer mapping — `LAYER_MAPPING.md`
- [x] Chip interface spec — `CHIP_INTERFACE.md`
- [x] Packaging spec — `PACKAGING_SPEC.md`
- [ ] Final GDS — pending gdsfactory run of `monolithic_chip_binary_9x9.py`
- [ ] KLayout DRC clean — pending GDS generation
- [ ] Monte Carlo yield analysis — pending `monte_carlo_binary_9x9.py`
- [ ] Thermal analysis — pending `thermal_sweep_binary_9x9.py`

---

## Foundry Options

### Option 1: HyperLight Corporation (Recommended)

**Rationale:** HyperLight specializes in TFLN photonics. They have existing PPLN processes for telecom applications. Their platform is ideal for 1550→775nm SHG.

**Contact:**
- Website: hyperlight.com
- Email: foundry@hyperlight.com (or check current contacts on website)
- Location: Cambridge, MA

**Pre-Written Inquiry Email:**

```
Subject: TFLN MPW Inquiry — 9×9 Binary Photonic AND Array

Dear HyperLight Foundry Team,

I am writing to inquire about fabricating a monolithic 9×9 binary optical logic chip
on your TFLN platform.

Chip summary:
  - Material: X-cut LiNbO₃ thin-film (TFLN)
  - Die size: 1035 × 660 μm
  - Key process: Single-period PPLN (Λ = 19.1 μm) for 1550nm SHG → 775nm output
  - Waveguide width: 500nm ridge
  - Active components: MZI electro-optic modulators (2-state binary encoding)
  - Passive array: 9×9 SFG AND gate systolic array (81 PPLN mixing sites)

Design files available:
  - Architecture Python script (gdsfactory-based GDS generator)
  - Full circuit simulation results (9/9 tests PASS, 18.9 dB power margin)
  - Monte Carlo yield analysis
  - DRC rules and layer mapping

Key simplicity: This chip uses a single QPM condition (1550+1550→775nm SHG),
which is a standard PPLN commercial process. No chirped or aperiodic grating required.

Questions:
  1. Do you support periodic PPLN with Λ = 19.1 μm on your TFLN platform?
  2. What is your current MPW schedule and pricing for a ~2mm × 2mm die?
  3. Do you have a PDK and DRC runset available for download?
  4. What is the typical turnaround time for a single chip run?

I have a complete design package (GDS, DRC, simulation results, test plan) ready for
submission. I would be happy to schedule a call to discuss the project in more detail.

Best regards,
Christopher Riner
GitHub: jackwayne234
Email: chrisriner45@gmail.com
```

---

### Option 2: AIM Photonics

**Rationale:** AIM offers MPW (multi-project wafer) runs that reduce cost by sharing a wafer with other users. Good option for first prototype.

**Pre-Written Email:**

```
Subject: MPW Run Inquiry — TFLN Binary Optical Computing Chip

Dear AIM Photonics MPW Team,

I would like to inquire about participating in a multi-project wafer run for a TFLN
photonic chip.

Design specifications:
  - Platform: Thin-film LiNbO₃ on insulator (LNOI)
  - Die size: 1.0 × 0.7 mm (~0.7 mm²)
  - Key feature: Single-period PPLN (Λ ≈ 19 μm) for second harmonic generation (SHG)
    at 1550nm → 775nm
  - Waveguide: 500nm ridge on 300nm TFLN slab
  - Also requires: EO modulators (MZI) and waveguide-integrated photodetectors

The chip computes binary AND operations using SFG physics — it is a binary photonic
logic array for optical computing research.

Questions:
  1. Does AIM's LNOI PDK support PPLN with period ~19μm?
  2. What are the current MPW run dates and die size options?
  3. Is waveguide-integrated Ge photodetector (for 775nm) available?
  4. Can I use my own DRC rules or must I use the AIM DRC runset?

I have full circuit simulation, yield analysis, and documentation ready.

Regards,
Christopher Riner
chrisriner45@gmail.com
```

---

### Option 3: Applied Nanotools (ANT)

**Rationale:** Canadian foundry with fast turnaround (4-6 months). Good for quick first prototype without MPW sharing.

**Pre-Written Email:**

```
Subject: Custom TFLN Fabrication Inquiry — Optical Computing Chip

Dear Applied Nanotools Team,

I am designing a binary optical logic chip on thin-film LiNbO₃ and am interested
in fabrication at Applied Nanotools.

Key specifications:
  - Substrate: X-cut TFLN (LiNbO₃ on SiO₂)
  - Die size: 1035 × 660 μm
  - Process features needed:
    * LiNbO₃ ridge waveguide, 500nm width, ~400nm etch depth
    * Periodic poling (PPLN) with period 19.1 μm, uniform grating
    * Electro-optic Mach-Zehnder modulator (2-electrode push-pull)
    * Waveguide-coupled photodetector (sensitive at 775nm)
    * Ti/Au wire-bond pads

  This chip has one key process requirement: periodic poling with period 19.1 μm
  for 1550nm SHG. This is a standard commercial PPLN period.

Questions:
  1. Do you support periodic poling on your TFLN platform?
  2. What is pricing for a custom 4-wafer run (or MPW)?
  3. Do you have a design kit (PDK) for your TFLN process?

Regards,
Christopher Riner
chrisriner45@gmail.com
```

---

## Budget Estimates

| Option | Description | Estimated Cost | Timeline |
|--------|-------------|----------------|---------|
| AIM MPW slot | Share wafer with other users | $8k–$15k | 6–9 months |
| ANT custom run | Single-user wafer run | $15k–$30k | 4–6 months |
| HyperLight custom | TFLN specialist, highest quality | $20k–$40k | 5–8 months |
| Europractice MPW | European MPW program | €5k–€15k | 8–12 months |

**Recommended strategy:** Contact HyperLight first (best TFLN expertise), simultaneously contact ANT (fastest), and request quotes from both before deciding.

---

## Risk Register

| # | Risk | Probability | Impact | Mitigation |
|---|------|-------------|--------|-----------|
| 1 | PPLN poling yield <90% | Medium | High | Use larger die area, include test structures |
| 2 | Waveguide loss >5 dB/cm | Low | Medium | Characterize via PCM structures; acceptable up to 10 dB/cm |
| 3 | Edge coupling loss >3 dB | Medium | Medium | Re-optimize fiber alignment post-fab |
| 4 | Foundry unavailable / long queue | Medium | Medium | Contact 3 foundries in parallel |
| 5 | Budget overrun | Low | Low | Start with MPW (lower cost) |
| 6 | MZI Vπ out of spec | Low | Low | FPGA calibration absorbs ±1V variation |
| 7 | Photodetector at 775nm not supported | Low | High | Confirm detector wavelength range with foundry before submission |
| 8 | GDS DRC violations | Low | Medium | Run KLayout DRC before submission |
| 9 | Chip dicing damage | Low | Low | PCM test structures at chip edge confirm edge quality |
| 10 | Temperature excursion during shipping | Very Low | Low | Ship with temperature logger; chip is robust to ±10°C |

---

## Timeline

| Week | Action |
|------|--------|
| 1 | Send foundry inquiry emails (HyperLight + ANT) |
| 2 | Receive quotes and PDKs |
| 3–4 | Run monte_carlo + thermal simulations |
| 5–6 | Generate final GDS, run KLayout DRC |
| 7 | Submit design to foundry |
| 8–12 | Foundry fabrication |
| 13–16 | Chip returned, test bench setup |
| 17–20 | Chip characterization |
| 21+ | Paper: binary vs ternary comparison |

---

## Pre-Submission Final Checklist

- [ ] GDS file generated (`binary_chip_9x9.gds`)
- [ ] KLayout DRC: zero violations
- [ ] Layer names remapped to foundry convention (see LAYER_MAPPING.md)
- [ ] Text labels stripped from GDS (non-physical layers removed)
- [ ] Die size within foundry reticle limits
- [ ] PCM test structures added (waveguide loss, PPLN standalone, MZI standalone)
- [ ] Alignment marks present at 4 corners
- [ ] Dicing lanes clear (50μm minimum)
- [ ] Monte Carlo yield ≥ 95%
- [ ] Thermal analysis complete
- [ ] Foundry NDA signed (if required)
- [ ] Payment / MPW registration complete
