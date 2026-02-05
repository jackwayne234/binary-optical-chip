#!/usr/bin/env python3
"""
Ternary Tier 3 RAM Generator - "Parking" Registers

Low-power bistable optical registers for the 81-trit ternary optical computer.
Data persists without refresh - ideal for constants and infrequent access.

Characteristics:
- 32+ registers (P0-P31)
- Bistable optical flip-flops (no refresh needed)
- Uses saturable absorber + gain medium
- Lowest power consumption
- Slower read/write

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
LAYER_SA: LayerSpec = (13, 0)           # Saturable absorber
LAYER_GAIN: LayerSpec = (14, 0)         # Gain medium
LAYER_RING: LayerSpec = (11, 0)
LAYER_TEXT: LayerSpec = (100, 0)

WAVEGUIDE_WIDTH = 0.5
RING_RADIUS = 15.0


# =============================================================================
# Bistable Components
# =============================================================================

@gf.cell
def saturable_absorber(length: float = 25.0) -> Component:
    """Saturable absorber section."""
    c = gf.Component()

    width = 1.2
    taper_len = 6.0

    c << gf.components.taper(length=taper_len, width1=WAVEGUIDE_WIDTH, width2=width)

    sa = c << gf.components.rectangle(size=(length, width), layer=LAYER_SA)
    sa.movex(taper_len)

    taper_out = c << gf.components.taper(length=taper_len, width1=width, width2=WAVEGUIDE_WIDTH)
    taper_out.movex(taper_len + length)

    bias = c << gf.components.rectangle(size=(length * 0.6, 4), layer=LAYER_METAL_PAD)
    bias.move((taper_len + length * 0.2, width + 2))

    total = 2 * taper_len + length
    c.add_port(name="in", center=(0, width/2), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_SA)
    c.add_port(name="out", center=(total, width/2), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_SA)

    return c


@gf.cell
def gain_section(length: float = 40.0) -> Component:
    """Gain medium section."""
    c = gf.Component()

    width = 1.8
    taper_len = 8.0

    c << gf.components.taper(length=taper_len, width1=WAVEGUIDE_WIDTH, width2=width)

    gain = c << gf.components.rectangle(size=(length, width), layer=LAYER_GAIN)
    gain.movex(taper_len)

    taper_out = c << gf.components.taper(length=taper_len, width1=width, width2=WAVEGUIDE_WIDTH)
    taper_out.movex(taper_len + length)

    # Pump electrodes
    pump_top = c << gf.components.rectangle(size=(length * 0.6, 5), layer=LAYER_METAL_PAD)
    pump_top.move((taper_len + length * 0.2, width + 3))

    pump_bot = c << gf.components.rectangle(size=(length * 0.6, 5), layer=LAYER_METAL_PAD)
    pump_bot.move((taper_len + length * 0.2, -6))

    total = 2 * taper_len + length
    c.add_port(name="in", center=(0, width/2), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_GAIN)
    c.add_port(name="out", center=(total, width/2), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_GAIN)

    return c


@gf.cell
def bistable_ring() -> Component:
    """Bistable ring resonator with SA and gain."""
    c = gf.Component()

    # Ring
    ring = c << gf.components.ring(radius=RING_RADIUS, width=WAVEGUIDE_WIDTH)
    ring.move((RING_RADIUS + 20, RING_RADIUS + 5))

    # Bus waveguide
    bus = c << gf.components.straight(length=4 * RING_RADIUS + 40, width=WAVEGUIDE_WIDTH)

    # SA in ring
    sa = c << saturable_absorber(length=15.0)
    sa.move((RING_RADIUS + 10, 2 * RING_RADIUS + 3))

    # Gain in ring
    gain = c << gain_section(length=25.0)
    gain.move((RING_RADIUS + 5, 3))

    # Coupling indicator
    coupling = c << gf.components.rectangle(size=(10, 3), layer=LAYER_RING)
    coupling.move((RING_RADIUS + 18, -1))

    c.add_port(name="in", center=(0, 0), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="out", center=(4 * RING_RADIUS + 40, 0), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)

    return c


@gf.cell
def ternary_bistable_cell() -> Component:
    """Single ternary bistable storage (3 channels for R/G/B)."""
    c = gf.Component()

    ch_spacing = 55

    # Three wavelength channels
    for i, ch in enumerate(["R", "G", "B"]):
        ring = c << bistable_ring()
        ring.move((0, i * ch_spacing))

        label = c << gf.components.text(text=ch, size=10, layer=LAYER_TEXT)
        label.move((-15, i * ch_spacing + 15))

    # Input demux
    demux = c << gf.components.rectangle(size=(15, ch_spacing * 2 + 30), layer=LAYER_RING)
    demux.move((-35, -5))
    demux_label = c << gf.components.text(text="DMX", size=5, layer=LAYER_TEXT)
    demux_label.move((-33, ch_spacing - 5))

    # Output mux
    mux = c << gf.components.rectangle(size=(15, ch_spacing * 2 + 30), layer=LAYER_RING)
    mux.move((105, -5))
    mux_label = c << gf.components.text(text="MUX", size=5, layer=LAYER_TEXT)
    mux_label.move((107, ch_spacing - 5))

    c.add_port(name="in", center=(-50, ch_spacing), width=WAVEGUIDE_WIDTH, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="out", center=(120, ch_spacing), width=WAVEGUIDE_WIDTH, orientation=0, layer=LAYER_WAVEGUIDE)

    return c


@gf.cell
def parking_register(register_id: int = 0) -> Component:
    """Single parking register (81 trits as 9x9 grid)."""
    c = gf.Component()

    cell_w = 35
    cell_h = 28

    for row in range(9):
        for col in range(9):
            idx = row * 9 + col
            cell = c << gf.components.rectangle(size=(cell_w - 3, cell_h - 3), layer=LAYER_WAVEGUIDE)
            cell.move((col * cell_w, row * cell_h))

            # Bistable dot
            dot = c << gf.components.circle(radius=2, layer=LAYER_SA)
            dot.move((col * cell_w + cell_w/2, row * cell_h + cell_h/2))

            if idx % 18 == 0:
                lbl = c << gf.components.text(text=str(idx), size=4, layer=LAYER_TEXT)
                lbl.move((col * cell_w + 2, row * cell_h + 2))

    # Register label
    reg_lbl = c << gf.components.text(text=f"P{register_id}", size=18, layer=LAYER_TEXT)
    reg_lbl.move((9 * cell_w / 2 - 15, 9 * cell_h + 8))

    # Input/output buses
    in_bus = c << gf.components.rectangle(size=(4, 9 * cell_h), layer=LAYER_WAVEGUIDE)
    in_bus.move((-15, 0))

    out_bus = c << gf.components.rectangle(size=(4, 9 * cell_h), layer=LAYER_WAVEGUIDE)
    out_bus.move((9 * cell_w + 8, 0))

    c.add_port(name="in", center=(-18, 9 * cell_h / 2), width=4, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="out", center=(9 * cell_w + 12, 9 * cell_h / 2), width=4, orientation=0, layer=LAYER_WAVEGUIDE)

    return c


@gf.cell
def tier3_register_file(num_registers: int = 32) -> Component:
    """Tier 3 Parking Register File."""
    c = gf.Component()

    num_registers = min(32, max(8, num_registers))

    reg_w = 340
    reg_h = 280
    regs_per_row = 4
    n_rows = (num_registers + regs_per_row - 1) // regs_per_row

    # Title
    title = c << gf.components.text(text="TIER 3: PARKING REGISTERS", size=30, layer=LAYER_TEXT)
    title.move((reg_w, n_rows * reg_h + 40))

    # Create registers
    for i in range(num_registers):
        row = i // regs_per_row
        col = i % regs_per_row

        reg = c << parking_register(register_id=i)
        reg.move((col * reg_w, row * reg_h))

    # Address decoder
    decoder = c << gf.components.rectangle(size=(80, 150), layer=LAYER_METAL_PAD)
    decoder.move((-150, n_rows * reg_h / 2 - 75))
    dec_label = c << gf.components.text(text="5:32\nDEC", size=12, layer=LAYER_TEXT)
    dec_label.move((-140, n_rows * reg_h / 2 - 30))

    # Data buses
    in_bus = c << gf.components.rectangle(size=(5, n_rows * reg_h), layer=LAYER_WAVEGUIDE)
    in_bus.move((-60, 0))

    out_bus = c << gf.components.rectangle(size=(5, n_rows * reg_h), layer=LAYER_WAVEGUIDE)
    out_bus.move((regs_per_row * reg_w + 20, 0))

    # Power rails
    vdd = c << gf.components.rectangle(size=(regs_per_row * reg_w + 100, 8), layer=LAYER_METAL_PAD)
    vdd.move((-50, n_rows * reg_h + 15))
    vdd_label = c << gf.components.text(text="VDD", size=8, layer=LAYER_TEXT)
    vdd_label.move((-45, n_rows * reg_h + 18))

    gnd = c << gf.components.rectangle(size=(regs_per_row * reg_w + 100, 8), layer=LAYER_METAL_PAD)
    gnd.move((-50, -25))
    gnd_label = c << gf.components.text(text="GND", size=8, layer=LAYER_TEXT)
    gnd_label.move((-45, -22))

    # Specs
    specs = c << gf.components.text(
        text=f"{num_registers} reg x 81 trit | bistable | ~0mW standby",
        size=12,
        layer=LAYER_TEXT
    )
    specs.move((0, -50))

    # Ports
    c.add_port(name="data_in", center=(-70, n_rows * reg_h / 2),
               width=5, orientation=180, layer=LAYER_WAVEGUIDE)
    c.add_port(name="data_out", center=(regs_per_row * reg_w + 25, n_rows * reg_h / 2),
               width=5, orientation=0, layer=LAYER_WAVEGUIDE)
    c.add_port(name="addr", center=(-180, n_rows * reg_h / 2),
               width=50, orientation=180, layer=LAYER_METAL_PAD)

    return c


def generate_tier3_registers(
    num_registers: int = 32,
    output_path: Optional[str] = None
) -> Component:
    """Generate Tier 3 Parking Register File."""
    print(f"Generating Tier 3 Parking Register File...")
    print(f"  Registers: {num_registers}")
    print(f"  Trits per register: 81")
    print(f"  Total capacity: {num_registers * 81} trits")
    print(f"  Storage: Bistable (no refresh)")
    print(f"  Standby power: ~0 mW")

    component = tier3_register_file(num_registers=num_registers)

    if output_path:
        component.write_gds(output_path)
        print(f"  Saved to: {output_path}")

    return component


def main():
    """CLI for Tier 3 RAM generation."""
    print("=" * 60)
    print("  TERNARY TIER 3 RAM GENERATOR")
    print("  'Parking' Registers - Low-Power Bistable Storage")
    print("=" * 60)

    print("\nOptions:")
    print("  1. Generate 8-register file (P0-P7)")
    print("  2. Generate 16-register file (P0-P15)")
    print("  3. Generate 32-register file (P0-P31) [Full]")

    choice = input("\nSelect option [1-3]: ").strip()
    output_dir = "Research/data/gds"

    if choice == "1":
        generate_tier3_registers(8, f"{output_dir}/tier3_parking_registers_8reg.gds")
    elif choice == "2":
        generate_tier3_registers(16, f"{output_dir}/tier3_parking_registers_16reg.gds")
    elif choice == "3":
        generate_tier3_registers(32, f"{output_dir}/tier3_parking_registers_32reg.gds")
    else:
        print("Invalid option")


if __name__ == "__main__":
    main()
