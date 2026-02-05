#!/usr/bin/env python3
"""
HOME AI Generator

Tier 2: Consumer/Prosumer AI Accelerator
- 243x243 Systolic Array (59,049 PEs)
- 8 WDM Channels (C-band)
- ~291 TFLOPS (3.5x RTX 4090)
- Round Table: 1 Kerr + 1-4 SC + 1-2 SIOC + 1-2 IOA

Usage:
    python3 home_ai_generator.py [--output-dir PATH] [--num-sc 1-4]
"""

import os
import sys
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optical_backplane import round_table_backplane
from c_band_wdm_systolic import wdm_systolic_array, wdm_processing_element, wdm_super_ioc
from super_ioc_module import super_ioc_module


def generate_home_ai(output_dir: str = None, num_sc: int = 1):
    """
    Generate all GDS files for Home AI configuration.

    Home AI specs:
    - 243x243 systolic array with 8 WDM channels
    - 1-4 supercomputers in Round Table config
    - ~291 TFLOPS peak (single SC)
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '..', 'data', 'gds', 'home_ai'
        )

    os.makedirs(output_dir, exist_ok=True)
    num_sc = max(1, min(4, num_sc))  # Clamp to 1-4

    print("=" * 70)
    print("HOME AI GENERATOR")
    print("Tier 2: Consumer/Prosumer AI Accelerator")
    print("=" * 70)
    print(f"\nOutput directory: {output_dir}")
    print(f"Supercomputer count: {num_sc}\n")

    # Calculate IOC/IOA count based on SC count
    num_sioc = max(1, num_sc // 2)
    num_ioa = num_sioc

    # 1. Generate Round Table backplane
    print(f">>> Generating Round Table Backplane ({num_sc} SC, {num_sioc} SIOC, {num_ioa} IOA)...")
    rt = round_table_backplane(n_supercomputers=num_sc, n_siocs=num_sioc, n_ioas=num_ioa)
    rt.write_gds(os.path.join(output_dir, f'home_ai_round_table_{num_sc}sc.gds'))
    bbox = rt.dbbox()
    print(f"    Size: {bbox.width():.0f} x {bbox.height():.0f} um")

    # 2. Generate WDM systolic array (243x243 with 8 WDM channels)
    # Note: For file size, we generate a smaller representative array
    print(">>> Generating WDM Systolic Array (27x27 representative, 8 WDM)...")
    try:
        array = wdm_systolic_array(array_size=27, n_wdm_channels=8)
        array.write_gds(os.path.join(output_dir, 'home_ai_wdm_systolic_27x27.gds'))
        bbox = array.dbbox()
        print(f"    Size: {bbox.width():.0f} x {bbox.height():.0f} um")
        print("    (Full 243x243 scales proportionally)")
    except Exception as e:
        print(f"    Warning: Could not generate WDM array: {e}")

    # 3. Generate WDM Processing Element
    print(">>> Generating WDM Processing Element (8 channels)...")
    try:
        pe = wdm_processing_element(n_wdm_channels=8)
        pe.write_gds(os.path.join(output_dir, 'home_ai_wdm_pe.gds'))
    except Exception as e:
        print(f"    Warning: Could not generate WDM PE: {e}")

    # 4. Generate WDM Super IOC
    print(">>> Generating WDM Super IOC Module...")
    try:
        sioc = wdm_super_ioc(array_size=243, n_wdm_channels=8)
        sioc.write_gds(os.path.join(output_dir, 'home_ai_wdm_super_ioc.gds'))
        bbox = sioc.dbbox()
        print(f"    Size: {bbox.width():.0f} x {bbox.height():.0f} um")
    except Exception as e:
        print(f"    Warning: Could not generate WDM SIOC: {e}")
        # Fallback to regular super IOC
        print("    Generating standard Super IOC as fallback...")
        sioc = super_ioc_module(array_size=243)
        sioc.write_gds(os.path.join(output_dir, 'home_ai_super_ioc.gds'))

    print("\n" + "=" * 70)
    print("HOME AI GENERATION COMPLETE")
    print("=" * 70)
    print(f"\nFiles generated in: {output_dir}")

    tflops = 291 * num_sc
    print(f"""
Specifications:
  - Systolic Array: 243x243 (59,049 PEs per SC)
  - WDM Channels: 8 (C-band, 1530-1565nm)
  - Supercomputers: {num_sc}
  - Peak Throughput: ~{tflops} TFLOPS ({tflops/83:.1f}x RTX 4090)
  - Round Table: 1 Kerr + {num_sc} SC + {num_sioc} SIOC + {num_ioa} IOA
  - Use Case: Local LLM inference, edge AI, home server
""")

    return output_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Home AI GDS files")
    parser.add_argument('--output-dir', type=str, help="Output directory for GDS files")
    parser.add_argument('--num-sc', type=int, default=1, help="Number of supercomputers (1-4)")
    args = parser.parse_args()

    generate_home_ai(args.output_dir, args.num_sc)
