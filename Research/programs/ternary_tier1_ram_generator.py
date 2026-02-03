#!/usr/bin/env python3
"""
Ternary Tier 1 RAM Generator - "Hot" Registers

Ultra-fast optical registers for the 81-trit ternary optical computer.
These are the fastest tier, designed for accumulator and temporary storage.

Characteristics:
- 2-4 registers (ACC, TMP, A, B)
- Ultra-short delay loops (~1 ns, ~20 cm)
- Continuous SOA amplification (always on)
- Minimal routing latency
- Highest power consumption
- Designed for inline ALU integration

Author: Wavelength-Division Ternary Optical Computer Project
"""

import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.typings import LayerSpec
import numpy as np
from typing import Optional

# Activate PDK
gf.gpdk.PDK.activate()

# =============================================================================
# Layer Definitions
# =============================================================================

LAYER_WAVEGUIDE: LayerSpec = (1, 0)      # Main optical waveguides
LAYER_HEATER: LayerSpec = (10, 0)        # Thermal tuning heaters
LAYER_METAL_PAD: LayerSpec = (12, 0)     # Electrical contact pads
LAYER_SOA: LayerSpec = (14, 0)           # SOA gain regions
LAYER_RING: LayerSpec = (11, 0)          # Ring resonators
LAYER_TEXT: LayerSpec = (100, 0)         # Labels

# =============================================================================
# Physical Constants
# =============================================================================

WAVEGUIDE_WIDTH = 0.5           # um
BEND_RADIUS = 10.0              # um
SOA_LENGTH = 100.0              # um
LOOP_LENGTH_1NS = 200.0         # um (~1 ns delay at n=1.5)


# =============================================================================
# Basic Components
# =============================================================================

@gf.cell
def hot_register_soa(
    length: float = SOA_LENGTH,
    width: float = 3.0
) -> Component:
    """
    Semiconductor Optical Amplifier for continuous refresh.
    Always-on for Tier 1 hot registers.
    """
    c = gf.Component()

    taper_length = 15.0

    # Input taper
    taper_in = c << gf.components.taper(
        length=taper_length,
        width1=WAVEGUIDE_WIDTH,
        width2=width
    )

    # Gain section (rectangle on SOA layer)
    gain = c << gf.components.rectangle(size=(length, width), layer=LAYER_SOA)
    gain.movex(taper_length)

    # Output taper
    taper_out = c << gf.components.taper(
        length=taper_length,
        width1=width,
        width2=WAVEGUIDE_WIDTH
    )
    taper_out.movex(taper_length + length)

    # Electrical contacts
    contact_width = length * 0.8
    contact_height = 10.0

    top_contact = c << gf.components.rectangle(
        size=(contact_width, contact_height),
        layer=LAYER_METAL_PAD
    )
    top_contact.move((taper_length + length * 0.1, width + 5))

    bottom_contact = c << gf.components.rectangle(
        size=(contact_width, contact_height),
        layer=LAYER_METAL_PAD
    )
    bottom_contact.move((taper_length + length * 0.1, -contact_height - 5))

    # Ports
    total_length = 2 * taper_length + length
    c.add_port(name="in", center=(0, width/2), width=WAVEGUIDE_WIDTH,
               orientation=180, layer=LAYER_SOA)
    c.add_port(name="out", center=(total_length, width/2), width=WAVEGUIDE_WIDTH,
               orientation=0, layer=LAYER_SOA)

    return c


@gf.cell
def directional_coupler(
    coupling_length: float = 20.0,
    gap: float = 0.3
) -> Component:
    """
    Directional coupler for loop input/output.
    """
    c = gf.Component()

    bend_length = 15.0
    port_spacing = 8.0

    # Coupling region - two parallel waveguides
    top_wg = c << gf.components.straight(length=coupling_length, width=WAVEGUIDE_WIDTH)
    top_wg.move((bend_length, gap/2 + WAVEGUIDE_WIDTH/2))

    bottom_wg = c << gf.components.straight(length=coupling_length, width=WAVEGUIDE_WIDTH)
    bottom_wg.move((bend_length, -gap/2 - WAVEGUIDE_WIDTH/2))

    # S-bends for input port separation
    in_top = c << gf.components.bend_s(size=(bend_length, port_spacing/2))
    in_top.move((0, port_spacing/2))
    in_top.mirror_y()

    in_bottom = c << gf.components.bend_s(size=(bend_length, port_spacing/2))
    in_bottom.move((0, -port_spacing/2))

    # S-bends for output
    out_top = c << gf.components.bend_s(size=(bend_length, port_spacing/2))
    out_top.move((bend_length + coupling_length, gap/2 + WAVEGUIDE_WIDTH/2))

    out_bottom = c << gf.components.bend_s(size=(bend_length, port_spacing/2))
    out_bottom.move((bend_length + coupling_length, -gap/2 - WAVEGUIDE_WIDTH/2))
    out_bottom.mirror_y()

    total_length = 2 * bend_length + coupling_length

    # Ports
    c.add_port(name="in_top", center=(0, port_spacing/2), width=WAVEGUIDE_WIDTH,
               orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="in_bottom", center=(0, -port_spacing/2), width=WAVEGUIDE_WIDTH,
               orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="out_top", center=(total_length, port_spacing/2), width=WAVEGUIDE_WIDTH,
               orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port(name="out_bottom", center=(total_length, -port_spacing/2), width=WAVEGUIDE_WIDTH,
               orientation=0, layer=LAYER_WAVEGUIDE)

    return c


@gf.cell
def serpentine_delay(
    delay_ns: float = 1.0,
    n_turns: int = 4
) -> Component:
    """
    Serpentine delay line for recirculating loop.
    """
    c = gf.Component()

    # Approximate: 200 um per ns at n=1.5
    total_length = delay_ns * 200.0
    straight_length = total_length / (n_turns + 1)
    straight_length = max(20, min(straight_length, 100))

    turn_spacing = 2 * BEND_RADIUS + 5

    y_pos = 0
    for i in range(n_turns + 1):
        # Straight section
        wg = c << gf.components.straight(length=straight_length, width=WAVEGUIDE_WIDTH)
        wg.move((0, y_pos))

        if i < n_turns:
            # 180-degree turn
            if i % 2 == 0:
                bend1 = c << gf.components.bend_euler(angle=90, radius=BEND_RADIUS)
                bend1.move((straight_length, y_pos))

                bend2 = c << gf.components.bend_euler(angle=90, radius=BEND_RADIUS)
                bend2.move((straight_length + BEND_RADIUS, y_pos + BEND_RADIUS))
                bend2.rotate(90)

                y_pos += turn_spacing
            else:
                bend1 = c << gf.components.bend_euler(angle=-90, radius=BEND_RADIUS)
                bend1.move((straight_length, y_pos))

                bend2 = c << gf.components.bend_euler(angle=-90, radius=BEND_RADIUS)
                bend2.move((straight_length + BEND_RADIUS, y_pos - BEND_RADIUS))
                bend2.rotate(-90)

                y_pos -= turn_spacing

    # Ports
    c.add_port(name="in", center=(0, 0), width=WAVEGUIDE_WIDTH,
               orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="out", center=(straight_length, y_pos), width=WAVEGUIDE_WIDTH,
               orientation=0, layer=LAYER_WAVEGUIDE)

    return c


# =============================================================================
# Hot Register Cell
# =============================================================================

@gf.cell
def hot_register_cell(
    loop_delay_ns: float = 1.0,
    register_id: int = 0
) -> Component:
    """
    Single Tier 1 "Hot" register cell.

    Architecture:
    - Input coupler (write path)
    - Ultra-short recirculating loop
    - Continuous SOA for refresh
    - Output tap couplers (2x for dual read)
    """
    c = gf.Component()

    x_offset = 0

    # 1. Write coupler
    write_coupler = c << directional_coupler(coupling_length=25.0)
    write_coupler.move((x_offset, 0))
    x_offset += 70

    # 2. Delay loop
    delay = c << serpentine_delay(delay_ns=loop_delay_ns, n_turns=3)
    delay.move((x_offset, -20))
    x_offset += 80

    # 3. SOA (continuous)
    soa = c << hot_register_soa(length=80.0)
    soa.move((x_offset, -1.5))
    x_offset += 130

    # 4. Read tap A
    read_a = c << directional_coupler(coupling_length=12.0)
    read_a.move((x_offset, 0))
    x_offset += 60

    # 5. Read tap B
    read_b = c << directional_coupler(coupling_length=12.0)
    read_b.move((x_offset, 0))
    x_offset += 60

    # Loopback path (simplified)
    loopback = c << gf.components.rectangle(size=(x_offset - 100, 2), layer=LAYER_WAVEGUIDE)
    loopback.move((50, 35))

    # Register label
    reg_names = ["ACC", "TMP", "A", "B"]
    reg_name = reg_names[register_id] if register_id < len(reg_names) else f"R{register_id}"
    label = c << gf.components.text(text=reg_name, size=15, layer=LAYER_TEXT)
    label.move((x_offset / 2 - 15, -40))

    # Ports
    c.add_port(name="write_in", center=(0, 5), width=WAVEGUIDE_WIDTH,
               orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="read_a", center=(x_offset - 60, 5), width=WAVEGUIDE_WIDTH,
               orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port(name="read_b", center=(x_offset, 5), width=WAVEGUIDE_WIDTH,
               orientation=0, layer=LAYER_WAVEGUIDE)

    return c


# =============================================================================
# MZI Switch
# =============================================================================

@gf.cell
def mzi_switch(arm_length: float = 80.0) -> Component:
    """MZI switch for register selection using MMI splitter/combiner."""
    c = gf.Component()

    y_split = 10.0

    # Input MMI 1x2 splitter
    splitter = c << gf.components.mmi1x2(width_mmi=5.0, length_mmi=15.0)

    # Top arm
    top_arm = c << gf.components.straight(length=arm_length, width=WAVEGUIDE_WIDTH)
    top_arm.move((25, y_split))

    # Bottom arm
    bottom_arm = c << gf.components.straight(length=arm_length, width=WAVEGUIDE_WIDTH)
    bottom_arm.move((25, -y_split))

    # Heater on top arm
    heater = c << gf.components.rectangle(size=(arm_length * 0.6, 3), layer=LAYER_HEATER)
    heater.move((25 + arm_length * 0.2, y_split + 3))

    # Heater pads
    pad_l = c << gf.components.rectangle(size=(12, 12), layer=LAYER_METAL_PAD)
    pad_l.move((25, y_split + 8))

    pad_r = c << gf.components.rectangle(size=(12, 12), layer=LAYER_METAL_PAD)
    pad_r.move((arm_length + 15, y_split + 8))

    # Output MMI 2x2
    combiner = c << gf.components.mmi2x2(width_mmi=5.0, length_mmi=20.0)
    combiner.move((25 + arm_length + 10, 0))

    total_length = 25 + arm_length + 10 + 25

    # Ports
    c.add_port(name="in", center=(0, 0), width=WAVEGUIDE_WIDTH,
               orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="out_bar", center=(total_length, y_split), width=WAVEGUIDE_WIDTH,
               orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port(name="out_cross", center=(total_length, -y_split), width=WAVEGUIDE_WIDTH,
               orientation=0, layer=LAYER_WAVEGUIDE)

    return c


# =============================================================================
# Tier 1 Register File
# =============================================================================

@gf.cell
def tier1_register_file(
    num_registers: int = 4,
    loop_delay_ns: float = 1.0
) -> Component:
    """
    Complete Tier 1 "Hot" Register File.

    Contains:
    - 2-4 hot registers (ACC, TMP, A, B)
    - Write demux (MZI tree)
    - Dual read mux
    - All SOAs always on
    """
    c = gf.Component()

    num_registers = min(4, max(2, num_registers))
    reg_spacing_y = 80
    reg_start_x = 200

    # Title
    title = c << gf.components.text(text="TIER 1: HOT REGISTERS", size=20, layer=LAYER_TEXT)
    title.move((reg_start_x + 50, num_registers * reg_spacing_y / 2 + 60))

    # Create registers
    for i in range(num_registers):
        reg = c << hot_register_cell(loop_delay_ns=loop_delay_ns, register_id=i)
        reg.move((reg_start_x, i * reg_spacing_y))

    # Write demux (simplified MZI)
    if num_registers >= 2:
        mzi = c << mzi_switch(arm_length=60)
        mzi.move((50, reg_spacing_y * (num_registers - 1) / 2))

    # Read buses (simplified)
    read_a_x = reg_start_x + 400
    read_b_x = reg_start_x + 460

    read_bus_a = c << gf.components.rectangle(
        size=(3, num_registers * reg_spacing_y),
        layer=LAYER_WAVEGUIDE
    )
    read_bus_a.move((read_a_x, 0))

    read_bus_b = c << gf.components.rectangle(
        size=(3, num_registers * reg_spacing_y),
        layer=LAYER_WAVEGUIDE
    )
    read_bus_b.move((read_b_x, 0))

    # Specs label
    specs = c << gf.components.text(
        text=f"{num_registers} reg | {loop_delay_ns}ns | always-on SOA",
        size=10,
        layer=LAYER_TEXT
    )
    specs.move((reg_start_x, -50))

    # Ports
    c.add_port(name="write_data", center=(0, reg_spacing_y * (num_registers - 1) / 2),
               width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="read_port_a", center=(read_a_x + 1.5, num_registers * reg_spacing_y),
               width=3, orientation=90, layer=LAYER_WAVEGUIDE)
    c.add_port(name="read_port_b", center=(read_b_x + 1.5, num_registers * reg_spacing_y),
               width=3, orientation=90, layer=LAYER_WAVEGUIDE)

    return c


# =============================================================================
# Main Generator Function
# =============================================================================

def generate_tier1_registers(
    num_registers: int = 4,
    loop_delay_ns: float = 1.0,
    output_path: Optional[str] = None
) -> Component:
    """
    Generate Tier 1 Hot Register File.
    """
    print(f"Generating Tier 1 Hot Register File...")
    print(f"  Registers: {num_registers}")
    print(f"  Loop delay: {loop_delay_ns} ns")
    print(f"  SOA mode: Continuous (always-on)")

    component = tier1_register_file(
        num_registers=num_registers,
        loop_delay_ns=loop_delay_ns
    )

    if output_path:
        component.write_gds(output_path)
        print(f"  Saved to: {output_path}")

    return component


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Interactive CLI for Tier 1 RAM generation."""
    print("=" * 60)
    print("  TERNARY TIER 1 RAM GENERATOR")
    print("  'Hot' Registers - Ultra-fast Optical Storage")
    print("=" * 60)
    print()

    print("Options:")
    print("  1. Generate 2-register file (ACC, TMP)")
    print("  2. Generate 4-register file (ACC, TMP, A, B)")
    print("  3. Generate single register cell (test)")
    print()

    choice = input("Select option [1-3]: ").strip()

    output_dir = "Research/data/gds"

    if choice == "1":
        generate_tier1_registers(num_registers=2, loop_delay_ns=1.0,
                                  output_path=f"{output_dir}/tier1_hot_registers_2reg.gds")
    elif choice == "2":
        generate_tier1_registers(num_registers=4, loop_delay_ns=1.0,
                                  output_path=f"{output_dir}/tier1_hot_registers_4reg.gds")
    elif choice == "3":
        print("Generating single hot register cell...")
        component = hot_register_cell(loop_delay_ns=1.0, register_id=0)
        component.write_gds(f"{output_dir}/tier1_single_cell_test.gds")
        print(f"  Saved to: {output_dir}/tier1_single_cell_test.gds")
    else:
        print("Invalid option")
        return

    print("\nGeneration complete!")


if __name__ == "__main__":
    main()
