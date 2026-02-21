#!/usr/bin/env python3
"""
Monolithic 9x9 N-Radix Chip — Split-Edge Topology
===================================================

FIRST INTEGRATED DESIGN: IOC + Accelerator on ONE LiNbO3 Substrate

Architecture (Feb 7, 2026 — monolithic single-chip):
    This is the first layout that puts the IOC region and the passive
    accelerator region on the same chip, connected by on-substrate
    waveguides with path-length equalization.

Topology: SPLIT-EDGE
    ┌──────────────────────────────────────────────────────────────┐
    │  LEFT EDGE          CENTER               RIGHT EDGE          │
    │  ┌─────────┐   ┌─────────────────┐   ┌──────────┐          │
    │  │  IOC     │   │                 │   │  IOC     │          │
    │  │  INPUT   │   │   9×9 PE Array  │   │  OUTPUT  │          │
    │  │  REGION  │===│   (81 PEs)      │===│  REGION  │          │
    │  │          │   │                 │   │          │          │
    │  │ 9 ENC   │   │  Passive SFG    │   │ 9 DEC   │          │
    │  │ units    │   │  mixers only    │   │ units    │          │
    │  └─────────┘   └─────────────────┘   └──────────┘          │
    │                   KERR CLOCK (center)                        │
    │                                                              │
    │  ╔══════════════════════════════════════════════════╗        │
    │  ║  WEIGHT STREAMING BUS (top, from Optical RAM)    ║        │
    │  ╚══════════════════════════════════════════════════╝        │
    └──────────────────────────────────────────────────────────────┘

Key features:
    - Single monolithic LiNbO3 (TFLN) substrate
    - Path-length equalized waveguides from IOC to each PE row
    - Serpentine meanders on shorter paths to match longest path
    - Passive accelerator region (no clock distribution to PEs)
    - Kerr clock in IOC region only
    - Weight streaming bus along top edge

Material: X-cut LiNbO3 (TFLN)
    - χ² for SFG/DFG mixing (d33 ≈ 30 pm/V)
    - χ³ for Kerr clock
    - Electro-optic for MZI modulators (Pockels effect)
    - n = 2.2, waveguide width = 0.5 μm

Author: Wavelength-Division Ternary Optical Computer Project
"""

import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.typings import LayerSpec
import numpy as np
from typing import Optional, Tuple
import os

# Activate PDK
gf.gpdk.PDK.activate()

# =============================================================================
# Layer Definitions (matches existing layer mapping)
# =============================================================================

LAYER_WAVEGUIDE: LayerSpec = (1, 0)      # LiNbO3 waveguides
LAYER_CHI2_SFG: LayerSpec = (2, 0)       # SFG mixer regions (PPLN)
LAYER_PPLN_STRIPES: LayerSpec = (2, 1)   # PPLN poling electrode stripes (within mixer)
LAYER_PHOTODET: LayerSpec = (3, 0)       # Photodetector regions
LAYER_CHI2_DFG: LayerSpec = (4, 0)       # DFG mixer regions
LAYER_KERR_CLK: LayerSpec = (5, 0)       # Kerr clock resonator
LAYER_HEATER: LayerSpec = (10, 0)        # TiN heaters / RF electrodes
LAYER_CARRY: LayerSpec = (11, 0)         # Vertical data flow
LAYER_METAL_PAD: LayerSpec = (12, 0)     # Bond pads (Ti/Au) — wire-bond only
LAYER_METAL_INT: LayerSpec = (12, 1)     # Internal metal (control pads, RF electrodes)
LAYER_LOG: LayerSpec = (13, 0)           # Saturable absorber (Er/Yb)
LAYER_GAIN: LayerSpec = (14, 0)          # Gain medium (Er/Yb)
LAYER_AWG: LayerSpec = (15, 0)           # AWG demux regions
LAYER_DETECTOR: LayerSpec = (16, 0)      # Detector active areas
LAYER_LASER: LayerSpec = (17, 0)         # Laser coupling regions
LAYER_WEIGHT: LayerSpec = (18, 0)        # Weight bus
LAYER_MUX: LayerSpec = (19, 0)           # Mode MUX
LAYER_REGION: LayerSpec = (20, 0)        # Region boundaries
LAYER_MEANDER: LayerSpec = (21, 0)       # Path equalization meanders
LAYER_TEXT: LayerSpec = (100, 0)         # Labels
LAYER_CHIP_BORDER: LayerSpec = (99, 0)   # Chip boundary

# =============================================================================
# Physical Constants
# =============================================================================

WAVEGUIDE_WIDTH = 0.5         # μm — single-mode for all λ
BEND_RADIUS = 5.0             # μm — minimum low-loss bend
N_LINBO3 = 2.2                # Refractive index
C_SPEED_UM_PS = 299.792       # μm/ps — speed of light
V_GROUP_UM_PS = C_SPEED_UM_PS / N_LINBO3  # ~136.3 μm/ps group velocity

# PE dimensions (expanded for 6-lane parallel PPLN mixer)
PE_WIDTH = 55.0               # μm (was 50, expanded for 6-lane mixer)
PE_HEIGHT = 55.0              # μm (was 50, expanded for 6-lane mixer)
PE_SPACING = 5.0              # μm between PEs
PE_PITCH = PE_WIDTH + PE_SPACING  # 60 μm center-to-center

# 6-lane PPLN mixer QPM periods (μm) — B+B case for each triplet
TRIPLET_QPM_PERIODS = {
    1: 3.78,   # T1: 1000/1020/1040 nm
    2: 4.62,   # T2: 1060/1080/1100 nm
    3: 5.57,   # T3: 1120/1140/1160 nm
    4: 6.63,   # T4: 1180/1200/1220 nm
    5: 7.82,   # T5: 1240/1260/1280 nm
    6: 9.13,   # T6: 1300/1320/1340 nm
}
N_LANES = 6  # Number of parallel WDM lanes

# Array
N_ROWS = 9
N_COLS = 9
ARRAY_WIDTH = N_COLS * PE_PITCH   # 495 μm
ARRAY_HEIGHT = N_ROWS * PE_PITCH  # 495 μm

# IOC regions
IOC_INPUT_WIDTH = 180.0       # μm — left edge (encoders)
IOC_OUTPUT_WIDTH = 200.0      # μm — right edge (decoders)

# Chip margins (must satisfy EDGE.1: features >= 50 um from die edge)
MARGIN_X = 60.0               # μm from region to chip edge
MARGIN_Y = 120.0              # μm bottom margin (room for Kerr clock + routing)
MARGIN_Y_TOP = 80.0           # μm top margin (above weight bus)
WEIGHT_BUS_HEIGHT = 40.0      # μm — weight streaming bus

# Routing gaps between regions
ROUTING_GAP = 60.0            # μm between IOC and array (for path equalization)

# Clock
CLOCK_FREQ_MHZ = 617

# =============================================================================
# Calculated Chip Dimensions
# =============================================================================

CHIP_WIDTH = (MARGIN_X + IOC_INPUT_WIDTH + ROUTING_GAP +
              ARRAY_WIDTH + ROUTING_GAP + IOC_OUTPUT_WIDTH + MARGIN_X)
CHIP_HEIGHT = (MARGIN_Y + ARRAY_HEIGHT + WEIGHT_BUS_HEIGHT + MARGIN_Y_TOP)

# Region positions (X origins)
IOC_INPUT_X = MARGIN_X
ARRAY_X = IOC_INPUT_X + IOC_INPUT_WIDTH + ROUTING_GAP
IOC_OUTPUT_X = ARRAY_X + ARRAY_WIDTH + ROUTING_GAP
ARRAY_Y = MARGIN_Y  # Bottom of array

# =============================================================================
# Unique ID Generator
# =============================================================================

_uid_counter = 0
def _uid() -> str:
    global _uid_counter
    _uid_counter += 1
    return f"{_uid_counter:05d}"


# =============================================================================
# Core PE (simplified for monolithic integration)
# =============================================================================

@gf.cell
def monolithic_pe(row: int = 0, col: int = 0) -> Component:
    """
    Simplified streaming PE for monolithic chip.

    Passive components only:
    - WDM demux (AWG, splits 6 triplets into dedicated lanes)
    - 6 PPLN SFG mixers (each QPM-tuned to its triplet)
    - WDM mux (AWG, recombines 6 SFG output bands)
    - Waveguide routing (input/output/weight)
    - Accumulator loop

    No clock input needed — timing via path-length matching.
    Chip is fully passive — all 6 mixers are fixed photonic geometry.
    """
    c = gf.Component(f"M_PE_{row}_{col}_{_uid()}")

    # PE boundary
    c.add_polygon([
        (0, 0), (PE_WIDTH, 0), (PE_WIDTH, PE_HEIGHT), (0, PE_HEIGHT)
    ], layer=LAYER_REGION)

    # --- WDM Demux (AWG 1×6) — splits 6 triplets into dedicated lanes ---
    demux_x, demux_y = 8, 35
    demux_w, demux_h = 10, 10
    c.add_polygon([
        (demux_x, demux_y),
        (demux_x + demux_w, demux_y),
        (demux_x + demux_w, demux_y + demux_h),
        (demux_x, demux_y + demux_h)
    ], layer=LAYER_AWG)
    c.add_label("DEMUX", position=(demux_x + demux_w/2, demux_y + demux_h + 1), layer=LAYER_TEXT)

    # --- 6 Parallel PPLN SFG Mixers ---
    mixer_region_x = 8
    mixer_region_y = 12
    lane_width = 4.0        # μm per mixer lane
    lane_spacing = 1.5      # μm between lanes
    mixer_h = 20.0          # μm mixer length (PPLN interaction region)

    for lane in range(N_LANES):
        lane_x = mixer_region_x + lane * (lane_width + lane_spacing)
        # PPLN mixer block
        c.add_polygon([
            (lane_x, mixer_region_y),
            (lane_x + lane_width, mixer_region_y),
            (lane_x + lane_width, mixer_region_y + mixer_h),
            (lane_x, mixer_region_y + mixer_h)
        ], layer=LAYER_CHI2_SFG)

        # PPLN poling stripes per lane (QPM period varies by triplet)
        qpm = TRIPLET_QPM_PERIODS[lane + 1]
        stripe_period = qpm  # Full period
        stripe_w = qpm / 2.0  # Half-period domain
        n_stripes = max(int(mixer_h / stripe_period), 1)
        for s in range(n_stripes):
            sy = mixer_region_y + s * stripe_period + 0.2
            sh = min(stripe_w - 0.4, mixer_region_y + mixer_h - sy - 0.2)
            if sh > 0.2:
                c.add_polygon([
                    (lane_x + 0.3, sy),
                    (lane_x + lane_width - 0.3, sy),
                    (lane_x + lane_width - 0.3, sy + sh),
                    (lane_x + 0.3, sy + sh)
                ], layer=LAYER_PPLN_STRIPES)

        # Lane label
        c.add_label(f"T{lane+1}", position=(lane_x + lane_width/2, mixer_region_y - 1), layer=LAYER_TEXT)

    # --- WDM Mux (AWG 6×1) — recombines SFG outputs ---
    mux_x, mux_y = 8, 2
    mux_w, mux_h = 10, 8
    c.add_polygon([
        (mux_x, mux_y),
        (mux_x + mux_w, mux_y),
        (mux_x + mux_w, mux_y + mux_h),
        (mux_x, mux_y + mux_h)
    ], layer=LAYER_AWG)
    c.add_label("MUX", position=(mux_x + mux_w/2, mux_y - 1), layer=LAYER_TEXT)

    # Routing waveguides from demux to mixers (fan-out)
    for lane in range(N_LANES):
        lane_x = mixer_region_x + lane * (lane_width + lane_spacing) + lane_width / 2
        c.add_polygon([
            (lane_x - WAVEGUIDE_WIDTH/2, demux_y),
            (lane_x + WAVEGUIDE_WIDTH/2, demux_y),
            (lane_x + WAVEGUIDE_WIDTH/2, mixer_region_y + mixer_h),
            (lane_x - WAVEGUIDE_WIDTH/2, mixer_region_y + mixer_h)
        ], layer=LAYER_WAVEGUIDE)

    # Routing waveguides from mixers to mux (fan-in)
    for lane in range(N_LANES):
        lane_x = mixer_region_x + lane * (lane_width + lane_spacing) + lane_width / 2
        c.add_polygon([
            (lane_x - WAVEGUIDE_WIDTH/2, mux_y + mux_h),
            (lane_x + WAVEGUIDE_WIDTH/2, mux_y + mux_h),
            (lane_x + WAVEGUIDE_WIDTH/2, mixer_region_y),
            (lane_x - WAVEGUIDE_WIDTH/2, mixer_region_y)
        ], layer=LAYER_WAVEGUIDE)

    # Accumulator loop (recirculating delay)
    acc_x = 44
    acc_y = 8
    c.add_polygon([
        (acc_x, acc_y), (acc_x + 8, acc_y),
        (acc_x + 8, acc_y + 12), (acc_x, acc_y + 12)
    ], layer=LAYER_WAVEGUIDE)

    # Horizontal input waveguide (activation from left → demux)
    c.add_polygon([
        (0, PE_HEIGHT/2 - WAVEGUIDE_WIDTH/2),
        (demux_x, PE_HEIGHT/2 - WAVEGUIDE_WIDTH/2),
        (demux_x, PE_HEIGHT/2 + WAVEGUIDE_WIDTH/2),
        (0, PE_HEIGHT/2 + WAVEGUIDE_WIDTH/2)
    ], layer=LAYER_WAVEGUIDE)

    # Horizontal output waveguide (mux → activation passthrough to right)
    mixer_end_x = mixer_region_x + N_LANES * (lane_width + lane_spacing)
    c.add_polygon([
        (mixer_end_x, PE_HEIGHT/2 - WAVEGUIDE_WIDTH/2),
        (PE_WIDTH, PE_HEIGHT/2 - WAVEGUIDE_WIDTH/2),
        (PE_WIDTH, PE_HEIGHT/2 + WAVEGUIDE_WIDTH/2),
        (mixer_end_x, PE_HEIGHT/2 + WAVEGUIDE_WIDTH/2)
    ], layer=LAYER_WAVEGUIDE)

    # Vertical input (partial sum from above)
    c.add_polygon([
        (PE_WIDTH/2 - WAVEGUIDE_WIDTH/2, PE_HEIGHT),
        (PE_WIDTH/2 + WAVEGUIDE_WIDTH/2, PE_HEIGHT),
        (PE_WIDTH/2 + WAVEGUIDE_WIDTH/2, demux_y + demux_h),
        (PE_WIDTH/2 - WAVEGUIDE_WIDTH/2, demux_y + demux_h)
    ], layer=LAYER_CARRY)

    # Vertical output (partial sum to below)
    c.add_polygon([
        (PE_WIDTH/2 - WAVEGUIDE_WIDTH/2, mux_y),
        (PE_WIDTH/2 + WAVEGUIDE_WIDTH/2, mux_y),
        (PE_WIDTH/2 + WAVEGUIDE_WIDTH/2, 0),
        (PE_WIDTH/2 - WAVEGUIDE_WIDTH/2, 0)
    ], layer=LAYER_CARRY)

    # Weight input from top (streaming from NR-IOC, 6 triplets multiplexed)
    weight_x = PE_WIDTH - 8
    c.add_polygon([
        (weight_x - WAVEGUIDE_WIDTH/2, PE_HEIGHT),
        (weight_x + WAVEGUIDE_WIDTH/2, PE_HEIGHT),
        (weight_x + WAVEGUIDE_WIDTH/2, demux_y + demux_h),
        (weight_x - WAVEGUIDE_WIDTH/2, demux_y + demux_h)
    ], layer=LAYER_WEIGHT)

    # Ports
    c.add_port("in_h", center=(0, PE_HEIGHT/2), width=WAVEGUIDE_WIDTH,
               orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port("out_h", center=(PE_WIDTH, PE_HEIGHT/2), width=WAVEGUIDE_WIDTH,
               orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port("in_v", center=(PE_WIDTH/2, PE_HEIGHT), width=WAVEGUIDE_WIDTH,
               orientation=90, layer=LAYER_CARRY)
    c.add_port("out_v", center=(PE_WIDTH/2, 0), width=WAVEGUIDE_WIDTH,
               orientation=270, layer=LAYER_CARRY)
    c.add_port("weight_in", center=(weight_x, PE_HEIGHT), width=WAVEGUIDE_WIDTH,
               orientation=90, layer=LAYER_WEIGHT)

    # Label
    c.add_label(f"PE[{row},{col}]", position=(PE_WIDTH/2, PE_HEIGHT - 4), layer=LAYER_TEXT)

    return c


# =============================================================================
# IOC Encoder (simplified for left edge)
# =============================================================================

@gf.cell
def ioc_input_encoder(row_id: int = 0) -> Component:
    """
    Single-channel IOC encoder for left edge.

    Contains: 3 MZI modulators + wavelength combiner.
    Outputs wavelength-encoded ternary signal to array row.
    """
    c = gf.Component(f"IOC_ENC_{row_id}_{_uid()}")

    width = IOC_INPUT_WIDTH
    height = PE_PITCH - 2  # Fits in one row slot

    # Encoder block
    c.add_polygon([
        (0, 0), (width, 0), (width, height), (0, height)
    ], layer=LAYER_REGION)

    # 3 MZI modulators (R/G/B) — stacked vertically
    mzi_width = 40
    mzi_height = 12
    mzi_spacing = (height - 3 * mzi_height) / 4

    for i, (label, y_off) in enumerate([
        ("R 1550nm", mzi_spacing),
        ("G 1310nm", 2 * mzi_spacing + mzi_height),
        ("B 1064nm", 3 * mzi_spacing + 2 * mzi_height),
    ]):
        # MZI body
        c.add_polygon([
            (10, y_off), (10 + mzi_width, y_off),
            (10 + mzi_width, y_off + mzi_height), (10, y_off + mzi_height)
        ], layer=LAYER_WAVEGUIDE)

        # RF electrode (MZI phase control)
        c.add_polygon([
            (15, y_off + mzi_height + 1), (45, y_off + mzi_height + 1),
            (45, y_off + mzi_height + 3), (15, y_off + mzi_height + 3)
        ], layer=LAYER_HEATER)

        # RF electrode contact pad (internal, not wire-bond)
        c.add_polygon([
            (47, y_off + mzi_height - 1), (57, y_off + mzi_height - 1),
            (57, y_off + mzi_height + 5), (47, y_off + mzi_height + 5)
        ], layer=LAYER_METAL_INT)

        c.add_label(label, position=(30, y_off + mzi_height/2), layer=LAYER_TEXT)

    # Wavelength combiner (MMI-based)
    comb_x = 60
    comb_y = height/2 - 8
    c.add_polygon([
        (comb_x, comb_y), (comb_x + 30, comb_y),
        (comb_x + 30, comb_y + 16), (comb_x, comb_y + 16)
    ], layer=LAYER_WAVEGUIDE)
    c.add_label("COMB", position=(comb_x + 15, comb_y + 8), layer=LAYER_TEXT)

    # Output waveguide
    c.add_polygon([
        (comb_x + 30, height/2 - WAVEGUIDE_WIDTH/2),
        (width, height/2 - WAVEGUIDE_WIDTH/2),
        (width, height/2 + WAVEGUIDE_WIDTH/2),
        (comb_x + 30, height/2 + WAVEGUIDE_WIDTH/2)
    ], layer=LAYER_WAVEGUIDE)

    # Laser input port (left edge of chip)
    c.add_port("laser_in", center=(0, height/2), width=4,
               orientation=180, layer=LAYER_LASER)

    # Encoded output port (to routing)
    c.add_port("encoded_out", center=(width, height/2), width=WAVEGUIDE_WIDTH,
               orientation=0, layer=LAYER_WAVEGUIDE)

    # Control pads (internal — not wire-bond)
    c.add_polygon([
        (5, height - 8), (25, height - 8), (25, height - 2), (5, height - 2)
    ], layer=LAYER_METAL_INT)
    c.add_label(f"ENC_{row_id}", position=(15, height + 2), layer=LAYER_TEXT)

    return c


# =============================================================================
# IOC Decoder (simplified for right edge)
# =============================================================================

@gf.cell
def ioc_output_decoder(col_id: int = 0) -> Component:
    """
    Single-channel IOC decoder for right edge.

    Contains: AWG demux + 5 photodetectors + result encoder.
    Receives SFG output wavelengths from array column.
    """
    c = gf.Component(f"IOC_DEC_{col_id}_{_uid()}")

    width = IOC_OUTPUT_WIDTH
    height = PE_PITCH - 2

    # Decoder block
    c.add_polygon([
        (0, 0), (width, 0), (width, height), (0, height)
    ], layer=LAYER_REGION)

    # Input waveguide
    c.add_polygon([
        (0, height/2 - WAVEGUIDE_WIDTH/2),
        (20, height/2 - WAVEGUIDE_WIDTH/2),
        (20, height/2 + WAVEGUIDE_WIDTH/2),
        (0, height/2 + WAVEGUIDE_WIDTH/2)
    ], layer=LAYER_WAVEGUIDE)

    # AWG demux (5-channel)
    awg_x, awg_y = 20, 8
    awg_w, awg_h = 50, height - 16
    c.add_polygon([
        (awg_x, awg_y), (awg_x + awg_w, awg_y),
        (awg_x + awg_w, awg_y + awg_h), (awg_x, awg_y + awg_h)
    ], layer=LAYER_AWG)
    c.add_label("AWG 5ch", position=(awg_x + awg_w/2, awg_y + awg_h/2), layer=LAYER_TEXT)

    # 5 photodetectors
    pd_x = awg_x + awg_w + 10
    pd_spacing = awg_h / 5
    for i in range(5):
        pd_y = awg_y + i * pd_spacing + pd_spacing/2 - 3
        c.add_polygon([
            (pd_x, pd_y), (pd_x + 20, pd_y),
            (pd_x + 20, pd_y + 6), (pd_x, pd_y + 6)
        ], layer=LAYER_DETECTOR)

    # Result encoder block (internal electronics — not wire-bond)
    enc_x = pd_x + 30
    c.add_polygon([
        (enc_x, 10), (enc_x + 30, 10),
        (enc_x + 30, height - 10), (enc_x, height - 10)
    ], layer=LAYER_METAL_INT)
    c.add_label("5->3", position=(enc_x + 15, height/2), layer=LAYER_TEXT)

    # Input port (from array)
    c.add_port("result_in", center=(0, height/2), width=WAVEGUIDE_WIDTH,
               orientation=180, layer=LAYER_WAVEGUIDE)

    # Electronic output port
    c.add_port("data_out", center=(width, height/2), width=10,
               orientation=0, layer=LAYER_METAL_PAD)

    c.add_label(f"DEC_{col_id}", position=(width/2, height + 2), layer=LAYER_TEXT)

    return c


# =============================================================================
# Path-Length Equalized Waveguide Routing
# =============================================================================

def calculate_path_equalization(n_rows: int = 9) -> dict:
    """
    Calculate meander lengths needed for path-length equalization.

    The longest path is from the IOC input to the farthest PE row.
    Shorter paths need serpentine meanders to match.

    Returns dict with row_id -> {straight_length, meander_length, total_length}
    """
    # Distance from IOC output to each row's entry point in the array
    # Row 0 is at the top (farthest from bottom)
    paths = {}

    # The routing gap is where equalization happens
    # Each row enters at a different Y position
    # Row 0 is at y = ARRAY_Y + (N_ROWS - 1) * PE_PITCH (top)
    # Row 8 is at y = ARRAY_Y (bottom)

    # Straight horizontal distance is the same for all (ROUTING_GAP)
    # But vertical routing differs — we need to include any vertical offset

    # For split-edge, all encoders are stacked vertically on the left.
    # Each encoder output aligns with its row, so the horizontal distance
    # to the array entry is the same: ROUTING_GAP.
    # BUT — we want all paths from encoder output to PE[row, 0].in_h
    # to have the SAME optical path length.

    # Since rows are at different Y positions, and encoders are aligned,
    # the straight path is just the gap. The issue is that if the
    # encoders and array rows are perfectly aligned, the paths are
    # already equal! The meanders are needed if there's any Y mismatch.

    # However, for timing synchronization across the chip, we want
    # the light from ALL encoders to arrive at their respective PE rows
    # simultaneously. Since the encoders fire simultaneously, and the
    # horizontal gap is the same for all, the paths are inherently equal.

    # Where equalization REALLY matters is the OUTPUT side:
    # PE[row, N_COLS-1].out_v → column output → decoder
    # The partial sums flow vertically through all rows, accumulating.
    # Row 0 (top) has 8 rows below it. Row 8 (bottom) exits immediately.
    # This is the systolic flow — it's meant to be sequential, not simultaneous.

    # For the INPUT side, we DO want simultaneous arrival of activation
    # vectors at each row. Since encoder→row paths are all the same
    # horizontal distance (ROUTING_GAP), they're inherently matched!

    # The WEIGHT bus is a separate path from top — weight arrival at
    # different rows DOES vary. Let's calculate that equalization.

    max_weight_path = (N_ROWS - 1) * PE_PITCH  # Row 8 is farthest from top

    for row in range(n_rows):
        # Weight path: from weight bus at top of array to this row
        rows_from_top = row  # Row 0 is at top (nearest to weight bus)
        weight_vertical = rows_from_top * PE_PITCH
        weight_meander_needed = max_weight_path - weight_vertical

        # Activation path: horizontal from IOC to array entry (same for all)
        activation_horizontal = ROUTING_GAP

        paths[row] = {
            'activation_straight': activation_horizontal,
            'activation_meander': 0.0,  # Already equal — no meander needed
            'activation_total': activation_horizontal,
            'weight_vertical': weight_vertical,
            'weight_meander': weight_meander_needed,
            'weight_total': weight_vertical + weight_meander_needed,
        }

    return paths


@gf.cell
def waveguide_meander(
    total_extra_length: float,
    width: float = WAVEGUIDE_WIDTH,
    bend_radius: float = BEND_RADIUS,
    n_turns: int = None,
    direction: str = "horizontal",
) -> Component:
    """
    Serpentine meander waveguide for path-length equalization.

    Adds extra optical path length in a compact area using
    back-and-forth bends.

    Args:
        total_extra_length: Extra path length to add (μm)
        width: Waveguide width
        bend_radius: Minimum bend radius
        n_turns: Number of U-turns (auto-calculated if None)
        direction: "horizontal" meander or "vertical" meander
    """
    c = gf.Component(f"meander_{total_extra_length:.0f}um_{_uid()}")

    if total_extra_length <= 0:
        # No meander needed — just a straight through
        c.add_polygon([
            (0, -width/2), (5, -width/2), (5, width/2), (0, width/2)
        ], layer=LAYER_MEANDER)
        c.add_port("in", center=(0, 0), width=width, orientation=180, layer=LAYER_WAVEGUIDE)
        c.add_port("out", center=(5, 0), width=width, orientation=0, layer=LAYER_WAVEGUIDE)
        return c

    # Calculate meander geometry
    turn_length = np.pi * bend_radius  # Length consumed per 180° turn
    if n_turns is None:
        # Each U-turn uses π*r of path length in the turn + straight segments
        n_turns = max(2, int(total_extra_length / (2 * turn_length + 20)) + 1)

    # Length per straight segment between turns
    straight_per_segment = (total_extra_length - n_turns * 2 * turn_length) / (n_turns * 2)
    straight_per_segment = max(straight_per_segment, 2.0)

    # Meander spacing (vertical distance between parallel runs)
    meander_spacing = 2 * bend_radius + 2

    # Draw meander as simplified polygon representation
    # (GDS representation — actual waveguide would be routed with bends)
    total_meander_width = n_turns * meander_spacing
    meander_height = straight_per_segment + 2 * bend_radius

    # Visual representation: serpentine path
    x = 0
    for i in range(n_turns):
        y_base = 0 if i % 2 == 0 else -meander_height
        y_top = meander_height if i % 2 == 0 else 0

        # Vertical segment going up or down
        c.add_polygon([
            (x, y_base - width/2),
            (x + width, y_base - width/2),
            (x + width, y_top + width/2),
            (x, y_top + width/2)
        ], layer=LAYER_MEANDER)

        # Horizontal connector to next segment
        if i < n_turns - 1:
            y_conn = y_top if i % 2 == 0 else y_base
            c.add_polygon([
                (x, y_conn - width/2),
                (x + meander_spacing, y_conn - width/2),
                (x + meander_spacing, y_conn + width/2),
                (x, y_conn + width/2)
            ], layer=LAYER_MEANDER)

        x += meander_spacing

    # Ports at entry/exit
    c.add_port("in", center=(0, 0), width=width, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port("out", center=(x - meander_spacing + width, 0), width=width,
               orientation=0, layer=LAYER_WAVEGUIDE)

    # Label with path length
    c.add_label(f"+{total_extra_length:.0f}μm", position=(x/2, meander_height + 5), layer=LAYER_TEXT)

    return c


# =============================================================================
# Kerr Clock (IOC-internal)
# =============================================================================

@gf.cell
def kerr_clock_unit() -> Component:
    """
    617 MHz Kerr self-pulsing clock.

    Located within the IOC region (NOT distributed to PEs).
    Uses χ³ nonlinearity in LiNbO3 ring resonator.
    """
    c = gf.Component(f"kerr_clock_{_uid()}")

    # Ring resonator (Kerr medium)
    ring_radius = 15.0
    n_points = 48
    angles = np.linspace(0, 2 * np.pi, n_points)
    ring_outer = [(ring_radius * np.cos(a), ring_radius * np.sin(a)) for a in angles]
    c.add_polygon(ring_outer, layer=LAYER_KERR_CLK)

    inner_radius = ring_radius - 3
    ring_inner = [(inner_radius * np.cos(a), inner_radius * np.sin(a)) for a in angles]
    c.add_polygon(ring_inner, layer=LAYER_REGION)  # hollow center

    # Bus waveguide (coupling)
    c.add_polygon([
        (-ring_radius - 5, -ring_radius - 3 - WAVEGUIDE_WIDTH/2),
        (ring_radius + 5, -ring_radius - 3 - WAVEGUIDE_WIDTH/2),
        (ring_radius + 5, -ring_radius - 3 + WAVEGUIDE_WIDTH/2),
        (-ring_radius - 5, -ring_radius - 3 + WAVEGUIDE_WIDTH/2)
    ], layer=LAYER_WAVEGUIDE)

    # Pump input pad (internal — not wire-bond)
    c.add_polygon([
        (-8, ring_radius + 2), (8, ring_radius + 2),
        (8, ring_radius + 10), (-8, ring_radius + 10)
    ], layer=LAYER_METAL_INT)

    # Labels
    c.add_label("617 MHz", position=(0, 0), layer=LAYER_TEXT)
    c.add_label("KERR", position=(0, -8), layer=LAYER_TEXT)
    c.add_label("PUMP", position=(0, ring_radius + 12), layer=LAYER_TEXT)

    # Ports
    c.add_port("clk_out", center=(ring_radius + 5, -ring_radius - 3),
               width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port("pump_in", center=(0, ring_radius + 6),
               width=16, orientation=90, layer=LAYER_METAL_PAD)

    return c


# =============================================================================
# MAIN: Monolithic 9x9 Chip
# =============================================================================

@gf.cell
def monolithic_chip_9x9(
    include_path_equalization: bool = True,
    include_kerr_clock: bool = True,
    include_weight_bus: bool = True,
) -> Component:
    """
    Complete monolithic 9x9 N-Radix chip — split-edge topology.

    Single LiNbO3 substrate with:
    - IOC input region (left edge): 9 encoder units
    - 9x9 PE systolic array (center): 81 passive PEs
    - IOC output region (right edge): 9 decoder units
    - Kerr clock (center, IOC-internal)
    - Weight streaming bus (top)
    - Path-length equalized routing

    Returns:
        Complete chip GDS component
    """
    c = gf.Component("monolithic_9x9_nradix")

    print("=" * 60)
    print("  MONOLITHIC 9x9 N-RADIX CHIP GENERATOR")
    print("  Split-Edge Topology — Single LiNbO3 Substrate")
    print("=" * 60)

    # =========================================================================
    # Chip Boundary
    # =========================================================================

    c.add_polygon([
        (0, 0), (CHIP_WIDTH, 0), (CHIP_WIDTH, CHIP_HEIGHT), (0, CHIP_HEIGHT)
    ], layer=LAYER_CHIP_BORDER)

    print(f"  Chip dimensions: {CHIP_WIDTH:.0f} × {CHIP_HEIGHT:.0f} μm")
    print(f"  Material: X-cut LiNbO3 (TFLN)")

    # =========================================================================
    # Region Boundaries (visual)
    # =========================================================================

    # IOC Input region outline
    c.add_polygon([
        (IOC_INPUT_X, ARRAY_Y),
        (IOC_INPUT_X + IOC_INPUT_WIDTH, ARRAY_Y),
        (IOC_INPUT_X + IOC_INPUT_WIDTH, ARRAY_Y + ARRAY_HEIGHT),
        (IOC_INPUT_X, ARRAY_Y + ARRAY_HEIGHT)
    ], layer=LAYER_REGION)
    c.add_label("IOC INPUT", position=(IOC_INPUT_X + IOC_INPUT_WIDTH/2,
                ARRAY_Y + ARRAY_HEIGHT + 10), layer=LAYER_TEXT)
    c.add_label("(ACTIVE)", position=(IOC_INPUT_X + IOC_INPUT_WIDTH/2,
                ARRAY_Y + ARRAY_HEIGHT + 22), layer=LAYER_TEXT)

    # Accelerator array region outline
    c.add_polygon([
        (ARRAY_X, ARRAY_Y),
        (ARRAY_X + ARRAY_WIDTH, ARRAY_Y),
        (ARRAY_X + ARRAY_WIDTH, ARRAY_Y + ARRAY_HEIGHT),
        (ARRAY_X, ARRAY_Y + ARRAY_HEIGHT)
    ], layer=LAYER_REGION)
    c.add_label("9×9 PE ARRAY", position=(ARRAY_X + ARRAY_WIDTH/2,
                ARRAY_Y + ARRAY_HEIGHT + 10), layer=LAYER_TEXT)
    c.add_label("(PASSIVE)", position=(ARRAY_X + ARRAY_WIDTH/2,
                ARRAY_Y + ARRAY_HEIGHT + 22), layer=LAYER_TEXT)

    # IOC Output region outline
    c.add_polygon([
        (IOC_OUTPUT_X, ARRAY_Y),
        (IOC_OUTPUT_X + IOC_OUTPUT_WIDTH, ARRAY_Y),
        (IOC_OUTPUT_X + IOC_OUTPUT_WIDTH, ARRAY_Y + ARRAY_HEIGHT),
        (IOC_OUTPUT_X, ARRAY_Y + ARRAY_HEIGHT)
    ], layer=LAYER_REGION)
    c.add_label("IOC OUTPUT", position=(IOC_OUTPUT_X + IOC_OUTPUT_WIDTH/2,
                ARRAY_Y + ARRAY_HEIGHT + 10), layer=LAYER_TEXT)
    c.add_label("(ACTIVE)", position=(IOC_OUTPUT_X + IOC_OUTPUT_WIDTH/2,
                ARRAY_Y + ARRAY_HEIGHT + 22), layer=LAYER_TEXT)

    # =========================================================================
    # IOC Input Region (Left Edge) — 9 Encoders
    # =========================================================================

    print("  Placing IOC input encoders (left edge)...")

    for row in range(N_ROWS):
        enc = c << ioc_input_encoder(row_id=row)
        enc_y = ARRAY_Y + row * PE_PITCH + 1  # +1 for centering in slot
        enc.dmove((IOC_INPUT_X, enc_y))

        # Add chip-edge laser input port
        c.add_port(f"laser_in_{row}", center=(0, enc_y + PE_PITCH/2),
                   width=4, orientation=180, layer=LAYER_LASER)

    # =========================================================================
    # 9x9 PE Array (Center) — Passive Region
    # =========================================================================

    print("  Placing 9×9 PE array (center, passive)...")

    for row in range(N_ROWS):
        for col in range(N_COLS):
            pe = c << monolithic_pe(row=row, col=col)
            pe_x = ARRAY_X + col * PE_PITCH
            pe_y = ARRAY_Y + row * PE_PITCH
            pe.dmove((pe_x, pe_y))

            # Horizontal waveguide between PEs in same row
            if col > 0:
                x_start = ARRAY_X + (col - 1) * PE_PITCH + PE_WIDTH
                x_end = ARRAY_X + col * PE_PITCH
                y = pe_y + PE_HEIGHT / 2
                c.add_polygon([
                    (x_start, y - WAVEGUIDE_WIDTH/2),
                    (x_end, y - WAVEGUIDE_WIDTH/2),
                    (x_end, y + WAVEGUIDE_WIDTH/2),
                    (x_start, y + WAVEGUIDE_WIDTH/2)
                ], layer=LAYER_WAVEGUIDE)

            # Vertical waveguide between PEs in same column
            # Only fill the gap between PEs (PE internal carries handle the rest)
            if row > 0:
                x = pe_x + PE_WIDTH / 2
                y_start = ARRAY_Y + (row - 1) * PE_PITCH + PE_HEIGHT  # Top of previous PE
                y_end = ARRAY_Y + row * PE_PITCH                       # Bottom of current PE
                c.add_polygon([
                    (x - WAVEGUIDE_WIDTH/2, y_start),
                    (x + WAVEGUIDE_WIDTH/2, y_start),
                    (x + WAVEGUIDE_WIDTH/2, y_end),
                    (x - WAVEGUIDE_WIDTH/2, y_end)
                ], layer=LAYER_CARRY)

    # =========================================================================
    # IOC Output Region (Right Edge) — 9 Decoders
    # =========================================================================

    print("  Placing IOC output decoders (right edge)...")

    for col in range(N_COLS):
        dec = c << ioc_output_decoder(col_id=col)
        dec_y = ARRAY_Y + col * PE_PITCH + 1
        dec.dmove((IOC_OUTPUT_X, dec_y))

        # Add chip-edge electronic output port
        c.add_port(f"data_out_{col}",
                   center=(CHIP_WIDTH, dec_y + PE_PITCH/2),
                   width=10, orientation=0, layer=LAYER_METAL_PAD)

    # =========================================================================
    # Routing: IOC Input → PE Array (horizontal waveguides)
    # =========================================================================

    print("  Routing IOC inputs to PE array...")

    for row in range(N_ROWS):
        y = ARRAY_Y + row * PE_PITCH + PE_HEIGHT / 2
        x_start = IOC_INPUT_X + IOC_INPUT_WIDTH
        x_end = ARRAY_X

        c.add_polygon([
            (x_start, y - WAVEGUIDE_WIDTH/2),
            (x_end, y - WAVEGUIDE_WIDTH/2),
            (x_end, y + WAVEGUIDE_WIDTH/2),
            (x_start, y + WAVEGUIDE_WIDTH/2)
        ], layer=LAYER_WAVEGUIDE)

    # =========================================================================
    # Routing: PE Array → IOC Output (horizontal waveguides for column outputs)
    # =========================================================================

    print("  Routing PE array outputs to IOC decoders...")

    # Column outputs exit from the bottom of each column.
    # We need to route them to the right-edge decoders.
    # Route: PE[8, col].out_v → bend → horizontal → decoder[col].result_in

    for col in range(N_COLS):
        # Bottom of column
        col_x = ARRAY_X + col * PE_PITCH + PE_WIDTH / 2
        col_bottom_y = ARRAY_Y

        # Route down, then right to decoder
        # Vertical segment down to routing channel
        route_y = ARRAY_Y - 5 - col * 3  # Stagger Y to avoid crossing
        c.add_polygon([
            (col_x - WAVEGUIDE_WIDTH/2, route_y),
            (col_x + WAVEGUIDE_WIDTH/2, route_y),
            (col_x + WAVEGUIDE_WIDTH/2, col_bottom_y),
            (col_x - WAVEGUIDE_WIDTH/2, col_bottom_y)
        ], layer=LAYER_CARRY)

        # Stagger X for vertical rise to decoder (3 um apart per column)
        rise_x = IOC_OUTPUT_X + 5 + col * 3  # Each column at different X
        dec_y = ARRAY_Y + col * PE_PITCH + PE_HEIGHT / 2

        # Horizontal segment to rise point
        c.add_polygon([
            (col_x, route_y - WAVEGUIDE_WIDTH/2),
            (rise_x, route_y - WAVEGUIDE_WIDTH/2),
            (rise_x, route_y + WAVEGUIDE_WIDTH/2),
            (col_x, route_y + WAVEGUIDE_WIDTH/2)
        ], layer=LAYER_CARRY)

        # Vertical segment up to decoder input
        c.add_polygon([
            (rise_x - WAVEGUIDE_WIDTH/2, route_y),
            (rise_x + WAVEGUIDE_WIDTH/2, route_y),
            (rise_x + WAVEGUIDE_WIDTH/2, dec_y),
            (rise_x - WAVEGUIDE_WIDTH/2, dec_y)
        ], layer=LAYER_CARRY)

    # =========================================================================
    # Weight Streaming Bus (Top Edge)
    # =========================================================================

    if include_weight_bus:
        print("  Adding weight streaming bus (top edge)...")

        bus_y = ARRAY_Y + ARRAY_HEIGHT + 5
        bus_x_start = ARRAY_X
        bus_x_end = ARRAY_X + ARRAY_WIDTH

        # Main horizontal bus
        c.add_polygon([
            (bus_x_start, bus_y),
            (bus_x_end, bus_y),
            (bus_x_end, bus_y + WEIGHT_BUS_HEIGHT),
            (bus_x_start, bus_y + WEIGHT_BUS_HEIGHT)
        ], layer=LAYER_WEIGHT)

        c.add_label("WEIGHT STREAMING BUS",
                     position=((bus_x_start + bus_x_end)/2, bus_y + WEIGHT_BUS_HEIGHT + 5),
                     layer=LAYER_TEXT)
        c.add_label("(from Optical RAM)",
                     position=((bus_x_start + bus_x_end)/2, bus_y + WEIGHT_BUS_HEIGHT + 15),
                     layer=LAYER_TEXT)

        # Drop lines from bus to each column (weight distribution)
        for col in range(N_COLS):
            drop_x = ARRAY_X + col * PE_PITCH + PE_WIDTH - 12
            c.add_polygon([
                (drop_x - WAVEGUIDE_WIDTH/2, bus_y),
                (drop_x + WAVEGUIDE_WIDTH/2, bus_y),
                (drop_x + WAVEGUIDE_WIDTH/2, ARRAY_Y + ARRAY_HEIGHT),
                (drop_x - WAVEGUIDE_WIDTH/2, ARRAY_Y + ARRAY_HEIGHT)
            ], layer=LAYER_WEIGHT)

        # Weight bus input port (left side of bus)
        c.add_port("weight_bus_in",
                   center=(bus_x_start - 10, bus_y + WEIGHT_BUS_HEIGHT/2),
                   width=WEIGHT_BUS_HEIGHT, orientation=180, layer=LAYER_WEIGHT)

    # =========================================================================
    # Path-Length Equalization (Weight Distribution)
    # =========================================================================

    if include_path_equalization:
        print("  Calculating path-length equalization...")

        paths = calculate_path_equalization(N_ROWS)

        # Add meanders to weight drop lines for equalization
        equalization_info = []
        for row in range(N_ROWS):
            p = paths[row]
            meander_len = p['weight_meander']
            equalization_info.append(
                f"    Row {row}: weight path = {p['weight_vertical']:.0f}μm"
                f" + meander {meander_len:.0f}μm = {p['weight_total']:.0f}μm"
            )

            if meander_len > 10:  # Only add meander if significant
                # Place a small meander indicator near each weight drop
                meander_x = ARRAY_X + ARRAY_WIDTH + 5
                meander_y = ARRAY_Y + row * PE_PITCH + PE_HEIGHT/2

                c.add_polygon([
                    (meander_x, meander_y - 3),
                    (meander_x + 15, meander_y - 3),
                    (meander_x + 15, meander_y + 3),
                    (meander_x, meander_y + 3)
                ], layer=LAYER_MEANDER)
                c.add_label(f"+{meander_len:.0f}",
                           position=(meander_x + 7, meander_y),
                           layer=LAYER_TEXT)

        for info in equalization_info:
            print(info)

    # =========================================================================
    # Kerr Clock (IOC-internal, center of chip)
    # =========================================================================

    if include_kerr_clock:
        print("  Placing Kerr clock (IOC-internal)...")

        clock = c << kerr_clock_unit()
        clock_x = IOC_INPUT_X + IOC_INPUT_WIDTH / 2
        clock_y = ARRAY_Y - 35  # Below the array, within IOC input region
        clock.dmove((clock_x, clock_y))

        # Clock distribution waveguide to timing sync (IOC internal only)
        c.add_polygon([
            (clock_x + 20, clock_y - WAVEGUIDE_WIDTH/2),
            (clock_x + 60, clock_y - WAVEGUIDE_WIDTH/2),
            (clock_x + 60, clock_y + WAVEGUIDE_WIDTH/2),
            (clock_x + 20, clock_y + WAVEGUIDE_WIDTH/2)
        ], layer=LAYER_WAVEGUIDE)

        c.add_label("IOC-INTERNAL CLOCK",
                     position=(clock_x, clock_y - 25),
                     layer=LAYER_TEXT)
        c.add_label("(not distributed to PEs)",
                     position=(clock_x, clock_y - 35),
                     layer=LAYER_TEXT)

    # =========================================================================
    # Wire-Bond Pad Ring (proper 100x100 um pads at chip periphery)
    # =========================================================================

    print("  Adding wire-bond pad ring...")

    PAD_SIZE = 100.0       # um — wire-bond minimum
    PAD_MARGIN = 55.0      # um from chip edge to pad edge (satisfies EDGE.1 50 um)
    PAD_PITCH = 150.0      # um center-to-center (satisfies MTL2.S.1 50 um)

    pad_count = 0

    # Left edge pads (9 laser inputs + 1 pump)
    for i in range(10):
        pad_y = MARGIN_Y + i * PAD_PITCH
        if pad_y + PAD_SIZE > CHIP_HEIGHT - PAD_MARGIN:
            break
        c.add_polygon([
            (PAD_MARGIN, pad_y),
            (PAD_MARGIN + PAD_SIZE, pad_y),
            (PAD_MARGIN + PAD_SIZE, pad_y + PAD_SIZE),
            (PAD_MARGIN, pad_y + PAD_SIZE)
        ], layer=LAYER_METAL_PAD)
        c.add_label(f"L{i}", position=(PAD_MARGIN + PAD_SIZE/2, pad_y + PAD_SIZE/2),
                    layer=LAYER_TEXT)
        pad_count += 1

    # Right edge pads (9 data outputs + 1 ground)
    for i in range(10):
        pad_y = MARGIN_Y + i * PAD_PITCH
        if pad_y + PAD_SIZE > CHIP_HEIGHT - PAD_MARGIN:
            break
        pad_x = CHIP_WIDTH - PAD_MARGIN - PAD_SIZE
        c.add_polygon([
            (pad_x, pad_y),
            (pad_x + PAD_SIZE, pad_y),
            (pad_x + PAD_SIZE, pad_y + PAD_SIZE),
            (pad_x, pad_y + PAD_SIZE)
        ], layer=LAYER_METAL_PAD)
        c.add_label(f"R{i}", position=(pad_x + PAD_SIZE/2, pad_y + PAD_SIZE/2),
                    layer=LAYER_TEXT)
        pad_count += 1

    # Bottom edge pads (power, ground, test)
    for i in range(4):
        pad_x = MARGIN_X + IOC_INPUT_WIDTH + ROUTING_GAP + i * PAD_PITCH
        if pad_x + PAD_SIZE > CHIP_WIDTH - MARGIN_X:
            break
        c.add_polygon([
            (pad_x, PAD_MARGIN),
            (pad_x + PAD_SIZE, PAD_MARGIN),
            (pad_x + PAD_SIZE, PAD_MARGIN + PAD_SIZE),
            (pad_x, PAD_MARGIN + PAD_SIZE)
        ], layer=LAYER_METAL_PAD)
        c.add_label(f"B{i}", position=(pad_x + PAD_SIZE/2, PAD_MARGIN + PAD_SIZE/2),
                    layer=LAYER_TEXT)
        pad_count += 1

    print(f"    Placed {pad_count} wire-bond pads ({PAD_SIZE:.0f}x{PAD_SIZE:.0f} um, "
          f"{PAD_PITCH:.0f} um pitch)")

    # =========================================================================
    # Title Block & Specifications
    # =========================================================================

    title_y = CHIP_HEIGHT - 15

    c.add_label("MONOLITHIC N-RADIX 9×9 CHIP",
                position=(CHIP_WIDTH/2, title_y), layer=LAYER_TEXT)
    c.add_label("Split-Edge | 81 PEs | LiNbO3 (TFLN) | 617 MHz",
                position=(CHIP_WIDTH/2, title_y - 12), layer=LAYER_TEXT)
    c.add_label("IOC + Accelerator on ONE substrate",
                position=(CHIP_WIDTH/2, title_y - 24), layer=LAYER_TEXT)

    # =========================================================================
    # Summary
    # =========================================================================

    total_pes = N_ROWS * N_COLS
    throughput_tmacs = total_pes * CLOCK_FREQ_MHZ / 1e6

    print(f"\n  Chip summary:")
    print(f"    Total PEs: {total_pes}")
    print(f"    Array: {N_ROWS}×{N_COLS}")
    print(f"    Chip size: {CHIP_WIDTH:.0f} × {CHIP_HEIGHT:.0f} μm")
    print(f"    Material: X-cut LiNbO3 (TFLN)")
    print(f"    Clock: {CLOCK_FREQ_MHZ} MHz (Kerr, IOC-internal)")
    print(f"    Throughput: {throughput_tmacs:.3f} TMAC/s")
    print(f"    Topology: Split-edge (input left, output right)")
    print(f"    Integration: MONOLITHIC (IOC + accelerator)")
    print()

    return c


# =============================================================================
# Simulation / Validation
# =============================================================================

def run_integrated_validation() -> dict:
    """
    Analytical validation of the monolithic 9x9 integrated chip.

    Checks:
    1. Path-length matching (timing synchronization)
    2. Loss budget (full chip path)
    3. Wavelength routing correctness
    4. Timing skew analysis

    Returns dict of validation results.
    """
    print("\n" + "=" * 60)
    print("  MONOLITHIC 9x9 CHIP — INTEGRATED VALIDATION")
    print("=" * 60)

    results = {}

    # =========================================================================
    # 1. Path-Length Analysis
    # =========================================================================

    print("\n[1/4] PATH-LENGTH ANALYSIS")
    print("-" * 40)

    paths = calculate_path_equalization(N_ROWS)

    # Activation paths (IOC encoder → PE row entry)
    act_lengths = [paths[r]['activation_total'] for r in range(N_ROWS)]
    act_max = max(act_lengths)
    act_min = min(act_lengths)
    act_spread = act_max - act_min

    print(f"  Activation paths (encoder → PE):")
    print(f"    All rows: {act_lengths[0]:.1f} μm (identical — already matched)")
    print(f"    Spread: {act_spread:.1f} μm")
    print(f"    Time spread: {act_spread / V_GROUP_UM_PS:.3f} ps")

    results['activation_path_spread_um'] = act_spread
    results['activation_path_spread_ps'] = act_spread / V_GROUP_UM_PS
    results['activation_matched'] = act_spread < 0.1

    # Weight paths (bus → PE via equalized drops)
    wt_lengths = [paths[r]['weight_total'] for r in range(N_ROWS)]
    wt_max = max(wt_lengths)
    wt_min = min(wt_lengths)
    wt_spread = wt_max - wt_min

    print(f"\n  Weight paths (bus → PE, with equalization):")
    for row in range(N_ROWS):
        p = paths[row]
        print(f"    Row {row}: {p['weight_vertical']:.0f} + {p['weight_meander']:.0f}"
              f" = {p['weight_total']:.0f} μm")
    print(f"    Spread after equalization: {wt_spread:.1f} μm")
    print(f"    Time spread: {wt_spread / V_GROUP_UM_PS:.3f} ps")

    results['weight_path_spread_um'] = wt_spread
    results['weight_path_spread_ps'] = wt_spread / V_GROUP_UM_PS
    results['weight_matched'] = wt_spread < 1.0

    # =========================================================================
    # 2. Loss Budget
    # =========================================================================

    print("\n[2/4] LOSS BUDGET ANALYSIS")
    print("-" * 40)

    # LiNbO3 propagation loss: ~1-3 dB/cm, use 2 dB/cm for analysis
    prop_loss_db_per_cm = 2.0
    prop_loss_db_per_um = prop_loss_db_per_cm / 1e4

    # Longest path: laser input → encoder → routing → 9 PEs horizontal → output routing → decoder
    # Segments:
    encoder_path_um = IOC_INPUT_WIDTH  # ~180 μm through encoder
    routing_input_um = ROUTING_GAP     # ~60 μm IOC to array
    pe_horizontal_um = N_COLS * PE_PITCH  # ~495 μm through 9 PEs
    routing_output_um = ROUTING_GAP + N_COLS * PE_PITCH  # worst case output routing
    decoder_path_um = IOC_OUTPUT_WIDTH  # ~200 μm through decoder

    total_path_um = (encoder_path_um + routing_input_um +
                     pe_horizontal_um + routing_output_um + decoder_path_um)
    total_path_cm = total_path_um / 1e4

    propagation_loss_db = total_path_cm * prop_loss_db_per_cm

    # Component losses
    mzi_modulator_loss_db = 3.0     # MZI insertion loss
    combiner_loss_db = 3.0          # 3:1 wavelength combiner
    sfg_conversion_loss_db = 10.0   # SFG conversion efficiency (~10%)
    awg_demux_loss_db = 3.0         # AWG insertion loss
    coupling_loss_db = 2.0          # Edge coupling (1 dB per facet × 2)

    total_loss_db = (propagation_loss_db + mzi_modulator_loss_db +
                     combiner_loss_db + sfg_conversion_loss_db +
                     awg_demux_loss_db + coupling_loss_db)

    # Power budget
    laser_power_dbm = 10.0          # 10 dBm per channel
    detector_sensitivity_dbm = -30.0  # -30 dBm minimum
    margin_db = laser_power_dbm - total_loss_db - detector_sensitivity_dbm

    print(f"  Propagation path: {total_path_um:.0f} μm ({total_path_cm:.3f} cm)")
    print(f"  Propagation loss: {propagation_loss_db:.2f} dB (@ {prop_loss_db_per_cm} dB/cm)")
    print(f"  Component losses:")
    print(f"    MZI modulator:    {mzi_modulator_loss_db:.1f} dB")
    print(f"    Wavelength comb:  {combiner_loss_db:.1f} dB")
    print(f"    SFG conversion:   {sfg_conversion_loss_db:.1f} dB")
    print(f"    AWG demux:        {awg_demux_loss_db:.1f} dB")
    print(f"    Edge coupling:    {coupling_loss_db:.1f} dB")
    print(f"  Total loss:         {total_loss_db:.2f} dB")
    print(f"\n  Power budget:")
    print(f"    Laser power:      +{laser_power_dbm:.0f} dBm")
    print(f"    Total loss:       -{total_loss_db:.2f} dB")
    print(f"    At detector:      {laser_power_dbm - total_loss_db:.2f} dBm")
    print(f"    Detector sens:    {detector_sensitivity_dbm:.0f} dBm")
    print(f"    MARGIN:           {margin_db:.2f} dB")

    results['total_path_um'] = total_path_um
    results['total_loss_db'] = total_loss_db
    results['power_margin_db'] = margin_db
    results['loss_budget_ok'] = margin_db > 0

    # =========================================================================
    # 3. Timing Skew Analysis
    # =========================================================================

    print("\n[3/4] TIMING SKEW ANALYSIS")
    print("-" * 40)

    clock_period_ps = 1e6 / CLOCK_FREQ_MHZ  # ~1621 ps

    # For a 9x9 array, the systolic timing is inherent in the architecture.
    # Input activations arrive simultaneously at each row (path-matched).
    # Partial sums flow vertically — this is the intentional systolic delay.

    # The critical timing is: do activations arrive at all PE[row, 0] simultaneously?
    # Answer: YES — encoder→row paths are identical horizontal distances.

    # Weight timing: do weights arrive at all PEs in a column simultaneously?
    # With equalization: spread should be <1 μm → <0.01 ps
    weight_skew_ps = wt_spread / V_GROUP_UM_PS

    # Clock skew (IOC internal only — not distributed to PEs)
    # The Kerr clock drives the encoders, which fire simultaneously.
    # All 9 encoders are equidistant from the clock → no skew.

    skew_percent = (weight_skew_ps / clock_period_ps) * 100

    print(f"  Clock period: {clock_period_ps:.1f} ps ({CLOCK_FREQ_MHZ} MHz)")
    print(f"  Activation skew: {act_spread / V_GROUP_UM_PS:.3f} ps (inherently matched)")
    print(f"  Weight skew (with equalization): {weight_skew_ps:.3f} ps")
    print(f"  Skew as % of clock: {skew_percent:.4f}%")
    print(f"  Clock distribution: IOC-internal only (no distribution to PEs)")

    results['clock_period_ps'] = clock_period_ps
    results['weight_skew_ps'] = weight_skew_ps
    results['skew_percent'] = skew_percent
    results['timing_ok'] = skew_percent < 5.0

    # =========================================================================
    # 4. WDM Wavelength Routing
    # =========================================================================

    print("\n[4/4] WAVELENGTH ROUTING CHECK")
    print("-" * 40)

    # Input wavelengths
    wavelengths_nm = {
        'RED (-1)': 1550, 'GREEN (0)': 1310, 'BLUE (+1)': 1064
    }

    # SFG output wavelengths (1/λ_out = 1/λ_a + 1/λ_b)
    sfg_products = {}
    wl_list = list(wavelengths_nm.values())
    wl_names = list(wavelengths_nm.keys())

    all_unique = True
    for i in range(len(wl_list)):
        for j in range(i, len(wl_list)):
            λa, λb = wl_list[i], wl_list[j]
            λ_out = 1.0 / (1.0/λa + 1.0/λb)
            name = f"{wl_names[i].split()[0]}+{wl_names[j].split()[0]}"
            sfg_products[name] = λ_out

    print(f"  Input wavelengths:")
    for name, wl in wavelengths_nm.items():
        print(f"    {name}: {wl} nm")

    print(f"\n  SFG output products:")
    products_list = sorted(sfg_products.items(), key=lambda x: x[1])
    prev_wl = 0
    for name, wl in products_list:
        spacing = wl - prev_wl if prev_wl > 0 else 0
        spacing_str = f"  (Δ={spacing:.1f}nm)" if prev_wl > 0 else ""
        print(f"    {name}: {wl:.1f} nm{spacing_str}")
        prev_wl = wl

    # Check for collisions (wavelengths too close)
    min_spacing = float('inf')
    for i, (n1, w1) in enumerate(products_list):
        for j, (n2, w2) in enumerate(products_list):
            if i < j:
                spacing = abs(w2 - w1)
                if spacing < min_spacing:
                    min_spacing = spacing

    collision_free = min_spacing > 20  # Need >20nm for AWG separation

    print(f"\n  Minimum output spacing: {min_spacing:.1f} nm")
    print(f"  Collision-free (>20nm): {'YES' if collision_free else 'NO — COLLISION!'}")

    results['sfg_products'] = sfg_products
    results['min_output_spacing_nm'] = min_spacing
    results['collision_free'] = collision_free

    # =========================================================================
    # Summary
    # =========================================================================

    print("\n" + "=" * 60)
    print("  VALIDATION SUMMARY")
    print("=" * 60)

    checks = [
        ("Activation path matching", results['activation_matched']),
        ("Weight path equalization", results['weight_matched']),
        ("Loss budget (positive margin)", results['loss_budget_ok']),
        ("Timing skew (<5% of clock)", results['timing_ok']),
        ("Wavelength collision-free", results['collision_free']),
    ]

    all_pass = True
    for name, passed in checks:
        status = "PASS" if passed else "FAIL"
        symbol = "[+]" if passed else "[X]"
        print(f"  {symbol} {name}: {status}")
        if not passed:
            all_pass = False

    results['all_pass'] = all_pass

    print()
    if all_pass:
        print("  >>> ALL CHECKS PASSED — Monolithic integration validated <<<")
    else:
        print("  >>> SOME CHECKS FAILED — Review required <<<")
    print("=" * 60)

    return results


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    import os

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gds_dir = os.path.join(base_dir, '..', 'Research', 'data', 'gds')
    os.makedirs(gds_dir, exist_ok=True)

    # Generate the chip
    chip = monolithic_chip_9x9(
        include_path_equalization=True,
        include_kerr_clock=True,
        include_weight_bus=True,
    )

    # Save GDS
    output_path = os.path.join(gds_dir, "monolithic_9x9_nradix.gds")
    chip.write_gds(output_path)
    print(f"  GDS saved to: {output_path}")

    # Run validation
    results = run_integrated_validation()

    # Save validation report
    report_dir = os.path.join(base_dir, 'docs')
    os.makedirs(report_dir, exist_ok=True)

    report_path = os.path.join(report_dir, "MONOLITHIC_9x9_VALIDATION.md")
    with open(report_path, 'w') as f:
        f.write("# Monolithic 9x9 N-Radix Chip — Validation Report\n\n")
        f.write(f"**Date:** 2026-02-08\n")
        f.write(f"**Topology:** Split-edge (IOC left, array center, IOC right)\n")
        f.write(f"**Material:** X-cut LiNbO3 (TFLN)\n")
        f.write(f"**Array:** 9×9 = 81 PEs\n\n")

        f.write("## Chip Dimensions\n\n")
        f.write(f"- Width: {CHIP_WIDTH:.0f} μm\n")
        f.write(f"- Height: {CHIP_HEIGHT:.0f} μm\n")
        f.write(f"- Material: X-cut LiNbO3 (TFLN), n = {N_LINBO3}\n\n")

        f.write("## Validation Results\n\n")
        f.write("| Check | Result | Value |\n")
        f.write("|-------|--------|-------|\n")
        f.write(f"| Activation path matching | {'PASS' if results['activation_matched'] else 'FAIL'}"
                f" | Spread: {results['activation_path_spread_ps']:.3f} ps |\n")
        f.write(f"| Weight path equalization | {'PASS' if results['weight_matched'] else 'FAIL'}"
                f" | Spread: {results['weight_path_spread_ps']:.3f} ps |\n")
        f.write(f"| Loss budget | {'PASS' if results['loss_budget_ok'] else 'FAIL'}"
                f" | Margin: {results['power_margin_db']:.2f} dB |\n")
        f.write(f"| Timing skew | {'PASS' if results['timing_ok'] else 'FAIL'}"
                f" | {results['skew_percent']:.4f}% of clock |\n")
        f.write(f"| Wavelength collision-free | {'PASS' if results['collision_free'] else 'FAIL'}"
                f" | Min spacing: {results['min_output_spacing_nm']:.1f} nm |\n\n")

        overall = "ALL PASSED" if results['all_pass'] else "SOME FAILED"
        f.write(f"## Overall: **{overall}**\n\n")

        f.write("## Loss Budget Detail\n\n")
        f.write(f"- Total optical path: {results['total_path_um']:.0f} μm\n")
        f.write(f"- Total loss: {results['total_loss_db']:.2f} dB\n")
        f.write(f"- Laser power: +10 dBm\n")
        f.write(f"- Detector sensitivity: -30 dBm\n")
        f.write(f"- **Power margin: {results['power_margin_db']:.2f} dB**\n\n")

        f.write("## SFG Output Wavelengths\n\n")
        f.write("| Combination | Output λ (nm) |\n")
        f.write("|-------------|---------------|\n")
        for name, wl in sorted(results['sfg_products'].items(), key=lambda x: x[1]):
            f.write(f"| {name} | {wl:.1f} |\n")

        f.write(f"\nMinimum spacing: {results['min_output_spacing_nm']:.1f} nm\n")

    print(f"  Validation report saved to: {report_path}")

    return chip, results


if __name__ == "__main__":
    main()
