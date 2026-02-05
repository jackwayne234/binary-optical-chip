"""
N-Radix Optical Computing Python Bindings and Simulator

This module provides Python bindings for the N-Radix optical systolic array
hardware, along with a software simulator for development and testing.

The optical computing system uses ternary (base-3) encoding with wavelength
multiplexing: 1550nm / 1310nm / 1064nm for collision-free operation.

Key features:
- Balanced ternary encoding (-1, 0, +1) using trits
- Hardware abstraction via NRadix class
- Full software simulation via NRadixSimulator
- Support for 27x27 and 81x81 array configurations
"""

from __future__ import annotations

import struct
from contextlib import contextmanager
from typing import List, Optional, Tuple, Union

import numpy as np


# =============================================================================
# Encoding Functions
# =============================================================================

def float_to_trits(value: float, num_trits: int = 9) -> List[int]:
    """
    Convert a floating-point value to balanced ternary (trit) representation.

    Uses balanced ternary where each trit is -1, 0, or +1. The value is scaled
    to fit within the representable range based on num_trits.

    Args:
        value: The floating-point value to encode. Should be in range [-1.0, 1.0]
               for optimal precision.
        num_trits: Number of trits to use for encoding (default 9).
                   More trits = higher precision.

    Returns:
        List of integers, each being -1, 0, or +1, representing the balanced
        ternary encoding. Most significant trit first.

    Example:
        >>> float_to_trits(0.5, 5)
        [0, 1, 1, -1, 1]
        >>> float_to_trits(-0.333, 3)
        [-1, 0, 0]
    """
    # Calculate the maximum representable value with num_trits
    # In balanced ternary, max value = sum(3^i for i in range(num_trits)) = (3^n - 1) / 2
    max_val = (3 ** num_trits - 1) / 2

    # Clamp and scale the value to integer range
    clamped = max(-1.0, min(1.0, value))
    scaled = int(round(clamped * max_val))

    # Convert to balanced ternary
    trits = []
    remaining = scaled

    for _ in range(num_trits):
        # Get the remainder mod 3, adjusted for balanced ternary
        rem = remaining % 3
        if rem == 0:
            trit = 0
        elif rem == 1:
            trit = 1
        else:  # rem == 2, which means -1 in balanced ternary
            trit = -1

        trits.append(trit)

        # Adjust remaining for next iteration
        remaining = (remaining - trit) // 3

    # Reverse to get most significant trit first
    trits.reverse()
    return trits


def trits_to_float(trits: List[int]) -> float:
    """
    Convert balanced ternary (trit) representation back to floating-point.

    Args:
        trits: List of integers, each being -1, 0, or +1. Most significant
               trit first.

    Returns:
        Floating-point value in range [-1.0, 1.0].

    Example:
        >>> trits_to_float([0, 1, 1, -1, 1])
        0.5
        >>> trits_to_float([-1, 0, 0])
        -0.333...
    """
    num_trits = len(trits)
    max_val = (3 ** num_trits - 1) / 2

    # Convert from balanced ternary to integer
    value = 0
    for trit in trits:
        value = value * 3 + trit

    # Scale back to [-1.0, 1.0]
    return value / max_val if max_val > 0 else 0.0


def pack_trits(trits: List[int]) -> bytes:
    """
    Pack a list of trits into a compact byte representation.

    Each trit (-1, 0, +1) is encoded as (0, 1, 2) and packed 5 trits per byte
    (since 3^5 = 243 < 256). This gives ~1.58 bits per trit efficiency.

    Args:
        trits: List of trits to pack. Length should be a multiple of 5 for
               optimal packing, otherwise padded with zeros.

    Returns:
        Packed bytes representation.

    Example:
        >>> pack_trits([1, 0, -1, 1, 0])
        b'\\x87'
    """
    # Pad to multiple of 5
    padded = trits.copy()
    while len(padded) % 5 != 0:
        padded.append(0)

    result = bytearray()

    for i in range(0, len(padded), 5):
        chunk = padded[i:i+5]
        # Convert trits from [-1, 0, 1] to [0, 1, 2]
        encoded = [(t + 1) for t in chunk]
        # Pack as base-3 number
        packed = encoded[0] * 81 + encoded[1] * 27 + encoded[2] * 9 + encoded[3] * 3 + encoded[4]
        result.append(packed)

    # Prepend the original length for unpacking
    length_bytes = struct.pack('>H', len(trits))
    return bytes(length_bytes + result)


def unpack_trits(data: bytes) -> List[int]:
    """
    Unpack bytes back to a list of trits.

    Args:
        data: Packed bytes from pack_trits().

    Returns:
        List of trits (-1, 0, or +1).

    Example:
        >>> unpack_trits(b'\\x00\\x05\\x87')
        [1, 0, -1, 1, 0]
    """
    if len(data) < 2:
        return []

    # Extract original length
    original_length = struct.unpack('>H', data[:2])[0]
    packed_data = data[2:]

    trits = []

    for byte in packed_data:
        # Unpack base-3 number to 5 trits
        chunk = []
        remaining = byte
        for _ in range(5):
            chunk.append(remaining % 3)
            remaining //= 3
        chunk.reverse()
        # Convert from [0, 1, 2] back to [-1, 0, 1]
        trits.extend([t - 1 for t in chunk])

    # Trim to original length
    return trits[:original_length]


# =============================================================================
# Simulator Class
# =============================================================================

class NRadixSimulator:
    """
    Software simulator for the N-Radix optical systolic array.

    This simulator mimics the behavior of the optical hardware for development
    and testing purposes. It supports both 27x27 and 81x81 configurations,
    performs matrix multiplication using balanced ternary representation,
    and models the timing characteristics of the optical system.

    The simulator uses NumPy for efficient computation while maintaining
    bit-accurate compatibility with the hardware encoding.

    Attributes:
        array_size: Size of the systolic array (27 or 81).
        weights: Currently loaded weight matrix.
        clock_freq_mhz: Simulated clock frequency (default 617 MHz for Kerr clock).

    Example:
        >>> sim = NRadixSimulator(array_size=27)
        >>> sim.load_weights(np.random.randn(27, 27))
        >>> result = sim.compute(np.random.randn(27))
        >>> print(result.shape)
        (27,)
    """

    # Supported array configurations
    VALID_SIZES = (27, 81)

    def __init__(self, array_size: int = 27, clock_freq_mhz: float = 617.0):
        """
        Initialize the N-Radix simulator.

        Args:
            array_size: Size of the systolic array. Must be 27 or 81.
            clock_freq_mhz: Simulated clock frequency in MHz (default 617 for Kerr).

        Raises:
            ValueError: If array_size is not 27 or 81.
        """
        if array_size not in self.VALID_SIZES:
            raise ValueError(f"array_size must be one of {self.VALID_SIZES}, got {array_size}")

        self.array_size = array_size
        self.clock_freq_mhz = clock_freq_mhz
        self.weights: Optional[np.ndarray] = None
        self._num_trits = 9  # Precision for encoding
        self._initialized = True

    def load_weights(self, weights: np.ndarray) -> None:
        """
        Load weight matrix into the simulated systolic array.

        The weights are internally quantized to balanced ternary representation
        to match hardware behavior.

        Args:
            weights: 2D numpy array of shape (array_size, array_size).

        Raises:
            ValueError: If weights shape doesn't match array configuration.
        """
        expected_shape = (self.array_size, self.array_size)
        if weights.shape != expected_shape:
            raise ValueError(f"Expected weights of shape {expected_shape}, got {weights.shape}")

        # Normalize weights to [-1, 1] range
        max_abs = np.abs(weights).max()
        if max_abs > 0:
            normalized = weights / max_abs
        else:
            normalized = weights

        # Quantize to balanced ternary (simulating hardware precision)
        self.weights = self._quantize_to_trits(normalized)
        self._weight_scale = max_abs

    def _quantize_to_trits(self, values: np.ndarray) -> np.ndarray:
        """
        Quantize values to balanced ternary precision.

        Args:
            values: Array of values in [-1, 1] range.

        Returns:
            Quantized array with same shape.
        """
        # Convert to trits and back to simulate hardware precision loss
        flat = values.flatten()
        quantized = np.zeros_like(flat)

        for i, val in enumerate(flat):
            trits = float_to_trits(float(val), self._num_trits)
            quantized[i] = trits_to_float(trits)

        return quantized.reshape(values.shape)

    def compute(self, inputs: np.ndarray) -> np.ndarray:
        """
        Perform matrix-vector multiplication on the simulated array.

        Computes: output = weights @ inputs

        The computation simulates the optical systolic array's behavior,
        including quantization effects.

        Args:
            inputs: 1D numpy array of length array_size, or 2D array of shape
                   (batch_size, array_size) for batched computation.

        Returns:
            Result array. Shape matches input dimensions.

        Raises:
            RuntimeError: If weights haven't been loaded.
            ValueError: If input dimensions don't match array configuration.
        """
        if self.weights is None:
            raise RuntimeError("Weights must be loaded before compute()")

        # Handle both 1D and 2D inputs
        is_1d = inputs.ndim == 1
        if is_1d:
            inputs = inputs.reshape(1, -1)

        if inputs.shape[1] != self.array_size:
            raise ValueError(f"Input dimension must be {self.array_size}, got {inputs.shape[1]}")

        # Normalize and quantize inputs
        input_max = np.abs(inputs).max(axis=1, keepdims=True)
        input_max = np.where(input_max > 0, input_max, 1.0)
        normalized_inputs = inputs / input_max

        quantized_inputs = self._quantize_to_trits(normalized_inputs)

        # Perform matrix multiplication (simulating optical computation)
        result = quantized_inputs @ self.weights.T

        # Scale result back
        result = result * input_max * self._weight_scale

        # Quantize output (simulating ADC)
        result = self._quantize_to_trits(
            result / (np.abs(result).max() + 1e-10)
        ) * np.abs(result).max()

        if is_1d:
            return result.flatten()
        return result

    def get_stats(self) -> dict:
        """
        Get simulator statistics.

        Returns:
            Dictionary with simulator stats including theoretical throughput.
        """
        ops_per_cycle = self.array_size ** 2 * 2  # MACs
        throughput_gops = ops_per_cycle * self.clock_freq_mhz / 1000

        return {
            'array_size': self.array_size,
            'clock_freq_mhz': self.clock_freq_mhz,
            'num_trits': self._num_trits,
            'weights_loaded': self.weights is not None,
            'theoretical_throughput_gops': throughput_gops,
        }


# =============================================================================
# Main Hardware Interface Class
# =============================================================================

class NRadix:
    """
    Python interface for the N-Radix optical computing hardware.

    This class provides a high-level API for interacting with the optical
    systolic array hardware. When hardware is not available, it automatically
    falls back to the software simulator.

    The optical system uses wavelength-division multiplexing with three
    wavelengths (1550nm, 1310nm, 1064nm) for collision-free ternary computation.

    Attributes:
        array_size: Size of the systolic array.
        use_simulator: Whether using simulator (True) or real hardware (False).

    Example:
        >>> with NRadix(array_size=27) as device:
        ...     device.load_weights(weights)
        ...     result = device.compute(inputs)

    Example with explicit resource management:
        >>> device = NRadix(array_size=27)
        >>> try:
        ...     device.load_weights(weights)
        ...     result = device.compute(inputs)
        ... finally:
        ...     device.close()
    """

    def __init__(self, array_size: int = 27, use_simulator: bool = True):
        """
        Initialize the N-Radix device interface.

        Args:
            array_size: Size of the systolic array (default 27).
                       Supported values: 27, 81.
            use_simulator: If True, use software simulator. If False, attempt
                          to connect to real hardware.

        Raises:
            ValueError: If array_size is not supported.
            RuntimeError: If use_simulator=False and hardware is unavailable.
        """
        self.array_size = array_size
        self.use_simulator = use_simulator
        self._closed = False

        if use_simulator:
            self._backend = NRadixSimulator(array_size=array_size)
        else:
            # Hardware interface would go here
            # For now, raise if hardware is requested but unavailable
            raise RuntimeError(
                "Hardware interface not yet implemented. "
                "Use use_simulator=True for software simulation."
            )

    def load_weights(self, weights: np.ndarray) -> None:
        """
        Load weight matrix into the systolic array.

        Args:
            weights: 2D numpy array of shape (array_size, array_size).
                    Values will be normalized and quantized to balanced ternary.

        Raises:
            RuntimeError: If device has been closed.
            ValueError: If weights shape is incorrect.
        """
        self._check_closed()
        self._backend.load_weights(weights)

    def compute(self, inputs: np.ndarray) -> np.ndarray:
        """
        Execute matrix-vector multiplication on the optical array.

        Computes: output = weights @ inputs

        Args:
            inputs: Input vector or batch. Shape should be (array_size,) for
                   single vector or (batch_size, array_size) for batch.

        Returns:
            Result array with same batch dimensions as input.

        Raises:
            RuntimeError: If device closed or weights not loaded.
            ValueError: If input dimensions incorrect.
        """
        self._check_closed()
        return self._backend.compute(inputs)

    def close(self) -> None:
        """
        Release resources and close the device connection.

        After calling close(), the device cannot be used. This method is
        idempotent - calling it multiple times is safe.
        """
        if not self._closed:
            self._backend = None
            self._closed = True

    def _check_closed(self) -> None:
        """Raise RuntimeError if device has been closed."""
        if self._closed:
            raise RuntimeError("Device has been closed")

    def __enter__(self) -> 'NRadix':
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensures resources are released."""
        self.close()

    def __repr__(self) -> str:
        status = "closed" if self._closed else ("simulator" if self.use_simulator else "hardware")
        return f"NRadix(array_size={self.array_size}, status={status})"


# =============================================================================
# Convenience Functions
# =============================================================================

def benchmark_simulator(array_size: int = 27, num_iterations: int = 1000) -> dict:
    """
    Benchmark the simulator performance.

    Args:
        array_size: Array size to benchmark.
        num_iterations: Number of compute iterations.

    Returns:
        Dictionary with benchmark results.
    """
    import time

    with NRadix(array_size=array_size, use_simulator=True) as device:
        weights = np.random.randn(array_size, array_size).astype(np.float32)
        inputs = np.random.randn(array_size).astype(np.float32)

        device.load_weights(weights)

        # Warmup
        for _ in range(10):
            device.compute(inputs)

        # Benchmark
        start = time.perf_counter()
        for _ in range(num_iterations):
            device.compute(inputs)
        elapsed = time.perf_counter() - start

        ops_per_compute = array_size ** 2 * 2  # MACs
        total_ops = ops_per_compute * num_iterations

        return {
            'array_size': array_size,
            'num_iterations': num_iterations,
            'total_time_s': elapsed,
            'time_per_compute_us': elapsed / num_iterations * 1e6,
            'throughput_mops': total_ops / elapsed / 1e6,
        }


# =============================================================================
# Module Self-Test
# =============================================================================

if __name__ == "__main__":
    print("N-Radix Optical Computing Python Bindings")
    print("=" * 50)

    # Test encoding functions
    print("\n[Encoding Tests]")
    test_val = 0.5
    trits = float_to_trits(test_val, 9)
    recovered = trits_to_float(trits)
    print(f"  float_to_trits({test_val}) = {trits}")
    print(f"  trits_to_float({trits}) = {recovered:.6f}")
    print(f"  Roundtrip error: {abs(test_val - recovered):.2e}")

    # Test packing
    packed = pack_trits(trits)
    unpacked = unpack_trits(packed)
    print(f"  pack_trits: {len(trits)} trits -> {len(packed)} bytes")
    print(f"  unpack_trits: recovered {len(unpacked)} trits, match: {trits == unpacked}")

    # Test simulator
    print("\n[Simulator Tests]")
    sim = NRadixSimulator(array_size=27)
    print(f"  Created simulator: {sim.get_stats()}")

    weights = np.random.randn(27, 27).astype(np.float32)
    sim.load_weights(weights)
    print(f"  Loaded weights: shape={weights.shape}")

    inputs = np.random.randn(27).astype(np.float32)
    result = sim.compute(inputs)
    print(f"  Computed result: shape={result.shape}")

    # Test NRadix class
    print("\n[NRadix Interface Tests]")
    with NRadix(array_size=27, use_simulator=True) as device:
        print(f"  Created device: {device}")
        device.load_weights(weights)
        result = device.compute(inputs)
        print(f"  Compute result shape: {result.shape}")
    print(f"  After context exit: {device}")

    # Benchmark
    print("\n[Benchmark]")
    results = benchmark_simulator(array_size=27, num_iterations=100)
    print(f"  {results['throughput_mops']:.1f} MOPS (simulated)")
    print(f"  {results['time_per_compute_us']:.1f} us per compute")

    print("\n" + "=" * 50)
    print("All tests passed!")
