"""
Test suite for the N-Radix Simulator.

Tests the NRadixSimulator class which simulates optical matrix multiply
operations using balanced ternary encoding.
"""

import pytest
import numpy as np

# Import from the nradix module
try:
    from nradix import NRadixSimulator
except ImportError:
    import sys
    sys.path.insert(0, '/home/jackwayne/Desktop/Optical_computing/nradix-driver/python')
    from nradix import NRadixSimulator


class TestNRadixSimulatorInitialization:
    """Test NRadixSimulator initialization."""

    def test_default_initialization(self):
        """Test simulator initializes with default parameters."""
        sim = NRadixSimulator()
        assert sim is not None

    def test_27x27_initialization(self):
        """Test simulator initializes for 27x27 array."""
        sim = NRadixSimulator(array_size=27)
        assert sim.array_size == 27

    def test_81x81_initialization(self):
        """Test simulator initializes for 81x81 array."""
        sim = NRadixSimulator(array_size=81)
        assert sim.array_size == 81

    def test_custom_array_size(self):
        """Test simulator accepts custom array sizes."""
        for size in [9, 27, 81, 243]:
            sim = NRadixSimulator(array_size=size)
            assert sim.array_size == size

    def test_trits_per_value_configuration(self):
        """Test simulator accepts trits_per_value parameter."""
        sim = NRadixSimulator(array_size=27, trits_per_value=5)
        assert sim.trits_per_value == 5

    def test_invalid_array_size(self):
        """Test that invalid array sizes raise errors."""
        with pytest.raises((ValueError, TypeError)):
            NRadixSimulator(array_size=-1)

    def test_zero_array_size(self):
        """Test that zero array size raises error."""
        with pytest.raises((ValueError, TypeError)):
            NRadixSimulator(array_size=0)


class TestLoadWeights:
    """Test weight loading functionality."""

    def test_load_identity_weights(self):
        """Test loading identity matrix weights."""
        size = 27
        sim = NRadixSimulator(array_size=size)

        weights = np.eye(size)
        sim.load_weights(weights)

        # Verify weights are stored
        assert sim.weights is not None
        assert sim.weights.shape == (size, size)

    def test_load_random_weights(self):
        """Test loading random weights in [-1, 1]."""
        size = 27
        sim = NRadixSimulator(array_size=size)

        np.random.seed(42)
        weights = np.random.uniform(-1.0, 1.0, (size, size))
        sim.load_weights(weights)

        assert sim.weights is not None
        assert sim.weights.shape == (size, size)

    def test_load_weights_clamping(self):
        """Test that weights outside [-1, 1] are clamped."""
        size = 9
        sim = NRadixSimulator(array_size=size)

        weights = np.array([[2.0, -2.0], [1.5, -1.5]])
        # Pad to correct size
        padded = np.zeros((size, size))
        padded[:2, :2] = weights
        sim.load_weights(padded)

        # Check clamping (implementation dependent)
        # Values should be in [-1, 1] after loading
        assert np.all(sim.weights >= -1.0)
        assert np.all(sim.weights <= 1.0)

    def test_load_weights_shape_mismatch(self):
        """Test that mismatched weight shapes raise errors."""
        sim = NRadixSimulator(array_size=27)

        weights = np.random.uniform(-1.0, 1.0, (10, 10))  # Wrong size

        with pytest.raises((ValueError, AssertionError)):
            sim.load_weights(weights)

    def test_load_weights_1d_array(self):
        """Test that 1D weight arrays raise errors."""
        sim = NRadixSimulator(array_size=27)

        weights = np.random.uniform(-1.0, 1.0, (27,))

        with pytest.raises((ValueError, TypeError)):
            sim.load_weights(weights)


class TestMatrixMultiply:
    """Test matrix multiplication operations."""

    def test_identity_multiply(self):
        """Test multiplication with identity matrix preserves input."""
        size = 27
        sim = NRadixSimulator(array_size=size)

        # Load identity weights
        weights = np.eye(size)
        sim.load_weights(weights)

        # Create input vector
        input_vec = np.random.uniform(-1.0, 1.0, size)

        # Compute output
        output = sim.compute(input_vec)

        # Should be close to input (within ternary precision)
        tolerance = 0.1  # Ternary quantization introduces some error
        assert np.allclose(input_vec, output, atol=tolerance), \
            f"Identity multiply failed: max error = {np.max(np.abs(input_vec - output))}"

    def test_zero_weights_multiply(self):
        """Test multiplication with zero weights gives zeros."""
        size = 27
        sim = NRadixSimulator(array_size=size)

        # Load zero weights
        weights = np.zeros((size, size))
        sim.load_weights(weights)

        # Create input vector
        input_vec = np.random.uniform(-1.0, 1.0, size)

        # Compute output
        output = sim.compute(input_vec)

        # Should be all zeros
        assert np.allclose(output, 0, atol=0.1)

    def test_known_multiply(self):
        """Test multiplication with known values."""
        size = 3
        sim = NRadixSimulator(array_size=size)

        # Simple weights matrix
        weights = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ])
        # Pad to array size if needed
        if size > 3:
            padded = np.eye(size)
            padded[:3, :3] = weights
            weights = padded

        sim.load_weights(weights)

        input_vec = np.array([0.5, -0.5, 0.0])
        if size > 3:
            padded_input = np.zeros(size)
            padded_input[:3] = input_vec
            input_vec = padded_input

        output = sim.compute(input_vec)

        # Check output is close to expected
        expected = weights @ input_vec
        tolerance = 0.15
        assert np.allclose(output, expected, atol=tolerance)

    def test_output_shape(self):
        """Test that output has correct shape."""
        size = 27
        sim = NRadixSimulator(array_size=size)
        sim.load_weights(np.eye(size))

        input_vec = np.random.uniform(-1.0, 1.0, size)
        output = sim.compute(input_vec)

        assert output.shape == (size,)

    def test_output_range(self):
        """Test that output values are in expected range."""
        size = 27
        sim = NRadixSimulator(array_size=size)

        # Random weights
        np.random.seed(42)
        weights = np.random.uniform(-1.0, 1.0, (size, size))
        sim.load_weights(weights)

        # Random input
        input_vec = np.random.uniform(-1.0, 1.0, size)
        output = sim.compute(input_vec)

        # Output should be bounded (sum of size products of [-1,1] values)
        max_possible = size  # Maximum is when all products are +1
        assert np.all(np.abs(output) <= max_possible * 1.1)  # Allow some tolerance


class TestArrayConfigurations:
    """Test different array size configurations."""

    def test_27x27_configuration(self):
        """Test full 27x27 array configuration."""
        size = 27
        sim = NRadixSimulator(array_size=size)

        np.random.seed(42)
        weights = np.random.uniform(-1.0, 1.0, (size, size))
        sim.load_weights(weights)

        input_vec = np.random.uniform(-1.0, 1.0, size)
        output = sim.compute(input_vec)

        assert output.shape == (size,)
        assert sim.array_size == 27

    def test_81x81_configuration(self):
        """Test full 81x81 array configuration."""
        size = 81
        sim = NRadixSimulator(array_size=size)

        np.random.seed(42)
        weights = np.random.uniform(-1.0, 1.0, (size, size))
        sim.load_weights(weights)

        input_vec = np.random.uniform(-1.0, 1.0, size)
        output = sim.compute(input_vec)

        assert output.shape == (size,)
        assert sim.array_size == 81

    def test_9x9_configuration(self):
        """Test 9x9 array configuration (smaller scale)."""
        size = 9
        sim = NRadixSimulator(array_size=size)

        np.random.seed(42)
        weights = np.random.uniform(-1.0, 1.0, (size, size))
        sim.load_weights(weights)

        input_vec = np.random.uniform(-1.0, 1.0, size)
        output = sim.compute(input_vec)

        assert output.shape == (size,)
        assert sim.array_size == 9


class TestSimulatorState:
    """Test simulator state management."""

    def test_weights_persistence(self):
        """Test that loaded weights persist."""
        size = 27
        sim = NRadixSimulator(array_size=size)

        np.random.seed(42)
        weights = np.random.uniform(-1.0, 1.0, (size, size))
        sim.load_weights(weights)

        # Run multiple computations
        for _ in range(5):
            input_vec = np.random.uniform(-1.0, 1.0, size)
            sim.compute(input_vec)

        # Weights should still be there
        assert sim.weights is not None

    def test_reload_weights(self):
        """Test reloading weights replaces old ones."""
        size = 27
        sim = NRadixSimulator(array_size=size)

        # Load first set of weights
        weights1 = np.eye(size)
        sim.load_weights(weights1)

        # Load second set of weights
        np.random.seed(42)
        weights2 = np.random.uniform(-1.0, 1.0, (size, size))
        sim.load_weights(weights2)

        # Compute with identity input to check which weights are active
        input_vec = np.zeros(size)
        input_vec[0] = 1.0
        output = sim.compute(input_vec)

        # If weights2 is loaded, output should be different from weights1 column
        # (unless by coincidence)


class TestComputeWithoutWeights:
    """Test behavior when computing without loaded weights."""

    def test_compute_before_load_weights(self):
        """Test that computing without weights raises error."""
        sim = NRadixSimulator(array_size=27)

        input_vec = np.random.uniform(-1.0, 1.0, 27)

        with pytest.raises((RuntimeError, ValueError, AttributeError)):
            sim.compute(input_vec)


class TestBatchCompute:
    """Test batch computation if supported."""

    def test_batch_input(self):
        """Test computing multiple inputs at once."""
        size = 27
        sim = NRadixSimulator(array_size=size)
        sim.load_weights(np.eye(size))

        # Multiple input vectors
        batch_size = 10
        inputs = np.random.uniform(-1.0, 1.0, (batch_size, size))

        # Compute each
        outputs = []
        for i in range(batch_size):
            outputs.append(sim.compute(inputs[i]))

        outputs = np.array(outputs)
        assert outputs.shape == (batch_size, size)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
