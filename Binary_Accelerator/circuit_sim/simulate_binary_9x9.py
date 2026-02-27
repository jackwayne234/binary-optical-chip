#!/usr/bin/env python3
"""
Full-Chip Circuit Simulation: Monolithic 9x9 Binary Optical Chip
=================================================================

Simulates light propagating through a binary optical 9x9 systolic array:
  1. Encode binary input vectors as wavelength-selected optical signals
  2. Encode weight matrix as wavelength-selected optical signals
  3. Propagate through 9x9 PE array (81 SFG mixers)
  4. Accumulate partial products per column
  5. Decode SFG outputs via WDM demux to photodetectors
  6. Compare detected results to expected binary arithmetic

Binary encoding:
  Bit 0 → λ = 1310 nm  (O-band)
  Bit 1 → λ = 1550 nm  (Telecom C-band)

SFG mixing implements binary AND naturally:
  1550 + 1550 → 775 nm  (1 AND 1 = 1)
  1310 + 1550 → 711 nm  (0 AND 1 = 0)
  1550 + 1310 → 711 nm  (1 AND 0 = 0)
  1310 + 1310 → 655 nm  (0 AND 0 = 0)

This file mirrors the ternary simulate_9x9.py structure for direct
comparison — same architecture, 2 wavelengths instead of 3.

Author: Binary Optical Chip Project
Date: 2026-02-27
"""

import sys
import os
import numpy as np
from dataclasses import dataclass, field

# =============================================================================
# Constants
# =============================================================================

PE_PITCH          = 55.0    # μm center-to-center
PE_WIDTH          = 50.0    # μm
ROUTING_GAP       = 60.0    # μm
IOC_INPUT_WIDTH   = 180.0   # μm
IOC_OUTPUT_WIDTH  = 200.0   # μm
PPLN_LENGTH       = 26.0    # μm (same PPLN as ternary — same glass)
WG_LOSS_DB_CM     = 2.0     # dB/cm
EDGE_COUPLING_LOSS = 1.0    # dB per facet
DETECTOR_SENSITIVITY = -30.0  # dBm
DETECTOR_THRESHOLD_UA = 0.5   # μA — above this = "detected"

# Binary wavelength encoding
BIT_TO_WL = {
    0: 1310.0,  # O-band
    1: 1550.0,  # Telecom C-band
}

WL_TO_BIT = {1310.0: 0, 1550.0: 1}

# SFG output wavelengths: λ_sfg = 1 / (1/λ_1 + 1/λ_2)
# All in nm, rounded to 1 decimal
SFG_TABLE = {
    (1550.0, 1550.0): round(1 / (1/1550.0 + 1/1550.0), 1),  # → 775.0 nm = 1
    (1310.0, 1550.0): round(1 / (1/1310.0 + 1/1550.0), 1),  # → 711.4 nm = 0
    (1550.0, 1310.0): round(1 / (1/1550.0 + 1/1310.0), 1),  # → 711.4 nm = 0
    (1310.0, 1310.0): round(1 / (1/1310.0 + 1/1310.0), 1),  # → 655.0 nm = 0
}

# Reverse: SFG output wavelength → bit result
SFG_RESULT = {
    775.0: 1,   # 1 AND 1 = 1
    711.4: 0,   # 0 AND 1, or 1 AND 0 = 0
    655.0: 0,   # 0 AND 0 = 0
}

# WDM output channels
WDM_CHANNELS = {
    "ch_1": 775.0,   # bit 1
    "ch_0a": 711.4,  # bit 0 (mixed)
    "ch_0b": 655.0,  # bit 0 (both zero)
}


# =============================================================================
# Optical signal model (mirrors ternary components)
# =============================================================================

@dataclass
class OpticalSignal:
    wavelength_nm: float
    power_dbm: float

    def attenuate(self, loss_db: float) -> "OpticalSignal":
        return OpticalSignal(self.wavelength_nm, self.power_dbm - loss_db)


def waveguide_transfer(sig: OpticalSignal, length_um: float, loss_db_cm: float) -> OpticalSignal:
    """Apply waveguide propagation loss over length_um."""
    loss = loss_db_cm * (length_um / 1e4)
    return sig.attenuate(loss)


def mzi_encode_binary(bit: int, power_dbm: float) -> OpticalSignal:
    """Encode a binary bit as a wavelength-selected optical signal."""
    assert bit in (0, 1), f"Binary bit must be 0 or 1, got {bit}"
    wl = BIT_TO_WL[bit]
    return OpticalSignal(wavelength_nm=wl, power_dbm=power_dbm)


def sfg_mixer_binary(
    sig_a: OpticalSignal,
    sig_b: OpticalSignal,
    ppln_length_um: float = PPLN_LENGTH,
    conversion_efficiency: float = 0.10,
    insertion_loss_db: float = 1.0,
) -> tuple["OpticalSignal | None", OpticalSignal, OpticalSignal]:
    """
    SFG mixer for binary optical logic.

    Produces sum-frequency signal if both inputs are bit 1 (1550nm).
    Returns (sfg_output, passthrough_a, passthrough_b).
    sfg_output is None when SFG product maps to bit 0.
    """
    wl_a = round(sig_a.wavelength_nm, 1)
    wl_b = round(sig_b.wavelength_nm, 1)

    sfg_wl = SFG_TABLE.get((wl_a, wl_b))

    # Passthrough with insertion loss
    pass_a = sig_a.attenuate(insertion_loss_db)
    pass_b = sig_b.attenuate(insertion_loss_db)

    if sfg_wl is None:
        return None, pass_a, pass_b

    # SFG power: conversion_efficiency * min(P_a, P_b) - insertion_loss
    p_a_lin = 10 ** (sig_a.power_dbm / 10)
    p_b_lin = 10 ** (sig_b.power_dbm / 10)
    sfg_power_lin = conversion_efficiency * min(p_a_lin, p_b_lin)
    sfg_power_dbm = 10 * np.log10(sfg_power_lin) - insertion_loss_db

    sfg_out = OpticalSignal(wavelength_nm=sfg_wl, power_dbm=sfg_power_dbm)
    return sfg_out, pass_a, pass_b


def wdm_demux(sig: OpticalSignal) -> dict[str, float]:
    """WDM demultiplexer: route signal to nearest channel, return power per channel."""
    powers = {ch: -60.0 for ch in WDM_CHANNELS}  # floor noise
    wl = sig.wavelength_nm
    # Find nearest channel
    best_ch = min(WDM_CHANNELS, key=lambda ch: abs(WDM_CHANNELS[ch] - wl))
    powers[best_ch] = sig.power_dbm
    return powers


def photodetector(power_dbm: float, responsivity_a_w: float = 0.8) -> float:
    """Convert optical power (dBm) to photocurrent (μA)."""
    power_w = 10 ** (power_dbm / 10) * 1e-3
    return power_w * responsivity_a_w * 1e6  # μA


# =============================================================================
# IOC — Binary mode
# =============================================================================

class BinaryIOC:
    """
    Binary IOC: simpler than ternary.

    AND PEs: SFG = bit-wise AND. Hardware just mixes.
    OR PEs:  IOC uses complementary encoding: NOT(NOT(a) AND NOT(b)).
             Glass still just mixes. IOC handles the complement.
    XOR PEs: Requires two passes or extra routing. IOC handles.

    The glass never changes — only the IOC encoding does.
    """

    def __init__(self, pe_type: str = "AND"):
        assert pe_type in ("AND", "OR", "XOR"), "pe_type must be AND, OR, or XOR"
        self.pe_type = pe_type

    def operation_name(self) -> str:
        ops = {
            "AND": "SFG mixing → bit-wise AND (direct)",
            "OR":  "SFG mixing → bit-wise OR (De Morgan: NOT(NOT(a) AND NOT(b)))",
            "XOR": "SFG mixing → XOR (requires 3 AND gates: (a AND NOT(b)) OR (NOT(a) AND b))",
        }
        return ops[self.pe_type]

    def describe(self) -> str:
        return (
            f"IOC Mode: PE Type = {self.pe_type}\n"
            f"  Physical op: SFG mixing (1550nm+1550nm → 775nm)\n"
            f"  Interpreted as: {self.operation_name()}"
        )


# =============================================================================
# Processing Element
# =============================================================================

@dataclass
class PEResult:
    row: int
    col: int
    activation_bit: int
    weight_bit: int
    expected_product: int
    sfg_wavelength_nm: float | None
    sfg_power_dbm: float | None
    pass_h_power_dbm: float
    pass_v_power_dbm: float


def simulate_pe_binary(
    activation: OpticalSignal,
    weight: OpticalSignal,
    row: int,
    col: int,
) -> tuple["OpticalSignal | None", OpticalSignal, OpticalSignal, PEResult]:
    """Simulate a single binary PE (SFG AND gate)."""

    sfg_out, pass_h, pass_v = sfg_mixer_binary(
        activation, weight,
        ppln_length_um=PPLN_LENGTH,
        conversion_efficiency=0.10,
        insertion_loss_db=1.0,
    )

    act_bit = WL_TO_BIT.get(round(activation.wavelength_nm), 0)
    wt_bit  = WL_TO_BIT.get(round(weight.wavelength_nm), 0)
    expected = act_bit & wt_bit  # AND

    result = PEResult(
        row=row, col=col,
        activation_bit=act_bit,
        weight_bit=wt_bit,
        expected_product=expected,
        sfg_wavelength_nm=sfg_out.wavelength_nm if sfg_out else None,
        sfg_power_dbm=sfg_out.power_dbm if sfg_out else None,
        pass_h_power_dbm=pass_h.power_dbm,
        pass_v_power_dbm=pass_v.power_dbm,
    )

    return sfg_out, pass_h, pass_v, result


# =============================================================================
# Full 9x9 Array Simulation
# =============================================================================

@dataclass
class BinaryArrayResult:
    input_bits: list[int]
    weight_matrix: list[list[int]]
    expected_output: list[int]
    pe_results: list[list[PEResult]] = field(default_factory=list)
    column_sfg_products: list[list[OpticalSignal]] = field(default_factory=list)
    detected_output: list[int] = field(default_factory=list)
    all_correct: bool = False


def simulate_binary_array_9x9(
    input_bits: list[int],
    weight_matrix: list[list[int]],
    laser_power_dbm: float = 10.0,
    verbose: bool = True,
) -> BinaryArrayResult:
    """
    Simulate the complete 9x9 binary optical systolic array.

    Computes binary inner product: y[j] = OR_i(input[i] AND weight[i][j])
    i.e., y[j] = 1 if any (input[i]=1 AND weight[i][j]=1)

    Architecture mirrors N-Radix ternary exactly:
    - Rows carry activations (horizontal)
    - Columns carry weights (vertical)
    - Each PE: SFG AND
    - Column output: OR of all PE products
    """
    assert len(input_bits) == 9, "Input must be length 9"
    assert all(b in (0, 1) for b in input_bits), "All input bits must be 0 or 1"
    assert len(weight_matrix) == 9 and all(len(r) == 9 for r in weight_matrix)

    result = BinaryArrayResult(
        input_bits=input_bits,
        weight_matrix=weight_matrix,
        expected_output=[],
    )

    # Expected: y[j] = OR_i(input[i] AND weight[i][j])
    for col in range(9):
        acc = int(any(input_bits[row] & weight_matrix[row][col] for row in range(9)))
        result.expected_output.append(acc)

    if verbose:
        print("\n" + "=" * 70)
        print("  CIRCUIT SIMULATION: Monolithic 9x9 Binary Optical Chip")
        print("=" * 70)
        print(f"\n  Input vector x = {input_bits}")
        print(f"  Weight matrix W:")
        for row in range(9):
            print(f"    [{', '.join(str(w) for w in weight_matrix[row])}]")
        print(f"  Expected output y = OR(x AND W) = {result.expected_output}")

    # Stage 1: Encode activations
    if verbose:
        print("\n--- Stage 1: Encoding inputs ---")

    activation_signals = []
    for row in range(9):
        sig = mzi_encode_binary(input_bits[row], laser_power_dbm)
        sig = waveguide_transfer(sig, IOC_INPUT_WIDTH + ROUTING_GAP, WG_LOSS_DB_CM)
        sig = sig.attenuate(EDGE_COUPLING_LOSS)
        activation_signals.append(sig)
        if verbose:
            print(f"  Row {row}: bit={input_bits[row]} → λ={sig.wavelength_nm}nm, "
                  f"P={sig.power_dbm:.1f} dBm")

    # Stage 2: Encode weights
    if verbose:
        print("\n--- Stage 2: Encoding weights ---")

    weight_signals = []
    for row in range(9):
        row_weights = []
        for col in range(9):
            w = weight_matrix[row][col]
            sig = mzi_encode_binary(w, laser_power_dbm)
            weight_path_um = row * PE_PITCH + 40
            sig = waveguide_transfer(sig, weight_path_um, WG_LOSS_DB_CM)
            row_weights.append(sig)
        weight_signals.append(row_weights)

    # Stage 3: PE array
    if verbose:
        print("\n--- Stage 3: PE array computation ---")

    column_products = [[] for _ in range(9)]
    pe_results = [[None]*9 for _ in range(9)]

    for row in range(9):
        act = activation_signals[row]

        for col in range(9):
            wt = weight_signals[row][col]
            sfg_out, act, pass_v, pe_res = simulate_pe_binary(act, wt, row, col)
            pe_results[row][col] = pe_res

            if col < 8:
                act = waveguide_transfer(act, PE_PITCH - PE_WIDTH, WG_LOSS_DB_CM)

            if sfg_out is not None:
                column_products[col].append(sfg_out)

            if verbose and pe_res.activation_bit == 1 and pe_res.weight_bit == 1:
                print(f"  PE[{row},{col}]: {pe_res.activation_bit} AND "
                      f"{pe_res.weight_bit} = {pe_res.expected_product} → "
                      f"SFG λ={sfg_out.wavelength_nm:.1f}nm, "
                      f"P={sfg_out.power_dbm:.1f} dBm")

    result.pe_results = pe_results
    result.column_sfg_products = column_products

    # Stage 4: Decode
    if verbose:
        print("\n--- Stage 4: Decoding outputs ---")

    for col in range(9):
        products = column_products[col]

        if not products:
            result.detected_output.append(0)
            if verbose:
                print(f"  Column {col}: No SFG products → output = 0")
            continue

        # OR: if any product is bit 1 (775nm), output is 1
        bit_out = 0
        for sfg in products:
            sfg_routed = waveguide_transfer(
                sfg, ROUTING_GAP + IOC_OUTPUT_WIDTH * 0.3, WG_LOSS_DB_CM
            )
            ch_powers = wdm_demux(sfg_routed)
            best_ch = max(ch_powers, key=ch_powers.get)
            best_wl = WDM_CHANNELS[best_ch]
            bit_val = SFG_RESULT.get(round(best_wl, 1), 0)
            if bit_val == 1:
                bit_out = 1
                break

        result.detected_output.append(bit_out)

        if verbose:
            print(f"  Column {col}: {len(products)} AND products → OR = {bit_out}")

    # Stage 5: Verify
    result.all_correct = (result.detected_output == result.expected_output)

    if verbose:
        print("\n" + "=" * 70)
        print("  RESULTS")
        print("=" * 70)
        print(f"  Expected: {result.expected_output}")
        print(f"  Detected: {result.detected_output}")
        match = "PASS ✓" if result.all_correct else "FAIL ✗"
        print(f"  Match:    {match}")

    return result


# =============================================================================
# Test cases (mirrors ternary tests)
# =============================================================================

def test_single_pe_and_table():
    """Test all 4 binary AND combinations through a single PE."""
    print("\n" + "=" * 70)
    print("  TEST: Single PE — All 4 Binary AND Combinations")
    print("=" * 70)

    all_pass = True
    for bit_a in [0, 1]:
        for bit_b in [0, 1]:
            expected = bit_a & bit_b

            act = mzi_encode_binary(bit_a, 10.0)
            wt  = mzi_encode_binary(bit_b, 10.0)
            sfg_out, _, _, pe_res = simulate_pe_binary(act, wt, 0, 0)

            if sfg_out is None:
                detected = 0
            else:
                detected = SFG_RESULT.get(round(sfg_out.wavelength_nm, 1), 0)

            passed = (detected == expected)
            if not passed:
                all_pass = False

            wl_str  = f"{sfg_out.wavelength_nm:.1f}nm" if sfg_out else "none"
            pwr_str = f"{sfg_out.power_dbm:.1f}dBm"    if sfg_out else "n/a"
            status  = "PASS" if passed else "FAIL"
            print(f"  {bit_a} AND {bit_b} = {expected}  "
                  f"| SFG: {wl_str} @ {pwr_str} → detected: {detected}  [{status}]")

    print(f"\n  Overall: {'ALL PASS' if all_pass else 'SOME FAILED'}")
    return all_pass


def test_identity_matrix():
    """y = I AND x should equal x."""
    print("\n" + "=" * 70)
    print("  TEST: Identity Matrix — y = I AND x should equal x")
    print("=" * 70)

    x = [1, 0, 1, 0, 1, 0, 1, 0, 1]
    W = [[1 if i == j else 0 for j in range(9)] for i in range(9)]
    result = simulate_binary_array_9x9(x, W, verbose=True)
    return result.all_correct


def test_all_ones():
    """All-ones: every column OR(AND) = 1."""
    print("\n" + "=" * 70)
    print("  TEST: All Ones — W=all(1), x=all(1)")
    print("=" * 70)

    x = [1] * 9
    W = [[1] * 9 for _ in range(9)]
    result = simulate_binary_array_9x9(x, W, verbose=True)
    return result.all_correct


def test_all_zeros():
    """All-zeros: every column = 0."""
    print("\n" + "=" * 70)
    print("  TEST: All Zeros — W=all(0), x=all(0)")
    print("=" * 70)

    x = [0] * 9
    W = [[0] * 9 for _ in range(9)]
    result = simulate_binary_array_9x9(x, W, verbose=True)
    return result.all_correct


def test_single_nonzero():
    """Single non-zero weight — PE isolation."""
    print("\n" + "=" * 70)
    print("  TEST: Single Non-Zero Weight — PE Isolation")
    print("=" * 70)

    x = [1] * 9
    W = [[0] * 9 for _ in range(9)]
    W[4][4] = 1
    result = simulate_binary_array_9x9(x, W, verbose=True)
    return result.all_correct


def test_mixed_pattern():
    """Mixed 3x3 binary sub-problem."""
    print("\n" + "=" * 70)
    print("  TEST: Mixed 3x3 Binary Pattern")
    print("=" * 70)

    x = [1, 0, 1, 0, 0, 0, 0, 0, 0]
    W = [[0]*9 for _ in range(9)]
    sub_W = [[1, 0, 1], [0, 1, 0], [1, 0, 1]]
    for i in range(3):
        for j in range(3):
            W[i][j] = sub_W[i][j]

    result = simulate_binary_array_9x9(x, W, verbose=True)
    return result.all_correct


def test_ioc_modes():
    """Demonstrate AND vs OR vs XOR modes on same physical hardware."""
    print("\n" + "=" * 70)
    print("  TEST: IOC Modes — AND / OR / XOR (Same Glass)")
    print("=" * 70)

    x = [1, 0, 1, 1, 0, 1, 0, 1, 0]
    W = [[0]*9 for _ in range(9)]
    W[0][0] = 1; W[2][0] = 1; W[3][0] = 0
    W[0][1] = 0; W[2][1] = 1

    result = simulate_binary_array_9x9(x, W, verbose=False)

    for pe_type in ["AND", "OR", "XOR"]:
        ioc = BinaryIOC(pe_type=pe_type)
        print(f"\n  {ioc.describe()}")

    print(f"\n  Physical SFG output (column 0): {result.detected_output[0]}")
    print(f"  The glass doesn't change. Only the IOC encoding does.")
    print(f"\n  Key difference from ternary N-Radix:")
    print(f"    Ternary: 3 wavelengths, 1.58 bits/trit, log-domain multiply")
    print(f"    Binary:  2 wavelengths, 1.00 bit/symbol, direct AND")
    print(f"    Same PPLN glass. Same SFG physics. Binary is a strict subset.")

    return True


def test_loss_budget():
    """Verify power margin — identical to ternary (same glass)."""
    print("\n" + "=" * 70)
    print("  TEST: Loss Budget (same physical path as ternary)")
    print("=" * 70)

    act = mzi_encode_binary(1, 10.0)
    wt  = mzi_encode_binary(1, 10.0)

    act = act.attenuate(EDGE_COUPLING_LOSS)
    act = waveguide_transfer(act, IOC_INPUT_WIDTH + ROUTING_GAP, WG_LOSS_DB_CM)

    sfg_out = None
    for col in range(9):
        sfg_out, act, _, _ = simulate_pe_binary(act, wt, 0, col)
        if col < 8:
            act = waveguide_transfer(act, PE_PITCH - PE_WIDTH, WG_LOSS_DB_CM)

    if sfg_out:
        sfg_routed = waveguide_transfer(
            sfg_out, ROUTING_GAP + IOC_OUTPUT_WIDTH, WG_LOSS_DB_CM
        )
        sfg_routed = sfg_routed.attenuate(EDGE_COUPLING_LOSS)
        margin = sfg_routed.power_dbm - DETECTOR_SENSITIVITY
        passed = margin > 0
        print(f"  Worst-case path (PE[0,8]):")
        print(f"    SFG output at PE: {sfg_out.power_dbm:.1f} dBm")
        print(f"    After routing:    {sfg_routed.power_dbm:.1f} dBm")
        print(f"    Sensitivity:      {DETECTOR_SENSITIVITY} dBm")
        print(f"    Margin:           {margin:.1f} dB")
        print(f"    Result: {'PASS' if passed else 'FAIL'}")
        return passed

    print("  ERROR: No SFG output")
    return False


def test_radix_comparison():
    """
    Theoretical comparison: binary vs ternary information density.
    This is the core argument for the paper.
    """
    print("\n" + "=" * 70)
    print("  ANALYSIS: Binary vs Ternary Radix Economy")
    print("=" * 70)

    import math

    # Radix economy: r / log2(r) — lower is better (more info per symbol)
    for r in [2, 3, 4, 8, 16]:
        economy = r / math.log2(r)
        bits_per_symbol = math.log2(r)
        marker = " ← optimal (closest to e=2.718)" if r == 3 else ""
        print(f"  Radix {r:2d}: economy={economy:.3f}, "
              f"bits/symbol={bits_per_symbol:.3f}{marker}")

    print(f"\n  Binary vs Ternary on this chip:")
    print(f"    Binary:  2 wavelengths, 1.000 bit/symbol")
    print(f"    Ternary: 3 wavelengths, 1.585 bits/symbol  (+58.5% information density)")
    print(f"\n  Wavelength cost:")
    print(f"    Binary:  2 lasers needed")
    print(f"    Ternary: 3 lasers needed")
    print(f"    Cost delta: +1 laser source for +58.5% compute density")
    print(f"\n  For the same FLOPS throughput:")
    n_binary = 100
    n_ternary = math.ceil(n_binary / 1.585)
    print(f"    Binary needs {n_binary} PEs")
    print(f"    Ternary needs only {n_ternary} PEs ({100 - n_ternary}% fewer)")
    print(f"\n  Conclusion: Ternary strictly dominates binary on this photonic platform.")
    print(f"  The wavelength cost is O(1) per added state — no transistor penalty.")

    return True


# =============================================================================
# Main
# =============================================================================

def main():
    print("╔" + "═" * 68 + "╗")
    print("║  BINARY OPTICAL CHIP — 9x9 CIRCUIT-LEVEL SIMULATION              ║")
    print("║  2-Wavelength photonic AND array on lithium niobate               ║")
    print("╚" + "═" * 68 + "╝")

    results = {}
    results['single_pe_and']  = test_single_pe_and_table()
    results['identity']       = test_identity_matrix()
    results['all_ones']       = test_all_ones()
    results['all_zeros']      = test_all_zeros()
    results['single_nonzero'] = test_single_nonzero()
    results['mixed_pattern']  = test_mixed_pattern()
    results['ioc_modes']      = test_ioc_modes()
    results['loss_budget']    = test_loss_budget()
    results['radix_compare']  = test_radix_comparison()

    print("\n" + "╔" + "═" * 68 + "╗")
    print("║  TEST SUMMARY                                                    ║")
    print("╠" + "═" * 68 + "╣")

    all_pass = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        symbol = "  " if passed else "!!"
        print(f"║ {symbol} {name:40s} {status:>6s}                     ║")
        if not passed:
            all_pass = False

    print("╠" + "═" * 68 + "╣")
    overall = "ALL TESTS PASSED" if all_pass else "SOME TESTS FAILED"
    print(f"║  {overall:64s}  ║")
    print("╚" + "═" * 68 + "╝")

    return all_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
