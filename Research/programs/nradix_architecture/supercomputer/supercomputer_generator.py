#!/usr/bin/env python3
"""
SUPERCOMPUTER Generator

Tier 3: Datacenter-Class AI Accelerator
- 243x243 Systolic Array per chip (59,049 PEs)
- 8 Supercomputers in Round Table configuration
- 8 WDM Channels (upgradeable to 24)
- ~2.33 PFLOPS (1.2x NVIDIA H100)
- Round Table: 1 Kerr + 8 SC + 8 SIOC + 8 IOA

Usage:
    python3 supercomputer_generator.py [--output-dir PATH] [--wdm-channels 8|24]
"""

import os
import sys
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optical_backplane import round_table_backplane
from c_band_wdm_systolic import wdm_systolic_array, wdm_processing_element, wdm_super_ioc
from super_ioc_module import super_ioc_module


def generate_supercomputer(output_dir: str = None, wdm_channels: int = 8):
    """
    Generate all GDS files for Supercomputer configuration.

    Supercomputer specs:
    - 8 supercomputers in Round Table (MAXIMUM config)
    - Each SC has 243x243 systolic array
    - 8 or 24 WDM channels
    - Central Kerr clock (617 MHz)
    - ALL COMPONENTS EQUIDISTANT FROM KERR
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '..', 'data', 'gds', 'supercomputer'
        )

    os.makedirs(output_dir, exist_ok=True)
    wdm_channels = 24 if wdm_channels >= 24 else 8

    print("=" * 70)
    print("SUPERCOMPUTER GENERATOR")
    print("Tier 3: Datacenter-Class AI Accelerator")
    print("=" * 70)
    print(f"\nOutput directory: {output_dir}")
    print(f"WDM Channels: {wdm_channels}\n")

    print("████████████████████████████████████████████████████████████████████")
    print("█  CRITICAL: ALL COMPONENTS EQUIDISTANT FROM CENTRAL KERR CLOCK    █")
    print("████████████████████████████████████████████████████████████████████\n")

    # 1. Generate Round Table backplane (MAXIMUM config: 8 SC, 8 SIOC, 8 IOA)
    print(">>> Generating Round Table Backplane (8 SC, 8 SIOC, 8 IOA)...")
    rt = round_table_backplane(n_supercomputers=8, n_siocs=8, n_ioas=8)
    rt.write_gds(os.path.join(output_dir, 'supercomputer_round_table.gds'))
    bbox = rt.dbbox()
    print(f"    Size: {bbox.width():.0f} x {bbox.height():.0f} um")

    # 2. Generate WDM systolic array (representative size)
    print(f">>> Generating WDM Systolic Array (27x27 representative, {wdm_channels} WDM)...")
    try:
        array = wdm_systolic_array(array_size=27, n_wdm_channels=wdm_channels)
        array.write_gds(os.path.join(output_dir, f'supercomputer_wdm_systolic_{wdm_channels}ch.gds'))
        bbox = array.dbbox()
        print(f"    Size: {bbox.width():.0f} x {bbox.height():.0f} um")
        print("    (Full 243x243 × 8 chips scales proportionally)")
    except Exception as e:
        print(f"    Warning: Could not generate WDM array: {e}")

    # 3. Generate WDM Processing Element
    print(f">>> Generating WDM Processing Element ({wdm_channels} channels)...")
    try:
        pe = wdm_processing_element(n_wdm_channels=wdm_channels)
        pe.write_gds(os.path.join(output_dir, f'supercomputer_wdm_pe_{wdm_channels}ch.gds'))
    except Exception as e:
        print(f"    Warning: Could not generate WDM PE: {e}")

    # 4. Generate WDM Super IOC
    print(f">>> Generating WDM Super IOC Module ({wdm_channels} channels)...")
    try:
        sioc = wdm_super_ioc(array_size=243, n_wdm_channels=wdm_channels)
        sioc.write_gds(os.path.join(output_dir, f'supercomputer_wdm_sioc_{wdm_channels}ch.gds'))
        bbox = sioc.dbbox()
        print(f"    Size: {bbox.width():.0f} x {bbox.height():.0f} um")
    except Exception as e:
        print(f"    Warning: Could not generate WDM SIOC: {e}")
        # Fallback
        print("    Generating standard Super IOC as fallback...")
        sioc = super_ioc_module(array_size=243)
        sioc.write_gds(os.path.join(output_dir, 'supercomputer_super_ioc.gds'))

    # 5. Generate individual chip module (single supercomputer unit)
    print(">>> Generating Single Supercomputer Chip Module...")
    single_rt = round_table_backplane(n_supercomputers=1, n_siocs=1, n_ioas=1)
    single_rt.write_gds(os.path.join(output_dir, 'supercomputer_single_chip.gds'))

    print("\n" + "=" * 70)
    print("SUPERCOMPUTER GENERATION COMPLETE")
    print("=" * 70)
    print(f"\nFiles generated in: {output_dir}")

    # Calculate performance
    if wdm_channels == 8:
        pflops = 2.33
        vs_h100 = "1.2x"
    else:  # 24 channels
        pflops = 7.0
        vs_h100 = "3.5x"

    print(f"""
Specifications:
  - Systolic Array: 243x243 per chip (59,049 PEs each)
  - Total Chips: 8 (Round Table MAXIMUM)
  - WDM Channels: {wdm_channels} ({('C-band' if wdm_channels == 8 else 'C+L band')})
  - Peak Throughput: ~{pflops} PFLOPS ({vs_h100} NVIDIA H100)
  - Round Table: 1 Kerr + 8 SC + 8 SIOC + 8 IOA
  - Use Case: Datacenter AI, LLM training, HPC

Architecture:
  - Ring 0 (CENTER): Kerr Clock (617 MHz)
  - Ring 1: 8 Supercomputers (equidistant from Kerr)
  - Ring 2: 8 Super IOCs
  - Ring 3: 8 IOAs (Modular: Ethernet/Fiber/NVMe/etc.)

Operating Modes:
  1. 8 Independent LLMs (each SC has own SIOC/IOA)
  2. Unified System (all 8 SCs work together)
  3. Hybrid (some SIOCs for networking, some for storage)
""")

    return output_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Supercomputer GDS files")
    parser.add_argument('--output-dir', type=str, help="Output directory for GDS files")
    parser.add_argument('--wdm-channels', type=int, default=8, choices=[8, 24],
                        help="Number of WDM channels (8 for C-band, 24 for C+L band)")
    args = parser.parse_args()

    generate_supercomputer(args.output_dir, args.wdm_channels)
