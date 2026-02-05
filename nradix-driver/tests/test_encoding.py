"""
Test suite for N-Radix encoding functions.

Tests the balanced ternary encoding system that converts floats in [-1, 1]
to trit representations and packs them efficiently into bytes.
"""

import pytest
import numpy as np

# Import from the nradix module (adjust path as needed when module is implemented)
try:
    from nradix import float_to_trits, trits_to_float, pack_trits, unpack_trits
except ImportError:
    # Fallback: try relative import or define stubs for test development
    import sys
    sys.path.insert(0, '/home/jackwayne/Desktop/Optical_computing/nradix-driver/python')
    from nradix import float_to_trits, trits_to_float, pack_trits, unpack_trits


class TestFloatToTritsRoundtrip:
    """Test float_to_trits and trits_to_float roundtrip conversions."""

    @pytest.mark.parametrize("value", [
        -1.0,
        0.0,
        1.0,
        0.5,
        -0.5,
    ])
    def test_edge_cases_roundtrip(self, value):
        """Test that edge case values survive roundtrip conversion."""
        num_trits = 5
        trits = float_to_trits(value, num_trits)
        reconstructed = trits_to_float(trits)

        # Ternary has limited precision, so we allow some tolerance
        # With 5 trits, precision is 1/3^5 = 1/243 ~ 0.004
        tolerance = 1.0 / (3 ** num_trits) * 2  # 2x the theoretical resolution
        assert abs(reconstructed - value) < tolerance, \
            f"Roundtrip failed for {value}: got {reconstructed}"

    def test_negative_one(self):
        """Test encoding of -1.0."""
        trits = float_to_trits(-1.0, 5)
        reconstructed = trits_to_float(trits)
        assert reconstructed <= -0.99, f"Expected near -1.0, got {reconstructed}"

    def test_zero(self):
        """Test encoding of 0.0."""
        trits = float_to_trits(0.0, 5)
        reconstructed = trits_to_float(trits)
        assert abs(reconstructed) < 0.01, f"Expected near 0.0, got {reconstructed}"

    def test_positive_one(self):
        """Test encoding of 1.0."""
        trits = float_to_trits(1.0, 5)
        reconstructed = trits_to_float(trits)
        assert reconstructed >= 0.99, f"Expected near 1.0, got {reconstructed}"

    def test_half_positive(self):
        """Test encoding of 0.5."""
        trits = float_to_trits(0.5, 5)
        reconstructed = trits_to_float(trits)
        assert abs(reconstructed - 0.5) < 0.02, f"Expected near 0.5, got {reconstructed}"

    def test_half_negative(self):
        """Test encoding of -0.5."""
        trits = float_to_trits(-0.5, 5)
        reconstructed = trits_to_float(trits)
        assert abs(reconstructed - (-0.5)) < 0.02, f"Expected near -0.5, got {reconstructed}"

    def test_random_values_roundtrip(self):
        """Test roundtrip for random values in [-1, 1]."""
        np.random.seed(42)
        num_trits = 5
        tolerance = 1.0 / (3 ** num_trits) * 2

        for _ in range(100):
            value = np.random.uniform(-1.0, 1.0)
            trits = float_to_trits(value, num_trits)
            reconstructed = trits_to_float(trits)
            assert abs(reconstructed - value) < tolerance, \
                f"Roundtrip failed for {value}: got {reconstructed}"

    def test_trits_are_valid(self):
        """Test that all trits are in {-1, 0, +1}."""
        for value in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            trits = float_to_trits(value, 5)
            for t in trits:
                assert t in [-1, 0, 1], f"Invalid trit {t} for value {value}"

    def test_different_precisions(self):
        """Test roundtrip with different numbers of trits."""
        value = 0.333
        for num_trits in [3, 5, 7, 10]:
            trits = float_to_trits(value, num_trits)
            reconstructed = trits_to_float(trits)
            tolerance = 1.0 / (3 ** num_trits) * 2
            assert abs(reconstructed - value) < tolerance, \
                f"Roundtrip failed for {value} with {num_trits} trits"


class TestPackUnpackTritsRoundtrip:
    """Test pack_trits and unpack_trits roundtrip conversions."""

    def test_all_zeros(self):
        """Test packing all zeros."""
        trits = [0, 0, 0, 0, 0]
        packed = pack_trits(trits)
        unpacked = unpack_trits(packed)
        assert list(unpacked) == trits

    def test_all_positive_ones(self):
        """Test packing all +1s."""
        trits = [1, 1, 1, 1, 1]
        packed = pack_trits(trits)
        unpacked = unpack_trits(packed)
        assert list(unpacked) == trits

    def test_all_negative_ones(self):
        """Test packing all -1s."""
        trits = [-1, -1, -1, -1, -1]
        packed = pack_trits(trits)
        unpacked = unpack_trits(packed)
        assert list(unpacked) == trits

    def test_mixed_trits(self):
        """Test packing mixed trit values."""
        trits = [-1, 0, 1, 0, -1]
        packed = pack_trits(trits)
        unpacked = unpack_trits(packed)
        assert list(unpacked) == trits

    def test_packed_value_range(self):
        """Test that packed value is always < 243 (3^5)."""
        # Test all possible combinations (3^5 = 243 combinations)
        for t0 in [-1, 0, 1]:
            for t1 in [-1, 0, 1]:
                for t2 in [-1, 0, 1]:
                    for t3 in [-1, 0, 1]:
                        for t4 in [-1, 0, 1]:
                            trits = [t0, t1, t2, t3, t4]
                            packed = pack_trits(trits)
                            assert 0 <= packed < 243, \
                                f"Packed value {packed} out of range for trits {trits}"

    def test_all_combinations_roundtrip(self):
        """Test roundtrip for all possible 5-trit combinations."""
        for t0 in [-1, 0, 1]:
            for t1 in [-1, 0, 1]:
                for t2 in [-1, 0, 1]:
                    for t3 in [-1, 0, 1]:
                        for t4 in [-1, 0, 1]:
                            trits = [t0, t1, t2, t3, t4]
                            packed = pack_trits(trits)
                            unpacked = unpack_trits(packed)
                            assert list(unpacked) == trits, \
                                f"Roundtrip failed: {trits} -> {packed} -> {list(unpacked)}"

    def test_unique_packing(self):
        """Test that each trit combination maps to a unique packed value."""
        seen_packed = {}
        for t0 in [-1, 0, 1]:
            for t1 in [-1, 0, 1]:
                for t2 in [-1, 0, 1]:
                    for t3 in [-1, 0, 1]:
                        for t4 in [-1, 0, 1]:
                            trits = (t0, t1, t2, t3, t4)
                            packed = pack_trits(list(trits))
                            assert packed not in seen_packed, \
                                f"Collision: {trits} and {seen_packed[packed]} both map to {packed}"
                            seen_packed[packed] = trits

    def test_packing_formula(self):
        """Test that packing follows expected formula: (t+1) + (t+1)*3 + ..."""
        # Formula: sum((t[i]+1) * 3^i for i in 0..4)
        trits = [1, -1, 0, 1, -1]
        expected = (
            (trits[0] + 1) * 1 +
            (trits[1] + 1) * 3 +
            (trits[2] + 1) * 9 +
            (trits[3] + 1) * 27 +
            (trits[4] + 1) * 81
        )
        packed = pack_trits(trits)
        assert packed == expected, f"Expected {expected}, got {packed}"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_clamping_above_one(self):
        """Test that values > 1.0 are clamped to 1.0."""
        trits = float_to_trits(1.5, 5)
        reconstructed = trits_to_float(trits)
        assert reconstructed >= 0.99, f"Value should be clamped to ~1.0, got {reconstructed}"

    def test_clamping_below_negative_one(self):
        """Test that values < -1.0 are clamped to -1.0."""
        trits = float_to_trits(-1.5, 5)
        reconstructed = trits_to_float(trits)
        assert reconstructed <= -0.99, f"Value should be clamped to ~-1.0, got {reconstructed}"

    def test_very_small_positive(self):
        """Test encoding of very small positive value."""
        trits = float_to_trits(0.001, 5)
        reconstructed = trits_to_float(trits)
        # Should be close to zero given 5-trit precision
        assert abs(reconstructed) < 0.05, f"Small value should be near zero, got {reconstructed}"

    def test_very_small_negative(self):
        """Test encoding of very small negative value."""
        trits = float_to_trits(-0.001, 5)
        reconstructed = trits_to_float(trits)
        assert abs(reconstructed) < 0.05, f"Small value should be near zero, got {reconstructed}"

    def test_float_precision_boundary(self):
        """Test values near the precision boundary."""
        num_trits = 5
        precision = 1.0 / (3 ** num_trits)  # ~0.004

        # Test value at exactly one precision unit
        trits = float_to_trits(precision, num_trits)
        reconstructed = trits_to_float(trits)
        # Should distinguish from zero
        assert reconstructed != 0.0 or abs(precision) < precision / 2


class TestIntegration:
    """Integration tests combining encoding and packing."""

    def test_full_pipeline(self):
        """Test full encoding -> packing -> unpacking -> decoding pipeline."""
        original_value = 0.333
        num_trits = 5

        # Encode float to trits
        trits = float_to_trits(original_value, num_trits)
        assert len(trits) == num_trits

        # Pack trits to byte
        packed = pack_trits(trits)
        assert 0 <= packed < 243

        # Unpack byte to trits
        unpacked = unpack_trits(packed)
        assert list(unpacked) == list(trits)

        # Decode trits to float
        reconstructed = trits_to_float(unpacked)

        tolerance = 1.0 / (3 ** num_trits) * 2
        assert abs(reconstructed - original_value) < tolerance

    def test_matrix_encoding_simulation(self):
        """Simulate encoding a small matrix through the pipeline."""
        # Create a 3x3 test matrix
        matrix = np.array([
            [-1.0, 0.0, 1.0],
            [0.5, -0.5, 0.25],
            [-0.25, 0.75, -0.75]
        ])

        num_trits = 5
        tolerance = 1.0 / (3 ** num_trits) * 2

        # Process each element
        reconstructed = np.zeros_like(matrix)
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                trits = float_to_trits(matrix[i, j], num_trits)
                packed = pack_trits(trits)
                unpacked = unpack_trits(packed)
                reconstructed[i, j] = trits_to_float(unpacked)

        # Check reconstruction accuracy
        assert np.allclose(matrix, reconstructed, atol=tolerance), \
            f"Matrix reconstruction error too large:\n{matrix}\nvs\n{reconstructed}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
