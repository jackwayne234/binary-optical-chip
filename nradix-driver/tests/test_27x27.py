"""
Integration tests for 27x27 N-Radix array configuration.

Tests the full pipeline from weight loading through computation
for a 27x27 optical matrix multiply array (3^3 x 3^3).
"""

import pytest
import numpy as np

try:
    from nradix import NRadixSimulator, float_to_trits, trits_to_float
except ImportError:
    import sys
    sys.path.insert(0, '/home/jackwayne/Desktop/Optical_computing/nradix-driver/python')
    from nradix import NRadixSimulator, float_to_trits, trits_to_float


ARRAY_SIZE = 27  # 3^3


class Test27x27Integration:
    """Integration tests for the 27x27 array."""

    @pytest.fixture
    def simulator(self):
        """Create a 27x27 simulator instance."""
        return NRadixSimulator(array_size=ARRAY_SIZE)

    @pytest.fixture
    def sample_weights(self):
        """Generate reproducible sample weights."""
        np.random.seed(2026)  # For reproducibility
        return np.random.uniform(-1.0, 1.0, (ARRAY_SIZE, ARRAY_SIZE))

    @pytest.fixture
    def sample_input(self):
        """Generate reproducible sample input."""
        np.random.seed(42)
        return np.random.uniform(-1.0, 1.0, ARRAY_SIZE)

    def test_full_computation_pipeline(self, simulator, sample_weights, sample_input):
        """Test complete load -> compute -> verify pipeline."""
        # Load weights
        simulator.load_weights(sample_weights)

        # Compute output
        output = simulator.compute(sample_input)

        # Verify output shape
        assert output.shape == (ARRAY_SIZE,)

        # Verify output is finite
        assert np.all(np.isfinite(output))

        # Compare with expected (ideal) matrix multiply
        expected = sample_weights @ sample_input

        # Calculate relative error
        # Allow for ternary quantization error (5 trits = 1/243 precision)
        tolerance = 0.15  # 15% tolerance due to quantization
        rel_error = np.abs(output - expected) / (np.abs(expected) + 1e-10)
        mean_rel_error = np.mean(rel_error)

        assert mean_rel_error < tolerance, \
            f"Mean relative error {mean_rel_error:.4f} exceeds tolerance {tolerance}"

    def test_identity_matrix_preservation(self, simulator):
        """Test that identity matrix preserves input."""
        # Load identity weights
        weights = np.eye(ARRAY_SIZE)
        simulator.load_weights(weights)

        # Create test input
        np.random.seed(123)
        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)

        # Compute
        output = simulator.compute(input_vec)

        # Should be close to input
        max_error = np.max(np.abs(output - input_vec))
        assert max_error < 0.1, f"Identity preservation failed, max error: {max_error}"

    def test_negative_identity_flip(self, simulator):
        """Test that -I matrix flips signs."""
        # Load negative identity
        weights = -np.eye(ARRAY_SIZE)
        simulator.load_weights(weights)

        # Create positive test input
        input_vec = np.full(ARRAY_SIZE, 0.5)

        # Compute
        output = simulator.compute(input_vec)

        # Should be approximately -0.5 everywhere
        expected = -input_vec
        assert np.allclose(output, expected, atol=0.15)

    def test_permutation_matrix(self, simulator):
        """Test permutation matrix shuffles correctly."""
        # Create a simple permutation (reverse order)
        weights = np.eye(ARRAY_SIZE)[::-1]
        simulator.load_weights(weights)

        # Create input with distinct values
        input_vec = np.linspace(-1.0, 1.0, ARRAY_SIZE)

        # Compute
        output = simulator.compute(input_vec)

        # Should be reversed
        expected = input_vec[::-1]
        assert np.allclose(output, expected, atol=0.15)

    def test_repeated_computations(self, simulator, sample_weights):
        """Test that repeated computations give consistent results."""
        simulator.load_weights(sample_weights)

        np.random.seed(42)
        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)

        # Run same computation multiple times
        outputs = [simulator.compute(input_vec) for _ in range(5)]

        # All outputs should be identical
        for i in range(1, len(outputs)):
            assert np.allclose(outputs[0], outputs[i]), \
                f"Output {i} differs from output 0"

    def test_different_inputs(self, simulator, sample_weights):
        """Test that different inputs give different outputs."""
        simulator.load_weights(sample_weights)

        # Two different inputs
        input1 = np.full(ARRAY_SIZE, 0.5)
        input2 = np.full(ARRAY_SIZE, -0.5)

        output1 = simulator.compute(input1)
        output2 = simulator.compute(input2)

        # Outputs should differ
        assert not np.allclose(output1, output2), \
            "Different inputs produced same output"

    def test_sparse_weights(self, simulator):
        """Test with sparse (mostly zero) weights."""
        # Create sparse weights (10% non-zero)
        np.random.seed(42)
        weights = np.zeros((ARRAY_SIZE, ARRAY_SIZE))
        n_nonzero = int(0.1 * ARRAY_SIZE * ARRAY_SIZE)
        indices = np.random.choice(ARRAY_SIZE * ARRAY_SIZE, n_nonzero, replace=False)
        weights.flat[indices] = np.random.uniform(-1.0, 1.0, n_nonzero)

        simulator.load_weights(weights)

        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
        output = simulator.compute(input_vec)

        # Verify output is reasonable
        assert np.all(np.isfinite(output))
        expected = weights @ input_vec
        # Sparse matrix should have smaller outputs on average
        assert np.mean(np.abs(output)) < ARRAY_SIZE

    def test_extreme_weights(self, simulator):
        """Test with extreme weight values at boundaries."""
        # All +1 weights
        weights_pos = np.ones((ARRAY_SIZE, ARRAY_SIZE))
        simulator.load_weights(weights_pos)

        input_vec = np.full(ARRAY_SIZE, 1.0)
        output = simulator.compute(input_vec)

        # Each output should be sum of 27 ones = 27
        expected_val = ARRAY_SIZE
        assert np.allclose(output, expected_val, atol=expected_val * 0.15)

    def test_zero_input(self, simulator, sample_weights):
        """Test with zero input vector."""
        simulator.load_weights(sample_weights)

        input_vec = np.zeros(ARRAY_SIZE)
        output = simulator.compute(input_vec)

        # Output should be near zero
        assert np.allclose(output, 0, atol=0.1)

    def test_unit_vectors(self, simulator, sample_weights):
        """Test with unit vectors (one-hot inputs)."""
        simulator.load_weights(sample_weights)

        for i in range(ARRAY_SIZE):
            input_vec = np.zeros(ARRAY_SIZE)
            input_vec[i] = 1.0

            output = simulator.compute(input_vec)

            # Output should be approximately column i of weights
            expected = sample_weights[:, i]
            assert np.allclose(output, expected, atol=0.15), \
                f"Unit vector {i} failed"


class Test27x27Performance:
    """Performance-related tests for 27x27 array."""

    def test_many_computations(self):
        """Test running many sequential computations."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE)

        np.random.seed(42)
        weights = np.random.uniform(-1.0, 1.0, (ARRAY_SIZE, ARRAY_SIZE))
        sim.load_weights(weights)

        # Run 100 computations
        n_computations = 100
        for i in range(n_computations):
            input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
            output = sim.compute(input_vec)
            assert output.shape == (ARRAY_SIZE,)

    def test_weight_reloading(self):
        """Test reloading weights many times."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE)

        np.random.seed(42)
        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)

        # Reload weights multiple times
        for i in range(10):
            weights = np.random.uniform(-1.0, 1.0, (ARRAY_SIZE, ARRAY_SIZE))
            sim.load_weights(weights)
            output = sim.compute(input_vec)
            assert output.shape == (ARRAY_SIZE,)


class Test27x27Accuracy:
    """Accuracy validation tests for 27x27 array."""

    def test_quantization_error_bounds(self):
        """Test that quantization error is within expected bounds."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE, trits_per_value=5)

        # Use identity to isolate quantization error
        weights = np.eye(ARRAY_SIZE)
        sim.load_weights(weights)

        np.random.seed(42)
        errors = []

        for _ in range(100):
            input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
            output = sim.compute(input_vec)
            error = np.abs(output - input_vec)
            errors.append(np.mean(error))

        mean_error = np.mean(errors)
        # With 5 trits, theoretical precision is 1/243 ~ 0.004
        # But accumulation can increase this
        assert mean_error < 0.1, f"Mean quantization error {mean_error} too high"

    def test_matrix_multiply_accuracy(self):
        """Test matrix multiply accuracy against numpy."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE)

        np.random.seed(42)
        weights = np.random.uniform(-1.0, 1.0, (ARRAY_SIZE, ARRAY_SIZE))
        sim.load_weights(weights)

        errors = []
        for _ in range(50):
            input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
            output = sim.compute(input_vec)
            expected = weights @ input_vec

            # Normalize error by expected magnitude
            rel_error = np.abs(output - expected) / (np.abs(expected) + 0.1)
            errors.append(np.mean(rel_error))

        mean_rel_error = np.mean(errors)
        assert mean_rel_error < 0.2, f"Mean relative error {mean_rel_error} too high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
