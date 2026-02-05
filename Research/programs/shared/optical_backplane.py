#!/usr/bin/env python3
"""
Optical Backplane Module for Ternary Optical Computer

High-bandwidth optical interconnect fabric connecting all system components:
- OPU slots (Optical Processing Units)
- IOC modules (Input/Output Converters)
- IOA adapters (External I/O Adapters)
- Storage interfaces (NVMe, DDR5, HBM)
- RAM tiers (Hot/Working/Parking registers)

Architecture:
- Wavelength-division multiplexed (WDM) optical bus
- Non-blocking crossbar switch fabric
- Broadcast capability for shared memory access
- Point-to-point channels for low-latency compute

Specifications:
- Slot count: 4 OPU + 2 IOC + 4 IOA + 1 Storage (configurable)
- Channel bandwidth: 100 Gbps per wavelength
- Total fabric bandwidth: 12.8 Tbps (128 wavelengths x 100 Gbps)
- Switching latency: <10 ns (all-optical)
- Power: ~5W total (dominated by EDFAs)

Author: Wavelength-Division Ternary Optical Computer Project
"""

import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.typings import LayerSpec
import numpy as np
from typing import Optional, Literal, List

# Activate PDK
gf.gpdk.PDK.activate()

# Default cross-section
XS = gf.cross_section.strip(width=0.5)

# Unique ID counter for component names
import uuid
def _uid() -> str:
    return str(uuid.uuid4())[:8]

# =============================================================================
# Layer Definitions
# =============================================================================

LAYER_WAVEGUIDE: LayerSpec = (1, 0)
LAYER_HEATER: LayerSpec = (10, 0)
LAYER_METAL_PAD: LayerSpec = (12, 0)
LAYER_GAIN: LayerSpec = (14, 0)
LAYER_AWG: LayerSpec = (15, 0)
LAYER_SWITCH: LayerSpec = (19, 0)
LAYER_BUS: LayerSpec = (20, 0)
LAYER_TEXT: LayerSpec = (100, 0)

# =============================================================================
# Backplane Constants
# =============================================================================

SLOT_PITCH = 500.0          # um between slots
BUS_WIDTH = 200.0           # um width of optical bus region
SWITCH_SIZE = 100.0         # um crossbar switch element
EDFA_LENGTH = 150.0         # um amplifier length


def backplane_slot(
    slot_type: Literal['opu', 'ioc', 'ioa', 'storage', 'ram'] = 'opu',
    slot_id: int = 0,
    n_channels: int = 8
) -> Component:
    """
    Single backplane slot connector.

    Args:
        slot_type: Type of slot (opu, ioc, ioa, storage, ram)
        slot_id: Slot identifier number
        n_channels: Number of optical channels

    Returns:
        Component with slot interface
    """
    c = gf.Component(f"backplane_slot_{slot_type}_{slot_id}_{_uid()}")

    # Slot dimensions based on type
    slot_dims = {
        'opu': (400, 300),
        'ioc': (300, 200),
        'ioa': (250, 180),
        'storage': (350, 250),
        'ram': (200, 150)
    }
    width, height = slot_dims.get(slot_type, (300, 200))

    # Slot outline
    outline = c.add_polygon(
        [(0, 0), (width, 0), (width, height), (0, height)],
        layer=LAYER_BUS
    )

    # Channel ports on bottom edge
    channel_pitch = width / (n_channels + 1)
    for i in range(n_channels):
        x = channel_pitch * (i + 1)
        # Input port
        c.add_port(
            name=f"ch{i}_in",
            center=(x, 0),
            width=0.5,
            orientation=270,
            layer=LAYER_WAVEGUIDE
        )
        # Output port (top)
        c.add_port(
            name=f"ch{i}_out",
            center=(x, height),
            width=0.5,
            orientation=90,
            layer=LAYER_WAVEGUIDE
        )
        # Vertical waveguide through slot
        wg = c.add_polygon(
            [(x - 0.25, 0), (x + 0.25, 0), (x + 0.25, height), (x - 0.25, height)],
            layer=LAYER_WAVEGUIDE
        )

    # Slot type label
    type_labels = {
        'opu': f"OPU-{slot_id}",
        'ioc': f"IOC-{slot_id}",
        'ioa': f"IOA-{slot_id}",
        'storage': f"STOR-{slot_id}",
        'ram': f"RAM-{slot_id}"
    }
    c.add_label(type_labels[slot_type], position=(width/2, height/2), layer=LAYER_TEXT)

    # Control/power pads
    pad_size = 30
    for i, pad_name in enumerate(['PWR', 'GND', 'CLK', 'RST']):
        pad_x = width - 40 - i * 35
        c.add_polygon(
            [(pad_x, height - 40), (pad_x + pad_size, height - 40),
             (pad_x + pad_size, height - 10), (pad_x, height - 10)],
            layer=LAYER_METAL_PAD
        )
        c.add_label(pad_name, position=(pad_x + pad_size/2, height - 25), layer=LAYER_TEXT)

    return c


def crossbar_switch(n_inputs: int = 4, n_outputs: int = 4) -> Component:
    """
    Non-blocking optical crossbar switch.

    Uses MZI-based 2x2 switches in Benes network topology.

    Args:
        n_inputs: Number of input ports
        n_outputs: Number of output ports

    Returns:
        Component with crossbar switch
    """
    c = gf.Component(f"crossbar_switch_{n_inputs}x{n_outputs}_{_uid()}")

    size = max(n_inputs, n_outputs) * SWITCH_SIZE

    # Switch fabric region
    c.add_polygon(
        [(0, 0), (size, 0), (size, size), (0, size)],
        layer=LAYER_SWITCH
    )

    # Input ports (left side)
    input_pitch = size / (n_inputs + 1)
    for i in range(n_inputs):
        y = input_pitch * (i + 1)
        c.add_port(
            name=f"in_{i}",
            center=(0, y),
            width=0.5,
            orientation=180,
            layer=LAYER_WAVEGUIDE
        )
        # Horizontal waveguide stub
        c.add_polygon(
            [(-10, y - 0.25), (20, y - 0.25), (20, y + 0.25), (-10, y + 0.25)],
            layer=LAYER_WAVEGUIDE
        )

    # Output ports (right side)
    output_pitch = size / (n_outputs + 1)
    for i in range(n_outputs):
        y = output_pitch * (i + 1)
        c.add_port(
            name=f"out_{i}",
            center=(size, y),
            width=0.5,
            orientation=0,
            layer=LAYER_WAVEGUIDE
        )
        c.add_polygon(
            [(size - 20, y - 0.25), (size + 10, y - 0.25),
             (size + 10, y + 0.25), (size - 20, y + 0.25)],
            layer=LAYER_WAVEGUIDE
        )

    # Internal switch elements (simplified representation)
    elem_size = 15
    for i in range(n_inputs):
        for j in range(n_outputs):
            ex = 30 + j * (size - 60) / max(1, n_outputs - 1)
            ey = input_pitch * (i + 1)
            c.add_polygon(
                [(ex, ey - elem_size/2), (ex + elem_size, ey - elem_size/2),
                 (ex + elem_size, ey + elem_size/2), (ex, ey + elem_size/2)],
                layer=LAYER_HEATER
            )

    c.add_label(f"XBAR {n_inputs}x{n_outputs}", position=(size/2, size + 15), layer=LAYER_TEXT)

    return c


def optical_bus(
    length: float = 2000.0,
    n_channels: int = 8,
    n_taps: int = 4
) -> Component:
    """
    Wavelength-division multiplexed optical bus.

    Args:
        length: Bus length in um
        n_channels: Number of WDM channels
        n_taps: Number of tap points along bus

    Returns:
        Component with optical bus
    """
    c = gf.Component(f"optical_bus_{n_channels}ch_{_uid()}")

    # Bus region
    c.add_polygon(
        [(0, 0), (length, 0), (length, BUS_WIDTH), (0, BUS_WIDTH)],
        layer=LAYER_BUS
    )

    # Individual channel waveguides
    channel_pitch = BUS_WIDTH / (n_channels + 1)
    for i in range(n_channels):
        y = channel_pitch * (i + 1)
        c.add_polygon(
            [(0, y - 0.25), (length, y - 0.25), (length, y + 0.25), (0, y + 0.25)],
            layer=LAYER_WAVEGUIDE
        )
        # End ports
        c.add_port(f"ch{i}_in", center=(0, y), width=0.5, orientation=180, layer=LAYER_WAVEGUIDE)
        c.add_port(f"ch{i}_out", center=(length, y), width=0.5, orientation=0, layer=LAYER_WAVEGUIDE)

    # Tap points with directional couplers
    tap_spacing = length / (n_taps + 1)
    for t in range(n_taps):
        tap_x = tap_spacing * (t + 1)
        # Tap coupler region
        c.add_polygon(
            [(tap_x - 20, -30), (tap_x + 20, -30), (tap_x + 20, BUS_WIDTH + 30), (tap_x - 20, BUS_WIDTH + 30)],
            layer=LAYER_AWG
        )
        # Tap ports
        c.add_port(f"tap{t}_drop", center=(tap_x, -30), width=0.5, orientation=270, layer=LAYER_WAVEGUIDE)
        c.add_port(f"tap{t}_add", center=(tap_x, BUS_WIDTH + 30), width=0.5, orientation=90, layer=LAYER_WAVEGUIDE)
        c.add_label(f"TAP-{t}", position=(tap_x, -45), layer=LAYER_TEXT)

    # EDFA amplifiers along bus
    edfa_spacing = length / 3
    for e in range(2):
        ex = edfa_spacing * (e + 1)
        c.add_polygon(
            [(ex - EDFA_LENGTH/2, BUS_WIDTH + 5), (ex + EDFA_LENGTH/2, BUS_WIDTH + 5),
             (ex + EDFA_LENGTH/2, BUS_WIDTH + 25), (ex - EDFA_LENGTH/2, BUS_WIDTH + 25)],
            layer=LAYER_GAIN
        )
        c.add_label("EDFA", position=(ex, BUS_WIDTH + 15), layer=LAYER_TEXT)

    c.add_label(f"OPTICAL BUS - {n_channels} CH WDM", position=(length/2, BUS_WIDTH/2), layer=LAYER_TEXT)

    return c


def backplane_edfa(gain_db: float = 20.0) -> Component:
    """
    Erbium-doped fiber amplifier for signal regeneration.

    Args:
        gain_db: Target gain in dB

    Returns:
        Component with EDFA
    """
    c = gf.Component(f"backplane_edfa_{int(gain_db)}dB_{_uid()}")

    # EDFA body
    c.add_polygon(
        [(0, 0), (EDFA_LENGTH, 0), (EDFA_LENGTH, 40), (0, 40)],
        layer=LAYER_GAIN
    )

    # Input/output waveguides
    c.add_polygon([(-20, 18), (0, 18), (0, 22), (-20, 22)], layer=LAYER_WAVEGUIDE)
    c.add_polygon([(EDFA_LENGTH, 18), (EDFA_LENGTH + 20, 18),
                   (EDFA_LENGTH + 20, 22), (EDFA_LENGTH, 22)], layer=LAYER_WAVEGUIDE)

    # Ports
    c.add_port("in", center=(-20, 20), width=0.5, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port("out", center=(EDFA_LENGTH + 20, 20), width=0.5, orientation=0, layer=LAYER_WAVEGUIDE)

    # Pump laser pad
    c.add_polygon([(EDFA_LENGTH/2 - 15, 40), (EDFA_LENGTH/2 + 15, 40),
                   (EDFA_LENGTH/2 + 15, 55), (EDFA_LENGTH/2 - 15, 55)], layer=LAYER_METAL_PAD)
    c.add_label("PUMP", position=(EDFA_LENGTH/2, 47), layer=LAYER_TEXT)

    c.add_label(f"EDFA +{int(gain_db)}dB", position=(EDFA_LENGTH/2, 20), layer=LAYER_TEXT)

    return c


def optical_backplane(
    n_opu_slots: int = 4,
    n_ioc_slots: int = 2,
    n_ioa_slots: int = 4,
    include_storage: bool = True,
    include_ram_bus: bool = True
) -> Component:
    """
    Complete optical backplane assembly.

    Args:
        n_opu_slots: Number of OPU slots
        n_ioc_slots: Number of IOC slots
        n_ioa_slots: Number of IOA slots
        include_storage: Include storage controller slot
        include_ram_bus: Include RAM tier bus

    Returns:
        Complete backplane component
    """
    c = gf.Component("optical_backplane")

    # Calculate total width
    total_slots = n_opu_slots + n_ioc_slots + n_ioa_slots + (1 if include_storage else 0)
    backplane_width = (total_slots + 1) * SLOT_PITCH
    backplane_height = 1200.0

    # Main backplane outline
    c.add_polygon(
        [(0, 0), (backplane_width, 0), (backplane_width, backplane_height), (0, backplane_height)],
        layer=LAYER_BUS
    )

    # Title
    c.add_label("TERNARY OPTICAL COMPUTER - BACKPLANE",
                position=(backplane_width/2, backplane_height - 30), layer=LAYER_TEXT)
    c.add_label(f"{n_opu_slots} OPU | {n_ioc_slots} IOC | {n_ioa_slots} IOA | Storage: {include_storage}",
                position=(backplane_width/2, backplane_height - 60), layer=LAYER_TEXT)

    current_x = SLOT_PITCH / 2

    # Add OPU slots
    for i in range(n_opu_slots):
        slot = c << backplane_slot('opu', i, n_channels=8)
        slot.dmove((current_x, 100))
        current_x += SLOT_PITCH

    # Add IOC slots
    for i in range(n_ioc_slots):
        slot = c << backplane_slot('ioc', i, n_channels=8)
        slot.dmove((current_x, 100))
        current_x += SLOT_PITCH

    # Add IOA slots
    for i in range(n_ioa_slots):
        slot = c << backplane_slot('ioa', i, n_channels=4)
        slot.dmove((current_x, 100))
        current_x += SLOT_PITCH

    # Add storage slot
    if include_storage:
        slot = c << backplane_slot('storage', 0, n_channels=8)
        slot.dmove((current_x, 100))
        current_x += SLOT_PITCH

    # Main interconnect bus (middle of backplane)
    bus = c << optical_bus(length=backplane_width - 100, n_channels=8, n_taps=total_slots)
    bus.dmove((50, 500))

    # Crossbar switch fabric
    xbar = c << crossbar_switch(n_inputs=total_slots, n_outputs=total_slots)
    xbar.dmove((backplane_width/2 - 200, 750))

    # RAM tier bus (if included)
    if include_ram_bus:
        ram_bus = c << optical_bus(length=backplane_width - 200, n_channels=4, n_taps=3)
        ram_bus.dmove((100, 950))
        c.add_label("RAM TIER BUS (T1/T2/T3)", position=(backplane_width/2, 1050), layer=LAYER_TEXT)

        # RAM tier slots
        for i, tier in enumerate(['T1-HOT', 'T2-WORK', 'T3-PARK']):
            ram_slot = c << backplane_slot('ram', i, n_channels=4)
            ram_slot.dmove((200 + i * 400, 1080))

    # Power distribution rail
    c.add_polygon(
        [(20, 30), (backplane_width - 20, 30), (backplane_width - 20, 50), (20, 50)],
        layer=LAYER_METAL_PAD
    )
    c.add_label("POWER RAIL (+3.3V / +1.8V / GND)", position=(backplane_width/2, 40), layer=LAYER_TEXT)

    # Clock distribution
    c.add_polygon(
        [(20, 55), (backplane_width - 20, 55), (backplane_width - 20, 65), (20, 65)],
        layer=LAYER_HEATER
    )
    c.add_label("CLOCK DIST (617 MHz)", position=(backplane_width/2, 60), layer=LAYER_TEXT)

    # External ports
    c.add_port("power_in", center=(0, 40), width=30, orientation=180, layer=LAYER_METAL_PAD)
    c.add_port("clock_in", center=(0, 60), width=10, orientation=180, layer=LAYER_HEATER)
    c.add_port("optical_in", center=(50, 500 + BUS_WIDTH/2), width=0.5, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port("optical_out", center=(backplane_width - 50, 500 + BUS_WIDTH/2), width=0.5, orientation=0, layer=LAYER_WAVEGUIDE)

    return c


def mini_backplane(n_slots: int = 4) -> Component:
    """
    Compact backplane for smaller systems.

    Args:
        n_slots: Total number of generic slots

    Returns:
        Mini backplane component
    """
    c = gf.Component(f"mini_backplane_{n_slots}slot_{_uid()}")

    width = (n_slots + 1) * 300
    height = 600

    # Outline
    c.add_polygon([(0, 0), (width, 0), (width, height), (0, height)], layer=LAYER_BUS)

    # Slots
    for i in range(n_slots):
        slot = c << backplane_slot('opu', i, n_channels=4)
        slot.dmove((150 + i * 300, 50))

    # Simple bus
    bus = c << optical_bus(length=width - 100, n_channels=4, n_taps=n_slots)
    bus.dmove((50, 300))

    c.add_label(f"MINI BACKPLANE - {n_slots} SLOTS", position=(width/2, height - 20), layer=LAYER_TEXT)

    return c


def kerr_clock_hub(radius: float = 150.0) -> Component:
    """
    Central Kerr resonator clock hub with radial distribution.

    The Kerr clock generates the 617 MHz timing signal that synchronizes
    all modules. Placing it centrally minimizes clock skew.

    Args:
        radius: Hub radius in um

    Returns:
        Component with central clock and distribution network
    """
    c = gf.Component(f"kerr_clock_hub_{_uid()}")

    # Central Kerr resonator (ring)
    kerr_radius = 30.0
    n_points = 64
    angles = np.linspace(0, 2*np.pi, n_points)

    # Outer ring
    outer_points = [(radius/5 + 5 + kerr_radius * np.cos(a),
                     radius/5 + kerr_radius * np.sin(a)) for a in angles]
    c.add_polygon(outer_points, layer=LAYER_WAVEGUIDE)

    # Inner ring (hollow)
    inner_points = [(radius/5 + 5 + (kerr_radius - 2) * np.cos(a),
                     radius/5 + (kerr_radius - 2) * np.sin(a)) for a in angles]

    # Hub body (circular region)
    hub_points = [(radius * np.cos(a), radius * np.sin(a)) for a in angles]
    c.add_polygon(hub_points, layer=LAYER_BUS)

    # Clock distribution ring
    dist_radius = radius * 0.7
    dist_points = [(dist_radius * np.cos(a), dist_radius * np.sin(a)) for a in angles]
    c.add_polygon(dist_points, layer=LAYER_HEATER)

    # Radial distribution lines (8 directions)
    n_lines = 8
    for i in range(n_lines):
        angle = i * 2 * np.pi / n_lines
        x1 = dist_radius * np.cos(angle)
        y1 = dist_radius * np.sin(angle)
        x2 = (radius - 10) * np.cos(angle)
        y2 = (radius - 10) * np.sin(angle)

        # Clock distribution waveguide
        dx = 2 * np.cos(angle + np.pi/2)
        dy = 2 * np.sin(angle + np.pi/2)
        c.add_polygon([
            (x1 - dx, y1 - dy), (x2 - dx, y2 - dy),
            (x2 + dx, y2 + dy), (x1 + dx, y1 + dy)
        ], layer=LAYER_WAVEGUIDE)

        # Output port at edge
        c.add_port(
            f"clk_out_{i}",
            center=(x2, y2),
            width=0.5,
            orientation=np.degrees(angle),
            layer=LAYER_WAVEGUIDE
        )

    # EDFA in center for clock amplification
    c.add_polygon([(-20, -10), (20, -10), (20, 10), (-20, 10)], layer=LAYER_GAIN)

    # Labels
    c.add_label("KERR", position=(radius/5 + 5, radius/5), layer=LAYER_TEXT)
    c.add_label("617 MHz", position=(0, -radius * 0.4), layer=LAYER_TEXT)
    c.add_label("CLOCK HUB", position=(0, radius * 0.85), layer=LAYER_TEXT)

    # Laser input port
    c.add_port("laser_in", center=(-radius, 0), width=0.5, orientation=180, layer=LAYER_WAVEGUIDE)

    return c


def backplane_central_clock(
    n_opu_slots: int = 4,
    n_ioc_slots: int = 2,
    n_ioa_slots: int = 2,
    include_storage: bool = True
) -> Component:
    """
    Backplane with central Kerr clock and radial module arrangement.

    Architecture:
    - Central Kerr resonator provides 617 MHz clock
    - Modules arranged in ring around clock for minimal skew
    - Clock distribution lines radiate from center
    - EDFA amplifiers at each radial arm

    Args:
        n_opu_slots: Number of OPU slots
        n_ioc_slots: Number of IOC slots
        n_ioa_slots: Number of IOA slots
        include_storage: Include storage controller slot

    Returns:
        Component with central clock backplane
    """
    c = gf.Component(f"backplane_central_clock_{_uid()}")

    total_slots = n_opu_slots + n_ioc_slots + n_ioa_slots + (1 if include_storage else 0)

    # Size based on number of slots (circular arrangement)
    hub_radius = 200.0
    slot_ring_radius = 600.0
    backplane_size = slot_ring_radius * 2 + 600

    # Background
    c.add_polygon([
        (0, 0), (backplane_size, 0),
        (backplane_size, backplane_size), (0, backplane_size)
    ], layer=LAYER_BUS)

    center_x = backplane_size / 2
    center_y = backplane_size / 2

    # Central clock hub
    clock = c << kerr_clock_hub(radius=hub_radius)
    clock.dmove((center_x, center_y))

    # Place slots in a ring around the clock
    slot_types = []
    slot_types.extend([('opu', i) for i in range(n_opu_slots)])
    slot_types.extend([('ioc', i) for i in range(n_ioc_slots)])
    slot_types.extend([('ioa', i) for i in range(n_ioa_slots)])
    if include_storage:
        slot_types.append(('storage', 0))

    # Distribute slots evenly around the ring
    for idx, (slot_type, slot_id) in enumerate(slot_types):
        angle = idx * 2 * np.pi / len(slot_types) - np.pi/2  # Start from top

        slot_x = center_x + slot_ring_radius * np.cos(angle)
        slot_y = center_y + slot_ring_radius * np.sin(angle)

        slot = c << backplane_slot(slot_type, slot_id, n_channels=4)
        slot.dmove((slot_x - 150, slot_y - 100))  # Center the slot

        # Clock distribution line from hub to slot
        hub_edge_x = center_x + (hub_radius - 10) * np.cos(angle)
        hub_edge_y = center_y + (hub_radius - 10) * np.sin(angle)

        # Waveguide to slot
        c.add_polygon([
            (hub_edge_x - 2, hub_edge_y - 2),
            (slot_x - 50 * np.cos(angle), slot_y - 50 * np.sin(angle)),
            (slot_x - 50 * np.cos(angle) + 4, slot_y - 50 * np.sin(angle) + 4),
            (hub_edge_x + 2, hub_edge_y + 2)
        ], layer=LAYER_WAVEGUIDE)

        # EDFA midpoint on each arm
        edfa_x = center_x + (slot_ring_radius * 0.5) * np.cos(angle)
        edfa_y = center_y + (slot_ring_radius * 0.5) * np.sin(angle)
        c.add_polygon([
            (edfa_x - 15, edfa_y - 8),
            (edfa_x + 15, edfa_y - 8),
            (edfa_x + 15, edfa_y + 8),
            (edfa_x - 15, edfa_y + 8)
        ], layer=LAYER_GAIN)
        c.add_label("EDFA", position=(edfa_x, edfa_y), layer=LAYER_TEXT)

    # Interconnect ring (data bus between slots)
    n_ring_points = 64
    ring_angles = np.linspace(0, 2*np.pi, n_ring_points)
    data_ring_radius = slot_ring_radius - 150

    # Data bus ring
    for i in range(n_ring_points - 1):
        a1, a2 = ring_angles[i], ring_angles[i+1]
        c.add_polygon([
            (center_x + (data_ring_radius - 5) * np.cos(a1), center_y + (data_ring_radius - 5) * np.sin(a1)),
            (center_x + (data_ring_radius + 5) * np.cos(a1), center_y + (data_ring_radius + 5) * np.sin(a1)),
            (center_x + (data_ring_radius + 5) * np.cos(a2), center_y + (data_ring_radius + 5) * np.sin(a2)),
            (center_x + (data_ring_radius - 5) * np.cos(a2), center_y + (data_ring_radius - 5) * np.sin(a2)),
        ], layer=LAYER_WAVEGUIDE)

    # Power/ground ring (outer)
    power_ring_radius = slot_ring_radius + 200
    for i in range(n_ring_points - 1):
        a1, a2 = ring_angles[i], ring_angles[i+1]
        c.add_polygon([
            (center_x + (power_ring_radius - 10) * np.cos(a1), center_y + (power_ring_radius - 10) * np.sin(a1)),
            (center_x + (power_ring_radius + 10) * np.cos(a1), center_y + (power_ring_radius + 10) * np.sin(a1)),
            (center_x + (power_ring_radius + 10) * np.cos(a2), center_y + (power_ring_radius + 10) * np.sin(a2)),
            (center_x + (power_ring_radius - 10) * np.cos(a2), center_y + (power_ring_radius - 10) * np.sin(a2)),
        ], layer=LAYER_METAL_PAD)

    # Labels
    c.add_label("TERNARY OPTICAL COMPUTER - CENTRAL CLOCK BACKPLANE",
                position=(center_x, backplane_size - 40), layer=LAYER_TEXT)
    c.add_label(f"{n_opu_slots} OPU | {n_ioc_slots} IOC | {n_ioa_slots} IOA | Storage: {include_storage}",
                position=(center_x, backplane_size - 80), layer=LAYER_TEXT)
    c.add_label("DATA BUS RING", position=(center_x + data_ring_radius + 50, center_y), layer=LAYER_TEXT)
    c.add_label("POWER RING", position=(center_x + power_ring_radius + 50, center_y - 30), layer=LAYER_TEXT)

    # External ports
    c.add_port("laser_in", center=(0, center_y), width=0.5, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port("power_in", center=(center_x, 0), width=20, orientation=270, layer=LAYER_METAL_PAD)

    return c


# =============================================================================
# ROUND TABLE ARCHITECTURE
# =============================================================================
#
# ████████████████████████████████████████████████████████████████████████████
# █                                                                          █
# █   CRITICAL DESIGN PRINCIPLE: MINIMIZE DISTANCE FROM KERR CLOCK           █
# █                                                                          █
# █   The Kerr resonator generates the 617 MHz master clock. ALL components  █
# █   must receive this clock with minimal skew. Clock skew causes:          █
# █     - Synchronization errors in systolic array                           █
# █     - Data corruption in streaming pipelines                             █
# █     - Timing violations at domain boundaries                             █
# █                                                                          █
# █   Therefore: Kerr MUST be at exact center, all components equidistant.   █
# █                                                                          █
# ████████████████████████████████████████████████████████████████████████████
#
# Architecture (Bird's Eye View - Concentric Rings):
#
#   Ring 0 (CENTER):  Kerr Clock (617 MHz)
#   Ring 1:           Supercomputers (1-8, equidistant from Kerr)
#   Ring 2:           Super IOCs (1-8, one per Supercomputer)
#   Ring 3 (OUTER):   IOAs (1-8, modular peripheral adapters)
#
# Modular Configurations:
#   MINIMUM: 1 Kerr + 1 SC + 1 SIOC + 1 IOA
#   MAXIMUM: 1 Kerr + 8 SC + 8 SIOC + 8 IOA
#
# =============================================================================


def round_table_backplane(
    n_supercomputers: int = 8,
    n_siocs: int = 8,
    n_ioas: int = 8,
    kerr_radius: float = 100.0,
    sc_ring_radius: float = 400.0,
    sioc_ring_radius: float = 650.0,
    ioa_ring_radius: float = 850.0
) -> Component:
    """
    ROUND TABLE BACKPLANE - The Primary System Architecture

    ████████████████████████████████████████████████████████████████████████
    █  CRITICAL: All components MUST be equidistant from central Kerr      █
    █  clock to ensure synchronized 617 MHz timing across the system.      █
    ████████████████████████████████████████████████████████████████████████

    Architecture (Concentric Rings):
        CENTER:  Kerr Clock (617 MHz master timing)
        Ring 1:  Supercomputers (optical compute units)
        Ring 2:  Super IOCs (streaming data interface)
        Ring 3:  IOAs (peripheral adapters: Ethernet, Fiber, NVMe, etc.)

    The backplane connects all supercomputers via optical waveguides,
    allowing them to operate as:
        - 8 independent LLMs (each with own SIOC/IOA)
        - 1 unified system (single SIOC for inter-group communication)
        - Hybrid configurations (some SIOCs for storage, some for networking)

    Args:
        n_supercomputers: Number of supercomputers (1-8)
        n_siocs: Number of Super IOCs (1-8, typically matches n_supercomputers)
        n_ioas: Number of IOAs (1-8, typically matches n_siocs)
        kerr_radius: Radius of central Kerr clock hub (um)
        sc_ring_radius: Radius of supercomputer ring from center (um)
        sioc_ring_radius: Radius of Super IOC ring from center (um)
        ioa_ring_radius: Radius of IOA ring from center (um)

    Returns:
        Complete Round Table backplane component

    Example Configurations:
        Minimum (dev kit):     round_table_backplane(1, 1, 1)
        Small cluster:         round_table_backplane(4, 2, 2)
        Full supercomputer:    round_table_backplane(8, 8, 8)
    """
    # Validate inputs
    n_supercomputers = max(1, min(8, n_supercomputers))
    n_siocs = max(1, min(8, n_siocs))
    n_ioas = max(1, min(8, n_ioas))

    c = gf.Component(f"round_table_{n_supercomputers}sc_{n_siocs}sioc_{n_ioas}ioa_{_uid()}")

    # Total backplane size (based on outermost ring + margin)
    backplane_radius = ioa_ring_radius + 200
    backplane_size = backplane_radius * 2
    center = backplane_size / 2

    # Background circle (the "table")
    n_points = 128
    angles = np.linspace(0, 2*np.pi, n_points)
    table_points = [(center + backplane_radius * np.cos(a),
                     center + backplane_radius * np.sin(a)) for a in angles]
    c.add_polygon(table_points, layer=LAYER_BUS)

    # =========================================================================
    # RING 0: CENTRAL KERR CLOCK (617 MHz)
    # =========================================================================
    # THIS IS THE HEART OF THE SYSTEM - ALL TIMING DERIVES FROM HERE

    kerr_hub = c << kerr_clock_hub(radius=kerr_radius)
    kerr_hub.dmove((center, center))

    # Emphasis label for Kerr centrality
    c.add_label("★ KERR 617MHz ★", position=(center, center - kerr_radius - 20), layer=LAYER_TEXT)
    c.add_label("MASTER CLOCK", position=(center, center - kerr_radius - 40), layer=LAYER_TEXT)

    # =========================================================================
    # RING 1: SUPERCOMPUTERS (Equidistant from Kerr)
    # =========================================================================

    sc_positions = []
    for i in range(n_supercomputers):
        # Distribute evenly around the ring, starting from top (12 o'clock)
        angle = (i * 2 * np.pi / n_supercomputers) - np.pi/2

        sc_x = center + sc_ring_radius * np.cos(angle)
        sc_y = center + sc_ring_radius * np.sin(angle)
        sc_positions.append((sc_x, sc_y, angle))

        # Supercomputer module (represented as larger slot)
        sc_slot = c << _supercomputer_module(sc_id=i)
        sc_slot.dmove((sc_x - 75, sc_y - 50))  # Center the module

        # Clock distribution waveguide from Kerr to SC
        # CRITICAL: These must all be the same length for clock synchronization
        kerr_edge_x = center + kerr_radius * np.cos(angle)
        kerr_edge_y = center + kerr_radius * np.sin(angle)
        sc_edge_x = center + (sc_ring_radius - 60) * np.cos(angle)
        sc_edge_y = center + (sc_ring_radius - 60) * np.sin(angle)

        # Clock waveguide (highlighted as critical path)
        _draw_clock_waveguide(c, kerr_edge_x, kerr_edge_y, sc_edge_x, sc_edge_y, angle)

        # EDFA amplifier on clock line (midpoint)
        edfa_x = center + (sc_ring_radius * 0.5) * np.cos(angle)
        edfa_y = center + (sc_ring_radius * 0.5) * np.sin(angle)
        c.add_polygon([
            (edfa_x - 12, edfa_y - 6),
            (edfa_x + 12, edfa_y - 6),
            (edfa_x + 12, edfa_y + 6),
            (edfa_x - 12, edfa_y + 6)
        ], layer=LAYER_GAIN)

    # =========================================================================
    # RING 2: SUPER IOCs (Streaming Data Interface)
    # =========================================================================

    sioc_positions = []
    for i in range(n_siocs):
        # Align with supercomputer positions if possible
        if i < n_supercomputers:
            angle = sc_positions[i][2]
        else:
            angle = (i * 2 * np.pi / n_siocs) - np.pi/2

        sioc_x = center + sioc_ring_radius * np.cos(angle)
        sioc_y = center + sioc_ring_radius * np.sin(angle)
        sioc_positions.append((sioc_x, sioc_y, angle))

        # Super IOC module
        sioc_slot = c << _super_ioc_slot(sioc_id=i)
        sioc_slot.dmove((sioc_x - 50, sioc_y - 35))

        # Data waveguide from SC to SIOC
        if i < n_supercomputers:
            sc_x, sc_y, _ = sc_positions[i]
            sc_outer_x = center + (sc_ring_radius + 60) * np.cos(angle)
            sc_outer_y = center + (sc_ring_radius + 60) * np.sin(angle)
            sioc_inner_x = center + (sioc_ring_radius - 55) * np.cos(angle)
            sioc_inner_y = center + (sioc_ring_radius - 55) * np.sin(angle)

            _draw_data_waveguide(c, sc_outer_x, sc_outer_y, sioc_inner_x, sioc_inner_y, angle)

    # =========================================================================
    # RING 3: IOAs (Peripheral Adapters)
    # =========================================================================

    for i in range(n_ioas):
        # Align with SIOC positions if possible
        if i < n_siocs:
            angle = sioc_positions[i][2]
        else:
            angle = (i * 2 * np.pi / n_ioas) - np.pi/2

        ioa_x = center + ioa_ring_radius * np.cos(angle)
        ioa_y = center + ioa_ring_radius * np.sin(angle)

        # IOA module
        ioa_slot = c << _ioa_slot(ioa_id=i)
        ioa_slot.dmove((ioa_x - 40, ioa_y - 30))

        # Data waveguide from SIOC to IOA
        if i < n_siocs:
            sioc_x, sioc_y, _ = sioc_positions[i]
            sioc_outer_x = center + (sioc_ring_radius + 45) * np.cos(angle)
            sioc_outer_y = center + (sioc_ring_radius + 45) * np.sin(angle)
            ioa_inner_x = center + (ioa_ring_radius - 45) * np.cos(angle)
            ioa_inner_y = center + (ioa_ring_radius - 45) * np.sin(angle)

            _draw_data_waveguide(c, sioc_outer_x, sioc_outer_y, ioa_inner_x, ioa_inner_y, angle)

    # =========================================================================
    # INTER-SUPERCOMPUTER DATA BUS (Ring connecting all SCs)
    # =========================================================================

    if n_supercomputers > 1:
        # Data bus ring (allows SCs to communicate via backplane)
        data_bus_radius = sc_ring_radius - 80
        _draw_ring_bus(c, center, data_bus_radius, "DATA BUS")

    # =========================================================================
    # LABELS AND DOCUMENTATION
    # =========================================================================

    # Title
    c.add_label("═══════════════════════════════════════════════════",
                position=(center, backplane_size - 30), layer=LAYER_TEXT)
    c.add_label("ROUND TABLE BACKPLANE - OPTICAL SUPERCOMPUTER",
                position=(center, backplane_size - 50), layer=LAYER_TEXT)
    c.add_label(f"{n_supercomputers} SC | {n_siocs} SIOC | {n_ioas} IOA",
                position=(center, backplane_size - 70), layer=LAYER_TEXT)
    c.add_label("═══════════════════════════════════════════════════",
                position=(center, backplane_size - 90), layer=LAYER_TEXT)

    # Ring labels
    c.add_label("Ring 1: SUPERCOMPUTERS",
                position=(center + sc_ring_radius + 100, center), layer=LAYER_TEXT)
    c.add_label("Ring 2: SUPER IOCs",
                position=(center + sioc_ring_radius + 80, center - 30), layer=LAYER_TEXT)
    c.add_label("Ring 3: IOAs",
                position=(center + ioa_ring_radius + 60, center - 60), layer=LAYER_TEXT)

    # Critical design note
    c.add_label("▼ ALL CLOCK PATHS EQUAL LENGTH ▼",
                position=(center, 60), layer=LAYER_TEXT)

    # External connection ports
    c.add_port("external_0", center=(center, backplane_size), width=10,
               orientation=90, layer=LAYER_WAVEGUIDE)
    c.add_port("power_in", center=(0, center), width=20,
               orientation=180, layer=LAYER_METAL_PAD)

    return c


def _supercomputer_module(sc_id: int = 0) -> Component:
    """
    Supercomputer module representation for Round Table.

    Contains: 243×243 Systolic Array (or 81×81), Super IOC interface
    """
    c = gf.Component(f"sc_module_{sc_id}_{_uid()}")

    width, height = 150, 100

    # Module outline
    c.add_polygon([(0, 0), (width, 0), (width, height), (0, height)], layer=LAYER_SWITCH)

    # Internal representation (systolic array grid)
    grid_margin = 10
    grid_size = 8
    cell_w = (width - 2*grid_margin) / grid_size
    cell_h = (height - 2*grid_margin) / grid_size
    for i in range(grid_size):
        for j in range(grid_size):
            cx = grid_margin + i * cell_w + cell_w/2
            cy = grid_margin + j * cell_h + cell_h/2
            c.add_polygon([
                (cx - 2, cy - 2), (cx + 2, cy - 2),
                (cx + 2, cy + 2), (cx - 2, cy + 2)
            ], layer=LAYER_WAVEGUIDE)

    # Label
    c.add_label(f"SC-{sc_id}", position=(width/2, height/2), layer=LAYER_TEXT)
    c.add_label("243×243", position=(width/2, height/2 - 15), layer=LAYER_TEXT)

    # Ports
    c.add_port("clk_in", center=(width/2, 0), width=2, orientation=270, layer=LAYER_WAVEGUIDE)
    c.add_port("data_out", center=(width/2, height), width=4, orientation=90, layer=LAYER_WAVEGUIDE)

    return c


def _super_ioc_slot(sioc_id: int = 0) -> Component:
    """
    Super IOC slot for Round Table.

    Handles: Weight loading, Activation streaming, Result collection
    """
    c = gf.Component(f"sioc_slot_{sioc_id}_{_uid()}")

    width, height = 100, 70

    # Module outline
    c.add_polygon([(0, 0), (width, 0), (width, height), (0, height)], layer=LAYER_AWG)

    # Internal blocks
    block_w = width / 3 - 5
    for i, label in enumerate(['WL', 'AS', 'RC']):  # Weight Loader, Act Streamer, Result Collector
        bx = 5 + i * (block_w + 2.5)
        c.add_polygon([
            (bx, 10), (bx + block_w, 10),
            (bx + block_w, height - 10), (bx, height - 10)
        ], layer=LAYER_HEATER)
        c.add_label(label, position=(bx + block_w/2, height/2), layer=LAYER_TEXT)

    # Label
    c.add_label(f"SIOC-{sioc_id}", position=(width/2, height - 5), layer=LAYER_TEXT)

    # Ports
    c.add_port("sc_in", center=(width/2, 0), width=4, orientation=270, layer=LAYER_WAVEGUIDE)
    c.add_port("ioa_out", center=(width/2, height), width=4, orientation=90, layer=LAYER_WAVEGUIDE)

    return c


def _ioa_slot(ioa_id: int = 0) -> Component:
    """
    IOA slot for Round Table.

    Modular adapter: Ethernet, Fiber, Coax, NVMe, etc.
    """
    c = gf.Component(f"ioa_slot_{ioa_id}_{_uid()}")

    width, height = 80, 60

    # Module outline
    c.add_polygon([(0, 0), (width, 0), (width, height), (0, height)], layer=LAYER_METAL_PAD)

    # Connector representation
    c.add_polygon([
        (width/2 - 15, height - 20), (width/2 + 15, height - 20),
        (width/2 + 15, height - 5), (width/2 - 15, height - 5)
    ], layer=LAYER_HEATER)

    # Label
    c.add_label(f"IOA-{ioa_id}", position=(width/2, height/2 - 10), layer=LAYER_TEXT)
    c.add_label("MODULAR", position=(width/2, 10), layer=LAYER_TEXT)

    # Port
    c.add_port("sioc_in", center=(width/2, 0), width=4, orientation=270, layer=LAYER_WAVEGUIDE)

    return c


def _draw_clock_waveguide(c: Component, x1: float, y1: float, x2: float, y2: float, angle: float):
    """Draw a clock distribution waveguide (critical path - highlighted)."""
    dx = 3 * np.cos(angle + np.pi/2)
    dy = 3 * np.sin(angle + np.pi/2)
    c.add_polygon([
        (x1 - dx, y1 - dy), (x2 - dx, y2 - dy),
        (x2 + dx, y2 + dy), (x1 + dx, y1 + dy)
    ], layer=LAYER_HEATER)  # Heater layer to highlight clock paths


def _draw_data_waveguide(c: Component, x1: float, y1: float, x2: float, y2: float, angle: float):
    """Draw a data waveguide between components."""
    dx = 2 * np.cos(angle + np.pi/2)
    dy = 2 * np.sin(angle + np.pi/2)
    c.add_polygon([
        (x1 - dx, y1 - dy), (x2 - dx, y2 - dy),
        (x2 + dx, y2 + dy), (x1 + dx, y1 + dy)
    ], layer=LAYER_WAVEGUIDE)


def _draw_ring_bus(c: Component, center: float, radius: float, label: str):
    """Draw a ring bus connecting components at given radius."""
    n_points = 64
    angles = np.linspace(0, 2*np.pi, n_points)

    for i in range(n_points - 1):
        a1, a2 = angles[i], angles[i+1]
        c.add_polygon([
            (center + (radius - 3) * np.cos(a1), center + (radius - 3) * np.sin(a1)),
            (center + (radius + 3) * np.cos(a1), center + (radius + 3) * np.sin(a1)),
            (center + (radius + 3) * np.cos(a2), center + (radius + 3) * np.sin(a2)),
            (center + (radius - 3) * np.cos(a2), center + (radius - 3) * np.sin(a2)),
        ], layer=LAYER_WAVEGUIDE)

    c.add_label(label, position=(center + radius + 30, center), layer=LAYER_TEXT)


# =============================================================================
# Export functions
# =============================================================================

__all__ = [
    'backplane_slot',
    'crossbar_switch',
    'optical_bus',
    'backplane_edfa',
    'optical_backplane',
    'mini_backplane',
    'kerr_clock_hub',
    'backplane_central_clock',
    'round_table_backplane',  # PRIMARY ARCHITECTURE
]


if __name__ == "__main__":
    import os

    print("=" * 70)
    print("OPTICAL BACKPLANE GENERATOR")
    print("=" * 70)

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'gds')
    os.makedirs(output_dir, exist_ok=True)

    # =========================================================================
    # ROUND TABLE BACKPLANES (PRIMARY ARCHITECTURE)
    # =========================================================================
    print("\n>>> ROUND TABLE ARCHITECTURE (Primary) <<<")
    print("    Critical: Kerr clock at center, all components equidistant\n")

    # Minimum configuration (dev kit)
    rt_min = round_table_backplane(n_supercomputers=1, n_siocs=1, n_ioas=1)
    bbox = rt_min.dbbox()
    print(f"  Round Table MINIMUM (1 SC):  {bbox.width():.0f} x {bbox.height():.0f} um")
    rt_min.write_gds(os.path.join(output_dir, 'round_table_minimum.gds'))

    # Small cluster
    rt_small = round_table_backplane(n_supercomputers=4, n_siocs=2, n_ioas=2)
    bbox = rt_small.dbbox()
    print(f"  Round Table SMALL (4 SC):    {bbox.width():.0f} x {bbox.height():.0f} um")
    rt_small.write_gds(os.path.join(output_dir, 'round_table_small.gds'))

    # Maximum configuration (full supercomputer)
    rt_max = round_table_backplane(n_supercomputers=8, n_siocs=8, n_ioas=8)
    bbox = rt_max.dbbox()
    print(f"  Round Table MAXIMUM (8 SC):  {bbox.width():.0f} x {bbox.height():.0f} um")
    rt_max.write_gds(os.path.join(output_dir, 'round_table_maximum.gds'))

    # =========================================================================
    # LEGACY BACKPLANES (for reference)
    # =========================================================================
    print("\n>>> Legacy Backplanes (reference only) <<<\n")

    # Full backplane (linear layout)
    bp = optical_backplane(n_opu_slots=4, n_ioc_slots=2, n_ioa_slots=4)
    bbox = bp.dbbox()
    print(f"  Linear Backplane:            {bbox.width():.0f} x {bbox.height():.0f} um")
    bp.write_gds(os.path.join(output_dir, 'optical_backplane.gds'))

    # Mini backplane
    mini = mini_backplane(n_slots=4)
    bbox = mini.dbbox()
    print(f"  Mini Backplane:              {bbox.width():.0f} x {bbox.height():.0f} um")
    mini.write_gds(os.path.join(output_dir, 'mini_backplane.gds'))

    print(f"\n>>> All files saved to {output_dir}")
    print("=" * 70)
