#!/usr/bin/env python3
"""
C-Band WDM-Parallel Optical Systolic Array
===========================================

Wavelength-Division Multiplexed AI Accelerator using telecom C-band.

Key Innovation: Multiple parallel compute streams in the same waveguide,
sidestepping the radix economy through light's unique properties.

Target: Beat NVIDIA H100/B200 (2000-4500 TFLOPS)

Specs:
- C-band: 1530-1565nm (35nm bandwidth)
- 8-24 WDM channels, each carrying independent ternary computation
- 243×243 PE array per chip (59,049 PEs)
- 8 chips in circular "round table" arrangement
- 617 MHz Kerr clock (central)

Throughput:
- 8 channels:  2.3 PFLOPS  (beats H100)
- 24 channels: 7.0 PFLOPS  (beats B200)

Author: Wavelength-Division Ternary Optical Computer Project
"""

import gdsfactory as gf
from gdsfactory.component import Component
import numpy as np
import os

# Activate the generic PDK
gf.gpdk.PDK.activate()

# =============================================================================
# LAYER DEFINITIONS
# =============================================================================

LAYER_WG = (1, 0)        # Silicon waveguide
LAYER_RIDGE = (2, 0)     # Ridge waveguide (low-loss routing)
LAYER_HEATER = (3, 0)    # Thermo-optic phase shifters
LAYER_METAL = (4, 0)     # Metal routing
LAYER_LNOI = (11, 0)     # Lithium Niobate (nonlinear)
LAYER_ANNOT = (100, 0)   # Annotations

# =============================================================================
# C-BAND WAVELENGTH GRID
# =============================================================================

class CBandGrid:
    """ITU-T C-Band wavelength grid for WDM ternary encoding."""

    C_SPEED = 299792458  # m/s
    C_BAND_START = 1530e-9
    C_BAND_END = 1565e-9
    L_BAND_END = 1625e-9
    INTRA_CHANNEL_GHZ = 100
    INTER_CHANNEL_GHZ = 400

    def __init__(self, n_channels: int = 8, use_l_band: bool = False):
        self.n_channels = n_channels
        self.use_l_band = use_l_band
        self.channels = self._generate_grid()

    def _freq_to_wavelength(self, freq_hz: float) -> float:
        return self.C_SPEED / freq_hz

    def _wavelength_to_freq(self, wavelength_m: float) -> float:
        return self.C_SPEED / wavelength_m

    def _generate_grid(self) -> list:
        channels = []
        start_freq = self._wavelength_to_freq(self.C_BAND_START)
        end_freq = self._wavelength_to_freq(self.L_BAND_END if self.use_l_band else self.C_BAND_END)
        intra_hz = self.INTRA_CHANNEL_GHZ * 1e9
        inter_hz = self.INTER_CHANNEL_GHZ * 1e9
        channel_width = 2 * intra_hz + inter_hz
        current_freq = start_freq

        for ch in range(self.n_channels):
            if current_freq - channel_width < end_freq:
                break
            channel = {
                'id': ch,
                'lambda_plus':  self._freq_to_wavelength(current_freq) * 1e9,
                'lambda_zero':  self._freq_to_wavelength(current_freq - intra_hz) * 1e9,
                'lambda_minus': self._freq_to_wavelength(current_freq - 2 * intra_hz) * 1e9,
            }
            channels.append(channel)
            current_freq -= channel_width
        return channels

    def print_grid(self):
        print(f"\n{'='*70}")
        print(f"C-BAND WDM TERNARY GRID ({len(self.channels)} channels)")
        print(f"{'='*70}")
        print(f"{'Ch':>3} | {'L₊₁ (nm)':>10} | {'L₀ (nm)':>10} | {'L₋₁ (nm)':>10}")
        print(f"{'-'*50}")
        for ch in self.channels:
            print(f"{ch['id']:>3} | {ch['lambda_plus']:>10.3f} | {ch['lambda_zero']:>10.3f} | {ch['lambda_minus']:>10.3f}")
        print(f"{'='*70}\n")


# =============================================================================
# WDM PROCESSING ELEMENT
# =============================================================================

@gf.cell
def wdm_processing_element(
    n_channels: int = 8,
    pe_size: float = 50.0,
) -> Component:
    """
    WDM-Parallel Processing Element.
    Processes N wavelength channels simultaneously.
    """
    c = Component()

    total_height = n_channels * pe_size
    total_width = pe_size * 3

    # Boundary
    boundary = c << gf.components.rectangle(size=(total_width, total_height), layer=LAYER_ANNOT)
    boundary.dmove((-total_width/2, -total_height/2))

    # N parallel compute units (one per wavelength)
    for i in range(n_channels):
        y_pos = (i - n_channels/2 + 0.5) * pe_size

        # Sub-PE for this channel
        sub_pe = c << gf.components.rectangle(size=(pe_size * 0.9, pe_size * 0.7), layer=LAYER_WG)
        sub_pe.dmove((-pe_size * 0.45, y_pos - pe_size * 0.35))

        # Weight register (Kerr bistable)
        weight_reg = c << gf.components.ring(radius=5, width=0.5, layer=LAYER_LNOI)
        weight_reg.dmove((-pe_size/4, y_pos))

        # Accumulator
        acc = c << gf.components.ring(radius=8, width=0.5, layer=LAYER_WG)
        acc.dmove((pe_size/4, y_pos))

    # Label
    label = c << gf.components.text(text=f"WDM-PE\n{n_channels}ch", size=8, layer=LAYER_ANNOT)
    label.dmove((-20, total_height/2 - 25))

    # Ports
    c.add_port(name="in_h", center=(-total_width/2, 0), width=0.5, orientation=180, layer=LAYER_WG)
    c.add_port(name="out_h", center=(total_width/2, 0), width=0.5, orientation=0, layer=LAYER_WG)
    c.add_port(name="in_v", center=(0, total_height/2), width=0.5, orientation=90, layer=LAYER_WG)
    c.add_port(name="out_v", center=(0, -total_height/2), width=0.5, orientation=270, layer=LAYER_WG)

    return c


# =============================================================================
# WDM SYSTOLIC ARRAY
# =============================================================================

@gf.cell
def wdm_systolic_array(
    n_rows: int = 27,
    n_cols: int = 27,
    n_channels: int = 8,
    pe_pitch: float = 180.0,
    array_id: str = "0",
) -> Component:
    """Full WDM-Parallel Systolic Array."""
    c = Component()

    total_pes = n_rows * n_cols
    total_compute = total_pes * n_channels
    clock_mhz = 617
    throughput_tflops = total_compute * clock_mhz / 1e6

    # Simplified for large arrays - show corners and center
    if n_rows > 27:
        # Just show representative PEs for large arrays
        positions = [(0, 0), (0, n_cols-1), (n_rows-1, 0), (n_rows-1, n_cols-1),
                     (n_rows//2, n_cols//2)]
        for row, col in positions:
            pe = c << wdm_processing_element(n_channels=n_channels)
            pe.dmove((col * pe_pitch, -row * pe_pitch))

        # Placeholder text
        placeholder = c << gf.components.text(
            text=f"... {n_rows}x{n_cols} array ...\n{total_pes:,} PEs",
            size=50, layer=LAYER_ANNOT
        )
        placeholder.dmove((n_cols * pe_pitch / 2 - 200, -n_rows * pe_pitch / 2))
    else:
        # Full array for smaller sizes
        for row in range(n_rows):
            for col in range(n_cols):
                pe = c << wdm_processing_element(n_channels=n_channels)
                pe.dmove((col * pe_pitch, -row * pe_pitch))

    # Boundary
    array_width = n_cols * pe_pitch + 100
    array_height = n_rows * pe_pitch + 100
    boundary = c << gf.components.rectangle(size=(array_width, array_height), layer=LAYER_ANNOT)
    boundary.dmove((-50, -array_height + 50))

    # Title
    title = c << gf.components.text(
        text=f"WDM ARRAY {array_id}: {n_rows}x{n_cols} x {n_channels}L = {total_compute:,} units @ {throughput_tflops:.1f} TFLOPS",
        size=30, layer=LAYER_ANNOT
    )
    title.dmove((array_width/2 - 400, 100))

    return c


# =============================================================================
# WDM SUPER IOC
# =============================================================================

@gf.cell
def wdm_super_ioc(n_channels: int = 8, n_data_lanes: int = 81) -> Component:
    """WDM-Parallel Super IOC - handles all wavelength I/O."""
    c = Component()

    width, height = 3000, 2000

    # Boundary
    c << gf.components.rectangle(size=(width, height), layer=LAYER_ANNOT)

    # Sections
    sections = [
        (100, 600, f"FREQ COMB\n{n_channels*3}L"),
        (800, 500, f"AWG DEMUX\n{n_channels}ch"),
        (1400, 600, f"LiNbO3 MOD\n{n_data_lanes}x{n_channels}"),
        (2100, 500, f"AWG MUX\n{n_channels}->1"),
    ]

    for x, w, text in sections:
        sec = c << gf.components.rectangle(size=(w, height - 200), layer=LAYER_WG)
        sec.dmove((x, 100))
        lbl = c << gf.components.text(text=text, size=20, layer=LAYER_ANNOT)
        lbl.dmove((x + 50, height/2))

    # Title
    title = c << gf.components.text(
        text=f"WDM SUPER IOC: {n_channels}L x {n_data_lanes} lanes",
        size=25, layer=LAYER_ANNOT
    )
    title.dmove((width/2 - 300, height - 100))

    return c


# =============================================================================
# CIRCULAR BACKPLANE (ROUND TABLE)
# =============================================================================

@gf.cell(check_instances=False)
def circular_backplane(
    n_chips: int = 8,
    chip_size: float = 4000.0,
    kerr_radius: float = 500.0,
    n_wdm: int = 8,
    array_size: int = 243,
) -> Component:
    """
    Circular "Round Table" Backplane.
    Central Kerr clock surrounded by N AI accelerator chips.
    """
    c = Component()

    angle_per_chip = 360.0 / n_chips
    chip_radius = kerr_radius + chip_size + 500
    ioc_radius = chip_radius + chip_size/2 + 1000
    total_radius = ioc_radius + 1500

    # Backplane boundary
    c << gf.components.circle(radius=total_radius, layer=LAYER_ANNOT)

    # Central Kerr clock
    kerr = c << gf.components.circle(radius=kerr_radius, layer=LAYER_LNOI)
    kerr_label = c << gf.components.text(text="KERR\n617MHz", size=80, layer=LAYER_ANNOT)
    kerr_label.dmove((-120, -60))

    # Clock distribution ring
    c << gf.components.ring(radius=kerr_radius + 150, width=10, layer=LAYER_WG)

    # Data bus ring
    c << gf.components.ring(radius=chip_radius, width=20, layer=LAYER_RIDGE)

    # AI chips and IOCs
    for i in range(n_chips):
        angle_rad = np.radians(i * angle_per_chip + angle_per_chip/2)

        # Chip position
        chip_x = chip_radius * np.cos(angle_rad)
        chip_y = chip_radius * np.sin(angle_rad)

        # Chip
        chip = c << gf.components.rectangle(size=(chip_size, chip_size), layer=LAYER_WG)
        chip.dmove((chip_x - chip_size/2, chip_y - chip_size/2))

        # Chip label
        chip_label = c << gf.components.text(
            text=f"AI-{i}\n{array_size}^2\nx{n_wdm}L",
            size=60, layer=LAYER_ANNOT
        )
        chip_label.dmove((chip_x - 100, chip_y - 50))

        # Clock waveguide to chip
        clock_wg = c << gf.components.straight(length=chip_radius - kerr_radius - chip_size/2 - 200, width=5)
        clock_wg.drotate(np.degrees(angle_rad))
        clock_wg.dmove(((kerr_radius + 200) * np.cos(angle_rad), (kerr_radius + 200) * np.sin(angle_rad)))

        # IOC
        ioc_x = ioc_radius * np.cos(angle_rad)
        ioc_y = ioc_radius * np.sin(angle_rad)
        ioc = c << gf.components.rectangle(size=(1200, 800), layer=LAYER_HEATER)
        ioc.drotate(np.degrees(angle_rad))
        ioc.dmove((ioc_x, ioc_y))

        ioc_label = c << gf.components.text(text=f"IOC-{i}", size=40, layer=LAYER_ANNOT)
        ioc_label.dmove((ioc_x - 60, ioc_y - 15))

    # Calculate throughput
    pes_per_chip = array_size * array_size
    total_compute = n_chips * pes_per_chip * n_wdm
    tflops = total_compute * 617 / 1e6

    # Title
    title = c << gf.components.text(
        text=f"CIRCULAR BACKPLANE: {n_chips} chips x {n_wdm}L WDM",
        size=100, layer=LAYER_ANNOT
    )
    title.dmove((-500, total_radius - 400))

    # Throughput
    tp_label = c << gf.components.text(
        text=f"THROUGHPUT: {tflops/1000:.2f} PFLOPS",
        size=120, layer=LAYER_ANNOT
    )
    tp_label.dmove((-600, -total_radius + 200))

    return c


# =============================================================================
# MAIN
# =============================================================================

def main():
    output_dir = "/home/jackwayne/Desktop/Optical_computing/Research/data/gds"
    os.makedirs(output_dir, exist_ok=True)

    print("="*70)
    print("C-BAND WDM OPTICAL AI ACCELERATOR GENERATOR")
    print("="*70)

    # Print wavelength grid
    grid = CBandGrid(n_channels=8)
    grid.print_grid()

    print("GENERATING GDS FILES...")
    print("-"*70)

    # 1. Single WDM PE
    print("[1/5] WDM Processing Element (8 channels)...")
    pe = wdm_processing_element(n_channels=8)
    pe.write_gds(f"{output_dir}/wdm_pe_8ch.gds")
    print(f"      Saved: wdm_pe_8ch.gds")

    # 2. Small WDM array (9x9)
    print("[2/5] WDM Systolic Array 9x9...")
    array_9x9 = wdm_systolic_array(n_rows=9, n_cols=9, n_channels=8, array_id="9x9")
    array_9x9.write_gds(f"{output_dir}/wdm_systolic_9x9.gds")
    pes = 81 * 8
    print(f"      PEs: 81 x 8L = {pes} compute units, {pes*617/1e6:.1f} TFLOPS")

    # 3. Medium array (27x27)
    print("[3/5] WDM Systolic Array 27x27...")
    array_27x27 = wdm_systolic_array(n_rows=27, n_cols=27, n_channels=8, array_id="27x27")
    array_27x27.write_gds(f"{output_dir}/wdm_systolic_27x27_wdm.gds")
    pes = 729 * 8
    print(f"      PEs: 729 x 8L = {pes} compute units, {pes*617/1e6:.1f} TFLOPS")

    # 4. WDM Super IOC
    print("[4/5] WDM Super IOC...")
    ioc = wdm_super_ioc(n_channels=8, n_data_lanes=243)
    ioc.write_gds(f"{output_dir}/wdm_super_ioc.gds")
    print(f"      Saved: wdm_super_ioc.gds")

    # 5. Complete circular backplane
    print("[5/5] Complete 8-Chip Circular Backplane (243x243 x 8L)...")
    complete = circular_backplane(n_chips=8, n_wdm=8, array_size=243)
    complete.write_gds(f"{output_dir}/wdm_circular_backplane.gds")
    print(f"      Saved: wdm_circular_backplane.gds")

    # Final stats
    n_chips = 8
    array_size = 243
    n_wdm = 8
    total_pes = n_chips * array_size * array_size
    total_compute = total_pes * n_wdm
    tflops = total_compute * 617 / 1e6

    print("\n" + "="*70)
    print("FINAL SYSTEM SPECIFICATIONS")
    print("="*70)
    print(f"Architecture:     Circular 'Round Table' Backplane")
    print(f"AI Chips:         {n_chips}")
    print(f"Array per chip:   {array_size}x{array_size} = {array_size**2:,} PEs")
    print(f"WDM Channels:     {n_wdm} (C-band)")
    print(f"Total PEs:        {total_pes:,}")
    print(f"Compute Units:    {total_compute:,}")
    print(f"Clock:            617 MHz (Kerr self-pulsing)")
    print()
    print(f">>> THROUGHPUT:   {tflops:,.0f} TFLOPS = {tflops/1000:.2f} PFLOPS <<<")
    print()
    print("COMPARISON TO STATE-OF-THE-ART:")
    print(f"  NVIDIA H100:    2,000 TFLOPS  ->  WE ARE {tflops/2000:.1f}x FASTER")
    print(f"  NVIDIA B200:    4,500 TFLOPS  ->  WE ARE {tflops/4500:.2f}x FASTER")
    print(f"  Google TPU v5p:   459 TFLOPS  ->  WE ARE {tflops/459:.1f}x FASTER")
    print("="*70)

    # Tier comparison
    print("\n" + "="*70)
    print("SYSTEM TIERS")
    print("="*70)

    # Tier 1: Standard Computer
    print("\nTIER 1: STANDARD COMPUTER")
    print("  81-trit ALU + IOC + Backplane")
    print("  ~3.2 TFLOPS equivalent")

    # Tier 2: Home AI (current single chip)
    single_chip_compute = array_size * array_size * n_wdm
    single_chip_tflops = single_chip_compute * 617 / 1e6
    print(f"\nTIER 2: HOME AI")
    print(f"  {array_size}x{array_size} x {n_wdm} WDM = {single_chip_compute:,} compute units")
    print(f"  {single_chip_tflops:,.0f} TFLOPS (vs RTX 4090: 83 TFLOPS)")

    # Tier 3: Supercomputer (8 chips)
    print(f"\nTIER 3: SUPERCOMPUTER (Current Build)")
    print(f"  {n_chips} chips x {array_size}x{array_size} x {n_wdm} WDM")
    print(f"  {total_compute:,} compute units")
    print(f"  {tflops:,.0f} TFLOPS = {tflops/1000:.2f} PFLOPS")

    # Upgrades
    print("\n--- UPGRADE PATHS ---")
    tflops_24 = total_pes * 24 * 617 / 1e6
    print(f"\nSUPERCOMPUTER+ (C+L Band, 24 WDM):")
    print(f"  {tflops_24:,.0f} TFLOPS = {tflops_24/1000:.2f} PFLOPS")
    print(f"  vs H100: {tflops_24/2000:.1f}x faster")

    total_pes_729 = n_chips * 729 * 729
    tflops_729 = total_pes_729 * 24 * 617 / 1e6
    print(f"\nSUPERCOMPUTER++ (729x729 + 24 WDM):")
    print(f"  {tflops_729:,.0f} TFLOPS = {tflops_729/1000:.1f} PFLOPS")
    print(f"  vs H100: {tflops_729/2000:.0f}x faster")
    print("="*70)


if __name__ == "__main__":
    main()
