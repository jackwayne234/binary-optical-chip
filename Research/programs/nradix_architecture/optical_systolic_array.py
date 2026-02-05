#!/usr/bin/env python3
"""
Optical Systolic Array Generator for AI Acceleration

81×81 = 6,561 Processing Elements with Multi-Domain Support:
- LINEAR mode:   ADD/SUB operations
- LOG mode:      MUL/DIV as ADD/SUB (current ALU capability)
- LOG-LOG mode:  POWER TOWERS as ADD/SUB (X^(a^b) becomes addition!)

Specifications:
- Array size: 81×81 = 6,561 PEs (3^8 - perfect ternary number)
- Precision: 9 trits per value (~14 bits equivalent)
- Clock: 617 MHz (from Kerr resonator)
- Throughput: 6,561 MACs/cycle = 4.05 TMAC/s
- Architecture: Weight-stationary systolic flow

For AI workloads:
- Matrix multiply: Use LOG mode (MUL→ADD)
- Softmax: Use LINEAR mode (EXP is native)
- Power scheduling: Use LOG-LOG mode (powers→ADD)
- Attention: Mixed mode

Author: Wavelength-Division Ternary Optical Computer Project
"""

import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.typings import LayerSpec
import numpy as np
from typing import Optional, Literal, Tuple
import os

# Activate PDK
gf.gpdk.PDK.activate()

# =============================================================================
# Layer Definitions
# =============================================================================

LAYER_WAVEGUIDE: LayerSpec = (1, 0)      # Optical waveguides
LAYER_HEATER: LayerSpec = (10, 0)        # Thermal tuning / control
LAYER_CARRY: LayerSpec = (11, 0)         # Data flow paths
LAYER_METAL_PAD: LayerSpec = (12, 0)     # Electrical contacts
LAYER_LOG: LayerSpec = (13, 0)           # LOG converter (saturable absorber)
LAYER_EXP: LayerSpec = (14, 0)           # EXP converter (gain medium)
LAYER_AWG: LayerSpec = (15, 0)           # Wavelength demux
LAYER_DETECTOR: LayerSpec = (16, 0)      # Photodetectors
LAYER_ACCUMULATOR: LayerSpec = (17, 0)   # Accumulator registers
LAYER_WEIGHT: LayerSpec = (18, 0)        # Weight storage
LAYER_MUX: LayerSpec = (19, 0)           # Mode selection MUX
LAYER_BUS: LayerSpec = (20, 0)           # Data bus regions
LAYER_TEXT: LayerSpec = (100, 0)         # Labels

# =============================================================================
# Physical Constants
# =============================================================================

WAVEGUIDE_WIDTH = 0.5           # μm
BEND_RADIUS = 5.0               # μm
TRIT_PRECISION = 9              # trits per value (~14 bits)
CLOCK_FREQ_MHZ = 617            # MHz

# PE dimensions (compact for 81×81 array)
PE_WIDTH = 50.0                 # μm
PE_HEIGHT = 50.0                # μm
PE_SPACING = 5.0                # μm between PEs

# =============================================================================
# Unique ID Generator
# =============================================================================

_uid_counter = 0
def _uid() -> str:
    global _uid_counter
    _uid_counter += 1
    return f"{_uid_counter:05d}"

# =============================================================================
# Basic Optical Components
# =============================================================================

@gf.cell
def optical_log_converter(length: float = 15.0) -> Component:
    """
    Logarithmic converter using saturable absorber.

    Intensity → log(Intensity)

    Physics: Saturable absorption gives logarithmic transfer function
    at high intensities due to gain saturation.
    """
    c = gf.Component()

    # Saturable absorber region
    sa = c.add_polygon([
        (0, -WAVEGUIDE_WIDTH),
        (length, -WAVEGUIDE_WIDTH),
        (length, WAVEGUIDE_WIDTH),
        (0, WAVEGUIDE_WIDTH)
    ], layer=LAYER_LOG)

    # Input/output waveguides
    c.add_polygon([(-5, -WAVEGUIDE_WIDTH/2), (0, -WAVEGUIDE_WIDTH/2),
                   (0, WAVEGUIDE_WIDTH/2), (-5, WAVEGUIDE_WIDTH/2)], layer=LAYER_WAVEGUIDE)
    c.add_polygon([(length, -WAVEGUIDE_WIDTH/2), (length+5, -WAVEGUIDE_WIDTH/2),
                   (length+5, WAVEGUIDE_WIDTH/2), (length, WAVEGUIDE_WIDTH/2)], layer=LAYER_WAVEGUIDE)

    # Ports
    c.add_port("in", center=(-5, 0), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port("out", center=(length+5, 0), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)

    c.add_label("LOG", position=(length/2, 0), layer=LAYER_TEXT)

    return c


@gf.cell
def optical_exp_converter(length: float = 15.0) -> Component:
    """
    Exponential converter using optical gain medium.

    log(Intensity) → Intensity

    Physics: Optical amplifier with exponential gain characteristic.
    """
    c = gf.Component()

    # Gain region
    gain = c.add_polygon([
        (0, -WAVEGUIDE_WIDTH),
        (length, -WAVEGUIDE_WIDTH),
        (length, WAVEGUIDE_WIDTH),
        (0, WAVEGUIDE_WIDTH)
    ], layer=LAYER_EXP)

    # Input/output waveguides
    c.add_polygon([(-5, -WAVEGUIDE_WIDTH/2), (0, -WAVEGUIDE_WIDTH/2),
                   (0, WAVEGUIDE_WIDTH/2), (-5, WAVEGUIDE_WIDTH/2)], layer=LAYER_WAVEGUIDE)
    c.add_polygon([(length, -WAVEGUIDE_WIDTH/2), (length+5, -WAVEGUIDE_WIDTH/2),
                   (length+5, WAVEGUIDE_WIDTH/2), (length, WAVEGUIDE_WIDTH/2)], layer=LAYER_WAVEGUIDE)

    # Pump port for gain
    c.add_polygon([(length/2-3, WAVEGUIDE_WIDTH), (length/2+3, WAVEGUIDE_WIDTH),
                   (length/2+3, WAVEGUIDE_WIDTH+5), (length/2-3, WAVEGUIDE_WIDTH+5)], layer=LAYER_METAL_PAD)

    # Ports
    c.add_port("in", center=(-5, 0), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port("out", center=(length+5, 0), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port("pump", center=(length/2, WAVEGUIDE_WIDTH+2.5), width=6, orientation=90, layer=LAYER_METAL_PAD)

    c.add_label("EXP", position=(length/2, 0), layer=LAYER_TEXT)

    return c


@gf.cell
def optical_adder_subtractor(length: float = 20.0) -> Component:
    """
    Optical adder/subtractor using SFG/DFG.

    SFG mode: A + B (sum frequency)
    DFG mode: A - B (difference frequency)
    """
    c = gf.Component()

    # Nonlinear mixing region (PPLN)
    mixer = c.add_polygon([
        (0, -3),
        (length, -3),
        (length, 3),
        (0, 3)
    ], layer=LAYER_WAVEGUIDE)

    # Poling pattern indicator
    for i in range(int(length/2)):
        x = i * 2 + 0.5
        c.add_polygon([(x, -2.5), (x+1, -2.5), (x+1, 2.5), (x, 2.5)], layer=LAYER_HEATER)

    # Input A
    c.add_polygon([(-8, 1), (0, 1), (0, 2), (-8, 2)], layer=LAYER_WAVEGUIDE)
    # Input B
    c.add_polygon([(-8, -2), (0, -2), (0, -1), (-8, -1)], layer=LAYER_WAVEGUIDE)
    # Output
    c.add_polygon([(length, -0.5), (length+8, -0.5), (length+8, 0.5), (length, 0.5)], layer=LAYER_WAVEGUIDE)

    # Mode control pad
    c.add_polygon([(length/2-4, 4), (length/2+4, 4), (length/2+4, 8), (length/2-4, 8)], layer=LAYER_METAL_PAD)

    # Ports
    c.add_port("in_a", center=(-8, 1.5), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port("in_b", center=(-8, -1.5), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port("out", center=(length+8, 0), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port("mode_ctrl", center=(length/2, 6), width=8, orientation=90, layer=LAYER_METAL_PAD)

    c.add_label("ADD/SUB", position=(length/2, 0), layer=LAYER_TEXT)

    return c


@gf.cell
def optical_accumulator(loop_length: float = 30.0) -> Component:
    """
    Optical accumulator using recirculating delay loop.

    Accumulates partial sums for MAC operations.
    """
    c = gf.Component()

    # Recirculating loop
    loop_radius = loop_length / (2 * np.pi) * 1.5

    # Coupler for add/tap
    c.add_polygon([(0, -2), (10, -2), (10, 2), (0, 2)], layer=LAYER_ACCUMULATOR)

    # Loop (simplified as rectangle)
    c.add_polygon([(10, 0), (10+loop_length/4, 0), (10+loop_length/4, 15),
                   (10, 15)], layer=LAYER_WAVEGUIDE)
    c.add_polygon([(10, 15), (10-loop_length/4, 15), (10-loop_length/4, 0),
                   (10, 0)], layer=LAYER_WAVEGUIDE)

    # SOA in loop for loss compensation
    c.add_polygon([(5, 12), (15, 12), (15, 15), (5, 15)], layer=LAYER_EXP)

    # Ports
    c.add_port("in", center=(0, 0), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port("out", center=(20, 0), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port("clear", center=(10, -5), width=5, orientation=270, layer=LAYER_METAL_PAD)

    # Clear control
    c.add_polygon([(7, -8), (13, -8), (13, -3), (7, -3)], layer=LAYER_METAL_PAD)

    c.add_label("ACC", position=(10, 7), layer=LAYER_TEXT)

    return c


@gf.cell
def mode_selector_3way() -> Component:
    """
    3-way MUX for selecting LINEAR/LOG/LOG-LOG domain.

    Uses cascaded MZI switches.
    """
    c = gf.Component()

    # MUX body
    c.add_polygon([(0, -8), (25, -8), (25, 8), (0, 8)], layer=LAYER_MUX)

    # Input
    c.add_polygon([(-5, -0.5), (0, -0.5), (0, 0.5), (-5, 0.5)], layer=LAYER_WAVEGUIDE)

    # Three outputs
    c.add_polygon([(25, 4.5), (30, 4.5), (30, 5.5), (25, 5.5)], layer=LAYER_WAVEGUIDE)  # LINEAR
    c.add_polygon([(25, -0.5), (30, -0.5), (30, 0.5), (25, 0.5)], layer=LAYER_WAVEGUIDE)  # LOG
    c.add_polygon([(25, -5.5), (30, -5.5), (30, -4.5), (25, -4.5)], layer=LAYER_WAVEGUIDE)  # LOG-LOG

    # Control pads (2-bit selection)
    c.add_polygon([(8, 9), (12, 9), (12, 13), (8, 13)], layer=LAYER_METAL_PAD)
    c.add_polygon([(14, 9), (18, 9), (18, 13), (14, 13)], layer=LAYER_METAL_PAD)

    # Labels
    c.add_label("MUX", position=(12, 0), layer=LAYER_TEXT)
    c.add_label("LIN", position=(32, 5), layer=LAYER_TEXT)
    c.add_label("LOG", position=(32, 0), layer=LAYER_TEXT)
    c.add_label("L-L", position=(32, -5), layer=LAYER_TEXT)

    # Ports
    c.add_port("in", center=(-5, 0), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port("out_linear", center=(30, 5), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port("out_log", center=(30, 0), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port("out_loglog", center=(30, -5), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port("sel0", center=(10, 11), width=4, orientation=90, layer=LAYER_METAL_PAD)
    c.add_port("sel1", center=(16, 11), width=4, orientation=90, layer=LAYER_METAL_PAD)

    return c


@gf.cell
def weight_register_9trit() -> Component:
    """
    9-trit weight register using bistable optical storage.

    Holds weight value for weight-stationary systolic operation.
    """
    c = gf.Component()

    # 9 bistable cells in a row
    cell_width = 4
    for i in range(9):
        x = i * cell_width
        # Bistable flip-flop cell
        c.add_polygon([(x, 0), (x+cell_width-0.5, 0),
                       (x+cell_width-0.5, 5), (x, 5)], layer=LAYER_WEIGHT)

    # Write bus
    c.add_polygon([(-3, 2), (0, 2), (0, 3), (-3, 3)], layer=LAYER_WAVEGUIDE)

    # Read bus
    c.add_polygon([(36, 2), (39, 2), (39, 3), (36, 3)], layer=LAYER_WAVEGUIDE)

    # Write enable
    c.add_polygon([(15, -5), (21, -5), (21, -2), (15, -2)], layer=LAYER_METAL_PAD)

    # Ports
    c.add_port("write", center=(-3, 2.5), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port("read", center=(39, 2.5), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port("we", center=(18, -3.5), width=6, orientation=270, layer=LAYER_METAL_PAD)

    c.add_label("W[8:0]", position=(18, 7), layer=LAYER_TEXT)

    return c


# =============================================================================
# Processing Element (PE) with Multi-Domain Support
# =============================================================================

@gf.cell
def processing_element_multidomain(
    pe_id: Tuple[int, int] = (0, 0),
    include_weight_reg: bool = True
) -> Component:
    """
    Single Processing Element with LINEAR/LOG/LOG-LOG support.

    Architecture:

        Weight ──────────────────────────────┐
                                             │
        Input_H ──→ [MODE_MUX] ──┬─ LINEAR ──┼──→ [ADD/SUB] ──→ [ACC] ──→ Output_V
        (horizontal)             ├─ LOG ─────┤        ↑
                                 └─ LOG-LOG ─┘        │
                                                      │
        Input_V ──────────────────────────────────────┘
        (vertical, partial sum from above)

    Modes:
        LINEAR (00): Direct add/sub
        LOG (01):    MUL/DIV via log-domain add/sub
        LOG-LOG (10): POWER via log-log-domain add/sub

    Args:
        pe_id: (row, col) identifier
        include_weight_reg: Whether to include weight storage
    """
    c = gf.Component(f"PE_{pe_id[0]}_{pe_id[1]}_{_uid()}")

    # Component dimensions
    total_width = PE_WIDTH
    total_height = PE_HEIGHT

    # Background
    c.add_polygon([(0, 0), (total_width, 0), (total_width, total_height), (0, total_height)],
                  layer=LAYER_BUS)

    # =========================================================================
    # Input Processing Path (horizontal data flow)
    # =========================================================================

    # Mode selector MUX
    mux = c << mode_selector_3way()
    mux.dmove((2, total_height/2 - 4))

    # LINEAR path (bypass)
    # Direct connection

    # LOG path (single log converter)
    log1 = c << optical_log_converter(length=8)
    log1.dmove((8, total_height/2 + 8))

    # LOG-LOG path (two log converters in series)
    log2a = c << optical_log_converter(length=6)
    log2a.dmove((8, total_height/2 - 15))

    log2b = c << optical_log_converter(length=6)
    log2b.dmove((22, total_height/2 - 15))

    # =========================================================================
    # Core ALU (ADD/SUB)
    # =========================================================================

    alu = c << optical_adder_subtractor(length=10)
    alu.dmove((total_width/2 - 5, total_height/2 - 5))

    # =========================================================================
    # Output Processing (reverse domain conversion)
    # =========================================================================

    # EXP converters for domain restoration
    exp1 = c << optical_exp_converter(length=6)
    exp1.dmove((total_width - 18, total_height/2 + 8))

    exp2a = c << optical_exp_converter(length=5)
    exp2a.dmove((total_width - 20, total_height/2 - 15))

    exp2b = c << optical_exp_converter(length=5)
    exp2b.dmove((total_width - 12, total_height/2 - 15))

    # =========================================================================
    # Accumulator
    # =========================================================================

    acc = c << optical_accumulator(loop_length=15)
    acc.dmove((total_width - 25, total_height/2 - 2))

    # =========================================================================
    # Weight Register (optional)
    # =========================================================================

    if include_weight_reg:
        weight = c << weight_register_9trit()
        weight.dmove((5, 2))

    # =========================================================================
    # Ports
    # =========================================================================

    # Horizontal data flow (activation input from left)
    c.add_port("in_h", center=(0, total_height/2), width=WAVEGUIDE_WIDTH,
               orientation=180, layer=LAYER_WAVEGUIDE)

    # Horizontal data flow (to next PE on right)
    c.add_port("out_h", center=(total_width, total_height/2), width=WAVEGUIDE_WIDTH,
               orientation=0, layer=LAYER_WAVEGUIDE)

    # Vertical data flow (partial sum from above)
    c.add_port("in_v", center=(total_width/2, total_height), width=WAVEGUIDE_WIDTH,
               orientation=90, layer=LAYER_WAVEGUIDE)

    # Vertical data flow (partial sum to below)
    c.add_port("out_v", center=(total_width/2, 0), width=WAVEGUIDE_WIDTH,
               orientation=270, layer=LAYER_WAVEGUIDE)

    # Weight write port
    if include_weight_reg:
        c.add_port("weight_in", center=(0, 5), width=WAVEGUIDE_WIDTH,
                   orientation=180, layer=LAYER_WAVEGUIDE)

    # Control ports
    c.add_port("mode_sel", center=(10, total_height), width=4,
               orientation=90, layer=LAYER_METAL_PAD)
    c.add_port("acc_clear", center=(total_width - 15, 0), width=4,
               orientation=270, layer=LAYER_METAL_PAD)

    # PE identifier label
    c.add_label(f"PE[{pe_id[0]},{pe_id[1]}]", position=(total_width/2, total_height - 3), layer=LAYER_TEXT)

    return c


# =============================================================================
# Systolic Array Row
# =============================================================================

@gf.cell
def systolic_row(
    row_id: int = 0,
    n_cols: int = 81,
    include_weights: bool = True
) -> Component:
    """
    Single row of the systolic array.

    Args:
        row_id: Row identifier
        n_cols: Number of columns (PEs in this row)
        include_weights: Include weight registers
    """
    c = gf.Component(f"systolic_row_{row_id}_{_uid()}")

    pe_pitch = PE_WIDTH + PE_SPACING

    for col in range(n_cols):
        pe = c << processing_element_multidomain(
            pe_id=(row_id, col),
            include_weight_reg=include_weights
        )
        pe.dmove((col * pe_pitch, 0))

        # Connect horizontal data flow between PEs
        if col > 0:
            # Waveguide connecting previous PE out_h to this PE in_h
            x_start = (col - 1) * pe_pitch + PE_WIDTH
            x_end = col * pe_pitch
            y = PE_HEIGHT / 2
            c.add_polygon([
                (x_start, y - WAVEGUIDE_WIDTH/2),
                (x_end, y - WAVEGUIDE_WIDTH/2),
                (x_end, y + WAVEGUIDE_WIDTH/2),
                (x_start, y + WAVEGUIDE_WIDTH/2)
            ], layer=LAYER_WAVEGUIDE)

    # Row input port (leftmost)
    c.add_port("row_in", center=(0, PE_HEIGHT/2), width=WAVEGUIDE_WIDTH,
               orientation=180, layer=LAYER_WAVEGUIDE)

    # Row output port (rightmost)
    c.add_port("row_out", center=(n_cols * pe_pitch - PE_SPACING, PE_HEIGHT/2),
               width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)

    # Vertical ports for each PE (partial sums)
    for col in range(n_cols):
        x = col * pe_pitch + PE_WIDTH/2
        c.add_port(f"col_{col}_in", center=(x, PE_HEIGHT), width=WAVEGUIDE_WIDTH,
                   orientation=90, layer=LAYER_WAVEGUIDE)
        c.add_port(f"col_{col}_out", center=(x, 0), width=WAVEGUIDE_WIDTH,
                   orientation=270, layer=LAYER_WAVEGUIDE)

    # Weight loading bus
    if include_weights:
        c.add_port("weight_bus", center=(0, 5), width=WAVEGUIDE_WIDTH,
                   orientation=180, layer=LAYER_WAVEGUIDE)

    c.add_label(f"ROW {row_id}", position=(n_cols * pe_pitch / 2, PE_HEIGHT + 5), layer=LAYER_TEXT)

    return c


# =============================================================================
# Full 81×81 Systolic Array
# =============================================================================

@gf.cell
def optical_systolic_array_81x81(
    include_io_buffers: bool = True,
    include_weight_loader: bool = True,
    include_clock_distribution: bool = True
) -> Component:
    """
    Complete 81×81 Optical Systolic Array for AI Acceleration.

    Specifications:
    - 6,561 Processing Elements (3^8)
    - 9-trit precision per value
    - LINEAR/LOG/LOG-LOG multi-domain support
    - Weight-stationary data flow
    - 617 MHz clock rate
    - 4.05 TMAC/s peak throughput

    Architecture:

        Weight Loading Bus (top)
              ↓ ↓ ↓ ↓ ↓
        ┌─────────────────────────────────────┐
        │  ┌───┬───┬───┬─────┬───┬───┬───┐  │
    A → │  │PE │PE │PE │ ... │PE │PE │PE │  │ → (activation passthrough)
        │  ├───┼───┼───┼─────┼───┼───┼───┤  │
    A → │  │PE │PE │PE │ ... │PE │PE │PE │  │
        │  ├───┼───┼───┼─────┼───┼───┼───┤  │
        │  │   :   :   :     :   :   :   │  │
        │  │      81 rows × 81 cols       │  │
        │  │   :   :   :     :   :   :   │  │
        │  ├───┼───┼───┼─────┼───┼───┼───┤  │
    A → │  │PE │PE │PE │ ... │PE │PE │PE │  │
        │  └───┴───┴───┴─────┴───┴───┴───┘  │
        └─────────────────────────────────────┘
              ↓ ↓ ↓ ↓ ↓
           Output columns (C = A × B)

    Args:
        include_io_buffers: Add input/output buffer stages
        include_weight_loader: Add weight loading interface
        include_clock_distribution: Add clock tree
    """
    c = gf.Component("optical_systolic_array_81x81")

    n_rows = 81
    n_cols = 81

    pe_pitch = PE_WIDTH + PE_SPACING
    row_pitch = PE_HEIGHT + PE_SPACING

    array_width = n_cols * pe_pitch
    array_height = n_rows * row_pitch

    # =========================================================================
    # Main Array
    # =========================================================================

    print(f"Generating 81×81 systolic array ({n_rows * n_cols} PEs)...")

    for row in range(n_rows):
        if row % 10 == 0:
            print(f"  Row {row}/81...")

        row_comp = c << systolic_row(
            row_id=row,
            n_cols=n_cols,
            include_weights=True
        )
        row_comp.dmove((100, 100 + row * row_pitch))

        # Connect vertical data flow between rows
        if row > 0:
            for col in range(n_cols):
                x = 100 + col * pe_pitch + PE_WIDTH/2
                y_start = 100 + (row - 1) * row_pitch
                y_end = 100 + row * row_pitch + PE_HEIGHT

                # Vertical waveguide
                c.add_polygon([
                    (x - WAVEGUIDE_WIDTH/2, y_start),
                    (x + WAVEGUIDE_WIDTH/2, y_start),
                    (x + WAVEGUIDE_WIDTH/2, y_end),
                    (x - WAVEGUIDE_WIDTH/2, y_end)
                ], layer=LAYER_CARRY)

    # =========================================================================
    # Input Buffers (Left side - activation inputs)
    # =========================================================================

    if include_io_buffers:
        c.add_label("ACTIVATION INPUTS", position=(50, array_height/2 + 100), layer=LAYER_TEXT)

        for row in range(n_rows):
            y = 100 + row * row_pitch + PE_HEIGHT/2

            # Input buffer block
            c.add_polygon([(20, y-3), (90, y-3), (90, y+3), (20, y+3)], layer=LAYER_BUS)
            c.add_polygon([(0, y-WAVEGUIDE_WIDTH/2), (20, y-WAVEGUIDE_WIDTH/2),
                          (20, y+WAVEGUIDE_WIDTH/2), (0, y+WAVEGUIDE_WIDTH/2)], layer=LAYER_WAVEGUIDE)

            # Port
            c.add_port(f"act_in_{row}", center=(0, y), width=WAVEGUIDE_WIDTH,
                      orientation=180, layer=LAYER_WAVEGUIDE)

    # =========================================================================
    # Output Buffers (Bottom - result outputs)
    # =========================================================================

    if include_io_buffers:
        c.add_label("RESULT OUTPUTS", position=(array_width/2 + 100, 50), layer=LAYER_TEXT)

        for col in range(n_cols):
            x = 100 + col * pe_pitch + PE_WIDTH/2

            # Output buffer block
            c.add_polygon([(x-3, 20), (x+3, 20), (x+3, 90), (x-3, 90)], layer=LAYER_BUS)
            c.add_polygon([(x-WAVEGUIDE_WIDTH/2, 0), (x+WAVEGUIDE_WIDTH/2, 0),
                          (x+WAVEGUIDE_WIDTH/2, 20), (x-WAVEGUIDE_WIDTH/2, 20)], layer=LAYER_WAVEGUIDE)

            # Port
            c.add_port(f"result_out_{col}", center=(x, 0), width=WAVEGUIDE_WIDTH,
                      orientation=270, layer=LAYER_WAVEGUIDE)

    # =========================================================================
    # Weight Loading Interface (Top)
    # =========================================================================

    if include_weight_loader:
        weight_bus_y = 100 + array_height + 20

        c.add_label("WEIGHT LOADING BUS", position=(array_width/2 + 100, weight_bus_y + 30), layer=LAYER_TEXT)

        # Main weight bus
        c.add_polygon([
            (100, weight_bus_y),
            (100 + array_width, weight_bus_y),
            (100 + array_width, weight_bus_y + 15),
            (100, weight_bus_y + 15)
        ], layer=LAYER_WEIGHT)

        # Drop lines to each column
        for col in range(n_cols):
            x = 100 + col * pe_pitch + PE_WIDTH/2
            c.add_polygon([
                (x - WAVEGUIDE_WIDTH/2, weight_bus_y),
                (x + WAVEGUIDE_WIDTH/2, weight_bus_y),
                (x + WAVEGUIDE_WIDTH/2, 100 + array_height),
                (x - WAVEGUIDE_WIDTH/2, 100 + array_height)
            ], layer=LAYER_WAVEGUIDE)

        # Weight input port
        c.add_port("weight_in", center=(100, weight_bus_y + 7.5), width=15,
                  orientation=180, layer=LAYER_WEIGHT)

    # =========================================================================
    # Clock Distribution (Center-out radial)
    # =========================================================================

    if include_clock_distribution:
        center_x = 100 + array_width / 2
        center_y = 100 + array_height / 2

        # Central clock hub
        hub_radius = 30
        n_points = 32
        angles = np.linspace(0, 2*np.pi, n_points)
        hub_points = [(center_x + hub_radius * np.cos(a),
                       center_y + hub_radius * np.sin(a)) for a in angles]
        c.add_polygon(hub_points, layer=LAYER_HEATER)

        c.add_label("617 MHz", position=(center_x, center_y), layer=LAYER_TEXT)
        c.add_label("CLOCK", position=(center_x, center_y - 10), layer=LAYER_TEXT)

        # Radial clock lines (8 directions)
        for i in range(8):
            angle = i * np.pi / 4
            x1 = center_x + hub_radius * np.cos(angle)
            y1 = center_y + hub_radius * np.sin(angle)
            x2 = center_x + (array_width/2 - 50) * np.cos(angle)
            y2 = center_y + (array_height/2 - 50) * np.sin(angle)

            dx = 2 * np.cos(angle + np.pi/2)
            dy = 2 * np.sin(angle + np.pi/2)

            c.add_polygon([
                (x1 - dx, y1 - dy),
                (x2 - dx, y2 - dy),
                (x2 + dx, y2 + dy),
                (x1 + dx, y1 + dy)
            ], layer=LAYER_HEATER)

    # =========================================================================
    # Global Control Pads
    # =========================================================================

    ctrl_x = 100 + array_width + 50
    ctrl_y = 100 + array_height / 2

    # Mode select (global)
    c.add_polygon([(ctrl_x, ctrl_y), (ctrl_x + 40, ctrl_y),
                   (ctrl_x + 40, ctrl_y + 25), (ctrl_x, ctrl_y + 25)], layer=LAYER_METAL_PAD)
    c.add_label("MODE[1:0]", position=(ctrl_x + 20, ctrl_y + 30), layer=LAYER_TEXT)

    # Accumulator clear (global)
    c.add_polygon([(ctrl_x, ctrl_y - 40), (ctrl_x + 40, ctrl_y - 40),
                   (ctrl_x + 40, ctrl_y - 15), (ctrl_x, ctrl_y - 15)], layer=LAYER_METAL_PAD)
    c.add_label("ACC_CLR", position=(ctrl_x + 20, ctrl_y - 45), layer=LAYER_TEXT)

    # Start signal
    c.add_polygon([(ctrl_x, ctrl_y - 80), (ctrl_x + 40, ctrl_y - 80),
                   (ctrl_x + 40, ctrl_y - 55), (ctrl_x, ctrl_y - 55)], layer=LAYER_METAL_PAD)
    c.add_label("START", position=(ctrl_x + 20, ctrl_y - 85), layer=LAYER_TEXT)

    c.add_port("mode_sel", center=(ctrl_x + 20, ctrl_y + 12.5), width=40,
               orientation=0, layer=LAYER_METAL_PAD)
    c.add_port("acc_clear", center=(ctrl_x + 20, ctrl_y - 27.5), width=40,
               orientation=0, layer=LAYER_METAL_PAD)
    c.add_port("start", center=(ctrl_x + 20, ctrl_y - 67.5), width=40,
               orientation=0, layer=LAYER_METAL_PAD)

    # =========================================================================
    # Title and Specifications
    # =========================================================================

    title_y = 100 + array_height + 80

    c.add_label("OPTICAL SYSTOLIC ARRAY 81×81", position=(array_width/2 + 100, title_y), layer=LAYER_TEXT)
    c.add_label("6,561 PEs | 9-trit precision | LINEAR/LOG/LOG-LOG",
                position=(array_width/2 + 100, title_y - 15), layer=LAYER_TEXT)
    c.add_label("4.05 TMAC/s @ 617 MHz | Weight-Stationary",
                position=(array_width/2 + 100, title_y - 30), layer=LAYER_TEXT)

    print(f"Array generation complete!")
    print(f"  Total PEs: {n_rows * n_cols}")
    print(f"  Array size: {array_width:.0f} × {array_height:.0f} μm")
    print(f"  Peak throughput: {n_rows * n_cols * CLOCK_FREQ_MHZ / 1e6:.2f} TMAC/s")

    return c


# =============================================================================
# Convenience Functions
# =============================================================================

def generate_full_array(output_path: Optional[str] = None) -> Component:
    """Generate the complete 81×81 array and optionally save to GDS."""

    array = optical_systolic_array_81x81(
        include_io_buffers=True,
        include_weight_loader=True,
        include_clock_distribution=True
    )

    if output_path:
        array.write_gds(output_path)
        print(f"Saved to: {output_path}")

    return array


def generate_test_array(size: int = 9, output_path: Optional[str] = None) -> Component:
    """Generate a smaller test array (default 9×9)."""

    c = gf.Component(f"optical_systolic_array_{size}x{size}_test")

    pe_pitch = PE_WIDTH + PE_SPACING
    row_pitch = PE_HEIGHT + PE_SPACING

    for row in range(size):
        for col in range(size):
            pe = c << processing_element_multidomain(
                pe_id=(row, col),
                include_weight_reg=True
            )
            pe.dmove((col * pe_pitch, row * row_pitch))

    c.add_label(f"TEST ARRAY {size}×{size}", position=(size * pe_pitch / 2, size * row_pitch + 10), layer=LAYER_TEXT)

    if output_path:
        c.write_gds(output_path)
        print(f"Saved to: {output_path}")

    return c


# =============================================================================
# Interactive CLI
# =============================================================================

def main():
    print("=" * 70)
    print("  OPTICAL SYSTOLIC ARRAY GENERATOR")
    print("  AI Acceleration with Multi-Domain Support")
    print("=" * 70)
    print()
    print("Capabilities:")
    print("  - LINEAR mode:   ADD/SUB operations")
    print("  - LOG mode:      MUL/DIV as ADD/SUB")
    print("  - LOG-LOG mode:  POWER TOWERS as ADD/SUB")
    print()
    print("Options:")
    print("  1. Generate full 81×81 array (6,561 PEs) - WARNING: Large file!")
    print("  2. Generate 27×27 test array (729 PEs)")
    print("  3. Generate 9×9 test array (81 PEs)")
    print("  4. Generate single PE (for inspection)")
    print("  5. Generate single row (81 PEs)")
    print()

    choice = input("Select option (1-5): ").strip()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gds_dir = os.path.join(base_dir, 'data', 'gds')
    os.makedirs(gds_dir, exist_ok=True)

    if choice == "1":
        print("\nGenerating 81×81 array... This may take a few minutes.")
        output_path = os.path.join(gds_dir, "optical_systolic_81x81.gds")
        array = generate_full_array(output_path)

    elif choice == "2":
        print("\nGenerating 27×27 test array...")
        output_path = os.path.join(gds_dir, "optical_systolic_27x27.gds")
        array = generate_test_array(size=27, output_path=output_path)

    elif choice == "3":
        print("\nGenerating 9×9 test array...")
        output_path = os.path.join(gds_dir, "optical_systolic_9x9.gds")
        array = generate_test_array(size=9, output_path=output_path)

    elif choice == "4":
        print("\nGenerating single PE...")
        pe = processing_element_multidomain(pe_id=(0, 0), include_weight_reg=True)
        output_path = os.path.join(gds_dir, "optical_systolic_pe.gds")
        pe.write_gds(output_path)
        print(f"Saved to: {output_path}")

    elif choice == "5":
        print("\nGenerating single row (81 PEs)...")
        row = systolic_row(row_id=0, n_cols=81, include_weights=True)
        output_path = os.path.join(gds_dir, "optical_systolic_row.gds")
        row.write_gds(output_path)
        print(f"Saved to: {output_path}")

    else:
        print("Invalid selection.")
        return

    # Offer to open in KLayout
    show = input("\nOpen in KLayout? (y/n): ").strip().lower()
    if show == "y":
        import subprocess
        try:
            subprocess.Popen(["klayout", output_path])
            print("KLayout launched!")
        except FileNotFoundError:
            print("KLayout not found in PATH")


if __name__ == "__main__":
    main()
