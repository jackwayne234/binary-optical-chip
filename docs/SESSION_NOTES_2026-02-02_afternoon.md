# Session Notes - February 2, 2026 (Afternoon Session)

## Summary

Extended the 81-trit ternary optical processor with **5-detector carry propagation**, **simplified AWG-based output**, **three arithmetic operations** (add/sub/mul), and **MZI selector option**.

---

## What We Accomplished

### 1. Added 5-Detector Output Stage with Carry Propagation

**Problem:** Original 3-detector design couldn't detect overflow/carry results (-2 and +2).

**Solution:** Extended output stage to detect all 5 possible arithmetic results:

| Detector | Wavelength | Result | Function |
|----------|------------|--------|----------|
| DET_-2 | 0.775 μm | -2 | Borrow (carry out) |
| DET_-1 | 0.681 μm | -1 | Normal result |
| DET_0 | 0.608 μm | 0 | Normal result |
| DET_+1 | 0.549 μm | +1 | Normal result |
| DET_+2 | 0.500 μm | +2 | Carry (carry out) |

**Carry logic:**
- Result -2: Output digit = +1, carry = -1 (borrow to next position)
- Result +2: Output digit = -1, carry = +1 (carry to next position)

### 2. Simplified Output Architecture (Major Optimization)

**Problem:** Original output stage used 5 ring resonator filters + splitter per ALU = 891 total rings for 81-trit chip.

**Solution:** Replace ring filters with single 5-channel AWG demultiplexer per ALU.

| Architecture | Components per ALU | Total Rings (81 ALUs) |
|--------------|-------------------|----------------------|
| Original (ring filters) | 1 splitter + 5 rings + 5 detectors = 11 | 891 |
| **Simplified (AWG)** | 1 AWG + 5 detectors = 6 | **486** |

**Savings:** 405 ring resonators eliminated (45% component reduction)

### 3. Electronic Carry Chain

Added GPIO-based carry propagation for multi-trit arithmetic:

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

### 4. Three Arithmetic Operations

| Operation | Mixer | Physics | Length | GDS Layer |
|-----------|-------|---------|--------|-----------|
| **Addition** | SFG | χ² sum-frequency | 20 μm | (2, 0) |
| **Subtraction** | DFG | χ² difference-frequency | 25 μm | (4, 0) |
| **Multiplication** | Kerr | χ³ four-wave mixing | 30 μm | (7, 0) |

**Multiplication truth table (balanced ternary):**
| A | B | A × B |
|---|---|-------|
| -1 | -1 | +1 |
| -1 | +1 | -1 |
| +1 | +1 | +1 |
| 0 | any | 0 |

### 5. MZI Selector Option

Added Mach-Zehnder Interferometer switches as alternative to ring resonators:

| Selector | Extinction | Fab Tolerance | Size | Control |
|----------|------------|---------------|------|---------|
| Ring (default) | ~20 dB | Sensitive | Compact | Wavelength-tuned |
| **MZI** | >30 dB | Tolerant | Larger | Voltage (heater) |

New components:
- `mzi_switch()` - Basic MZI with heater electrode
- `wavelength_selector_mzi()` - MZI-based wavelength selector

### 6. Updated Foundry Inquiry Email

Updated `Phase3_Chip_Simulation/foundry_inquiry_email.txt` with:
- v1.2 simplified architecture specs
- Component counts (486 rings, 243 AWGs, 405 detectors)
- Optimized wavelengths
- Target foundries with specialties

---

## Generated GDS Files

| File | Size | Operation | Selectors | Notes |
|------|------|-----------|-----------|-------|
| `ternary_81trit_simplified.gds` | 3.0 MB | ADD | Ring | **RECOMMENDED** |
| `ternary_81trit_add_mzi.gds` | 5.1 MB | ADD | MZI | Larger, more tolerant |
| `ternary_81trit_sub.gds` | 3.0 MB | SUB | Ring | DFG mixer |
| `ternary_81trit_mul.gds` | 3.0 MB | MUL | Ring | Kerr mixer |
| `ternary_81trit_5det_complete.gds` | 3.2 MB | ADD | Ring | Ring filter output |

---

## Final Chip Specifications

### Architecture
```
Ternary81 Processor
├── 1 Centered Frontend (Kerr clock + Y-junction)
├── 81 ALUs, each with:
│   ├── 2 AWG demux (3-ch) - input R/G/B separation
│   ├── 6 selectors (ring or MZI) - wavelength gating
│   ├── 2 wavelength combiners
│   ├── 1 MMI 2×2 - operand combiner
│   ├── 1 mixer (SFG/DFG/Kerr) - arithmetic operation
│   ├── 1 AWG demux (5-ch) - output separation
│   ├── 5 photodetectors (DET_-2 to DET_+2)
│   └── 3 carry pads (CARRY_IN, CARRY_OUT_POS, CARRY_OUT_NEG)
└── Carry chain wiring labels
```

### Component Counts
| Component | Count |
|-----------|-------|
| Ring resonators | 486 (or 0 if MZI) |
| MZI switches | 0 (or 486 if MZI) |
| AWG demux | 243 |
| Mixers | 81 |
| Photodetectors | 405 |
| MMI couplers | ~500 |

### GDS Layers
| Layer | Purpose |
|-------|---------|
| (1, 0) | Waveguide core |
| (2, 0) | SFG mixer (addition) |
| (3, 0) | Photodetector |
| (4, 0) | DFG mixer (subtraction) |
| (5, 0) | Kerr resonator |
| (6, 0) | AWG body |
| (7, 0) | MUL mixer (multiplication) |
| (10, 0) | MZI heater/electrode |
| (100, 0) | Labels |

---

## Git Commits This Session

1. `8d382a0` - Update design summary with optimized wavelengths (v1.1)
2. `0089463` - Add 5-detector output stage with carry propagation
3. `6f01ec5` - Add simplified output stage using AWG demux
4. `3ae6727` - Update design summary for simplified AWG architecture (v1.2)
5. `57045b8` - Add afternoon session notes
6. `5291a37` - Add carry chain, sub/mul operations, and MZI selectors
7. `b3de892` - Update design summary to v1.3 with full ALU capabilities

---

## Files Modified

| File | Changes |
|------|---------|
| `Research/programs/ternary_chip_generator.py` | AWG 5-ch, carry chain, DFG/MUL mixers, MZI switches |
| `Phase3_Chip_Simulation/DESIGN_SUMMARY.md` | v1.3 with full capabilities |
| `Phase3_Chip_Simulation/foundry_inquiry_email.txt` | Updated specs and foundry list |

---

## Usage Examples

```python
# Generate 81-trit ADD chip with ring selectors (default, recommended)
chip = generate_complete_81_trit(
    name='T81_ADD',
    operation='add',
    selector_type='ring',
    simplified_output=True
)

# Generate 81-trit SUB chip
chip = generate_complete_81_trit(
    name='T81_SUB',
    operation='sub'
)

# Generate 81-trit MUL chip with MZI selectors
chip = generate_complete_81_trit(
    name='T81_MUL_MZI',
    operation='mul',
    selector_type='mzi'
)

# Generate single ALU for testing
alu = generate_complete_alu(
    name='TestALU',
    operation='add',
    selector_type='ring',
    simplified_output=True
)
```

---

## Commands Reference

```bash
# Activate environment
source bin/activate_env.sh

# Run interactive chip generator
python3 Research/programs/ternary_chip_generator.py

# Open chips in KLayout
klayout Research/data/gds/ternary_81trit_simplified.gds  # ADD + Ring
klayout Research/data/gds/ternary_81trit_add_mzi.gds     # ADD + MZI
klayout Research/data/gds/ternary_81trit_sub.gds         # SUB
klayout Research/data/gds/ternary_81trit_mul.gds         # MUL

# Check design summary
cat Phase3_Chip_Simulation/DESIGN_SUMMARY.md
```

---

## Next Steps (For Future Sessions)

1. **Division operation** - Add DFG-based division (inverse of multiplication)
2. **Multi-chip system** - Connect multiple 81-trit chips for larger word sizes
3. **Foundry submission** - Send inquiry emails to target foundries
4. **Firmware development** - ESP32/FPGA code for carry propagation and control
5. **Power budget analysis** - Calculate optical loss through full signal path
6. **Timing analysis** - Propagation delay through carry chain

---

## Key Design Decisions Made

1. **5 detectors** - Enables full carry propagation for multi-trit arithmetic
2. **AWG demux for output** - Simpler than ring filters, same functionality
3. **Electronic carry** - Simpler than optical feedback, firmware handles propagation
4. **Three operations** - SFG (add), DFG (sub), Kerr (mul) cover basic arithmetic
5. **MZI option** - Better for fabs with less precise lithography

---

*Session with Claude Code - Opus 4.5*
