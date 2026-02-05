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

def find_resonance_and_animate():
    """
    1. Sweeps frequency to find the EXACT resonance dip of the ring.
    2. Updates source to that frequency.
    3. Generates two animations:
       - OFF (Resonance matched -> Light Trapped)
       - ON  (Resonance shifted -> Light Passed)
    """

    # -------------------------------------------------------------------------
    # 1. Setup & Parameters
    # -------------------------------------------------------------------------
    resolution = 25
    n_core_off = 2.2
    n_core_on = 2.21 # Shifted
    n_clad = 1.0
    
    # Geometry
    pad = 2
    dpml = 1.0
    wg_width = 0.5
    gap = 0.15 # Critical coupling gap
    
    # Initial Guess
    target_wvl_guess = 1.0
    mode_num = 10 
    r_ring = (mode_num * target_wvl_guess) / (2 * np.pi * n_core_off)
    
    cell_x = 2 * r_ring + 6
    cell_y = 2 * r_ring + 4
    cell_size = mp.Vector3(cell_x, cell_y, 0)
    
    # -------------------------------------------------------------------------
    # 2. Step 1: Broad Sweep to Find Resonance
    # -------------------------------------------------------------------------
    print(">>> PHASE 1: Finding Exact Resonance Dip...")
    
    fcen = 1 / target_wvl_guess
    df = 0.2 * fcen
    
    sources = [
        mp.Source(
            mp.GaussianSource(fcen, fwidth=df),
            component=mp.Ez,
            center=mp.Vector3(-0.5 * cell_x + dpml + 0.5, -(r_ring + gap + wg_width)),
            size=mp.Vector3(0, wg_width, 0)
        )
    ]
    
    # Geometry (OFF State)
    material_off = mp.Medium(index=n_core_off)
    geometry_off = [
        mp.Block(mp.Vector3(mp.inf, wg_width, mp.inf), center=mp.Vector3(0, -(r_ring + gap + wg_width), 0), material=material_off),
        mp.Cylinder(radius=r_ring + wg_width/2, height=mp.inf, axis=mp.Vector3(0, 0, 1), material=material_off),
        mp.Cylinder(radius=r_ring - wg_width/2, height=mp.inf, axis=mp.Vector3(0, 0, 1), material=mp.Medium(index=n_clad))
    ]
    
    sim = mp.Simulation(
        cell_size=cell_size,
        boundary_layers=[mp.PML(dpml)],
        geometry=geometry_off,
        sources=sources,
        resolution=resolution,
    )
    
    trans = sim.add_flux(
        fcen, df, 1000, # High res frequency points
        mp.FluxRegion(center=mp.Vector3(0.5 * cell_x - dpml - 0.5, -(r_ring + gap + wg_width)), size=mp.Vector3(0, 2*wg_width, 0))
    )
    
    sim.run(until_after_sources=mp.stop_when_fields_decayed(50, mp.Ez, mp.Vector3(0.5*cell_x - dpml - 0.5, -(r_ring + gap + wg_width)), 1e-3))
    
    freqs = mp.get_flux_freqs(trans)
    flux = mp.get_fluxes(trans)
    
    # Find the minimum flux (deepest dip)
    min_flux_idx = np.argmin(flux)
    res_freq = freqs[min_flux_idx]
    res_wvl = 1 / res_freq
    
    print(f"    Target Wavelength: {target_wvl_guess:.4f} um")
    print(f"    Found Dip at:      {res_wvl:.4f} um (Freq: {res_freq:.4f})")
    
    # -------------------------------------------------------------------------
    # 3. Step 2: Animate OFF (Blocked)
    # -------------------------------------------------------------------------
    print(f"\n>>> PHASE 2: Animating BLOCKED State (Wvl={res_wvl:.4f})...")
    create_animation(
        "selector_BLOCKED.mp4",
        res_freq,
        n_core_off,
        cell_size,
        geometry_off,
        r_ring, gap, wg_width, dpml
    )
    
    # -------------------------------------------------------------------------
    # 4. Step 3: Animate ON (Passed)
    # -------------------------------------------------------------------------
    print(f"\n>>> PHASE 3: Animating PASSED State (Voltage ON, Wvl={res_wvl:.4f})...")
    
    material_on = mp.Medium(index=n_core_on)
    geometry_on = [
        mp.Block(mp.Vector3(mp.inf, wg_width, mp.inf), center=mp.Vector3(0, -(r_ring + gap + wg_width), 0), material=material_on),
        mp.Cylinder(radius=r_ring + wg_width/2, height=mp.inf, axis=mp.Vector3(0, 0, 1), material=material_on),
        mp.Cylinder(radius=r_ring - wg_width/2, height=mp.inf, axis=mp.Vector3(0, 0, 1), material=mp.Medium(index=n_clad))
    ]
    
    create_animation(
        "selector_PASSED.mp4",
        res_freq, # Keep source SAME frequency
        n_core_on,
        cell_size,
        geometry_on,
        r_ring, gap, wg_width, dpml
    )

def create_animation(filename, freq, n_core, cell_size, geometry, r_ring, gap, wg_width, dpml):
    resolution = 25
    sources = [
        mp.Source(
            mp.ContinuousSource(frequency=freq), # CW source
            component=mp.Ez,
            center=mp.Vector3(-0.5 * cell_size.x + dpml + 0.5, -(r_ring + gap + wg_width)),
            size=mp.Vector3(0, wg_width, 0)
        )
    ]
    
    sim = mp.Simulation(
        cell_size=cell_size,
        boundary_layers=[mp.PML(dpml)],
        geometry=geometry,
        sources=sources,
        resolution=resolution,
    )
    
    sim.init_sim()
    
    anim = mp.Animate2D(
        sim, 
        fields=mp.Ez, 
        realtime=False, 
        normalize=True,
        eps_parameters={'contour': True, 'alpha': 0.2}
    )
    
    sim.run(mp.at_every(0.5, anim), until=60)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    video_path = os.path.join(base_dir, 'data', filename)
    
    # Fix PATH for ffmpeg
    env_bin = os.path.dirname(sys.executable)
    if env_bin not in os.environ["PATH"]:
        os.environ["PATH"] = env_bin + os.pathsep + os.environ["PATH"]
        
    anim.to_mp4(10, video_path)
    print(f"    Video saved: {video_path}")

if __name__ == "__main__":
    find_resonance_and_animate()
