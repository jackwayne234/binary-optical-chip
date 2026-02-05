#!/usr/bin/env python3
"""
IOC Tower Level Limit Tester

Tests how many tower levels the IOC can handle before precision degrades.
The IOC encodes/decodes values at different tower levels:
- Level 0: trit = trit (base)
- Level 2: trit represents trit³ (ADD/SUB scaled)
- Level 3: trit represents trit^(3^3) (MUL/DIV scaled)
- Level 4+: even higher towers

We test round-trip accuracy: encode → decode → compare to original.
"""

import math
from decimal import Decimal, getcontext
import numpy as np

# Set high precision for Decimal operations
getcontext().prec = 100

# Ternary trit values
TRIT_VALUES = [-1, 0, 1]


def tower_power(base, levels):
    """
    Compute a power tower: base^base^base^... (levels times)

    Examples:
        tower_power(3, 1) = 3
        tower_power(3, 2) = 3^3 = 27
        tower_power(3, 3) = 3^(3^3) = 3^27 = 7,625,597,484,987
        tower_power(3, 4) = 3^(3^(3^3)) = 3^7625597484987 = incomprehensibly large
    """
    if levels <= 0:
        return 1
    result = base
    for _ in range(levels - 1):
        result = base ** result
    return result


def test_tower_computability():
    """Test which tower levels we can even compute."""
    print("=" * 60)
    print("TOWER COMPUTABILITY TEST")
    print("=" * 60)
    print("\nTesting which power towers we can represent...\n")

    for level in range(1, 8):
        try:
            if level <= 3:
                value = tower_power(3, level)
                print(f"Level {level}: 3^" + "^3" * (level - 1) + f" = {value:,}")
            else:
                # For level 4+, just try to compute and see if it overflows
                # Use logarithms to estimate
                log_value = 3 ** (level - 1) * math.log10(3)
                print(f"Level {level}: 3^...^3 ({level} 3s) ≈ 10^{log_value:.2e} (too large to store)")
        except (OverflowError, ValueError) as e:
            print(f"Level {level}: OVERFLOW - Cannot compute")
            break

    print()


class IOCEncoder:
    """
    Simulates IOC encoding/decoding at various tower levels.
    """

    def __init__(self, tower_level=0, use_decimal=False):
        """
        Initialize IOC encoder at a specific tower level.

        tower_level 0: trit = trit (linear)
        tower_level 1: trit = trit (log domain, still base representation)
        tower_level 2: trit represents trit³ (ADD/SUB scaled)
        tower_level 3: trit represents trit^27 (MUL/DIV scaled)
        """
        self.tower_level = tower_level
        self.use_decimal = use_decimal

        # Calculate the exponent for this tower level
        if tower_level <= 1:
            self.exponent = 1
        else:
            # Level 2: exponent = 3^1 = 3
            # Level 3: exponent = 3^3 = 27
            # Level 4: exponent = 3^27 = huge
            self.exponent = tower_power(3, tower_level - 1)

    def encode_trit(self, value):
        """
        Encode a value into a trit at this tower level.

        The trit physically is still -1, 0, or +1.
        But it REPRESENTS value^exponent.
        """
        if value == 0:
            return 0

        # The trit represents the value raised to self.exponent
        # So to encode, we need to find what trit^exponent = value
        # Which means trit = value^(1/exponent)

        if self.use_decimal:
            d_value = Decimal(str(value))
            d_exp = Decimal(str(self.exponent))

            if value > 0:
                # trit = value^(1/exponent)
                root = float(d_value ** (1 / d_exp))
            else:
                # Handle negative values
                root = -float(abs(d_value) ** (1 / d_exp))
        else:
            if value > 0:
                root = value ** (1.0 / self.exponent)
            else:
                root = -(abs(value) ** (1.0 / self.exponent))

        # Quantize to nearest trit
        if root < -0.5:
            return -1
        elif root > 0.5:
            return 1
        else:
            return 0

    def decode_trit(self, trit):
        """
        Decode a trit back to its represented value at this tower level.

        The trit physically is -1, 0, or +1.
        It REPRESENTS trit^exponent.
        """
        if trit == 0:
            return 0

        if self.use_decimal:
            d_trit = Decimal(str(trit))
            d_exp = Decimal(str(self.exponent))
            return float(d_trit ** d_exp)
        else:
            return trit ** self.exponent

    def round_trip(self, value):
        """Encode then decode a value. Test accuracy."""
        trit = self.encode_trit(value)
        decoded = self.decode_trit(trit)
        return trit, decoded

    def test_range(self, test_values):
        """Test encoding/decoding for a range of values."""
        results = []
        for val in test_values:
            trit, decoded = self.round_trip(val)
            error = abs(decoded - val) if val != 0 else abs(decoded)
            rel_error = error / abs(val) if val != 0 else error
            results.append({
                'input': val,
                'trit': trit,
                'decoded': decoded,
                'error': error,
                'rel_error': rel_error
            })
        return results


def test_ioc_levels():
    """Test IOC encoding/decoding at each tower level."""
    print("=" * 60)
    print("IOC TOWER LEVEL PRECISION TEST")
    print("=" * 60)

    # Test values representing typical computations
    test_values = [-1, -0.5, 0, 0.5, 1, 0.1, 0.9, -0.9]

    for level in range(0, 5):
        print(f"\n--- Tower Level {level} ---")

        try:
            ioc = IOCEncoder(tower_level=level)
            print(f"Exponent: {ioc.exponent}")

            if ioc.exponent > 1e15:
                print("Exponent too large for standard float precision")
                print("Would need arbitrary precision arithmetic")
                continue

            results = ioc.test_range(test_values)

            print(f"{'Input':>10} | {'Trit':>5} | {'Decoded':>15} | {'Error':>12}")
            print("-" * 50)
            for r in results:
                print(f"{r['input']:>10.4f} | {r['trit']:>5} | {r['decoded']:>15.6f} | {r['error']:>12.6f}")

            max_error = max(r['error'] for r in results)
            print(f"\nMax error at level {level}: {max_error:.6e}")

        except (OverflowError, ValueError) as e:
            print(f"FAILED: {e}")
            break


def test_multi_trit_encoding():
    """
    Test encoding larger numbers using multiple trits.
    This is closer to how the actual IOC would work.
    """
    print("\n" + "=" * 60)
    print("MULTI-TRIT ENCODING TEST")
    print("=" * 60)

    def encode_balanced_ternary(n, num_trits=9):
        """Encode integer n in balanced ternary using num_trits trits."""
        if n == 0:
            return [0] * num_trits

        trits = []
        val = n
        for _ in range(num_trits):
            remainder = val % 3
            if remainder == 0:
                trits.append(0)
                val = val // 3
            elif remainder == 1:
                trits.append(1)
                val = val // 3
            else:  # remainder == 2
                trits.append(-1)
                val = (val + 1) // 3
        return trits

    def decode_balanced_ternary(trits):
        """Decode balanced ternary back to integer."""
        result = 0
        for i, t in enumerate(trits):
            result += t * (3 ** i)
        return result

    # Test range of values
    print("\nBalanced ternary round-trip test (9 trits):")
    print(f"Range: {-3**9//2} to {3**9//2} ({3**9} values)")

    errors = 0
    test_range = range(-1000, 1001)
    for val in test_range:
        trits = encode_balanced_ternary(val)
        decoded = decode_balanced_ternary(trits)
        if decoded != val:
            errors += 1
            if errors <= 5:
                print(f"  ERROR: {val} -> {trits} -> {decoded}")

    print(f"\nErrors: {errors}/{len(list(test_range))}")

    # Now test with tower scaling applied to the decoded value
    print("\n" + "-" * 40)
    print("Tower scaling applied to multi-trit values:")

    for level in [0, 2, 3]:
        ioc = IOCEncoder(tower_level=level)
        if ioc.exponent > 1e10:
            print(f"\nLevel {level}: Exponent {ioc.exponent:.2e} - too large")
            continue

        print(f"\nLevel {level} (exponent = {ioc.exponent}):")

        # Test a few values
        test_vals = [1, 10, 100, 1000]
        for val in test_vals:
            # The multi-trit value gets raised to the tower exponent
            scaled_val = val ** ioc.exponent
            print(f"  {val} -> {val}^{ioc.exponent} = {scaled_val:.2e}")


def test_floating_point_limits():
    """Test where floating point precision breaks down."""
    print("\n" + "=" * 60)
    print("FLOATING POINT PRECISION LIMITS")
    print("=" * 60)

    print(f"\nPython float (64-bit IEEE 754):")
    print(f"  Max value: {float('inf')} (but useful max ≈ 1.8e308)")
    print(f"  Min positive: {np.finfo(float).tiny:.2e}")
    print(f"  Precision: {np.finfo(float).precision} decimal digits")
    print(f"  Machine epsilon: {np.finfo(float).eps:.2e}")

    print(f"\nTower level implications:")

    # At what tower level does 3^...^3 exceed float max?
    for level in range(1, 6):
        try:
            exp = tower_power(3, level)
            # Can we represent 1.5^exp without overflow?
            test_val = 1.5 ** exp if exp < 1000 else float('inf')
            if test_val == float('inf'):
                print(f"  Level {level}: exponent = {exp:,} - OVERFLOW for values > 1")
            else:
                print(f"  Level {level}: exponent = {exp:,} - OK (1.5^exp = {test_val:.2e})")
        except OverflowError:
            print(f"  Level {level}: OVERFLOW computing exponent")
            break


def test_practical_ioc_limits():
    """
    Determine practical IOC limits based on:
    1. Numerical precision
    2. Representable range
    3. Round-trip accuracy
    """
    print("\n" + "=" * 60)
    print("PRACTICAL IOC LIMITS ANALYSIS")
    print("=" * 60)

    print("\nFor ADD/SUB PEs (even levels: 0, 2, 4, ...):")
    print("-" * 40)

    for level in [0, 2, 4]:
        exp = tower_power(3, max(0, level - 1)) if level > 1 else 1
        print(f"\n  Level {level}: trit represents trit^{exp}")

        if exp == 1:
            print(f"    Range: -1 to +1 (base)")
            print(f"    Precision: Perfect")
            print(f"    Status: ✓ WORKS")
        elif exp <= 27:
            print(f"    Trit -1 represents: (-1)^{exp} = {(-1)**exp}")
            print(f"    Trit +1 represents: (+1)^{exp} = {(+1)**exp}")
            print(f"    Range: Still -1 to +1 (odd exponent)")
            print(f"    Precision: Perfect for trit values")
            print(f"    Status: ✓ WORKS")
        else:
            print(f"    Exponent {exp:,} exceeds practical limits")
            print(f"    Status: ✗ NEEDS SPECIAL HANDLING")

    print("\n\nFor MUL/DIV PEs (odd levels: 1, 3, 5, ...):")
    print("-" * 40)

    for level in [1, 3, 5]:
        exp = tower_power(3, max(0, level - 1)) if level > 1 else 1
        print(f"\n  Level {level}: trit represents trit^{exp}")

        if exp == 1:
            print(f"    Range: -1 to +1 (base log domain)")
            print(f"    Status: ✓ WORKS")
        elif exp <= 27:
            print(f"    Exponent: {exp}")
            print(f"    Status: ✓ WORKS (exponent fits in standard int)")
        else:
            print(f"    Exponent: {exp:,}")
            print(f"    Status: ✗ NEEDS ARBITRARY PRECISION")


def test_3333_impossibility():
    """
    Demonstrate why 3^3^3^3 encoding is mathematically impossible.

    This isn't "future tech" - it's beyond the physical limits of computing.
    """
    print("\n" + "=" * 60)
    print("3^3^3^3 IMPOSSIBILITY ANALYSIS")
    print("=" * 60)

    # 3^3 = 27
    # 3^3^3 = 3^27 = 7,625,597,484,987
    # 3^3^3^3 = 3^7,625,597,484,987

    level_3_exponent = 7_625_597_484_987  # 3^3^3

    print(f"\nThe tower progression:")
    print(f"  3^3       = 27")
    print(f"  3^3^3     = 3^27 = 7,625,597,484,987 (~7.6 trillion)")
    print(f"  3^3^3^3   = 3^7,625,597,484,987")

    # To represent 3^N distinct states, you need log2(3^N) = N * log2(3) bits
    # For 3^3^3^3, that's 3^7625597484987 states
    # Bits needed = 7625597484987 * log2(3) ≈ 7625597484987 * 1.585

    bits_needed = level_3_exponent * math.log2(3)

    print(f"\n" + "-" * 40)
    print(f"BITS REQUIRED FOR 3^3^3^3 ENCODING:")
    print(f"-" * 40)
    print(f"  Bits needed: {bits_needed:.3e}")
    print(f"             = {bits_needed / 1e12:.1f} TERABITS")
    print(f"             = {bits_needed / 1e12:.1f} trillion bits")

    bytes_needed = bits_needed / 8
    terabytes_needed = bytes_needed / 1e12

    print(f"\n  Storage required: {terabytes_needed:.2f} TERABYTES")
    print(f"                  = {terabytes_needed * 1000:.0f} PETABYTES")
    print(f"                  = Just to store ONE number!")

    print(f"\n" + "-" * 40)
    print(f"COMPARISON TO STANDARD BIT WIDTHS:")
    print(f"-" * 40)
    standard_widths = [64, 128, 256, 512, 1024]
    for width in standard_widths:
        ratio = bits_needed / width
        print(f"  {width:>4}-bit: {ratio:.2e}x larger")

    print(f"\n  For context:")
    print(f"    - A 64-bit register holds 18 quintillion values")
    print(f"    - 3^3^3^3 would need {bits_needed / 64:.2e} 64-bit registers")
    print(f"    - That's {bits_needed / 64 / 1e12:.1f} trillion registers")

    print(f"\n" + "-" * 40)
    print(f"PHYSICAL REALITY CHECK:")
    print(f"-" * 40)

    # Total transistors on Earth (rough estimate ~10^21)
    transistors_on_earth = 1e21
    transistors_needed = bits_needed  # 1 bit ≈ multiple transistors, but use 1:1 for simplicity

    print(f"  Transistors in ALL computers on Earth: ~10^21")
    print(f"  Transistors needed for one 3^3^3^3 register: {transistors_needed:.2e}")
    print(f"  Ratio: {transistors_needed / transistors_on_earth:.2e}x all computing on Earth")

    print(f"\n" + "=" * 60)
    print(f"VERDICT: 3^3^3^3 is not 'future tech' - it's mathematically")
    print(f"         beyond physical computing. Period.")
    print(f"=" * 60)


def main():
    """Run all IOC limit tests."""
    print("\n" + "=" * 60)
    print("   IOC TOWER LEVEL LIMIT TESTER")
    print("   Finding the ceiling for tower scaling")
    print("=" * 60)

    test_tower_computability()
    test_ioc_levels()
    test_multi_trit_encoding()
    test_floating_point_limits()
    test_practical_ioc_limits()
    test_3333_impossibility()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
Key findings:

1. TOWER COMPUTABILITY:
   - Level 1: 3 (trivial)
   - Level 2: 27 (easy)
   - Level 3: 7.6 trillion (fits in 64-bit int)
   - Level 4+: Exceeds standard numeric types

2. IOC PRECISION LIMITS:
   - Levels 0-3: Standard 64-bit float/int works
   - Level 4+: Needs arbitrary precision (e.g., Python Decimal, GMP)

3. PRACTICAL CEILING:
   - With standard hardware: Level 3 (3^3^3)
   - With arbitrary precision: Theoretically unlimited
   - Real limit: Transistor interface bandwidth

4. NEXT STEPS:
   - Test actual IOC implementation at levels 0-3
   - Profile encoding/decoding latency at each level
   - Test transistor interface (PCIe) throughput limits
   - Find the true bottleneck

5. WHY 3^3^3^3 IS IMPOSSIBLE:
   - 3^3^3^3 = 3^7,625,597,484,987
   - Would need 12 TERABIT registers (12 trillion bits)
   - 1.5 TERABYTES to store ONE number
   - This isn't "future tech" - it's beyond physical computing

6. REAL-WORLD PERFORMANCE (3^3 encoding):
   - Only ADD/SUB gets 9x boost (27 states vs 3 states)
   - MUL/DIV stays at baseline (1x) - still 3-state operations
   - Matrix multiply (50/50 ADD/MUL): ~1.8x overall
   - Transformer attention (~60/40 ADD-heavy): ~2.1x overall
   - The 9x only applies to ADD-heavy workloads
""")


if __name__ == "__main__":
    main()
