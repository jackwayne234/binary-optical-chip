#!/usr/bin/env python3
"""
Ternary Tier 2 RAM Generator - "Working" Registers

Balanced optical registers for the 81-trit ternary optical computer.
General-purpose working memory with good speed/capacity tradeoff.

Characteristics:
- 8-16 registers (R0-R15)
- Medium delay loops (~10 ns)
- Pulsed SOA refresh (power-efficient)
- Full MUX/DEMUX addressing
- Moderate power consumption

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

LAYER_WAVEGUIDE: LayerSpec = (1, 0)
LAYER_HEATER: LayerSpec = (10, 0)
LAYER_METAL_PAD: LayerSpec = (12, 0)
LAYER_SOA: LayerSpec = (14, 0)
LAYER_RING: LayerSpec = (11, 0)
LAYER_TEXT: LayerSpec = (100, 0)

WAVEGUIDE_WIDTH = 0.5
BEND_RADIUS = 10.0


# =============================================================================
# Components
# =============================================================================

@gf.cell
def working_soa(length: float = 100.0, width: float = 3.0) -> Component:
    """Pulsed SOA with gate control."""
    c = gf.Component()

    taper_length = 12.0

    # Tapers
    c << gf.components.taper(length=taper_length, width1=WAVEGUIDE_WIDTH, width2=width)

    gain = c << gf.components.rectangle(size=(length, width), layer=LAYER_SOA)
    gain.movex(taper_length)

    taper_out = c << gf.components.taper(length=taper_length, width1=width, width2=WAVEGUIDE_WIDTH)
    taper_out.movex(taper_length + length)

    # Contacts
    main_contact = c << gf.components.rectangle(size=(length * 0.5, 8), layer=LAYER_METAL_PAD)
    main_contact.move((taper_length + length * 0.1, width + 4))

    gate_contact = c << gf.components.rectangle(size=(length * 0.2, 8), layer=LAYER_METAL_PAD)
    gate_contact.move((taper_length + length * 0.7, width + 4))

    gate_label = c << gf.components.text(text="G", size=5, layer=LAYER_TEXT)
    gate_label.move((taper_length + length * 0.75, width + 14))

    total_length = 2 * taper_length + length
    c.add_port(name="in", center=(0, width/2), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_SOA)
    c.add_port(name="out", center=(total_length, width/2), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_SOA)

    return c


@gf.cell
def serpentine_10ns(n_turns: int = 6) -> Component:
    """Serpentine for ~10ns delay."""
    c = gf.Component()

    straight_len = 40.0
    turn_spacing = 2 * BEND_RADIUS + 8

    y_pos = 0
    for i in range(n_turns + 1):
        wg = c << gf.components.straight(length=straight_len, width=WAVEGUIDE_WIDTH)
        wg.move((0, y_pos))

        if i < n_turns:
            if i % 2 == 0:
                b1 = c << gf.components.bend_euler(angle=90, radius=BEND_RADIUS)
                b1.move((straight_len, y_pos))
                b2 = c << gf.components.bend_euler(angle=90, radius=BEND_RADIUS)
                b2.move((straight_len + BEND_RADIUS, y_pos + BEND_RADIUS))
                b2.rotate(90)
                y_pos += turn_spacing
            else:
                b1 = c << gf.components.bend_euler(angle=-90, radius=BEND_RADIUS)
                b1.move((straight_len, y_pos))
                b2 = c << gf.components.bend_euler(angle=-90, radius=BEND_RADIUS)
                b2.move((straight_len + BEND_RADIUS, y_pos - BEND_RADIUS))
                b2.rotate(-90)
                y_pos -= turn_spacing

    c.add_port(name="in", center=(0, 0), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="out", center=(straight_len, y_pos), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)

    return c


@gf.cell
def tunable_coupler(coupling_length: float = 20.0) -> Component:
    """Tunable directional coupler with heater."""
    c = gf.Component()

    gap = 0.3
    bend_len = 12.0
    port_spacing = 6.0

    top_wg = c << gf.components.straight(length=coupling_length, width=WAVEGUIDE_WIDTH)
    top_wg.move((bend_len, gap/2 + WAVEGUIDE_WIDTH/2))

    bottom_wg = c << gf.components.straight(length=coupling_length, width=WAVEGUIDE_WIDTH)
    bottom_wg.move((bend_len, -gap/2 - WAVEGUIDE_WIDTH/2))

    # S-bends
    for pos, y_off in [(0, port_spacing/2), (0, -port_spacing/2)]:
        s = c << gf.components.bend_s(size=(bend_len, abs(y_off)))
        s.move((pos, y_off))
        if y_off > 0:
            s.mirror_y()

    for pos in [bend_len + coupling_length]:
        s1 = c << gf.components.bend_s(size=(bend_len, port_spacing/2))
        s1.move((pos, gap/2 + WAVEGUIDE_WIDTH/2))
        s2 = c << gf.components.bend_s(size=(bend_len, port_spacing/2))
        s2.move((pos, -gap/2 - WAVEGUIDE_WIDTH/2))
        s2.mirror_y()

    # Heater
    heater = c << gf.components.rectangle(size=(coupling_length * 0.7, 2), layer=LAYER_HEATER)
    heater.move((bend_len + coupling_length * 0.15, gap/2 + WAVEGUIDE_WIDTH + 2))

    total_length = 2 * bend_len + coupling_length

    c.add_port(name="in_thru", center=(0, port_spacing/2), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="in_loop", center=(0, -port_spacing/2), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="out_thru", center=(total_length, port_spacing/2), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port(name="out_loop", center=(total_length, -port_spacing/2), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)

    return c


@gf.cell
def working_register_cell(register_id: int = 0) -> Component:
    """Single Tier 2 working register cell."""
    c = gf.Component()

    x = 0

    # Write coupler
    wc = c << tunable_coupler(coupling_length=30.0)
    wc.move((x, 0))
    x += 70

    # Delay loop
    delay = c << serpentine_10ns(n_turns=5)
    delay.move((x, -30))
    x += 100

    # Pulsed SOA
    soa = c << working_soa(length=80.0)
    soa.move((x, -1.5))
    x += 120

    # Read taps
    ra = c << tunable_coupler(coupling_length=12.0)
    ra.move((x, 0))
    x += 55

    rb = c << tunable_coupler(coupling_length=12.0)
    rb.move((x, 0))
    x += 55

    # Loopback
    loopback = c << gf.components.rectangle(size=(x - 120, 2), layer=LAYER_WAVEGUIDE)
    loopback.move((60, 45))

    # Label
    label = c << gf.components.text(text=f"R{register_id}", size=15, layer=LAYER_TEXT)
    label.move((x/2 - 15, -50))

    c.add_port(name="write_in", center=(0, 4), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="read_a", center=(x - 55, 4), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port(name="read_b", center=(x, 4), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)

    return c


@gf.cell
def tier2_register_file(num_registers: int = 8) -> Component:
    """Tier 2 Working Register File."""
    c = gf.Component()

    num_registers = 8 if num_registers <= 8 else 16
    reg_spacing = 100
    reg_start_x = 300

    # Title
    title = c << gf.components.text(text="TIER 2: WORKING REGISTERS", size=25, layer=LAYER_TEXT)
    title.move((reg_start_x + 50, num_registers * reg_spacing / 2 + 70))

    # Registers
    for i in range(num_registers):
        reg = c << working_register_cell(register_id=i)
        reg.move((reg_start_x, i * reg_spacing))

    # Write demux representation
    demux = c << gf.components.rectangle(size=(80, num_registers * reg_spacing * 0.8), layer=LAYER_RING)
    demux.move((100, num_registers * reg_spacing * 0.1))
    demux_label = c << gf.components.text(text="1:N\nDMX", size=12, layer=LAYER_TEXT)
    demux_label.move((120, num_registers * reg_spacing / 2 - 20))

    # Read buses
    read_a_x = reg_start_x + 400
    read_b_x = reg_start_x + 455

    bus_a = c << gf.components.rectangle(size=(3, num_registers * reg_spacing), layer=LAYER_WAVEGUIDE)
    bus_a.move((read_a_x, 0))

    bus_b = c << gf.components.rectangle(size=(3, num_registers * reg_spacing), layer=LAYER_WAVEGUIDE)
    bus_b.move((read_b_x, 0))

    # Read MUX representations
    mux_a = c << gf.components.rectangle(size=(60, 80), layer=LAYER_RING)
    mux_a.move((read_a_x + 20, num_registers * reg_spacing / 2 - 40))
    mux_a_label = c << gf.components.text(text="MUX\nA", size=10, layer=LAYER_TEXT)
    mux_a_label.move((read_a_x + 35, num_registers * reg_spacing / 2 - 20))

    mux_b = c << gf.components.rectangle(size=(60, 80), layer=LAYER_RING)
    mux_b.move((read_b_x + 20, num_registers * reg_spacing / 2 - 40))
    mux_b_label = c << gf.components.text(text="MUX\nB", size=10, layer=LAYER_TEXT)
    mux_b_label.move((read_b_x + 35, num_registers * reg_spacing / 2 - 20))

    # Specs
    specs = c << gf.components.text(text=f"{num_registers} reg | 10ns loop | pulsed SOA", size=12, layer=LAYER_TEXT)
    specs.move((reg_start_x, -60))

    # Ports
    c.add_port(name="write_data", center=(50, num_registers * reg_spacing / 2),
               width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="read_port_a", center=(read_a_x + 80, num_registers * reg_spacing / 2),
               width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port(name="read_port_b", center=(read_b_x + 80, num_registers * reg_spacing / 2),
               width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)

    return c


def generate_tier2_registers(
    num_registers: int = 8,
    output_path: Optional[str] = None
) -> Component:
    """Generate Tier 2 Working Register File."""
    print(f"Generating Tier 2 Working Register File...")
    print(f"  Registers: {num_registers}")
    print(f"  Loop delay: ~10 ns")
    print(f"  SOA mode: Pulsed (power-efficient)")

    component = tier2_register_file(num_registers=num_registers)

    if output_path:
        component.write_gds(output_path)
        print(f"  Saved to: {output_path}")

    return component


def main():
    """CLI for Tier 2 RAM generation."""
    print("=" * 60)
    print("  TERNARY TIER 2 RAM GENERATOR")
    print("  'Working' Registers - Balanced Optical Storage")
    print("=" * 60)

    print("\nOptions:")
    print("  1. Generate 8-register file (R0-R7)")
    print("  2. Generate 16-register file (R0-R15)")

    choice = input("\nSelect option [1-2]: ").strip()
    output_dir = "Research/data/gds"

    if choice == "1":
        generate_tier2_registers(8, f"{output_dir}/tier2_working_registers_8reg.gds")
    elif choice == "2":
        generate_tier2_registers(16, f"{output_dir}/tier2_working_registers_16reg.gds")
    else:
        print("Invalid option")


if __name__ == "__main__":
    main()
