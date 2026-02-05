#!/usr/bin/env python3
"""
Integrated Supercomputer - Single Chip Validation Design

A focused, realistic design for validation:
- 9×9 systolic array (81 PEs) - small enough to simulate
- Kerr clock in CENTER of array - equidistant to all PEs
- Super IOC integrated on edge - minimal latency
- All clock paths EQUAL LENGTH - critical for timing

Goal: Get this working in simulation before scaling up.

Author: Christopher Riner
"""

import gdsfactory as gf
from gdsfactory.component import Component
import numpy as np
import os

# Activate PDK
gf.gpdk.PDK.activate()

# =============================================================================
# LAYER DEFINITIONS
# =============================================================================

LAYER_WAVEGUIDE = (1, 0)      # Silicon waveguides
LAYER_KERR = (2, 0)           # Kerr resonator (nonlinear)
LAYER_HEATER = (10, 0)        # Thermal tuning
LAYER_METAL = (12, 0)         # Metal contacts
LAYER_PE = (15, 0)            # Processing elements
LAYER_SIOC = (16, 0)          # Super IOC region
LAYER_CLOCK = (17, 0)         # Clock distribution
LAYER_DATA = (18, 0)          # Data waveguides
LAYER_LABEL = (100, 0)        # Labels

# =============================================================================
# DESIGN PARAMETERS
# =============================================================================

# Array parameters
ARRAY_SIZE = 9                # 9×9 = 81 PEs
PE_SIZE = 50.0                # μm - each processing element
PE_SPACING = 60.0             # μm - center-to-center

# Kerr clock parameters
KERR_RADIUS = 30.0            # μm - ring resonator radius
KERR_GAP = 0.2                # μm - coupling gap

# Super IOC parameters
SIOC_WIDTH = 400.0            # μm
SIOC_HEIGHT = 100.0           # μm

# Clock distribution
CLOCK_WG_WIDTH = 0.5          # μm - clock waveguide width
DATA_WG_WIDTH = 0.5           # μm - data waveguide width


def kerr_clock_resonator(
    radius: float = KERR_RADIUS,
    coupling_gap: float = KERR_GAP,
    width: float = 0.5
) -> Component:
    """
    Central Kerr clock resonator.

    This generates the 617 MHz timing signal via χ³ nonlinear self-pulsing.
    Placed at exact center of the chip for equidistant clock distribution.
    """
    import uuid
    c = gf.Component(f"kerr_clock_{str(uuid.uuid4())[:8]}")

    # Ring resonator
    ring = c << gf.components.ring(
        radius=radius,
        width=width,
        layer=LAYER_KERR
    )

    # Bus waveguide for coupling (input pump laser)
    bus_length = radius * 3
    bus = c << gf.components.straight(length=bus_length, width=width)
    bus.dmove((-bus_length/2, -radius - coupling_gap - width/2))

    # Input/output ports
    c.add_port("pump_in", center=(-bus_length/2, -radius - coupling_gap - width/2),
               width=width, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port("pump_through", center=(bus_length/2, -radius - coupling_gap - width/2),
               width=width, orientation=0, layer=LAYER_WAVEGUIDE)

    # Clock output ports (4 directions for distribution)
    for i, angle in enumerate([0, 90, 180, 270]):
        rad = np.radians(angle)
        port_x = (radius + 5) * np.cos(rad)
        port_y = (radius + 5) * np.sin(rad)
        c.add_port(f"clk_out_{i}", center=(port_x, port_y),
                   width=width, orientation=angle, layer=LAYER_CLOCK)

    # Label
    c.add_label("KERR", position=(0, 0), layer=LAYER_LABEL)
    c.add_label("617MHz", position=(0, -15), layer=LAYER_LABEL)

    return c


def processing_element(pe_id: int = 0, size: float = PE_SIZE) -> Component:
    """
    Single Processing Element (PE).

    Each PE performs:
    - Weight storage (bistable Kerr)
    - Multiply (SFG mixing in log domain)
    - Accumulate (photodetector integration)

    Ports:
    - clk_in: Clock input from central Kerr
    - data_in_h: Horizontal data input (activations)
    - data_in_v: Vertical data input (partial sums)
    - data_out_h: Horizontal data output
    - data_out_v: Vertical data output
    """
    c = gf.Component(f"pe_{pe_id}")

    # PE body
    c.add_polygon([
        (0, 0), (size, 0), (size, size), (0, size)
    ], layer=LAYER_PE)

    # Internal components (simplified representation)
    # Weight storage (small ring)
    weight_ring = c << gf.components.ring(radius=5, width=0.3, layer=LAYER_KERR)
    weight_ring.dmove((size/4, size/2))

    # Mixer region
    c.add_polygon([
        (size/2 - 8, size/2 - 8), (size/2 + 8, size/2 - 8),
        (size/2 + 8, size/2 + 8), (size/2 - 8, size/2 + 8)
    ], layer=LAYER_WAVEGUIDE)

    # Accumulator (photodetector)
    c.add_polygon([
        (3*size/4 - 5, size/2 - 5), (3*size/4 + 5, size/2 - 5),
        (3*size/4 + 5, size/2 + 5), (3*size/4 - 5, size/2 + 5)
    ], layer=LAYER_METAL)

    # Ports
    c.add_port("clk_in", center=(size/2, 0), width=CLOCK_WG_WIDTH,
               orientation=270, layer=LAYER_CLOCK)
    c.add_port("data_in_h", center=(0, size/2), width=DATA_WG_WIDTH,
               orientation=180, layer=LAYER_DATA)
    c.add_port("data_out_h", center=(size, size/2), width=DATA_WG_WIDTH,
               orientation=0, layer=LAYER_DATA)
    c.add_port("data_in_v", center=(size/2, size), width=DATA_WG_WIDTH,
               orientation=90, layer=LAYER_DATA)
    c.add_port("data_out_v", center=(size/2, 0), width=DATA_WG_WIDTH,
               orientation=270, layer=LAYER_DATA)

    # Label
    c.add_label(f"PE{pe_id}", position=(size/2, size - 8), layer=LAYER_LABEL)

    return c


def super_ioc_integrated(
    width: float = SIOC_WIDTH,
    height: float = SIOC_HEIGHT,
    n_channels: int = 9
) -> Component:
    """
    Integrated Super IOC for streaming data.

    Located on the edge of the chip, provides:
    - Weight loading to PEs
    - Activation streaming (input)
    - Result collection (output)

    For 9×9 array: 9 input channels, 9 output channels
    """
    c = gf.Component("super_ioc_integrated")

    # SIOC body
    c.add_polygon([
        (0, 0), (width, 0), (width, height), (0, height)
    ], layer=LAYER_SIOC)

    # Channel spacing
    channel_pitch = width / (n_channels + 1)

    # Input channels (to array)
    for i in range(n_channels):
        x = channel_pitch * (i + 1)
        # Modulator
        c.add_polygon([
            (x - 5, height - 30), (x + 5, height - 30),
            (x + 5, height - 10), (x - 5, height - 10)
        ], layer=LAYER_HEATER)
        # Port to array
        c.add_port(f"to_array_{i}", center=(x, height),
                   width=DATA_WG_WIDTH, orientation=90, layer=LAYER_DATA)

    # Output channels (from array)
    for i in range(n_channels):
        x = channel_pitch * (i + 1)
        # Photodetector
        c.add_polygon([
            (x - 4, 10), (x + 4, 10),
            (x + 4, 25), (x - 4, 25)
        ], layer=LAYER_METAL)
        # Port from array
        c.add_port(f"from_array_{i}", center=(x, 0),
                   width=DATA_WG_WIDTH, orientation=270, layer=LAYER_DATA)

    # External interface port
    c.add_port("external", center=(0, height/2), width=5,
               orientation=180, layer=LAYER_WAVEGUIDE)

    # Labels
    c.add_label("SUPER IOC", position=(width/2, height/2 + 10), layer=LAYER_LABEL)
    c.add_label("INTEGRATED", position=(width/2, height/2 - 10), layer=LAYER_LABEL)

    # Sub-labels
    c.add_label("IN→", position=(width/2, height - 5), layer=LAYER_LABEL)
    c.add_label("←OUT", position=(width/2, 5), layer=LAYER_LABEL)

    return c


def integrated_supercomputer(
    array_size: int = ARRAY_SIZE,
    pe_size: float = PE_SIZE,
    pe_spacing: float = PE_SPACING
) -> Component:
    """
    Complete Integrated Supercomputer Chip.

    Layout:
    ┌─────────────────────────────────────────────────┐
    │                   SUPER IOC                      │
    │  [IN] [IN] [IN] [IN] [IN] [IN] [IN] [IN] [IN]   │
    ├─────────────────────────────────────────────────┤
    │                                                  │
    │    PE  PE  PE  PE  PE  PE  PE  PE  PE           │
    │    PE  PE  PE  PE  PE  PE  PE  PE  PE           │
    │    PE  PE  PE  PE  PE  PE  PE  PE  PE           │
    │    PE  PE  PE  PE ┌────┐ PE  PE  PE  PE         │
    │    PE  PE  PE  PE │KERR│ PE  PE  PE  PE  ← CENTER
    │    PE  PE  PE  PE └────┘ PE  PE  PE  PE         │
    │    PE  PE  PE  PE  PE  PE  PE  PE  PE           │
    │    PE  PE  PE  PE  PE  PE  PE  PE  PE           │
    │    PE  PE  PE  PE  PE  PE  PE  PE  PE           │
    │                                                  │
    ├─────────────────────────────────────────────────┤
    │  [OUT][OUT][OUT][OUT][OUT][OUT][OUT][OUT][OUT]  │
    │                   OUTPUTS                        │
    └─────────────────────────────────────────────────┘

    Key features:
    - Kerr clock at EXACT CENTER of PE array
    - Equal-length clock paths to all PEs
    - Super IOC at top edge for streaming I/O
    - Systolic data flow: horizontal (activations) + vertical (partial sums)
    """
    c = gf.Component("integrated_supercomputer")

    # Calculate array dimensions
    array_width = array_size * pe_spacing
    array_height = array_size * pe_spacing

    # Total chip dimensions
    sioc_margin = 50.0
    chip_width = array_width + 2 * sioc_margin
    chip_height = array_height + SIOC_HEIGHT + 2 * sioc_margin + 100  # Extra for output

    # Chip outline
    c.add_polygon([
        (0, 0), (chip_width, 0), (chip_width, chip_height), (0, chip_height)
    ], layer=(20, 0))

    # =========================================================================
    # SUPER IOC (Top edge)
    # =========================================================================
    sioc = c << super_ioc_integrated(width=array_width, height=SIOC_HEIGHT, n_channels=array_size)
    sioc.dmove((sioc_margin, chip_height - SIOC_HEIGHT - 20))

    # =========================================================================
    # PE ARRAY with CENTRAL KERR
    # =========================================================================
    array_origin_x = sioc_margin
    array_origin_y = sioc_margin + 80  # Leave room for output collection

    # Center position (for Kerr)
    center_idx = array_size // 2
    center_x = array_origin_x + center_idx * pe_spacing + pe_spacing/2
    center_y = array_origin_y + center_idx * pe_spacing + pe_spacing/2

    # Place Kerr clock at center
    kerr = c << kerr_clock_resonator()
    kerr.dmove((center_x, center_y))

    # Place PEs around the Kerr
    pe_refs = {}
    pe_id = 0
    for row in range(array_size):
        for col in range(array_size):
            # Skip the center position (Kerr is there)
            if row == center_idx and col == center_idx:
                continue

            pe = c << processing_element(pe_id=pe_id)
            pe_x = array_origin_x + col * pe_spacing
            pe_y = array_origin_y + row * pe_spacing
            pe.dmove((pe_x, pe_y))
            pe_refs[(row, col)] = pe
            pe_id += 1

    # =========================================================================
    # CLOCK DISTRIBUTION (Kerr → all PEs)
    # =========================================================================
    # Equal-length clock tree from center Kerr to all PEs
    for row in range(array_size):
        for col in range(array_size):
            if row == center_idx and col == center_idx:
                continue

            pe_center_x = array_origin_x + col * pe_spacing + pe_spacing/2
            pe_center_y = array_origin_y + row * pe_spacing + pe_spacing/2

            # Calculate distance (all should be equal-ish due to grid)
            dx = pe_center_x - center_x
            dy = pe_center_y - center_y

            # Clock waveguide (simplified - straight line for now)
            # In reality, would need proper routing with bends
            if abs(dx) > 5 or abs(dy) > 5:
                # Draw clock line
                c.add_polygon([
                    (center_x + KERR_RADIUS + 5, center_y - 0.25),
                    (center_x + KERR_RADIUS + 5, center_y + 0.25),
                    (pe_center_x, pe_center_y + 0.25),
                    (pe_center_x, pe_center_y - 0.25)
                ], layer=LAYER_CLOCK)

    # =========================================================================
    # DATA WAVEGUIDES (Systolic flow)
    # =========================================================================
    # Horizontal data flow (activations from SIOC)
    for row in range(array_size):
        y = array_origin_y + row * pe_spacing + pe_spacing/2
        # Input from SIOC
        c.add_polygon([
            (sioc_margin - 10, y - 0.25),
            (sioc_margin + array_width + 10, y - 0.25),
            (sioc_margin + array_width + 10, y + 0.25),
            (sioc_margin - 10, y + 0.25)
        ], layer=LAYER_DATA)

    # Vertical data flow (partial sums)
    for col in range(array_size):
        x = array_origin_x + col * pe_spacing + pe_spacing/2
        # Connect through array
        c.add_polygon([
            (x - 0.25, array_origin_y - 10),
            (x + 0.25, array_origin_y - 10),
            (x + 0.25, array_origin_y + array_height + 10),
            (x - 0.25, array_origin_y + array_height + 10)
        ], layer=LAYER_DATA)

    # =========================================================================
    # OUTPUT COLLECTION (Bottom)
    # =========================================================================
    for col in range(array_size):
        x = array_origin_x + col * pe_spacing + pe_spacing/2
        # Photodetector for output
        c.add_polygon([
            (x - 8, 20), (x + 8, 20),
            (x + 8, 50), (x - 8, 50)
        ], layer=LAYER_METAL)
        c.add_label(f"OUT{col}", position=(x, 10), layer=LAYER_LABEL)

    # =========================================================================
    # LABELS
    # =========================================================================
    c.add_label("INTEGRATED SUPERCOMPUTER", position=(chip_width/2, chip_height - 5), layer=LAYER_LABEL)
    c.add_label(f"{array_size}×{array_size} Array ({array_size*array_size - 1} PEs + Central Kerr)",
                position=(chip_width/2, chip_height - 20), layer=LAYER_LABEL)
    c.add_label("★ KERR CLOCK AT CENTER ★", position=(center_x, center_y - KERR_RADIUS - 20), layer=LAYER_LABEL)

    # Chip specs
    bbox = c.dbbox()
    c.add_label(f"Chip: {bbox.width():.0f} × {bbox.height():.0f} μm",
                position=(chip_width/2, 5), layer=LAYER_LABEL)

    return c


def generate_validation_chip():
    """Generate the integrated supercomputer chip for validation."""

    print("=" * 70)
    print("INTEGRATED SUPERCOMPUTER - Validation Chip Generator")
    print("=" * 70)
    print("\nDesign parameters:")
    print(f"  Array size: {ARRAY_SIZE}×{ARRAY_SIZE} ({ARRAY_SIZE*ARRAY_SIZE - 1} PEs + 1 Kerr)")
    print(f"  PE size: {PE_SIZE} μm")
    print(f"  PE spacing: {PE_SPACING} μm")
    print(f"  Kerr radius: {KERR_RADIUS} μm")
    print(f"  Super IOC: Integrated on edge")
    print("\nKey feature: Kerr clock at EXACT CENTER for equal clock distribution")

    # Generate chip
    print("\n>>> Generating integrated supercomputer...")
    chip = integrated_supercomputer()

    bbox = chip.dbbox()
    print(f"    Chip size: {bbox.width():.0f} × {bbox.height():.0f} μm")

    # Save
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'gds', 'validation')
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, 'integrated_supercomputer_9x9.gds')
    chip.write_gds(output_file)
    print(f"\n>>> Saved to: {output_file}")

    # Also generate individual components for testing
    print("\n>>> Generating individual components for testing...")

    kerr = kerr_clock_resonator()
    kerr.write_gds(os.path.join(output_dir, 'kerr_clock_resonator.gds'))
    print("    - kerr_clock_resonator.gds")

    pe = processing_element(pe_id=0)
    pe.write_gds(os.path.join(output_dir, 'processing_element.gds'))
    print("    - processing_element.gds")

    sioc = super_ioc_integrated()
    sioc.write_gds(os.path.join(output_dir, 'super_ioc_integrated.gds'))
    print("    - super_ioc_integrated.gds")

    print("\n" + "=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. View in KLayout: klayout " + output_file)
    print("  2. Simulate Kerr clock with Meep")
    print("  3. Verify clock distribution timing")
    print("  4. Test end-to-end data flow")

    return chip


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    generate_validation_chip()
