# Functional Test Plan — Binary Optical Chip 9×9

**Version:** 1.0
**Last updated:** 2026-02-27

---

## Overview

This document defines the step-by-step post-fabrication test procedure for the binary optical chip. Three test levels build confidence progressively from single-PE verification to full 9×9 array function.

A technician with the test bench described in TEST_BENCH_DESIGN.md should be able to follow this document independently and verify chip functionality.

---

## Prerequisites

Before testing, complete:
1. Die attach and wire bonding per PACKAGING_SPEC.md
2. Fiber array alignment (target: <1 dB coupling per channel)
3. PCB assembly (TIA, DAC, ADC)
4. Software: run `simulate_binary_9x9.py` to get expected outputs for all test patterns

---

## Calibration Procedure (Before Level 1 Tests)

### Cal-1: Laser Power Baseline

1. Set all 18 MZI encoders to V=0 (bit 0, 1310nm)
2. Inject 1310nm laser at 0 dBm into activation channel 0
3. Measure transmission at output channel 0 (should see 1310nm, no 775nm)
4. Record: T_baseline_dB = measured transmission
5. Repeat for all 9 channels

**Expected:** T_baseline ≈ −3 to −8 dB (edge coupling + waveguide propagation)
**Flag for investigation if:** T_baseline < −15 dB (possible fiber misalignment or waveguide defect)

### Cal-2: MZI Vπ Characterization

1. Inject 1310nm + 1550nm combined into activation channel 0 (via 3dB coupler)
2. Sweep MZI voltage from 0 to 5V
3. Monitor output at 1310nm and 1550nm bandpass separately (or use OSA)
4. Locate Vπ where 1310nm minimum and 1550nm maximum
5. Record Vπ for each of the 18 MZI channels

**Expected:** Vπ ≈ 1.5–3.0V per channel
**Flag if:** Vπ > 5V (possible electrode damage or bond failure)

### Cal-3: Detector Dark Current Baseline

1. Block all laser inputs
2. Apply detector bias voltage (2V reverse)
3. Measure each detector output via TIA
4. Record dark current baseline: I_dark per channel

**Expected:** I_dark < 1 μA per channel
**Flag if:** I_dark > 10 μA (possible detector damage or leakage)

---

## Level 1: Single PE Test

**Purpose:** Verify that one PE correctly implements binary AND using SFG physics.
**Expected duration:** 30 minutes

### Test L1-1: AND Truth Table — PE[4, 4]

Use PE at row 4, column 4 (center of array).

Setup:
- Activate only row 4 (all other rows: bit 0, 1310nm)
- Activate only column 4 weight (all other columns: bit 0, 1310nm)
- Monitor output detector column 4

| Step | Act row 4 | Wt col 4 | Expected SFG | Expected Det 4 | Pass Threshold |
|------|-----------|----------|-------------|----------------|----------------|
| 1 | 0 (1310nm) | 0 (1310nm) | 655nm (rejected) | 0 | I < 0.3 μA |
| 2 | 1 (1550nm) | 0 (1310nm) | 711nm (rejected) | 0 | I < 0.3 μA |
| 3 | 0 (1310nm) | 1 (1550nm) | 711nm (rejected) | 0 | I < 0.3 μA |
| 4 | **1 (1550nm)** | **1 (1550nm)** | **775nm (detected)** | **1** | **I > 0.5 μA** |

**Pass criteria:** Step 4 produces I > 0.5 μA AND steps 1-3 produce I < 0.3 μA.

**Diagnosis if step 4 fails (no 775nm):**
- [ ] Verify both MZI_ACT_4 and MZI_WT_4 are at Vπ (1550nm selected)
- [ ] Verify laser power > 1 mW at input facets
- [ ] Check PPLN efficiency: scan temperature ±5°C to find phase-match point
- [ ] Check edge coupling: reoptimize fiber array position

**Diagnosis if steps 1-3 show false positive (775nm appears):**
- [ ] Check for crosstalk between adjacent channels
- [ ] Verify WDM coupler rejection (should reject 711nm/655nm)
- [ ] Check detector leakage current (Cal-3)

---

## Level 2: Single Row Test

**Purpose:** Verify activation propagation through all 9 PEs in row 0.
**Expected duration:** 45 minutes

### Test L2-1: Row 0 Sweep

Fix activation row 0 = bit 1 (1550nm). Sweep weight pattern column by column.

| Step | Weight Pattern (cols 0-8) | Expected Output | Pass If |
|------|--------------------------|-----------------|---------|
| A | 1,0,0,0,0,0,0,0,0 | 1,0,0,0,0,0,0,0,0 | Only col 0 > 0.5μA |
| B | 0,1,0,0,0,0,0,0,0 | 0,1,0,0,0,0,0,0,0 | Only col 1 > 0.5μA |
| C | 0,0,0,0,1,0,0,0,0 | 0,0,0,0,1,0,0,0,0 | Only col 4 > 0.5μA |
| D | 0,0,0,0,0,0,0,0,1 | 0,0,0,0,0,0,0,0,1 | Only col 8 > 0.5μA |
| E | 1,1,1,1,1,1,1,1,1 | 1,1,1,1,1,1,1,1,1 | All cols > 0.5μA |
| F | 0,0,0,0,0,0,0,0,0 | 0,0,0,0,0,0,0,0,0 | All cols < 0.3μA |

**Key test:** Step D (col 8) verifies that the activation signal survives 9 PE crossings with sufficient power for SFG at the last PE. This validates the 18.9 dB loss budget.

**Pass criteria:** All 6 patterns correct.

### Test L2-2: Loss Measurement

During step D above, measure:
- Activation power at chip input: P_in
- 775nm SFG power at column 8 output: P_sfg

Calculate: insertion loss = P_in - P_sfg - 10*log10(SFG_efficiency)
Expected: ≤12 dB total insertion loss at PE[0,8]

---

## Level 3: Full 9×9 Array Test

**Purpose:** Verify complete 9×9 binary systolic array computes correctly.
**Expected duration:** 2 hours

Run all 9 test patterns from `simulate_binary_9x9.py`. Compare detector outputs to expected values.

### Test L3-1: Identity Matrix

Input: x = [1,0,1,0,1,0,1,0,1]
Weight: W = identity matrix (W[i][j] = 1 if i==j else 0)
Expected output: y = [1,0,1,0,1,0,1,0,1]

| Col | Expected | Det Current | Pass (>0.5μA or <0.3μA) |
|-----|---------|-------------|--------------------------|
| 0 | 1 | measured | >0.5 μA |
| 1 | 0 | measured | <0.3 μA |
| 2 | 1 | measured | >0.5 μA |
| 3 | 0 | measured | <0.3 μA |
| 4 | 1 | measured | >0.5 μA |
| 5 | 0 | measured | <0.3 μA |
| 6 | 1 | measured | >0.5 μA |
| 7 | 0 | measured | <0.3 μA |
| 8 | 1 | measured | >0.5 μA |

### Test L3-2: All-Ones Stress Test

Input: x = all(1), W = all(1)
Expected: y = all(1)

All 9 detectors must exceed 0.5 μA simultaneously.

### Test L3-3: All-Zeros Baseline

Input: x = all(0), W = all(0)
Expected: y = all(0)

All 9 detectors must stay below 0.3 μA.

### Test L3-4: Single Nonzero (Isolation)

Input: x = all(1), W = all(0) except W[4][4]=1
Expected: y = [0,0,0,0,1,0,0,0,0]

Only column 4 should light up.

### Test L3-5: Mixed Pattern

Input: x = [1,0,1,0,0,0,0,0,0]
W[0:3][0:3] = [[1,0,1],[0,1,0],[1,0,1]], rest = 0
Expected: y = [1,0,1,0,0,0,0,0,0]

### Tests L3-6 through L3-9

Run remaining test patterns from `simulate_binary_9x9.py` output.

---

## Pass/Fail Criteria Summary

| Level | Tests | Pass Threshold | Fail Action |
|-------|-------|---------------|-------------|
| Cal | 3 calibrations | All within expected | Re-align fiber or check bonds |
| L1 | AND truth table | 4/4 combinations correct | Check PPLN, MZI, laser |
| L2 | Row sweep | 6/6 patterns correct | Check propagation loss, row 0 path |
| L3 | Full 9×9 | 9/9 test patterns correct | Analyze per-column failure pattern |

**Chip grade:**
- All L3 tests pass → **Grade A** (full function)
- L1+L2 pass, some L3 fail → **Grade B** (partial — diagnose faulty columns)
- L1 fails → **Grade F** (PPLN or MZI issue — return to foundry)

---

## Failure Diagnosis Flowchart

```
Test fails?
│
├── Level 1 fails (single PE no 775nm)
│   ├── Check: laser power at input >1mW?  NO → adjust fiber alignment
│   ├── Check: MZI at Vπ (1550nm)?        NO → recalibrate Vπ
│   ├── Check: detector dark current?     HIGH → check detector bonding
│   └── Check: 775nm filter in place?     NO → add 800nm shortpass filter
│
├── Level 2 fails (activation doesn't reach last PE)
│   ├── Check: insertion loss per PE      HIGH → check waveguide continuity
│   └── Check: coupling loss             HIGH → re-optimize fiber alignment
│
└── Level 3 fails (some columns wrong)
    ├── Check: which columns fail?
    │   ├── Consistent pattern → specific PE defect
    │   └── Random pattern → possible crosstalk issue
    ├── Run L1 on each failing column individually
    └── Check: weight bus continuity for failing columns
```

---

## Data Recording Template

For each test run, record:
- Date/time
- Chip ID (die number)
- Temperature (°C)
- Laser power levels (mW per channel)
- Vπ measured for each MZI channel
- Detector currents for each output column
- Pass/fail per test
- Notes on any anomalies

Compare measured vs. simulated values from `simulate_binary_9x9.py`.
