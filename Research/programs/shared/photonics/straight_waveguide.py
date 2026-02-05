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

# Ensure we can import local modules if needed (standard practice)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_simulation():
    """
    Sets up and runs a simple 2D straight waveguide simulation.
    Saves HDF5 output to the /data directory.
    """
    
    # -------------------------------------------------------------------------
    # 1. Physical Parameters
    # -------------------------------------------------------------------------
    resolution = 20        # pixels/um
    
    # Geometry dimensions
    cell_x = 16            # Length of domain in X
    cell_y = 8             # Width of domain in Y
    pml_thickness = 1.0    # Thickness of PML layers
    
    # Waveguide
    wg_width = 0.5         # Width of silicon waveguide
    n_si = 3.4             # Refractive index of Silicon
    n_air = 1.0            # Refractive index of Air (Background)
    
    # Source
    wavelength = 1.55      # Central wavelength (telecom)
    fcen = 1 / wavelength  # Frequency
    df = 0.1 * fcen        # Bandwidth (for gaussian pulse)

    # -------------------------------------------------------------------------
    # 2. Geometry Setup
    # -------------------------------------------------------------------------
    cell_size = mp.Vector3(cell_x, cell_y, 0)
    
    # Define materials
    si_material = mp.Medium(index=n_si)
    
    # Create the waveguide (infinite in X)
    geometry = [
        mp.Block(
            mp.Vector3(mp.inf, wg_width, mp.inf),
            center=mp.Vector3(),
            material=si_material
        )
    ]
    
    # -------------------------------------------------------------------------
    # 3. Simulation Configuration
    # -------------------------------------------------------------------------
    # Sources: Gaussian pulse at the left side
    sources = [
        mp.Source(
            mp.GaussianSource(fcen, fwidth=df),
            component=mp.Ez,
            center=mp.Vector3(-0.5 * cell_x + pml_thickness + 0.5, 0),
            size=mp.Vector3(0, wg_width, 0) # Line source for efficiency
        )
    ]
    
    # Boundary Conditions (PML)
    pml_layers = [mp.PML(pml_thickness)]
    
    # Determine output prefix
    # Use relative path to avoid issues with Meep's path handling
    # Running from project root, so data is in 'data/'
    file_prefix = 'data/straight_waveguide'

    sim = mp.Simulation(
        cell_size=cell_size,
        boundary_layers=pml_layers,
        geometry=geometry,
        sources=sources,
        resolution=resolution,
        default_material=mp.Medium(index=n_air), # Background is air
        filename_prefix=file_prefix
    )

    # -------------------------------------------------------------------------
    # 4. Run Simulation
    # -------------------------------------------------------------------------
    print(f"Starting simulation...")
    print(f"Output will be saved to: {file_prefix}-*.h5")
    
    # Run until the fields have decayed sufficiently
    sim.run(
        mp.at_beginning(mp.output_epsilon), # Save geometry (epsilon)
        mp.at_end(mp.output_efield_z),      # Save Ez field at end
        until_after_sources=mp.stop_when_fields_decayed(50, mp.Ez, mp.Vector3(0.5*cell_x - pml_thickness - 0.5, 0), 1e-3)
    )
    
    print("Simulation complete.")

if __name__ == "__main__":
    run_simulation()
