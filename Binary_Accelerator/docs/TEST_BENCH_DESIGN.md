# Test Bench Design — Binary Optical Chip 9×9

**Version:** 1.0
**Last updated:** 2026-02-27

---

## Overview

Four budget tiers for testing the binary optical chip after fabrication. Binary chip is simpler to test than ternary: only 2 input wavelengths and 1 output wavelength band (775nm) vs ternary's 3+3.

---

## Tier 1 — Minimum Viable ($1,800–$4,000)

**Goal:** Prove the AND gate physics work. Single PE test only.

| Item | Quantity | Approx Cost | Description |
|------|---------|-------------|-------------|
| 1310nm DFB laser (fiber-pigtailed) | 1 | $300–$600 | Thorlabs S3FC1310 or Eblana |
| 1550nm DFB laser (fiber-pigtailed) | 1 | $300–$600 | Thorlabs S3FC1550 |
| 3dB fiber coupler (1310/1550nm) | 2 | $50 each | WDM combiner |
| Lensed fiber (SMF-28, 2.5μm spot) | 2 | $400 each | OZ Optics |
| Manual 5-axis fiber alignment stage | 2 | $800 each | Thorlabs NanoMax or Melles Griot |
| 775nm bandpass filter | 1 | $200 | Semrock FF01-775/46 |
| Silicon photodetector (Si, 400-1000nm) | 1 | $150 | Thorlabs FDS100 |
| Transimpedance amplifier | 1 | $100–$300 | OPA657 circuit |
| Oscilloscope (100MHz) | 1 | borrow | |
| Voltage source (0–5V) | 1 | $200 | Keithley 2401 (borrow) |
| Chip mounting / fiber holder jig | 1 | $100 | Custom machined or 3D printed |
| **Total** | | **~$3,200** | |

**What you can test:**
- Level 1 tests (single PE AND truth table)
- Verify SFG 775nm exists
- Estimate conversion efficiency
- Basic loss budget measurement

**What you cannot test:**
- Full 9×9 array
- All 18 MZI channels simultaneously
- High-speed operation

---

## Tier 2 — Complete Bench ($5,000–$12,000)

**Goal:** Full 9×9 array characterization at low speed (< 1 MHz).

| Item | Quantity | Approx Cost | Description |
|------|---------|-------------|-------------|
| 1310nm DFB laser, PM fiber | 1 | $800 | Thorlabs S3FC1310P |
| 1550nm DFB laser, PM fiber | 1 | $800 | Thorlabs S3FC1550P |
| 1×9 fiber splitter (1310nm) | 1 | $300 | Tapered fiber splitter |
| 1×9 fiber splitter (1550nm) | 1 | $300 | |
| 9×2 WDM fiber coupler array | 1 | $500 | Custom fiber array |
| 9-channel lensed fiber array | 2 | $1,200 each | Nanonics or OZ Optics |
| 6-axis motorized alignment stages | 2 | $2,000 each | Thorlabs MAX601D |
| 18-channel DAC (16-bit, 0–5V) | 1 | $300 | Texas Instruments DAC8830 |
| FPGA eval board (Xilinx Arty A7) | 1 | $200 | For DAC/ADC control |
| 9× TIA (OPA657 or AD8015) | 9 | $30 each | Transimpedance amplifiers |
| 9-channel ADC (12-bit, 1 MSPS) | 1 | $200 | ADS1299 or similar |
| 775nm bandpass filter array | 1 | $500 | 9-channel fiber filter array |
| Current-limited laser driver (×2) | 2 | $300 each | Thorlabs ITC4020 |
| Temperature controller (for chip) | 1 | $400 | Thorlabs TED200C |
| Optical power meter | 1 | $800 | Thorlabs PM400 + S154C |
| PC with data acquisition software | 1 | own | |
| PCB (custom, 4-layer) | 1 | $500 | OSH Park or PCBWay |
| **Total** | | **~$10,500** | |

**What you can test:**
- All Level 1, 2, 3 tests
- Full 9×9 array function
- All 9 output channels simultaneously
- Steady-state compute verification

**What you cannot test:**
- GHz-speed operation
- Dynamic switching at full rate

---

## Tier 3 — High-Speed Characterization ($12,000–$25,000)

**Goal:** Measure real-time binary computation speed.

Tier 2 equipment PLUS:

| Item | Approx Cost | Description |
|------|-------------|-------------|
| High-speed MZI driver (>1GHz) ×18 | $3,000 | Picosecond Pulse Labs 5510 or custom |
| 775nm avalanche photodetector ×9 | $2,000 | Thorlabs APD410C or Hamamatsu C12703 |
| Real-time oscilloscope (20GHz, 4ch) | $8,000 | Keysight DSOV204A or borrow |
| Bit pattern generator (2.5 Gbps) | $2,000 | Tektronix AWG7000 series |
| Vector network analyzer (10GHz) | $5,000 | Siglent SVA1032X |
| **Additional cost** | **~$20,000** | |
| **Tier 3 total** | **~$30,500** | |

---

## Tier 4 — Full Production Test ($25,000+)

**Goal:** Complete characterization for paper publication.

Tier 3 PLUS:
- Optical spectrum analyzer (OSA) for SFG wavelength verification: ~$15k
- Polarization controller array: ~$2k
- Automated probe station: ~$30k
- Lock-in amplifier for noise floor characterization: ~$5k

---

## Binary vs Ternary Test Bench Cost Comparison

| Component | Binary | Ternary N-Radix | Savings |
|-----------|--------|-----------------|---------|
| Laser sources | 2 | 3 | ~$800 |
| Input fiber arrays | 2 | 2 | same |
| Output wavelength bands | 1 (775nm) | 3 (500-670nm) | ~$1,500 |
| Output demux (AWG vs filter) | Dichroic filter | AWG | ~$3,000 |
| MZI drive channels | 18 (2-state) | 27 (3-state) | ~$500 |
| **Tier 2 total** | **~$10.5k** | **~$15k** | **~$4,500** |

---

## FPGA Firmware Spec

The FPGA on Tier 2+ bench implements:

```
FPGA Block Diagram:
  PC (USB/UART) → FPGA →  DAC (18ch): MZI_ACT[0-8], MZI_WT[0-8]
                       ←  ADC (9ch):  DET[0-8]
                       →  Laser enable (2): EN_1310, EN_1550
```

**Software interface (Python):**
```python
from binary_ioc import BinaryIOC

ioc = BinaryIOC(port="/dev/ttyUSB0")
ioc.set_activation([1,0,1,0,1,0,1,0,1])  # bit vector
ioc.set_weights([[1,0,...]])               # 9×9 matrix
output = ioc.read_outputs()               # returns [0,1,...] list of 9 bits
```

**Calibration storage:** FPGA stores Vπ for each of 18 MZI channels in flash (update after each Cal-2 run).

---

## Setup Procedure

1. Mount chip on AlN submount, cure UV epoxy
2. Attach submount to PCB
3. Wire bond: activations (left edge) → DAC, outputs (right edge) → TIA/ADC
4. Align input fiber array 1 (activations): optimize coupling on 1310nm
5. Align input fiber array 2 (weights): optimize coupling on 1310nm
6. Align output fiber array: optimize 775nm collection
7. Run Cal-1 through Cal-3
8. Run Level 1 tests
9. Run Level 2-3 tests if L1 passes

**Alignment tip:** UV epoxy has working time ~10 minutes. Complete alignment before applying epoxy. Use active feedback (monitor TIA output while adjusting fiber position). Target: <1 dB coupling loss per channel.
