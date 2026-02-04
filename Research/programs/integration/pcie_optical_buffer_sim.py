#!/usr/bin/env python3
# Copyright (c) 2026 Christopher Riner
# Licensed under the MIT License. See LICENSE file for details.
#
# Wavelength-Division Ternary Optical Computer
# https://github.com/jackwayne234/-wavelength-ternary-optical-computer
#
# This file is part of an open source research project to develop a
# ternary optical computer using wavelength-division multiplexing.
# The research is documented in the paper published on Zenodo:
# DOI: 10.5281/zenodo.18437600

"""
PCIe to Optical Chip Data Flow Interface Simulation

This module simulates the data flow interface between a standard PCIe host
and the optical ternary computing chip. It models:

1. PCIe Input Side:
   - PCIe 4.0 x16 bandwidth (~32 GB/s max)
   - 64-bit word input from host
   - Configurable input data rate

2. FIFO Buffer:
   - Elastic buffer that absorbs speed differences
   - Tracks fill level, overflow/underflow conditions
   - Configurable depth

3. Binary to Ternary Conversion:
   - Convert 64-bit binary words to ternary (base-3) representation
   - 81-trit word output (matches the optical chip's ALU width)
   - Tracks conversion timing

4. Optical Chip Interface:
   - 617 MHz clock rate
   - 81-trit words consumed per cycle
   - Models as a consumer that pulls from the buffer

5. Results Path (reverse direction):
   - Optical chip outputs 81-trit results
   - Ternary to binary conversion
   - Buffer back to host

The simulation validates that the interface can sustain the required throughput
without buffer overflow or underflow under various workload scenarios.

Key Insight:
    64 bits of binary data encodes 2^64 possible values
    81 trits of ternary data encodes 3^81 possible values
    3^81 >> 2^64, so 81 trits can always represent a 64-bit value
    (Actually, only ~41 trits are needed for 64 bits, but we pad to 81)

Author: Wavelength-Division Ternary Optical Computer Project
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from collections import deque
import time


# =============================================================================
# PHYSICAL CONSTANTS AND SYSTEM PARAMETERS
# =============================================================================

# PCIe 4.0 x16 specifications
PCIE_4_X16_BANDWIDTH_GBPS = 256      # Raw bandwidth: 16 lanes * 16 GT/s
PCIE_4_X16_BANDWIDTH_GBS = 32        # After 128b/130b encoding: ~31.5 GB/s
PCIE_WORD_BITS = 64                  # Standard 64-bit word from host

# Optical chip specifications (from ARCHITECTURE_NOTES.md)
OPTICAL_CLOCK_MHZ = 617              # Kerr resonator master clock
OPTICAL_WORD_TRITS = 81              # 81-trit ALU width
OPTICAL_CYCLE_NS = 1000 / OPTICAL_CLOCK_MHZ  # ~1.62 ns per cycle

# Conversion constants
TRITS_PER_64BIT = 41                 # ceil(64 * log(2) / log(3)) = 41 trits needed
PADDING_TRITS = OPTICAL_WORD_TRITS - TRITS_PER_64BIT  # 40 padding trits

# Timing
BINARY_TO_TERNARY_CYCLES = 2         # Clock cycles for B2T conversion
TERNARY_TO_BINARY_CYCLES = 2         # Clock cycles for T2B conversion


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TernaryWord:
    """
    Represents an 81-trit ternary word.

    Uses balanced ternary: each trit is -1, 0, or +1.
    Stored as a list of integers for simulation simplicity.
    """
    trits: List[int] = field(default_factory=lambda: [0] * OPTICAL_WORD_TRITS)

    @classmethod
    def from_binary(cls, value: int) -> 'TernaryWord':
        """
        Convert a 64-bit unsigned integer to balanced ternary.

        Balanced ternary conversion:
        - Divide by 3, remainder determines trit
        - Remainder 0 -> trit 0
        - Remainder 1 -> trit +1
        - Remainder 2 -> trit -1, carry +1 to next position

        This naturally handles negative numbers through the balanced representation.
        """
        trits = []
        n = value

        # Handle negative numbers by using two's complement interpretation
        if n < 0:
            n = n & 0xFFFFFFFFFFFFFFFF  # Mask to 64 bits

        while n != 0 and len(trits) < OPTICAL_WORD_TRITS:
            remainder = n % 3
            if remainder == 0:
                trits.append(0)
                n = n // 3
            elif remainder == 1:
                trits.append(1)
                n = n // 3
            else:  # remainder == 2
                trits.append(-1)
                n = (n + 1) // 3

        # Pad to 81 trits
        while len(trits) < OPTICAL_WORD_TRITS:
            trits.append(0)

        return cls(trits=trits)

    def to_binary(self) -> int:
        """Convert balanced ternary back to integer."""
        result = 0
        for i, trit in enumerate(self.trits):
            result += trit * (3 ** i)

        # Clamp to 64-bit range for host interface
        if result > 0x7FFFFFFFFFFFFFFF:
            result = result & 0xFFFFFFFFFFFFFFFF

        return result

    def __str__(self) -> str:
        """String representation showing first few trits."""
        trit_str = ''.join({-1: 'T', 0: '0', 1: '1'}[t] for t in self.trits[:12])
        return f"[{trit_str}...] = {self.to_binary()}"


@dataclass
class FIFOBuffer:
    """
    Elastic FIFO buffer between PCIe and optical chip.

    Absorbs timing differences between the bursty PCIe input
    and the steady optical chip consumption rate.

    Tracks:
    - Current fill level
    - High/low water marks
    - Overflow/underflow events
    """
    depth: int
    name: str = "FIFO"

    # Internal state
    queue: deque = field(default_factory=deque)

    # Statistics
    total_writes: int = 0
    total_reads: int = 0
    overflow_count: int = 0
    underflow_count: int = 0
    max_fill: int = 0
    min_fill: int = 0
    fill_samples: List[int] = field(default_factory=list)

    def __post_init__(self):
        self.queue = deque(maxlen=None)  # We track overflow manually
        self.min_fill = self.depth  # Will be updated on first sample

    def write(self, item) -> bool:
        """
        Write an item to the FIFO.

        Returns:
            True if successful, False if overflow
        """
        if len(self.queue) >= self.depth:
            self.overflow_count += 1
            return False

        self.queue.append(item)
        self.total_writes += 1

        # Update statistics
        current_fill = len(self.queue)
        self.max_fill = max(self.max_fill, current_fill)

        return True

    def read(self) -> Optional[any]:
        """
        Read an item from the FIFO.

        Returns:
            Item if available, None if underflow
        """
        if len(self.queue) == 0:
            self.underflow_count += 1
            return None

        item = self.queue.popleft()
        self.total_reads += 1

        # Update statistics
        current_fill = len(self.queue)
        self.min_fill = min(self.min_fill, current_fill)

        return item

    def peek_fill_level(self) -> int:
        """Get current fill level without modifying state."""
        return len(self.queue)

    def sample_fill_level(self):
        """Record current fill level for statistics."""
        self.fill_samples.append(len(self.queue))

    def get_utilization(self) -> float:
        """Get average buffer utilization (0.0 to 1.0)."""
        if not self.fill_samples:
            return 0.0
        return np.mean(self.fill_samples) / self.depth

    def is_empty(self) -> bool:
        return len(self.queue) == 0

    def is_full(self) -> bool:
        return len(self.queue) >= self.depth


@dataclass
class SimulationMetrics:
    """Tracks all simulation metrics for analysis."""

    # Timing
    total_sim_time_ns: float = 0.0
    total_cycles: int = 0

    # Throughput (forward path: host -> optical)
    host_words_sent: int = 0
    optical_words_consumed: int = 0
    conversion_latency_ns: float = 0.0

    # Throughput (return path: optical -> host)
    optical_results_produced: int = 0
    host_words_received: int = 0

    # Bandwidth
    effective_input_bandwidth_gbs: float = 0.0
    effective_output_bandwidth_gbs: float = 0.0
    theoretical_max_bandwidth_gbs: float = PCIE_4_X16_BANDWIDTH_GBS

    # Latency tracking
    latencies_ns: List[float] = field(default_factory=list)

    # Buffer statistics
    input_buffer_utilization: float = 0.0
    output_buffer_utilization: float = 0.0
    input_overflows: int = 0
    input_underflows: int = 0
    output_overflows: int = 0
    output_underflows: int = 0

    def avg_latency_ns(self) -> float:
        """Calculate average end-to-end latency."""
        if not self.latencies_ns:
            return 0.0
        return np.mean(self.latencies_ns)

    def p99_latency_ns(self) -> float:
        """Calculate 99th percentile latency."""
        if not self.latencies_ns:
            return 0.0
        return np.percentile(self.latencies_ns, 99)


# =============================================================================
# INTERFACE SIMULATION
# =============================================================================

class PCIeOpticalInterface:
    """
    Simulates the complete PCIe to optical chip data flow interface.

    Architecture:

        ┌─────────────┐     ┌─────────┐     ┌───────────┐     ┌──────────────┐
        │  PCIe Host  │────▶│  Input  │────▶│  Binary   │────▶│  Optical     │
        │  (64-bit)   │     │  FIFO   │     │  to       │     │  Chip        │
        │             │     │         │     │  Ternary  │     │  (81-trit)   │
        └─────────────┘     └─────────┘     └───────────┘     └──────┬───────┘
                                                                     │
        ┌─────────────┐     ┌─────────┐     ┌───────────┐            │
        │  PCIe Host  │◀────│  Output │◀────│  Ternary  │◀───────────┘
        │  (64-bit)   │     │  FIFO   │     │  to       │
        │             │     │         │     │  Binary   │
        └─────────────┘     └─────────┘     └───────────┘

    Timing model:
    - Optical chip runs at 617 MHz (1.62 ns cycle)
    - PCIe input is bursty but averages up to 32 GB/s
    - FIFOs absorb timing differences
    - Conversion takes 2 cycles each direction
    """

    def __init__(
        self,
        input_buffer_depth: int = 1024,
        output_buffer_depth: int = 1024,
        verbose: bool = False
    ):
        """
        Initialize the interface simulation.

        Args:
            input_buffer_depth: Depth of input FIFO (in 64-bit words)
            output_buffer_depth: Depth of output FIFO (in 81-trit words)
            verbose: Print detailed progress
        """
        self.verbose = verbose

        # Create buffers
        self.input_fifo = FIFOBuffer(depth=input_buffer_depth, name="Input FIFO")
        self.output_fifo = FIFOBuffer(depth=output_buffer_depth, name="Output FIFO")

        # Conversion pipeline state
        self.b2t_pipeline: deque = deque()  # Binary-to-ternary pipeline
        self.t2b_pipeline: deque = deque()  # Ternary-to-binary pipeline

        # Timing state
        self.current_time_ns = 0.0
        self.current_cycle = 0

        # Metrics
        self.metrics = SimulationMetrics()

        # Latency tracking (word_id -> entry_time_ns)
        self.inflight_latencies: dict = {}
        self.next_word_id = 0

    def reset(self):
        """Reset simulation state."""
        self.input_fifo = FIFOBuffer(
            depth=self.input_fifo.depth,
            name="Input FIFO"
        )
        self.output_fifo = FIFOBuffer(
            depth=self.output_fifo.depth,
            name="Output FIFO"
        )
        self.b2t_pipeline.clear()
        self.t2b_pipeline.clear()
        self.current_time_ns = 0.0
        self.current_cycle = 0
        self.metrics = SimulationMetrics()
        self.inflight_latencies.clear()
        self.next_word_id = 0

    def inject_binary_word(self, value: int) -> Tuple[bool, int]:
        """
        Inject a 64-bit binary word from the PCIe host.

        Args:
            value: 64-bit unsigned integer

        Returns:
            Tuple of (success, word_id)
        """
        word_id = self.next_word_id
        self.next_word_id += 1

        # Try to write to input FIFO
        success = self.input_fifo.write((value, word_id, self.current_time_ns))

        if success:
            self.metrics.host_words_sent += 1
            self.inflight_latencies[word_id] = self.current_time_ns

        return success, word_id

    def receive_binary_result(self) -> Optional[Tuple[int, int]]:
        """
        Receive a 64-bit result destined for the PCIe host.

        Returns:
            Tuple of (value, word_id) if available, None otherwise
        """
        item = self.output_fifo.read()
        if item is None:
            return None

        value, word_id = item
        self.metrics.host_words_received += 1

        # Record latency if we were tracking this word
        if word_id in self.inflight_latencies:
            latency = self.current_time_ns - self.inflight_latencies[word_id]
            self.metrics.latencies_ns.append(latency)
            del self.inflight_latencies[word_id]

        return value, word_id

    def _step_conversion_pipelines(self):
        """
        Advance the binary<->ternary conversion pipelines by one cycle.

        Each conversion takes BINARY_TO_TERNARY_CYCLES or TERNARY_TO_BINARY_CYCLES
        clock cycles to complete.
        """
        # ===== Binary-to-Ternary Pipeline (Host -> Optical) =====

        # Age existing pipeline entries
        aged_b2t = []
        for (value, word_id, age) in self.b2t_pipeline:
            if age + 1 >= BINARY_TO_TERNARY_CYCLES:
                # Conversion complete - item ready for optical chip
                ternary = TernaryWord.from_binary(value)
                aged_b2t.append(('complete', ternary, word_id))
            else:
                aged_b2t.append(('pending', value, word_id, age + 1))

        self.b2t_pipeline.clear()

        # Process completed conversions (send to optical chip)
        # and keep pending ones in pipeline
        for item in aged_b2t:
            if item[0] == 'complete':
                _, ternary, word_id = item
                self.metrics.optical_words_consumed += 1

                # Simulate optical chip processing (instant for now)
                # In reality, this would go to the optical ALU
                # For this sim, we immediately create a result
                result_ternary = ternary  # Echo back (would be ALU result)

                # Put result into T2B pipeline
                self.t2b_pipeline.append((result_ternary, word_id, 0))
            else:
                _, value, word_id, age = item
                self.b2t_pipeline.append((value, word_id, age))

        # Pull new item from input FIFO into B2T pipeline
        if not self.input_fifo.is_empty():
            item = self.input_fifo.read()
            if item:
                value, word_id, _ = item
                self.b2t_pipeline.append((value, word_id, 0))

        # ===== Ternary-to-Binary Pipeline (Optical -> Host) =====

        # Age existing pipeline entries
        aged_t2b = []
        for (ternary, word_id, age) in self.t2b_pipeline:
            if age + 1 >= TERNARY_TO_BINARY_CYCLES:
                # Conversion complete - ready for host
                binary_value = ternary.to_binary()
                aged_t2b.append(('complete', binary_value, word_id))
            else:
                aged_t2b.append(('pending', ternary, word_id, age + 1))

        self.t2b_pipeline.clear()

        # Process completed conversions (send to output FIFO)
        for item in aged_t2b:
            if item[0] == 'complete':
                _, binary_value, word_id = item
                self.output_fifo.write((binary_value, word_id))
                self.metrics.optical_results_produced += 1
            else:
                _, ternary, word_id, age = item
                self.t2b_pipeline.append((ternary, word_id, age))

    def step_cycle(self):
        """
        Advance the simulation by one optical clock cycle.

        At 617 MHz, each cycle is ~1.62 ns.
        """
        # Update timing
        self.current_cycle += 1
        self.current_time_ns += OPTICAL_CYCLE_NS

        # Process conversion pipelines
        self._step_conversion_pipelines()

        # Sample buffer fill levels (every 100 cycles to reduce memory)
        if self.current_cycle % 100 == 0:
            self.input_fifo.sample_fill_level()
            self.output_fifo.sample_fill_level()

    def run_cycles(self, n_cycles: int):
        """Run simulation for n optical clock cycles."""
        for _ in range(n_cycles):
            self.step_cycle()

    def finalize_metrics(self):
        """Calculate final metrics after simulation."""
        self.metrics.total_sim_time_ns = self.current_time_ns
        self.metrics.total_cycles = self.current_cycle

        # Calculate effective bandwidths
        if self.current_time_ns > 0:
            # Input bandwidth: 64-bit words sent, converted to GB/s
            bytes_in = self.metrics.host_words_sent * 8
            self.metrics.effective_input_bandwidth_gbs = bytes_in / self.current_time_ns

            # Output bandwidth: 64-bit words received
            bytes_out = self.metrics.host_words_received * 8
            self.metrics.effective_output_bandwidth_gbs = bytes_out / self.current_time_ns

        # Buffer statistics
        self.metrics.input_buffer_utilization = self.input_fifo.get_utilization()
        self.metrics.output_buffer_utilization = self.output_fifo.get_utilization()
        self.metrics.input_overflows = self.input_fifo.overflow_count
        self.metrics.input_underflows = self.input_fifo.underflow_count
        self.metrics.output_overflows = self.output_fifo.overflow_count
        self.metrics.output_underflows = self.output_fifo.underflow_count

        # Conversion latency (cycles * cycle time)
        self.metrics.conversion_latency_ns = (
            BINARY_TO_TERNARY_CYCLES + TERNARY_TO_BINARY_CYCLES
        ) * OPTICAL_CYCLE_NS


# =============================================================================
# SIMULATION SCENARIOS
# =============================================================================

def scenario_burst_input(
    interface: PCIeOpticalInterface,
    burst_size: int = 1000,
    burst_count: int = 10,
    inter_burst_cycles: int = 500
) -> SimulationMetrics:
    """
    Scenario 1: Burst Input (Weight Loading)

    Simulates loading neural network weights where data arrives in bursts
    at full PCIe bandwidth, with gaps between bursts.

    This tests:
    - Buffer ability to absorb bursts
    - Recovery between bursts
    - Overflow handling

    Args:
        interface: The interface to test
        burst_size: Number of 64-bit words per burst
        burst_count: Number of bursts
        inter_burst_cycles: Optical cycles between bursts

    Returns:
        Simulation metrics
    """
    print(f"\n{'='*60}")
    print("SCENARIO: Burst Input (Weight Loading)")
    print(f"{'='*60}")
    print(f"  Burst size: {burst_size} words (64-bit)")
    print(f"  Burst count: {burst_count}")
    print(f"  Inter-burst gap: {inter_burst_cycles} cycles ({inter_burst_cycles * OPTICAL_CYCLE_NS:.1f} ns)")

    interface.reset()

    # Generate test data
    np.random.seed(42)
    test_data = np.random.randint(0, 2**63, size=burst_size * burst_count, dtype=np.uint64)

    data_idx = 0
    overflows_in_burst = 0

    for burst in range(burst_count):
        # Inject burst at maximum rate
        burst_start_idx = data_idx
        while data_idx < burst_start_idx + burst_size:
            success, _ = interface.inject_binary_word(int(test_data[data_idx]))
            if success:
                data_idx += 1
            else:
                overflows_in_burst += 1
                # Run some cycles to drain buffer
                interface.run_cycles(10)

        # Run cycles between bursts (optical chip processing)
        interface.run_cycles(inter_burst_cycles)

        # Also drain output buffer
        while True:
            result = interface.receive_binary_result()
            if result is None:
                break

    # Drain remaining data
    for _ in range(5000):
        interface.step_cycle()
        interface.receive_binary_result()

    interface.finalize_metrics()

    print(f"\nResults:")
    print(f"  Words sent: {interface.metrics.host_words_sent}")
    print(f"  Words received: {interface.metrics.host_words_received}")
    print(f"  Overflows during bursts: {overflows_in_burst}")
    print(f"  Avg latency: {interface.metrics.avg_latency_ns():.1f} ns")
    print(f"  Input buffer utilization: {interface.metrics.input_buffer_utilization*100:.1f}%")

    return interface.metrics


def scenario_streaming_input(
    interface: PCIeOpticalInterface,
    stream_duration_us: float = 100.0,
    input_rate_fraction: float = 0.8
) -> SimulationMetrics:
    """
    Scenario 2: Streaming Input (Inference)

    Simulates continuous inference where data streams in at a steady rate
    slightly below the optical chip's consumption rate.

    This tests:
    - Sustained throughput
    - Buffer stability
    - Steady-state latency

    Args:
        interface: The interface to test
        stream_duration_us: Duration of streaming in microseconds
        input_rate_fraction: Fraction of optical chip rate (0.0 to 1.0)

    Returns:
        Simulation metrics
    """
    print(f"\n{'='*60}")
    print("SCENARIO: Streaming Input (Inference)")
    print(f"{'='*60}")
    print(f"  Duration: {stream_duration_us:.1f} us")
    print(f"  Input rate: {input_rate_fraction*100:.0f}% of optical chip rate")

    interface.reset()

    # Calculate timing
    duration_ns = stream_duration_us * 1000
    total_cycles = int(duration_ns / OPTICAL_CYCLE_NS)

    # Input rate: inject one word every N cycles
    # If fraction = 1.0, inject every cycle
    # If fraction = 0.5, inject every 2 cycles
    inject_interval = int(1.0 / input_rate_fraction) if input_rate_fraction > 0 else total_cycles + 1

    print(f"  Total cycles: {total_cycles}")
    print(f"  Inject interval: every {inject_interval} cycles")

    np.random.seed(123)

    for cycle in range(total_cycles):
        # Inject input at configured rate
        if cycle % inject_interval == 0:
            value = np.random.randint(0, 2**63, dtype=np.uint64)
            interface.inject_binary_word(int(value))

        # Step the simulation
        interface.step_cycle()

        # Drain output (host always ready)
        interface.receive_binary_result()

    # Drain any remaining
    for _ in range(1000):
        interface.step_cycle()
        interface.receive_binary_result()

    interface.finalize_metrics()

    print(f"\nResults:")
    print(f"  Words sent: {interface.metrics.host_words_sent}")
    print(f"  Words received: {interface.metrics.host_words_received}")
    print(f"  Effective throughput: {interface.metrics.effective_input_bandwidth_gbs:.2f} GB/s")
    print(f"  Avg latency: {interface.metrics.avg_latency_ns():.1f} ns")
    print(f"  P99 latency: {interface.metrics.p99_latency_ns():.1f} ns")
    print(f"  Input buffer utilization: {interface.metrics.input_buffer_utilization*100:.1f}%")

    return interface.metrics


def scenario_backpressure(
    interface: PCIeOpticalInterface,
    duration_us: float = 50.0
) -> SimulationMetrics:
    """
    Scenario 3: Backpressure Handling

    Simulates what happens when the host tries to push data faster than
    the optical chip can consume it. Tests overflow handling and recovery.

    Args:
        interface: The interface to test
        duration_us: Duration of test in microseconds

    Returns:
        Simulation metrics
    """
    print(f"\n{'='*60}")
    print("SCENARIO: Backpressure Handling")
    print(f"{'='*60}")
    print(f"  Duration: {duration_us:.1f} us")
    print(f"  Input rate: MAXIMUM (faster than optical chip)")

    interface.reset()

    duration_ns = duration_us * 1000
    total_cycles = int(duration_ns / OPTICAL_CYCLE_NS)

    print(f"  Total cycles: {total_cycles}")
    print(f"  Buffer depth: {interface.input_fifo.depth}")

    np.random.seed(456)

    # Track backpressure events
    backpressure_cycles = 0

    for cycle in range(total_cycles):
        # Try to inject at every cycle (overwhelming rate)
        for _ in range(3):  # Try 3 words per cycle
            value = np.random.randint(0, 2**63, dtype=np.uint64)
            success, _ = interface.inject_binary_word(int(value))
            if not success:
                backpressure_cycles += 1

        # Step the simulation
        interface.step_cycle()

        # Drain output
        interface.receive_binary_result()

    # Drain remaining
    drain_cycles = 0
    while interface.input_fifo.peek_fill_level() > 0 or len(interface.b2t_pipeline) > 0:
        interface.step_cycle()
        interface.receive_binary_result()
        drain_cycles += 1
        if drain_cycles > 10000:
            break

    interface.finalize_metrics()

    print(f"\nResults:")
    print(f"  Words sent: {interface.metrics.host_words_sent}")
    print(f"  Words received: {interface.metrics.host_words_received}")
    print(f"  Input overflows: {interface.metrics.input_overflows}")
    print(f"  Backpressure events: {backpressure_cycles}")
    print(f"  Drain cycles needed: {drain_cycles}")
    print(f"  Max buffer fill: {interface.input_fifo.max_fill}")
    print(f"  Avg latency: {interface.metrics.avg_latency_ns():.1f} ns")

    return interface.metrics


def scenario_variable_compute_time(
    interface: PCIeOpticalInterface,
    duration_us: float = 100.0,
    compute_cycles_range: Tuple[int, int] = (1, 10)
) -> SimulationMetrics:
    """
    Scenario 4: Variable Compute Time

    Simulates varying optical chip computation time (e.g., different
    operations take different numbers of cycles).

    Args:
        interface: The interface to test
        duration_us: Duration in microseconds
        compute_cycles_range: (min, max) cycles for compute operations

    Returns:
        Simulation metrics
    """
    print(f"\n{'='*60}")
    print("SCENARIO: Variable Compute Time")
    print(f"{'='*60}")
    print(f"  Duration: {duration_us:.1f} us")
    print(f"  Compute time range: {compute_cycles_range[0]}-{compute_cycles_range[1]} cycles")

    interface.reset()

    duration_ns = duration_us * 1000
    total_cycles = int(duration_ns / OPTICAL_CYCLE_NS)

    np.random.seed(789)

    # Modify the interface behavior: variable processing
    # We simulate this by varying how often we read from the output
    compute_cycles = np.random.randint(
        compute_cycles_range[0],
        compute_cycles_range[1] + 1,
        size=total_cycles
    )

    cycles_until_next_output = 0

    for cycle in range(total_cycles):
        # Inject at steady rate (every 2 cycles)
        if cycle % 2 == 0:
            value = np.random.randint(0, 2**63, dtype=np.uint64)
            interface.inject_binary_word(int(value))

        interface.step_cycle()

        # Variable output rate based on "compute time"
        if cycles_until_next_output <= 0:
            interface.receive_binary_result()
            cycles_until_next_output = compute_cycles[cycle]
        else:
            cycles_until_next_output -= 1

    # Drain remaining
    for _ in range(2000):
        interface.step_cycle()
        interface.receive_binary_result()

    interface.finalize_metrics()

    print(f"\nResults:")
    print(f"  Words sent: {interface.metrics.host_words_sent}")
    print(f"  Words received: {interface.metrics.host_words_received}")
    print(f"  Avg latency: {interface.metrics.avg_latency_ns():.1f} ns")
    print(f"  P99 latency: {interface.metrics.p99_latency_ns():.1f} ns")
    print(f"  Output buffer utilization: {interface.metrics.output_buffer_utilization*100:.1f}%")

    return interface.metrics


# =============================================================================
# RESULTS SUMMARY
# =============================================================================

def print_summary_table(results: dict):
    """
    Print a summary table of all scenario results.

    Args:
        results: Dict mapping scenario names to SimulationMetrics
    """
    print("\n")
    print("=" * 90)
    print("                        PCIe-OPTICAL INTERFACE SIMULATION RESULTS")
    print("=" * 90)
    print()

    # System parameters
    print("System Parameters:")
    print(f"  PCIe Bandwidth:        {PCIE_4_X16_BANDWIDTH_GBS} GB/s (PCIe 4.0 x16)")
    print(f"  Optical Clock:         {OPTICAL_CLOCK_MHZ} MHz")
    print(f"  Optical Cycle Time:    {OPTICAL_CYCLE_NS:.2f} ns")
    print(f"  Binary Word Size:      {PCIE_WORD_BITS} bits")
    print(f"  Ternary Word Size:     {OPTICAL_WORD_TRITS} trits")
    print(f"  Trits for 64-bit:      {TRITS_PER_64BIT} (with {PADDING_TRITS} padding)")
    print(f"  Conversion Latency:    {(BINARY_TO_TERNARY_CYCLES + TERNARY_TO_BINARY_CYCLES) * OPTICAL_CYCLE_NS:.1f} ns")
    print()

    # Results table
    print("-" * 90)
    print(f"{'Scenario':<25} {'Words In':>10} {'Words Out':>10} {'Throughput':>12} "
          f"{'Avg Lat':>10} {'P99 Lat':>10} {'Overflows':>10}")
    print(f"{'':<25} {'':>10} {'':>10} {'(GB/s)':>12} {'(ns)':>10} {'(ns)':>10} {'':>10}")
    print("-" * 90)

    for name, metrics in results.items():
        print(f"{name:<25} "
              f"{metrics.host_words_sent:>10,} "
              f"{metrics.host_words_received:>10,} "
              f"{metrics.effective_input_bandwidth_gbs:>12.2f} "
              f"{metrics.avg_latency_ns():>10.1f} "
              f"{metrics.p99_latency_ns():>10.1f} "
              f"{metrics.input_overflows:>10}")

    print("-" * 90)
    print()

    # Buffer statistics
    print("Buffer Statistics:")
    print("-" * 90)
    print(f"{'Scenario':<25} {'In Util':>10} {'Out Util':>10} {'In Max':>10} "
          f"{'In Overflows':>12} {'In Underflows':>14}")
    print("-" * 90)

    for name, metrics in results.items():
        # Get the interface for this scenario's buffer stats
        print(f"{name:<25} "
              f"{metrics.input_buffer_utilization*100:>9.1f}% "
              f"{metrics.output_buffer_utilization*100:>9.1f}% "
              f"{'N/A':>10} "
              f"{metrics.input_overflows:>12} "
              f"{metrics.input_underflows:>14}")

    print("-" * 90)
    print()

    # Analysis
    print("Analysis:")
    print("-" * 90)

    # Theoretical maximum throughput
    optical_throughput_words_per_sec = OPTICAL_CLOCK_MHZ * 1e6
    optical_throughput_gbs = optical_throughput_words_per_sec * 8 / 1e9

    print(f"  Optical chip max throughput: {optical_throughput_gbs:.2f} GB/s "
          f"({OPTICAL_CLOCK_MHZ} MHz * 64 bits)")
    print(f"  PCIe 4.0 x16 max bandwidth:  {PCIE_4_X16_BANDWIDTH_GBS:.2f} GB/s")
    print()

    if optical_throughput_gbs < PCIE_4_X16_BANDWIDTH_GBS:
        print("  BOTTLENECK: Optical chip (617 MHz clock)")
        print(f"  The optical chip can process {optical_throughput_gbs:.2f} GB/s,")
        print(f"  which is {optical_throughput_gbs/PCIE_4_X16_BANDWIDTH_GBS*100:.1f}% of PCIe bandwidth.")
        print()
        print("  RECOMMENDATION: This is acceptable for compute-bound workloads.")
        print("  For memory-bound workloads, consider multiple optical chips or")
        print("  increasing the clock rate.")
    else:
        print("  BOTTLENECK: PCIe bandwidth")
        print("  Consider PCIe 5.0 or multiple lanes for higher throughput.")

    print()
    print("=" * 90)
    print("                              END OF SIMULATION REPORT")
    print("=" * 90)


# =============================================================================
# CONVERSION VERIFICATION
# =============================================================================

def verify_ternary_conversion():
    """
    Verify that binary-to-ternary and ternary-to-binary conversions
    are correct and lossless.
    """
    print("\n" + "=" * 60)
    print("TERNARY CONVERSION VERIFICATION")
    print("=" * 60)

    test_values = [
        0,
        1,
        2,
        3,
        42,
        255,
        65535,
        2**32 - 1,
        2**63 - 1,
        2**64 - 1,  # Max 64-bit unsigned
    ]

    print(f"\n{'Input Value':<25} {'Ternary (first 12)':<20} {'Recovered':<25} {'Match':>8}")
    print("-" * 80)

    all_match = True
    for val in test_values:
        ternary = TernaryWord.from_binary(val)
        recovered = ternary.to_binary()

        # For values > 2^63, we expect them to wrap
        expected = val if val < 2**64 else val & 0xFFFFFFFFFFFFFFFF
        match = "OK" if recovered == expected else "FAIL"

        if match == "FAIL":
            all_match = False

        trit_str = ''.join({-1: 'T', 0: '0', 1: '1'}[t] for t in ternary.trits[:12])

        print(f"{val:<25,} {trit_str:<20} {recovered:<25,} {match:>8}")

    print("-" * 80)

    # Random verification
    print("\nRandom verification (1000 values)...", end=" ")
    np.random.seed(999)
    random_values = np.random.randint(0, 2**63, size=1000, dtype=np.uint64)

    errors = 0
    for val in random_values:
        ternary = TernaryWord.from_binary(int(val))
        recovered = ternary.to_binary()
        if recovered != val:
            errors += 1

    if errors == 0:
        print("OK (all 1000 values roundtrip correctly)")
    else:
        print(f"FAILED ({errors} errors)")
        all_match = False

    # Verify 81 trits can represent 64 bits
    print(f"\nCapacity check:")
    print(f"  64 bits can represent:  2^64 = {2**64:.2e} values")
    print(f"  81 trits can represent: 3^81 = {3**81:.2e} values")
    print(f"  Ratio: 3^81 / 2^64 = {3**81 / 2**64:.2e}x")
    print(f"  Minimum trits for 64 bits: ceil(64 * ln(2) / ln(3)) = {TRITS_PER_64BIT}")

    return all_match


# =============================================================================
# VISUALIZATION (Optional - requires matplotlib)
# =============================================================================

def plot_results(results: dict, save_path: Optional[str] = None):
    """
    Generate visualization plots for the simulation results.

    Args:
        results: Dict mapping scenario names to SimulationMetrics
        save_path: If provided, save plots to this directory
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("  [Matplotlib not available - skipping plots]")
        return

    import os

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('PCIe-Optical Interface Simulation Results', fontsize=14, fontweight='bold')

    scenarios = list(results.keys())
    colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c', '#f39c12']

    # Plot 1: Throughput comparison
    ax1 = axes[0, 0]
    throughputs = [results[s].effective_input_bandwidth_gbs for s in scenarios]
    bars = ax1.bar(range(len(scenarios)), throughputs, color=colors[:len(scenarios)])
    ax1.axhline(y=PCIE_4_X16_BANDWIDTH_GBS, color='red', linestyle='--', label=f'PCIe 4.0 x16 Max ({PCIE_4_X16_BANDWIDTH_GBS} GB/s)')
    ax1.axhline(y=OPTICAL_CLOCK_MHZ * 8 / 1000, color='orange', linestyle='--', label=f'Optical Chip Max ({OPTICAL_CLOCK_MHZ * 8 / 1000:.1f} GB/s)')
    ax1.set_ylabel('Throughput (GB/s)')
    ax1.set_title('Effective Throughput by Scenario')
    ax1.set_xticks(range(len(scenarios)))
    ax1.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=8)
    ax1.legend(loc='upper right', fontsize=8)
    ax1.grid(axis='y', alpha=0.3)

    # Plot 2: Latency comparison
    ax2 = axes[0, 1]
    avg_latencies = [results[s].avg_latency_ns() for s in scenarios]
    p99_latencies = [results[s].p99_latency_ns() for s in scenarios]
    x = range(len(scenarios))
    width = 0.35
    ax2.bar([i - width/2 for i in x], avg_latencies, width, label='Avg Latency', color='#3498db')
    ax2.bar([i + width/2 for i in x], p99_latencies, width, label='P99 Latency', color='#e74c3c')
    ax2.set_ylabel('Latency (ns)')
    ax2.set_title('Latency by Scenario')
    ax2.set_xticks(range(len(scenarios)))
    ax2.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=8)
    ax2.legend(loc='upper right', fontsize=8)
    ax2.grid(axis='y', alpha=0.3)

    # Plot 3: Buffer utilization
    ax3 = axes[1, 0]
    input_util = [results[s].input_buffer_utilization * 100 for s in scenarios]
    output_util = [results[s].output_buffer_utilization * 100 for s in scenarios]
    ax3.bar([i - width/2 for i in x], input_util, width, label='Input Buffer', color='#2ecc71')
    ax3.bar([i + width/2 for i in x], output_util, width, label='Output Buffer', color='#9b59b6')
    ax3.set_ylabel('Utilization (%)')
    ax3.set_title('Buffer Utilization by Scenario')
    ax3.set_xticks(range(len(scenarios)))
    ax3.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=8)
    ax3.legend(loc='upper right', fontsize=8)
    ax3.set_ylim(0, 100)
    ax3.grid(axis='y', alpha=0.3)

    # Plot 4: Data flow diagram (conceptual)
    ax4 = axes[1, 1]
    ax4.axis('off')

    # Draw a simple block diagram
    diagram_text = """
    DATA FLOW ARCHITECTURE
    ======================

    PCIe Host (64-bit)
         |
         v
    [Input FIFO] -----> [B2T Converter] -----> Optical Chip
    (Elastic Buffer)    (2 cycles)            (617 MHz, 81-trit)
                                                    |
                                                    v
    [Output FIFO] <---- [T2B Converter] <----- ALU Result
    (Elastic Buffer)    (2 cycles)

    Key Metrics:
    - PCIe 4.0 x16: 32 GB/s max
    - Optical Clock: 617 MHz (1.62 ns/cycle)
    - Conversion: 6.5 ns roundtrip
    - 81 trits can represent 2^128 values
    """
    ax4.text(0.1, 0.95, diagram_text, transform=ax4.transAxes,
             fontfamily='monospace', fontsize=9, verticalalignment='top')

    plt.tight_layout()

    if save_path:
        os.makedirs(save_path, exist_ok=True)
        plot_path = os.path.join(save_path, 'pcie_optical_interface_results.png')
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        print(f"\n  Plot saved to: {plot_path}")
    else:
        plt.show()

    plt.close()


# =============================================================================
# THROUGHPUT ANALYSIS
# =============================================================================

def analyze_throughput_limits():
    """
    Detailed analysis of throughput limits and bottlenecks.

    This function calculates theoretical limits and identifies where
    bottlenecks occur in the data path.
    """
    print("\n" + "=" * 70)
    print("DETAILED THROUGHPUT ANALYSIS")
    print("=" * 70)

    # PCIe Bandwidth
    print("\n1. PCIe 4.0 x16 Bandwidth:")
    print(f"   - Raw bandwidth: {PCIE_4_X16_BANDWIDTH_GBPS} Gbps (16 lanes x 16 GT/s)")
    print(f"   - 128b/130b encoding overhead: 1.56%")
    print(f"   - Effective bandwidth: ~{PCIE_4_X16_BANDWIDTH_GBS} GB/s")
    print(f"   - Words per second: {PCIE_4_X16_BANDWIDTH_GBS * 1e9 / 8:.2e} (64-bit words)")

    # Optical Chip Throughput
    print("\n2. Optical Chip Throughput:")
    optical_words_per_sec = OPTICAL_CLOCK_MHZ * 1e6
    optical_gbs = optical_words_per_sec * 8 / 1e9
    print(f"   - Clock rate: {OPTICAL_CLOCK_MHZ} MHz")
    print(f"   - Cycle time: {OPTICAL_CYCLE_NS:.2f} ns")
    print(f"   - Words per second: {optical_words_per_sec:.2e} (81-trit words)")
    print(f"   - Equivalent bandwidth: {optical_gbs:.2f} GB/s (64-bit equivalent)")

    # Conversion Overhead
    print("\n3. Conversion Overhead:")
    print(f"   - Binary-to-Ternary: {BINARY_TO_TERNARY_CYCLES} cycles ({BINARY_TO_TERNARY_CYCLES * OPTICAL_CYCLE_NS:.2f} ns)")
    print(f"   - Ternary-to-Binary: {TERNARY_TO_BINARY_CYCLES} cycles ({TERNARY_TO_BINARY_CYCLES * OPTICAL_CYCLE_NS:.2f} ns)")
    print(f"   - Total roundtrip: {(BINARY_TO_TERNARY_CYCLES + TERNARY_TO_BINARY_CYCLES) * OPTICAL_CYCLE_NS:.2f} ns")
    print(f"   - Conversion is pipelined: no throughput impact (only latency)")

    # Bottleneck Analysis
    print("\n4. Bottleneck Analysis:")
    print(f"   - PCIe can supply:     {PCIE_4_X16_BANDWIDTH_GBS:.2f} GB/s")
    print(f"   - Optical chip needs:  {optical_gbs:.2f} GB/s")

    if optical_gbs < PCIE_4_X16_BANDWIDTH_GBS:
        ratio = PCIE_4_X16_BANDWIDTH_GBS / optical_gbs
        print(f"\n   BOTTLENECK: Optical chip clock rate")
        print(f"   - PCIe has {ratio:.1f}x more bandwidth than optical chip needs")
        print(f"   - This is GOOD for compute-bound workloads (chip always fed)")
        print(f"   - Extra PCIe bandwidth can be used for:")
        print(f"     * Multiple streams (inference + weight updates)")
        print(f"     * Multi-chip configurations")
        print(f"     * Result prefetching")
    else:
        print(f"\n   BOTTLENECK: PCIe bandwidth")
        print(f"   - Consider PCIe 5.0 x16 (~64 GB/s)")

    # Multi-chip Scaling
    print("\n5. Multi-Chip Scaling:")
    max_chips = int(PCIE_4_X16_BANDWIDTH_GBS / optical_gbs)
    print(f"   - PCIe 4.0 x16 can saturate {max_chips} optical chips")
    print(f"   - With {max_chips} chips: {max_chips * optical_gbs:.2f} GB/s total throughput")

    # Information Density
    print("\n6. Information Density:")
    print(f"   - 64-bit binary:  2^64  = {2**64:.2e} possible values")
    print(f"   - 81-trit ternary: 3^81 = {3**81:.2e} possible values")
    print(f"   - Ternary advantage: {3**81 / 2**64:.2e}x more values")
    print(f"   - Bits equivalent: 81 trits = {81 * np.log2(3):.1f} bits of information")
    print(f"   - Radix economy gain: {81 * np.log2(3) / 64 * 100 - 100:.1f}% more information per word")

    print("\n" + "=" * 70)


# =============================================================================
# BUFFER SIZING RECOMMENDATIONS
# =============================================================================

def recommend_buffer_sizes(
    burst_size_words: int = 1000,
    max_latency_ns: float = 10000.0
) -> Tuple[int, int]:
    """
    Recommend optimal buffer sizes based on workload characteristics.

    Args:
        burst_size_words: Expected maximum burst size from host
        max_latency_ns: Maximum acceptable end-to-end latency

    Returns:
        Tuple of (input_buffer_depth, output_buffer_depth)
    """
    print("\n" + "=" * 70)
    print("BUFFER SIZING RECOMMENDATIONS")
    print("=" * 70)

    print(f"\nInputs:")
    print(f"  Expected burst size: {burst_size_words} words")
    print(f"  Max acceptable latency: {max_latency_ns:.0f} ns")

    # Input buffer needs to absorb bursts while optical chip catches up
    # Rate mismatch: PCIe can push 32 GB/s, optical chip consumes ~5 GB/s
    pcie_words_per_ns = PCIE_4_X16_BANDWIDTH_GBS * 1e9 / 8 / 1e9  # words per ns
    optical_words_per_ns = OPTICAL_CLOCK_MHZ * 1e6 / 1e9  # words per ns

    # During a burst at PCIe rate, buffer fills at (pcie - optical) rate
    net_fill_rate = pcie_words_per_ns - optical_words_per_ns

    # To absorb a burst of N words:
    # Buffer needs to hold: N * (1 - optical/pcie)
    burst_absorption = burst_size_words * (1 - optical_words_per_ns / pcie_words_per_ns)
    input_buffer_recommended = int(burst_absorption * 1.5)  # 50% safety margin

    print(f"\nInput Buffer Analysis:")
    print(f"  PCIe input rate: {pcie_words_per_ns:.4f} words/ns")
    print(f"  Optical consumption rate: {optical_words_per_ns:.4f} words/ns")
    print(f"  Net fill rate during burst: {net_fill_rate:.4f} words/ns")
    print(f"  Burst absorption needed: {burst_absorption:.0f} words")
    print(f"  Recommended input buffer: {input_buffer_recommended} words ({input_buffer_recommended * 8 / 1024:.1f} KB)")

    # Output buffer needs to handle latency jitter
    # Worst case: output stalls while host is busy, then bursts read
    max_queue_time_cycles = int(max_latency_ns / OPTICAL_CYCLE_NS)
    output_buffer_recommended = max_queue_time_cycles

    print(f"\nOutput Buffer Analysis:")
    print(f"  Max latency: {max_latency_ns:.0f} ns = {max_queue_time_cycles} cycles")
    print(f"  Recommended output buffer: {output_buffer_recommended} words")

    # Final recommendations
    input_buffer = max(256, min(16384, input_buffer_recommended))
    output_buffer = max(256, min(16384, output_buffer_recommended))

    print(f"\nFinal Recommendations (with bounds):")
    print(f"  Input buffer:  {input_buffer} words ({input_buffer * 8 / 1024:.1f} KB)")
    print(f"  Output buffer: {output_buffer} words ({output_buffer * 8 / 1024:.1f} KB)")
    print(f"  Total buffer memory: {(input_buffer + output_buffer) * 8 / 1024:.1f} KB")

    print("\n" + "=" * 70)

    return input_buffer, output_buffer


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run all simulation scenarios and print results."""

    print("\n" + "=" * 70)
    print("   PCIe TO OPTICAL CHIP DATA FLOW INTERFACE SIMULATION")
    print("   Wavelength-Division Ternary Optical Computer")
    print("=" * 70)

    # Verify conversion correctness first
    if not verify_ternary_conversion():
        print("\nERROR: Ternary conversion verification failed!")
        return

    # Create interface with configurable buffer depths
    interface = PCIeOpticalInterface(
        input_buffer_depth=1024,   # 1024 x 64-bit words = 8 KB
        output_buffer_depth=1024,  # 1024 x 81-trit words
        verbose=False
    )

    # Run all scenarios
    results = {}

    # Scenario 1: Burst input (weight loading)
    results["Burst (Weight Load)"] = scenario_burst_input(
        interface,
        burst_size=500,
        burst_count=20,
        inter_burst_cycles=1000
    )

    # Scenario 2: Streaming input at various rates
    results["Stream (80% rate)"] = scenario_streaming_input(
        interface,
        stream_duration_us=100.0,
        input_rate_fraction=0.8
    )

    results["Stream (100% rate)"] = scenario_streaming_input(
        interface,
        stream_duration_us=100.0,
        input_rate_fraction=1.0
    )

    # Scenario 3: Backpressure handling
    results["Backpressure"] = scenario_backpressure(
        interface,
        duration_us=50.0
    )

    # Scenario 4: Variable compute time
    results["Variable Compute"] = scenario_variable_compute_time(
        interface,
        duration_us=100.0,
        compute_cycles_range=(1, 10)
    )

    # Print summary
    print_summary_table(results)

    # Additional analysis
    analyze_throughput_limits()

    # Buffer sizing recommendations
    recommend_buffer_sizes(burst_size_words=1000, max_latency_ns=10000.0)

    # Generate plots (optional - requires matplotlib)
    import os
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'png')
    plot_results(results, save_path=data_dir)


if __name__ == "__main__":
    main()
