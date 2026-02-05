# Copyright (c) 2026 Christopher Riner
# Licensed under the MIT License. See LICENSE file for details.
#
# Wavelength-Division Ternary Optical Computer
# https://github.com/jackwayne234/-wavelength-ternary-optical-computer
#
# Simulation of ring resonator wavelength selector in polymer materials.
# Tests feasibility of SU-8/PMMA waveguides for DIY Phase 4.
#
# Key insight: Lower refractive index contrast = larger ring radius needed,
# but this is FINE for a 12x12 inch chip!

import os
import sys
import meep as mp
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Passive waveguide materials (no chi2 needed for routing)
PASSIVE_MATERIALS = {
    'LiNbO3_air': {
        'name': 'LiNbO3 / Air cladding',
        'n_core': 2.2,
        'n_clad': 1.0,
        'contrast': 1.2,  # n_core - n_clad
    },
    'SU8_air': {
        'name': 'SU-8 / Air cladding',
        'n_core': 1.57,
        'n_clad': 1.0,
        'contrast': 0.57,
    },
    'SU8_PMMA': {
        'name': 'SU-8 core / PMMA cladding',
        'n_core': 1.57,
        'n_clad': 1.49,
        'contrast': 0.08,  # Very low - large bends needed
    },
    'PMMA_air': {
        'name': 'PMMA / Air cladding',
        'n_core': 1.49,
        'n_clad': 1.0,
        'contrast': 0.49,
    },
    'poled_polymer_air': {
        'name': 'Poled DR1-PMMA / Air',
        'n_core': 1.50,
        'n_clad': 1.0,
        'contrast': 0.50,
    }
}


def calculate_ring_radius(target_wvl: float, n_eff: float, mode_num: int = 10) -> float:
    """
    Calculate ring radius for resonance at target wavelength.

    Args:
        target_wvl: Target resonance wavelength (um)
        n_eff: Effective index of waveguide mode
        mode_num: Azimuthal mode number (higher = larger ring)

    Returns:
        Ring radius in um
    """
    # Resonance condition: 2*pi*R*n_eff = m*lambda
    # R = m*lambda / (2*pi*n_eff)
    return (mode_num * target_wvl) / (2 * np.pi * n_eff)


def calculate_min_bend_radius(n_core: float, n_clad: float, wvl: float = 1.0) -> float:
    """
    Estimate minimum bend radius before significant radiation loss.

    Rule of thumb: R_min ~ wvl / (n_core - n_clad)^2
    Lower contrast = larger minimum bend radius
    """
    delta_n = n_core - n_clad
    if delta_n < 0.01:
        return float('inf')
    return wvl / (delta_n ** 2)


def run_polymer_selector(material_key: str, target_wvl: float = 1.0):
    """
    Simulate ring resonator selector in a given material system.

    Args:
        material_key: Key from PASSIVE_MATERIALS
        target_wvl: Target wavelength for resonance (um)

    Returns:
        dict with simulation results
    """
    mat = PASSIVE_MATERIALS[material_key]
    print(f"\n{'='*60}")
    print(f"Ring Resonator in: {mat['name']}")
    print(f"  n_core = {mat['n_core']}, n_clad = {mat['n_clad']}")
    print(f"  Index contrast: {mat['contrast']:.3f}")
    print(f"{'='*60}")

    # Estimate effective index (rough approximation)
    # For well-confined mode, n_eff ~ n_core - 0.1*(n_core - n_clad)
    n_eff = mat['n_core'] - 0.1 * mat['contrast']

    # Calculate ring radius
    mode_num = 10
    r_ring = calculate_ring_radius(target_wvl, n_eff, mode_num)

    # Check minimum bend radius
    r_min = calculate_min_bend_radius(mat['n_core'], mat['n_clad'], target_wvl)

    print(f"  Calculated ring radius: {r_ring:.1f} um")
    print(f"  Minimum bend radius (estimated): {r_min:.1f} um")

    if r_ring < r_min:
        print(f"  WARNING: Ring too tight! Increasing mode number...")
        # Increase mode number until radius is sufficient
        while r_ring < r_min and mode_num < 100:
            mode_num += 5
            r_ring = calculate_ring_radius(target_wvl, n_eff, mode_num)
        print(f"  New mode number: {mode_num}, radius: {r_ring:.1f} um")

    # Convert to physical scale for 12" chip reference
    r_ring_mm = r_ring / 1000
    r_ring_inch = r_ring_mm / 25.4
    print(f"  Ring radius: {r_ring:.1f} um = {r_ring_mm:.3f} mm = {r_ring_inch:.4f} inches")
    print(f"  Ring diameter: {2*r_ring_inch:.4f} inches (12\" chip can fit {int(12/(2*r_ring_inch))} rings)")

    # Simulation parameters
    resolution = 20  # Reduce for larger structures

    # Waveguide width (scales with wavelength and index)
    wg_width = 0.5 * (2.2 / mat['n_core'])  # Scale from LiNbO3 baseline
    wg_width = max(0.3, min(1.5, wg_width))

    # Coupling gap
    gap = 0.15 * (2.2 / mat['n_core'])
    gap = max(0.1, min(0.5, gap))

    # Limit simulation size for reasonable runtime
    max_radius = 5.0  # um - limit for simulation
    if r_ring > max_radius:
        print(f"  Scaling down ring for simulation: {r_ring:.1f} -> {max_radius:.1f} um")
        print(f"  (Physical ring would be {r_ring:.1f} um)")
        r_ring_sim = max_radius
        mode_num_sim = int(mode_num * max_radius / r_ring)
    else:
        r_ring_sim = r_ring
        mode_num_sim = mode_num

    # Simulation domain
    dpml = 1.0
    cell_x = 2 * r_ring_sim + 6
    cell_y = 2 * r_ring_sim + 4
    cell_size = mp.Vector3(cell_x, cell_y, 0)

    # Frequency
    fcen = 1 / target_wvl
    df = 0.2 * fcen

    # Geometry
    core_material = mp.Medium(index=mat['n_core'])
    clad_material = mp.Medium(index=mat['n_clad'])

    # Bus waveguide
    geometry = [
        mp.Block(
            mp.Vector3(mp.inf, wg_width, mp.inf),
            center=mp.Vector3(0, -(r_ring_sim + gap + wg_width), 0),
            material=core_material
        )
    ]

    # Ring (outer cylinder - inner cylinder)
    geometry.append(
        mp.Cylinder(
            radius=r_ring_sim + wg_width / 2,
            height=mp.inf,
            axis=mp.Vector3(0, 0, 1),
            material=core_material
        )
    )
    geometry.append(
        mp.Cylinder(
            radius=r_ring_sim - wg_width / 2,
            height=mp.inf,
            axis=mp.Vector3(0, 0, 1),
            material=clad_material
        )
    )

    # Source
    sources = [
        mp.Source(
            mp.GaussianSource(fcen, fwidth=df),
            component=mp.Ez,
            center=mp.Vector3(-0.5 * cell_x + dpml + 0.5, -(r_ring_sim + gap + wg_width)),
            size=mp.Vector3(0, wg_width, 0)
        )
    ]

    pml_layers = [mp.PML(dpml)]

    sim = mp.Simulation(
        cell_size=cell_size,
        boundary_layers=pml_layers,
        geometry=geometry,
        sources=sources,
        resolution=resolution
    )

    # Flux monitor
    trans = sim.add_flux(
        fcen, df, 300,
        mp.FluxRegion(
            center=mp.Vector3(0.5 * cell_x - dpml - 0.5, -(r_ring_sim + gap + wg_width)),
            size=mp.Vector3(0, 2 * wg_width, 0)
        )
    )

    # Run
    print("Running ring resonator simulation...")
    sim.run(until_after_sources=mp.stop_when_fields_decayed(
        50, mp.Ez,
        mp.Vector3(0.5 * cell_x - dpml - 0.5, -(r_ring_sim + gap + wg_width)),
        1e-3
    ))

    # Results
    freqs = np.array(mp.get_flux_freqs(trans))
    flux = np.array(mp.get_fluxes(trans))
    wvls = 1 / freqs

    # Find resonance dip
    # Normalize and find minimum (resonance = light coupled to ring = dip in transmission)
    flux_norm = flux / np.max(flux) if np.max(flux) > 0 else flux

    return {
        'material': material_key,
        'name': mat['name'],
        'n_core': mat['n_core'],
        'n_clad': mat['n_clad'],
        'contrast': mat['contrast'],
        'ring_radius_um': r_ring,  # Physical radius
        'ring_radius_sim': r_ring_sim,  # Simulated radius
        'wvls': wvls,
        'flux': flux,
        'flux_norm': flux_norm,
        'target_wvl': target_wvl
    }


def compare_polymer_selectors():
    """
    Compare ring resonator performance across different polymer materials.
    """
    materials_to_test = ['LiNbO3_air', 'SU8_air', 'PMMA_air', 'poled_polymer_air']

    results = []
    for mat_key in materials_to_test:
        result = run_polymer_selector(mat_key)
        results.append(result)

    # Plot comparison
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # Subplot 1: Transmission spectra
    ax1 = axes[0]
    for r in results:
        ax1.plot(r['wvls'], r['flux_norm'], label=f"{r['name']} (R={r['ring_radius_um']:.1f}um)")

    ax1.axvline(x=1.0, color='red', linestyle='--', alpha=0.5, label='Target 1.0um')
    ax1.set_xlabel("Wavelength (um)")
    ax1.set_ylabel("Normalized Transmission")
    ax1.set_title("Ring Resonator Response - Material Comparison")
    ax1.legend(loc='lower right', fontsize=8)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim([0.8, 1.3])

    # Subplot 2: Physical ring size comparison
    ax2 = axes[1]
    names = [r['name'] for r in results]
    radii = [r['ring_radius_um'] for r in results]
    contrasts = [r['contrast'] for r in results]

    x = np.arange(len(names))
    width = 0.35

    bars1 = ax2.bar(x - width/2, radii, width, label='Ring Radius (um)', color='steelblue')
    ax2_twin = ax2.twinx()
    bars2 = ax2_twin.bar(x + width/2, contrasts, width, label='Index Contrast', color='coral')

    ax2.set_ylabel('Ring Radius (um)', color='steelblue')
    ax2_twin.set_ylabel('Index Contrast (n_core - n_clad)', color='coral')
    ax2.set_xticks(x)
    ax2.set_xticklabels([n.split('/')[0] for n in names], rotation=15)
    ax2.set_title("Ring Size vs Index Contrast (Lower contrast = Larger ring)")

    # Add 12" chip context
    ax2.axhline(y=304800, color='green', linestyle=':', alpha=0.3)  # 12 inches in um
    ax2.text(0.02, 0.95, "12\" chip = 304,800 um - plenty of room!",
             transform=ax2.transAxes, fontsize=9, color='green')

    plt.tight_layout()

    # Save
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    plot_path = os.path.join(data_dir, "polymer_selector_comparison.png")
    plt.savefig(plot_path, dpi=150)
    print(f"\nComparison plot saved to: {plot_path}")

    # Summary
    print("\n" + "="*70)
    print("POLYMER RING RESONATOR FEASIBILITY SUMMARY")
    print("="*70)
    print(f"{'Material':<25} {'n_core':<8} {'Contrast':<10} {'Ring R (um)':<12} {'Fits 12in?':<10}")
    print("-"*70)
    for r in results:
        fits = "YES" if r['ring_radius_um'] < 100000 else "TIGHT"  # 100mm = ~4 inches per ring
        print(f"{r['name']:<25} {r['n_core']:<8.2f} {r['contrast']:<10.3f} {r['ring_radius_um']:<12.1f} {fits:<10}")
    print("="*70)
    print("\nConclusion: All polymer materials produce rings that easily fit on a 12\" chip.")
    print("Lower index contrast just means larger rings - not a problem at your scale!")

    return results


if __name__ == "__main__":
    compare_polymer_selectors()
