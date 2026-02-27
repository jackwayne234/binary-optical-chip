# Monte Carlo Process Variation Analysis — Binary Optical Chip 9×9

**Status:** PENDING (run `monte_carlo_binary_9x9.py` to populate results)
**Script:** `Binary_Accelerator/simulations/monte_carlo_binary_9x9.py`
**Last updated:** 2026-02-27

---

## Overview

This document summarizes the Monte Carlo yield analysis for the binary optical chip. Process variations from real TFLN foundry fabrication are modeled as Gaussian distributions. We run 10,000 virtual chip instances and count what fraction pass all design validation checks.

---

## Why Binary Expects Higher Yield Than Ternary

The ternary N-Radix chip achieved 99.82% yield across 10,000 trials. The binary chip is expected to achieve even higher yield for three reasons:

| Factor | Ternary N-Radix | Binary | Impact |
|--------|----------------|--------|--------|
| QPM conditions needed | 6 | **1** | Single PPLN period — one thing to get right |
| Ring resonators | Yes (critical) | **None** | Ring tuning was limiting factor in ternary |
| Min WDM separation | ~20 nm | **535 nm** | Binary separations are trivially large |
| SFG combinations | 9 (need 3 right) | **4 (need 1 right)** | Fewer failure modes |

The ternary Monte Carlo showed ring resonator tuning was the dominant yield limiter. Binary has no ring resonators. The expected yield improvement is significant.

**Expected binary yield: >99.5%**

---

## Parameter Variation Model

Based on DRC_RULES.md tolerances and TFLN foundry literature.

| Parameter | Nominal | σ (1σ) | Distribution | Source |
|-----------|---------|--------|-------------|--------|
| Waveguide width (nm) | 500 | 7 | Gaussian | DRC WG.W.1: ±20nm at 3σ |
| Etch depth (nm) | 400 | 3.3 | Gaussian | DRC §10.1: ±10nm at 3σ |
| PPLN period (μm) | 19.1 | 0.067 | Gaussian | Foundry spec: ±0.2μm at 3σ |
| Waveguide loss (dB/cm) | 2.0 | 0.5 | Gaussian | TFLN literature range |
| Edge coupling loss (dB) | 1.0 | 0.3 | Gaussian | Lensed fiber alignment |
| SFG conversion (frac) | 0.10 | 0.01 | Gaussian | ±30% relative at 3σ |

---

## Validation Checks

5 checks per trial. All must pass for the chip to be counted as functional:

### Check 1: Loss Budget

**Question:** Does the 775nm SFG signal at the worst-case path (PE[0,8]) reach the detector with positive margin?

**Model:**
- Sum all losses along the worst-case path (edge coupling, waveguide propagation, 9 PE crossings, output routing)
- Apply PPLN efficiency including sinc² phase-mismatch penalty from period variation
- Compare to detector sensitivity threshold (−30 dBm)

**Nominal margin:** 18.9 dB
**Expected yield:** >99% (large nominal margin)

---

### Check 2: PPLN Phase Mismatch

**Question:** Does the PPLN period variation reduce SFG conversion below the minimum threshold?

**Model:**
- For each sampled period Λ, compute sinc²(ΔφL/2π) penalty
- Δφ = (2π/Λ_nominal − 2π/Λ_actual) × PPLN_length
- Pass if effective conversion ≥ 3% (threshold: 30% of nominal 10%)

**Why this is easy for binary:** Only one QPM condition to maintain.
For ternary: need 6 QPM conditions simultaneously, each with its own period.

**Expected yield:** >99.9% (±0.2μm period variation produces small sinc² penalty)

---

### Check 3: WDM Wavelength Separation

**Question:** Are 775nm, 1310nm, and 1550nm still adequately separated for demultiplexing despite waveguide width variation?

**Model:**
- Waveguide width variation → effective index shift → SFG wavelength drift
- For ±20nm width variation: effective index shifts ~0.1%, SFG wavelength shifts ~±0.8nm
- Pass if min(|775−1310|, |775−1550|) > 10nm

**This check almost never fails:** Binary separations are 535nm and 775nm. Even a 100nm SFG wavelength shift would still leave huge margins.

**Expected yield:** ~100% (trivially large separations)

---

### Check 4: Timing Skew

**Question:** Does waveguide width variation cause enough effective index drift to misalign photon arrival timing?

**Model:**
- Width variation → Δn_eff → Δt = L × Δn_eff / c
- Longest path L ≈ 800μm
- Threshold: 0.5 ps

**Expected yield:** >99.9% (small timing shifts at these path lengths)

---

### Check 5: Detector Current

**Question:** Does the photocurrent exceed the 0.5 μA detection threshold?

**Model:**
- Combines Check 1 (power margin) with detector responsivity variation
- Pass if I_ph = P_sfg × R_det > 0.5 μA

**Expected yield:** Same as Check 1 (loss budget is the binding constraint)

---

## Results

**Status:** PENDING — run `monte_carlo_binary_9x9.py` to generate results.

```bash
cd Binary_Accelerator/simulations/
python3 monte_carlo_binary_9x9.py
```

Expected output format:
```
╔════════════════════════════════════════════════════════════════════╗
║  MONTE CARLO RESULTS — BINARY OPTICAL CHIP 9×9                  ║
╠════════════════════════════════════════════════════════════════════╣
║  Trials:       10,000                                            ║
║  Passing:       X,XXX                                            ║
║  YIELD:          XX.XX%                                          ║
╠════════════════════════════════════════════════════════════════════╣
║  Per-check yields:                                               ║
║    loss_budget             XX.XX%  ████████████████████         ║
║    ppln_efficiency         XX.XX%  ████████████████████         ║
║    wavelength_sep         ~100.0%  ████████████████████         ║
║    timing                  XX.XX%  ████████████████████         ║
║    detector                XX.XX%  ████████████████████         ║
```

Results will be updated here after running.

---

## Sensitivity Analysis

The yield-limiting factors in order of importance (predicted):

1. **Loss budget** — waveguide loss variation × path length is largest contributor
2. **PPLN efficiency** — period variation reduces conversion, but 18.9 dB nominal margin absorbs most of it
3. **Timing** — minimal effect at these path lengths
4. **WDM separation** — essentially zero sensitivity (535nm gap)

The most effective way to improve yield if it falls below 95%:
1. Increase laser power (more headroom in loss budget)
2. Increase PPLN length (higher conversion efficiency baseline)
3. Use lower-loss waveguide process (2.0 → 1.0 dB/cm)

---

## Comparison: Binary vs Ternary N-Radix

| Metric | Binary | Ternary N-Radix |
|--------|--------|-----------------|
| Monte Carlo trials | 10,000 | 10,000 |
| Ternary yield | — | **99.82%** |
| Expected binary yield | **>99.5%** | — |
| Yield-limiting factor | Loss budget | Ring tuning |
| Ring resonator concern | **None** | Critical |
| QPM concerns | 1 period | 6 periods |
| WDM concern | **None** (~535nm gap) | Significant (~20nm gap) |
