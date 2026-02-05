# Copyright (c) 2026 Christopher Riner
# Licensed under the MIT License. See LICENSE file for details.
#
# Wavelength-Division Ternary Optical Computer
# https://github.com/jackwayne234/-wavelength-ternary-optical-computer
#
# This file is part of an open source research project to develop a
# ternary optical computer using wavelength-division multiplexing.
# The research is documented in the paper published on Zenodo:
# DOI: 10.5281/zenodo.18437600

import os
import sys
import meep as mp
import numpy as np
import matplotlib.pyplot as plt

# Ensure we can import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_selector_simulation(voltage_on: bool = False):
    """
    Simulates an Optical Selector (Filter) using a Ring Resonator.
    Args:
        voltage_on (bool): If True, applies an index shift (electro-optic effect) to the ring.
    """

    # -------------------------------------------------------------------------
    # 1. Physical Parameters
    # -------------------------------------------------------------------------
    resolution = 30        # pixels/um (Need high res for gaps)
    
    # Material
    n_core = 2.2           # LiNbO3
    if voltage_on:
        # Pockels effect: Delta_n = -0.5 * n^3 * r * E
        # For simulation, we manually inject a realistic index shift
        # A shift of 0.01 is often enough to shift resonance by a linewidth
        n_core += 0.01
        print(">>> VOLTAGE APPLIED: Refractive Index shifted by +0.01")
    else:
        print(">>> VOLTAGE OFF: Standard Refractive Index")

    n_clad = 1.0           # Air
    
    # Geometry
    pad = 2                # Padding around waveguide
    dpml = 1.0             # PML thickness
    
    wg_width = 0.5
    gap = 0.15             # Coupling gap between bus and ring
    
    # Ring Design
    # We want resonance at wvl = 1.0 um (Input B from SFG)
    # L = 2*pi*R = m * (wvl/n_eff). Let's solve for R.
    # Assume n_eff ~ n_core for simple estimation (simulation will show actual peak)
    target_wvl = 1.0
    mode_num = 10 
    # R approx:
    r_ring = (mode_num * target_wvl) / (2 * np.pi * n_core)
    
    print(f"Designing Ring for lambda={target_wvl}um")
    print(f"Estimated Radius: {r_ring:.3f} um")
    
    # Simulation Domain
    cell_x = 2 * r_ring + 6
    cell_y = 2 * r_ring + 4
    cell_size = mp.Vector3(cell_x, cell_y, 0)
    
    # Sources
    fcen = 1 / target_wvl
    df = 0.2 * fcen  # Broad bandwidth to see the dip
    
    # -------------------------------------------------------------------------
    # 2. Geometry Setup
    # -------------------------------------------------------------------------
    material = mp.Medium(index=n_core)
    
    # Bus Waveguide
    geometry = [
        mp.Block(
            mp.Vector3(mp.inf, wg_width, mp.inf),
            center=mp.Vector3(0, -(r_ring + gap + wg_width), 0),
            material=material
        )
    ]
    
    # Ring Resonator
    # Create a ring by subtracting a smaller cylinder from a larger one
    geometry.append(
        mp.Cylinder(
            radius=r_ring + wg_width/2,
            height=mp.inf,
            axis=mp.Vector3(0, 0, 1),
            material=material
        )
    )
    geometry.append(
        mp.Cylinder(
            radius=r_ring - wg_width/2,
            height=mp.inf,
            axis=mp.Vector3(0, 0, 1),
            material=mp.Medium(index=n_clad)
        )
    )
    
    # -------------------------------------------------------------------------
    # 3. Simulation Config
    # -------------------------------------------------------------------------
    sources = [
        mp.Source(
            mp.GaussianSource(fcen, fwidth=df),
            component=mp.Ez,
            center=mp.Vector3(-0.5 * cell_x + dpml + 0.5, -(r_ring + gap + wg_width)),
            size=mp.Vector3(0, wg_width, 0)
        )
    ]
    
    pml_layers = [mp.PML(dpml)]
    
    sim = mp.Simulation(
        cell_size=cell_size,
        boundary_layers=pml_layers,
        geometry=geometry,
        sources=sources,
        resolution=resolution,
        filename_prefix='data/optical_selector'
    )
    
    # -------------------------------------------------------------------------
    # 4. Monitors
    # -------------------------------------------------------------------------
    # Transmission monitor at end of bus
    trans = sim.add_flux(
        fcen, df, 500,
        mp.FluxRegion(
            center=mp.Vector3(0.5 * cell_x - dpml - 0.5, -(r_ring + gap + wg_width)),
            size=mp.Vector3(0, 2*wg_width, 0)
        )
    )
    
    # -------------------------------------------------------------------------
    # 5. Run & Normalize
    # -------------------------------------------------------------------------
    # To get transmission, we usually need a normalization run (straight waveguide).
    # For this demo, we'll just look at the raw spectrum to find the dip.
    
    print("Starting Ring Resonator simulation...")
    sim.run(
        until_after_sources=mp.stop_when_fields_decayed(
            50, mp.Ez, 
            mp.Vector3(0.5 * cell_x - dpml - 0.5, -(r_ring + gap + wg_width)), 
            1e-3
        )
    )
    
    # -------------------------------------------------------------------------
    # 6. Analysis
    # -------------------------------------------------------------------------
    freqs = mp.get_flux_freqs(trans)
    flux = mp.get_fluxes(trans)
    wvls = [1/f for f in freqs]
    
    # Save plot
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    state_label = "ON" if voltage_on else "OFF"
    plot_path = os.path.join(base_dir, 'data', f"selector_spectrum_{state_label}.png")
    
    plt.figure()
    plt.plot(wvls, flux, 'b-', label=f'State: {state_label}')
    plt.axvline(x=target_wvl, color='r', linestyle='--', label=f'Target {target_wvl}um')
    plt.xlabel("Wavelength (um)")
    plt.ylabel("Transmission (a.u.)")
    plt.title(f"Optical Selector (Voltage {state_label})")
    plt.legend()
    plt.grid(True)
    plt.savefig(plot_path)
    print(f"Selector spectrum saved to: {plot_path}")

if __name__ == "__main__":
    print("\n--- SIMULATION 1: VOLTAGE OFF ---")
    run_selector_simulation(voltage_on=False)
    
    # Reset Meep structure/fields is handled by creating new sim object in function
    print("\n--- SIMULATION 2: VOLTAGE ON ---")
    run_selector_simulation(voltage_on=True)
