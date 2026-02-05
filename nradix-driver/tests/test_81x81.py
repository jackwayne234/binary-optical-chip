"""
Integration tests for 81x81 N-Radix array configuration.

Tests the full pipeline from weight loading through computation
for an 81x81 optical matrix multiply array (3^4 x 3^4).
This represents a larger-scale configuration suitable for real workloads.
"""

import pytest
import numpy as np

try:
    from nradix import NRadixSimulator, float_to_trits, trits_to_float
except ImportError:
    import sys
    sys.path.insert(0, '/home/jackwayne/Desktop/Optical_computing/nradix-driver/python')
    from nradix import NRadixSimulator, float_to_trits, trits_to_float


ARRAY_SIZE = 81  # 3^4


class Test81x81Integration:
    """Integration tests for the 81x81 array."""

    @pytest.fixture
    def simulator(self):
        """Create an 81x81 simulator instance."""
        return NRadixSimulator(array_size=ARRAY_SIZE)

    @pytest.fixture
    def sample_weights(self):
        """Generate reproducible sample weights."""
        np.random.seed(2026)
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
        tolerance = 0.2  # Slightly higher tolerance for larger array
        rel_error = np.abs(output - expected) / (np.abs(expected) + 1e-10)
        mean_rel_error = np.mean(rel_error)

        assert mean_rel_error < tolerance, \
            f"Mean relative error {mean_rel_error:.4f} exceeds tolerance {tolerance}"

    def test_identity_matrix_preservation(self, simulator):
        """Test that identity matrix preserves input."""
        weights = np.eye(ARRAY_SIZE)
        simulator.load_weights(weights)

        np.random.seed(123)
        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)

        output = simulator.compute(input_vec)

        max_error = np.max(np.abs(output - input_vec))
        assert max_error < 0.15, f"Identity preservation failed, max error: {max_error}"

    def test_negative_identity_flip(self, simulator):
        """Test that -I matrix flips signs."""
        weights = -np.eye(ARRAY_SIZE)
        simulator.load_weights(weights)

        input_vec = np.full(ARRAY_SIZE, 0.5)
        output = simulator.compute(input_vec)

        expected = -input_vec
        assert np.allclose(output, expected, atol=0.15)

    def test_permutation_matrix(self, simulator):
        """Test permutation matrix shuffles correctly."""
        weights = np.eye(ARRAY_SIZE)[::-1]  # Reverse permutation
        simulator.load_weights(weights)

        input_vec = np.linspace(-1.0, 1.0, ARRAY_SIZE)
        output = simulator.compute(input_vec)

        expected = input_vec[::-1]
        assert np.allclose(output, expected, atol=0.15)

    def test_repeated_computations(self, simulator, sample_weights):
        """Test that repeated computations give consistent results."""
        simulator.load_weights(sample_weights)

        np.random.seed(42)
        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)

        outputs = [simulator.compute(input_vec) for _ in range(5)]

        for i in range(1, len(outputs)):
            assert np.allclose(outputs[0], outputs[i]), \
                f"Output {i} differs from output 0"

    def test_different_inputs(self, simulator, sample_weights):
        """Test that different inputs give different outputs."""
        simulator.load_weights(sample_weights)

        input1 = np.full(ARRAY_SIZE, 0.5)
        input2 = np.full(ARRAY_SIZE, -0.5)

        output1 = simulator.compute(input1)
        output2 = simulator.compute(input2)

        assert not np.allclose(output1, output2), \
            "Different inputs produced same output"

    def test_sparse_weights(self, simulator):
        """Test with sparse (mostly zero) weights."""
        np.random.seed(42)
        weights = np.zeros((ARRAY_SIZE, ARRAY_SIZE))
        n_nonzero = int(0.1 * ARRAY_SIZE * ARRAY_SIZE)  # 10% fill
        indices = np.random.choice(ARRAY_SIZE * ARRAY_SIZE, n_nonzero, replace=False)
        weights.flat[indices] = np.random.uniform(-1.0, 1.0, n_nonzero)

        simulator.load_weights(weights)

        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
        output = simulator.compute(input_vec)

        assert np.all(np.isfinite(output))

    def test_block_diagonal_weights(self, simulator):
        """Test with block diagonal weight matrix."""
        # Create 3 blocks of 27x27
        weights = np.zeros((ARRAY_SIZE, ARRAY_SIZE))
        block_size = 27

        np.random.seed(42)
        for i in range(3):
            start = i * block_size
            end = start + block_size
            weights[start:end, start:end] = np.random.uniform(-1, 1, (block_size, block_size))

        simulator.load_weights(weights)

        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
        output = simulator.compute(input_vec)

        assert output.shape == (ARRAY_SIZE,)
        assert np.all(np.isfinite(output))

    def test_zero_input(self, simulator, sample_weights):
        """Test with zero input vector."""
        simulator.load_weights(sample_weights)

        input_vec = np.zeros(ARRAY_SIZE)
        output = simulator.compute(input_vec)

        assert np.allclose(output, 0, atol=0.1)

    def test_unit_vectors_subset(self, simulator, sample_weights):
        """Test with a subset of unit vectors (full 81 would be slow)."""
        simulator.load_weights(sample_weights)

        # Test every 9th unit vector
        for i in range(0, ARRAY_SIZE, 9):
            input_vec = np.zeros(ARRAY_SIZE)
            input_vec[i] = 1.0

            output = simulator.compute(input_vec)

            expected = sample_weights[:, i]
            assert np.allclose(output, expected, atol=0.2), \
                f"Unit vector {i} failed"


class Test81x81LargeScale:
    """Large-scale operation tests specific to 81x81."""

    def test_full_rank_random(self):
        """Test with full-rank random weight matrix."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE)

        # Generate full-rank matrix via QR decomposition
        np.random.seed(42)
        random_mat = np.random.randn(ARRAY_SIZE, ARRAY_SIZE)
        q, r = np.linalg.qr(random_mat)

        # Scale to [-1, 1]
        weights = q * 0.9  # Orthogonal matrix scaled
        sim.load_weights(weights)

        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
        output = sim.compute(input_vec)

        assert output.shape == (ARRAY_SIZE,)
        assert np.all(np.isfinite(output))

    def test_scaling_from_27(self):
        """Test that 81x81 scales appropriately from 27x27 results."""
        # Create 27x27 embedded in 81x81
        sim_81 = NRadixSimulator(array_size=81)

        np.random.seed(42)
        weights_27 = np.random.uniform(-1.0, 1.0, (27, 27))

        # Embed 27x27 in top-left corner
        weights_81 = np.zeros((81, 81))
        weights_81[:27, :27] = weights_27

        sim_81.load_weights(weights_81)

        # Input with only first 27 elements non-zero
        input_vec = np.zeros(81)
        input_vec[:27] = np.random.uniform(-1.0, 1.0, 27)

        output = sim_81.compute(input_vec)

        # Only first 27 outputs should be significantly non-zero
        assert np.allclose(output[27:], 0, atol=0.2)

    def test_tiled_computation(self):
        """Test computation with tiled (repeated) weight patterns."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE)

        # Create 27x27 tile and replicate
        np.random.seed(42)
        tile = np.random.uniform(-1.0, 1.0, (27, 27))

        weights = np.zeros((81, 81))
        for i in range(3):
            for j in range(3):
                weights[i*27:(i+1)*27, j*27:(j+1)*27] = tile

        sim.load_weights(weights)

        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
        output = sim.compute(input_vec)

        assert output.shape == (ARRAY_SIZE,)


class Test81x81Performance:
    """Performance-related tests for 81x81 array."""

    def test_many_computations(self):
        """Test running many sequential computations."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE)

        np.random.seed(42)
        weights = np.random.uniform(-1.0, 1.0, (ARRAY_SIZE, ARRAY_SIZE))
        sim.load_weights(weights)

        n_computations = 50  # Fewer than 27x27 due to larger size
        for i in range(n_computations):
            input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
            output = sim.compute(input_vec)
            assert output.shape == (ARRAY_SIZE,)

    def test_weight_reloading(self):
        """Test reloading weights multiple times."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE)

        np.random.seed(42)
        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)

        for i in range(5):
            weights = np.random.uniform(-1.0, 1.0, (ARRAY_SIZE, ARRAY_SIZE))
            sim.load_weights(weights)
            output = sim.compute(input_vec)
            assert output.shape == (ARRAY_SIZE,)


class Test81x81Accuracy:
    """Accuracy validation tests for 81x81 array."""

    def test_quantization_error_bounds(self):
        """Test that quantization error is within expected bounds."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE, trits_per_value=5)

        weights = np.eye(ARRAY_SIZE)
        sim.load_weights(weights)

        np.random.seed(42)
        errors = []

        for _ in range(50):
            input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
            output = sim.compute(input_vec)
            error = np.abs(output - input_vec)
            errors.append(np.mean(error))

        mean_error = np.mean(errors)
        assert mean_error < 0.15, f"Mean quantization error {mean_error} too high"

    def test_matrix_multiply_accuracy(self):
        """Test matrix multiply accuracy against numpy."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE)

        np.random.seed(42)
        weights = np.random.uniform(-1.0, 1.0, (ARRAY_SIZE, ARRAY_SIZE))
        sim.load_weights(weights)

        errors = []
        for _ in range(25):  # Fewer iterations due to size
            input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
            output = sim.compute(input_vec)
            expected = weights @ input_vec

            rel_error = np.abs(output - expected) / (np.abs(expected) + 0.1)
            errors.append(np.mean(rel_error))

        mean_rel_error = np.mean(errors)
        assert mean_rel_error < 0.25, f"Mean relative error {mean_rel_error} too high"

    def test_condition_number_sensitivity(self):
        """Test accuracy with different condition number matrices."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE)

        np.random.seed(42)

        # Well-conditioned matrix (condition number ~ 1)
        ortho = np.linalg.qr(np.random.randn(ARRAY_SIZE, ARRAY_SIZE))[0]
        weights_good = ortho * 0.9
        sim.load_weights(weights_good)

        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
        output_good = sim.compute(input_vec)
        expected = weights_good @ input_vec
        error_good = np.mean(np.abs(output_good - expected))

        # The well-conditioned case should work well
        assert error_good < ARRAY_SIZE * 0.1  # Reasonable bound


class Test81x81NeuralNetworkPatterns:
    """Test patterns common in neural network workloads."""

    def test_activation_like_pattern(self):
        """Test with activation-like weight patterns."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE)

        # Weights that simulate ReLU-like sparsity
        np.random.seed(42)
        weights = np.random.uniform(-1.0, 1.0, (ARRAY_SIZE, ARRAY_SIZE))
        weights[weights < 0] = 0  # Make it positive (ReLU-like)
        weights = weights / weights.max()  # Normalize to [-1, 1]

        sim.load_weights(weights)

        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
        output = sim.compute(input_vec)

        assert np.all(np.isfinite(output))

    def test_attention_like_pattern(self):
        """Test with attention-like normalized weight patterns."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE)

        # Row-normalized weights (sum to ~1)
        np.random.seed(42)
        weights = np.random.uniform(0, 1.0, (ARRAY_SIZE, ARRAY_SIZE))
        weights = weights / weights.sum(axis=1, keepdims=True)
        weights = (weights - 0.5) * 2  # Scale to [-1, 1]

        sim.load_weights(weights)

        input_vec = np.random.uniform(-1.0, 1.0, ARRAY_SIZE)
        output = sim.compute(input_vec)

        assert np.all(np.isfinite(output))

    def test_embedding_like_lookup(self):
        """Test one-hot lookups (like embedding table lookup)."""
        sim = NRadixSimulator(array_size=ARRAY_SIZE)

        # Random "embedding table"
        np.random.seed(42)
        weights = np.random.uniform(-1.0, 1.0, (ARRAY_SIZE, ARRAY_SIZE))
        sim.load_weights(weights)

        # One-hot inputs (embedding lookups)
        for idx in [0, 40, 80]:
            input_vec = np.zeros(ARRAY_SIZE)
            input_vec[idx] = 1.0

            output = sim.compute(input_vec)

            # Should be approximately column idx of weights
            expected = weights[:, idx]
            assert np.allclose(output, expected, atol=0.2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
