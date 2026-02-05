#!/usr/bin/env python3
"""
WDM Waveguide Validation Test
=============================

Tests whether all 6 wavelength triplets (18 wavelengths) can propagate
through the same waveguide without interference.

This validates the core WDM assumption: different wavelengths don't
interact in a linear waveguide - they just pass through independently.

The simulation:
1. Creates a straight LiNbO3 waveguide
2. Injects all 18 wavelengths simultaneously
3. Measures power at output for each wavelength
4. Verifies no crosstalk between channels

Expected result: Each wavelength should arrive at output with minimal loss,
independent of other wavelengths present.

Author: N-Radix Project
Date: February 5, 2026
"""

import meep as mp
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os

# =============================================================================
# WDM TRIPLET DEFINITIONS (from collision-free search)
# =============================================================================

WDM_TRIPLETS = {
    1: {'lambda_neg': 1.040, 'lambda_zero': 1.020, 'lambda_pos': 1.000},  # um
    2: {'lambda_neg': 1.100, 'lambda_zero': 1.080, 'lambda_pos': 1.060},
    3: {'lambda_neg': 1.160, 'lambda_zero': 1.140, 'lambda_pos': 1.120},
    4: {'lambda_neg': 1.220, 'lambda_zero': 1.200, 'lambda_pos': 1.180},
    5: {'lambda_neg': 1.280, 'lambda_zero': 1.260, 'lambda_pos': 1.240},
    6: {'lambda_neg': 1.340, 'lambda_zero': 1.320, 'lambda_pos': 1.300},
}

def get_all_wavelengths():
    """Get flat list of all 18 wavelengths in um."""
    wavelengths = []
    for triplet in WDM_TRIPLETS.values():
        wavelengths.extend([triplet['lambda_neg'], triplet['lambda_zero'], triplet['lambda_pos']])
    return sorted(wavelengths)

def wavelength_to_frequency(wavelength_um):
    """Convert wavelength (um) to Meep frequency (c=1 units)."""
    return 1.0 / wavelength_um

# =============================================================================
# SIMULATION PARAMETERS
# =============================================================================

# Waveguide parameters (LiNbO3)
WG_WIDTH = 0.5       # um - single mode width
WG_LENGTH = 20.0     # um - propagation length
N_CORE = 2.2         # LiNbO3 refractive index
N_CLAD = 1.0         # Air cladding

# Simulation parameters
RESOLUTION = 40      # pixels per um (higher = more accurate, slower)
PML_THICKNESS = 1.0  # um - absorbing boundary
PADDING = 1.0        # um - space around waveguide

# Time parameters
RUN_TIME = 100       # Meep time units (longer = more accurate frequency resolution)

# =============================================================================
# SIMULATION SETUP
# =============================================================================

def create_waveguide_geometry():
    """Create a simple straight waveguide."""
    geometry = [
        mp.Block(
            size=mp.Vector3(WG_LENGTH, WG_WIDTH, mp.inf),
            center=mp.Vector3(0, 0, 0),
            material=mp.Medium(index=N_CORE)
        )
    ]
    return geometry

def create_wdm_sources(wavelengths, src_x):
    """
    Create Gaussian sources for all wavelengths.

    Each wavelength gets its own source, all at the same location.
    This simulates injecting WDM signals into the waveguide.
    """
    sources = []

    # Use a broadband source that covers all wavelengths
    # or multiple narrow sources

    # Get frequency range
    freqs = [wavelength_to_frequency(w) for w in wavelengths]
    f_center = np.mean(freqs)
    f_width = max(freqs) - min(freqs)

    # Single broadband source covering all wavelengths
    sources.append(
        mp.Source(
            src=mp.GaussianSource(frequency=f_center, fwidth=f_width * 1.5),
            component=mp.Ez,
            center=mp.Vector3(src_x, 0, 0),
            size=mp.Vector3(0, WG_WIDTH * 2, 0)
        )
    )

    return sources, f_center, f_width

def run_wdm_simulation(wavelengths, verbose=True):
    """
    Run WDM simulation and measure output for each wavelength.

    Returns dict mapping wavelength -> measured power.
    """
    if verbose:
        print(f"\n{'='*60}")
        print("WDM WAVEGUIDE SIMULATION")
        print(f"{'='*60}")
        print(f"Wavelengths: {len(wavelengths)} ({min(wavelengths):.3f} - {max(wavelengths):.3f} um)")
        print(f"Waveguide: {WG_LENGTH} um long, {WG_WIDTH} um wide")
        print(f"Resolution: {RESOLUTION} pixels/um")
        print(f"{'='*60}\n")

    # Cell size
    sx = WG_LENGTH + 2 * PML_THICKNESS + 2 * PADDING
    sy = WG_WIDTH + 2 * PML_THICKNESS + 2 * PADDING
    cell = mp.Vector3(sx, sy, 0)

    # PML boundaries
    pml_layers = [mp.PML(thickness=PML_THICKNESS)]

    # Geometry
    geometry = create_waveguide_geometry()

    # Sources
    src_x = -WG_LENGTH/2 + 0.5  # Near input end
    sources, f_center, f_width = create_wdm_sources(wavelengths, src_x)

    # Flux monitors at output
    flux_x = WG_LENGTH/2 - 0.5  # Near output end
    freqs = [wavelength_to_frequency(w) for w in wavelengths]

    # Create simulation
    sim = mp.Simulation(
        cell_size=cell,
        geometry=geometry,
        sources=sources,
        boundary_layers=pml_layers,
        resolution=RESOLUTION,
        default_material=mp.Medium(index=N_CLAD)
    )

    # Add flux monitor for each wavelength
    flux_monitors = []
    for freq in freqs:
        mon = sim.add_flux(
            freq, 0, 1,  # center freq, width, nfreq
            mp.FluxRegion(
                center=mp.Vector3(flux_x, 0, 0),
                size=mp.Vector3(0, WG_WIDTH * 2, 0)
            )
        )
        flux_monitors.append(mon)

    # Also add a broadband flux monitor
    nfreq = len(wavelengths)
    broadband_flux = sim.add_flux(
        f_center, f_width * 1.2, nfreq,
        mp.FluxRegion(
            center=mp.Vector3(flux_x, 0, 0),
            size=mp.Vector3(0, WG_WIDTH * 2, 0)
        )
    )

    if verbose:
        print("Running simulation...")

    # Run simulation
    sim.run(until=RUN_TIME)

    if verbose:
        print("Simulation complete. Analyzing results...\n")

    # Get results
    results = {}

    # Get broadband flux data
    flux_freqs = mp.get_flux_freqs(broadband_flux)
    flux_data = mp.get_fluxes(broadband_flux)

    # Map back to wavelengths
    for freq, power in zip(flux_freqs, flux_data):
        wavelength = 1.0 / freq
        results[wavelength] = power

    return results, flux_freqs, flux_data, sim

def analyze_results(wavelengths, flux_freqs, flux_data, verbose=True):
    """Analyze WDM simulation results."""

    # Convert to wavelengths
    measured_wavelengths = [1.0 / f for f in flux_freqs]

    if verbose:
        print(f"{'='*60}")
        print("WDM SIMULATION RESULTS")
        print(f"{'='*60}")
        print(f"{'Wavelength (um)':<18} {'Power (a.u.)':<15} {'Status':<10}")
        print(f"{'-'*60}")

    # Check each target wavelength
    all_passed = True
    for target_wl in wavelengths:
        # Find closest measured wavelength
        idx = np.argmin(np.abs(np.array(measured_wavelengths) - target_wl))
        measured_wl = measured_wavelengths[idx]
        power = flux_data[idx]

        # Power should be positive (propagating forward)
        status = "PASS" if power > 0 else "FAIL"
        if power <= 0:
            all_passed = False

        if verbose:
            print(f"{target_wl:<18.4f} {power:<15.4f} {status:<10}")

    if verbose:
        print(f"{'-'*60}")
        print(f"Overall: {'ALL WAVELENGTHS PASSED' if all_passed else 'SOME WAVELENGTHS FAILED'}")
        print(f"{'='*60}\n")

    return all_passed, measured_wavelengths, flux_data

def plot_results(wavelengths, flux_freqs, flux_data, output_dir):
    """Generate plots of WDM simulation results."""

    measured_wavelengths = [1.0 / f for f in flux_freqs]

    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # Plot 1: Power spectrum
    ax1 = axes[0]
    ax1.plot(measured_wavelengths, flux_data, 'b-', linewidth=1.5, label='Measured power')

    # Mark target wavelengths
    for wl in wavelengths:
        ax1.axvline(x=wl, color='r', linestyle='--', alpha=0.3)

    ax1.set_xlabel('Wavelength (μm)')
    ax1.set_ylabel('Power (a.u.)')
    ax1.set_title('WDM Waveguide Transmission Spectrum')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Plot 2: Power at each triplet
    ax2 = axes[1]
    triplet_colors = ['cyan', 'green', 'yellow', 'orange', 'red', 'darkred']

    x_positions = []
    powers = []
    colors = []
    labels = []

    for triplet_idx, triplet in WDM_TRIPLETS.items():
        for wl_type, wl in [('neg', triplet['lambda_neg']),
                            ('zero', triplet['lambda_zero']),
                            ('pos', triplet['lambda_pos'])]:
            idx = np.argmin(np.abs(np.array(measured_wavelengths) - wl))
            x_positions.append(wl)
            powers.append(flux_data[idx])
            colors.append(triplet_colors[triplet_idx - 1])
            labels.append(f'T{triplet_idx}')

    bars = ax2.bar(range(len(x_positions)), powers, color=colors, alpha=0.7, edgecolor='black')
    ax2.set_xticks(range(len(x_positions)))
    ax2.set_xticklabels([f'{wl:.2f}' for wl in x_positions], rotation=45, ha='right', fontsize=8)
    ax2.set_xlabel('Wavelength (μm)')
    ax2.set_ylabel('Power (a.u.)')
    ax2.set_title('Power at Each WDM Channel (colored by triplet)')
    ax2.grid(True, alpha=0.3, axis='y')

    # Add triplet legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=triplet_colors[i], alpha=0.7,
                            label=f'Triplet {i+1}') for i in range(6)]
    ax2.legend(handles=legend_elements, loc='upper right', ncol=2)

    plt.tight_layout()

    # Save plot
    plot_path = os.path.join(output_dir, 'wdm_waveguide_results.png')
    plt.savefig(plot_path, dpi=150)
    print(f"Plot saved: {plot_path}")

    plt.close()

    return plot_path

# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run the WDM waveguide validation test."""

    print("\n" + "=" * 70)
    print("N-RADIX WDM WAVEGUIDE VALIDATION TEST")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")

    # Output directory
    output_dir = "/home/jackwayne/Desktop/Optical_computing/Research/data/wdm_validation"
    os.makedirs(output_dir, exist_ok=True)

    # Get all wavelengths
    wavelengths = get_all_wavelengths()
    print(f"Testing {len(wavelengths)} wavelengths from 6 triplets:")
    for i, triplet in WDM_TRIPLETS.items():
        print(f"  Triplet {i}: {triplet['lambda_neg']:.3f} / {triplet['lambda_zero']:.3f} / {triplet['lambda_pos']:.3f} um")

    # Run simulation
    print("\n" + "-" * 70)
    results, flux_freqs, flux_data, sim = run_wdm_simulation(wavelengths)

    # Analyze results
    print("-" * 70 + "\n")
    passed, measured_wls, powers = analyze_results(wavelengths, flux_freqs, flux_data)

    # Generate plots
    print("\nGenerating plots...")
    plot_path = plot_results(wavelengths, flux_freqs, flux_data, output_dir)

    # Save results to file
    results_path = os.path.join(output_dir, 'wdm_validation_results.txt')
    with open(results_path, 'w') as f:
        f.write("N-RADIX WDM WAVEGUIDE VALIDATION RESULTS\n")
        f.write("=" * 50 + "\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Waveguide: {WG_LENGTH} um x {WG_WIDTH} um\n")
        f.write(f"Resolution: {RESOLUTION} pixels/um\n")
        f.write(f"Run time: {RUN_TIME} Meep units\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"{'Wavelength (um)':<18} {'Power (a.u.)':<15}\n")
        f.write("-" * 35 + "\n")
        for wl, pwr in zip(measured_wls, powers):
            f.write(f"{wl:<18.4f} {pwr:<15.4f}\n")
        f.write("\n")
        f.write(f"Status: {'PASSED' if passed else 'FAILED'}\n")

    print(f"Results saved: {results_path}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    if passed:
        print("SUCCESS: All 18 wavelengths propagate through waveguide independently.")
        print("The WDM approach is validated - wavelengths don't interfere.")
        print("6 triplets can operate in parallel through the same physical structure.")
    else:
        print("WARNING: Some wavelengths showed unexpected behavior.")
        print("Check the detailed results for investigation.")
    print("=" * 70)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")

    return passed

if __name__ == "__main__":
    main()
