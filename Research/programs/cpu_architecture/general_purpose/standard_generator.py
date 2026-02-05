#!/usr/bin/env python3
"""
STANDARD COMPUTER Generator

Tier 1: General Purpose Ternary Computer
- 81x81 Systolic Array (6,561 PEs)
- ~4.0 TFLOPS equivalent
- Round Table: 1 Kerr + 1 SC + 1 SIOC + 1 IOA

Usage:
    python3 standard_generator.py [--output-dir PATH]
"""

import os
import sys
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optical_backplane import round_table_backplane
from optical_systolic_array import optical_systolic_array, processing_element
from super_ioc_module import super_ioc_module
from ioc_module import ioc_module


def generate_standard_computer(output_dir: str = None):
    """
    Generate all GDS files for Standard Computer configuration.

    Standard Computer specs:
    - 81x81 systolic array
    - Single SIOC for streaming
    - Single IOA for peripherals
    - Round Table MINIMUM config
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '..', 'data', 'gds', 'standard_computer'
        )

    os.makedirs(output_dir, exist_ok=True)

    print("=" * 70)
    print("STANDARD COMPUTER GENERATOR")
    print("Tier 1: General Purpose Ternary Computer")
    print("=" * 70)
    print(f"\nOutput directory: {output_dir}\n")

    # 1. Generate Round Table backplane (minimum config)
    print(">>> Generating Round Table Backplane (1 SC, 1 SIOC, 1 IOA)...")
    rt = round_table_backplane(n_supercomputers=1, n_siocs=1, n_ioas=1)
    rt.write_gds(os.path.join(output_dir, 'standard_round_table.gds'))
    bbox = rt.dbbox()
    print(f"    Size: {bbox.width():.0f} x {bbox.height():.0f} um")

    # 2. Generate 81x81 systolic array
    print(">>> Generating 81x81 Systolic Array (6,561 PEs)...")
    array = optical_systolic_array(array_size=81)
    array.write_gds(os.path.join(output_dir, 'standard_systolic_81x81.gds'))
    bbox = array.dbbox()
    print(f"    Size: {bbox.width():.0f} x {bbox.height():.0f} um")

    # 3. Generate single PE (for inspection)
    print(">>> Generating Single Processing Element...")
    pe = processing_element(pe_id=0)
    pe.write_gds(os.path.join(output_dir, 'standard_pe.gds'))

    # 4. Generate Super IOC
    print(">>> Generating Super IOC Module...")
    sioc = super_ioc_module(array_size=81)
    sioc.write_gds(os.path.join(output_dir, 'standard_super_ioc.gds'))
    bbox = sioc.dbbox()
    print(f"    Size: {bbox.width():.0f} x {bbox.height():.0f} um")

    # 5. Generate IOC (legacy, for compatibility)
    print(">>> Generating IOC Module...")
    ioc = ioc_module()
    ioc.write_gds(os.path.join(output_dir, 'standard_ioc.gds'))

    print("\n" + "=" * 70)
    print("STANDARD COMPUTER GENERATION COMPLETE")
    print("=" * 70)
    print(f"\nFiles generated in: {output_dir}")
    print("""
Specifications:
  - Systolic Array: 81x81 (6,561 PEs)
  - Peak Throughput: ~4.0 TFLOPS
  - Round Table: 1 Kerr + 1 SC + 1 SIOC + 1 IOA
  - Use Case: General ternary computing, research, education
""")

    return output_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Standard Computer GDS files")
    parser.add_argument('--output-dir', type=str, help="Output directory for GDS files")
    args = parser.parse_args()

    generate_standard_computer(args.output_dir)
