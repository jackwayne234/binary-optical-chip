import os
import sys
import meep as mp
import numpy as np
import matplotlib.pyplot as plt

# Ensure we can import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_y_junction_simulation():
    """
    Simulates a photonic Y-junction acting as a combiner.
    Merges two input waveguides (Red and Blue) into a single output waveguide.
    """

    # -------------------------------------------------------------------------
    # 1. Physical Parameters
    # -------------------------------------------------------------------------
    resolution = 25        # pixels/um
    
    # Dimensions
    cell_x = 12            # Length
    cell_y = 6             # Width
    pml_thickness = 1.0
    
    # Waveguide
    wg_width = 0.5         
    n_core = 3.4           # Silicon
    n_clad = 1.0           # Air/Oxide
    
    # Y-Junction Geometry Parameters
    # We use two bent waveguides merging into one
    y_branch_length = 4.0  # Length of the splitting section
    y_branch_sep = 2.0     # Separation at input
    
    # Sources
    wvl_red = 1.55         # "Red" (Logic -1)
    wvl_blue = 1.0         # "Blue" (Logic 1)
    
    fcen_red = 1 / wvl_red
    fcen_blue = 1 / wvl_blue
    
    # Pulse
    df = 0.1 * fcen_red

    # -------------------------------------------------------------------------
    # 2. Geometry Setup
    # -------------------------------------------------------------------------
    cell_size = mp.Vector3(cell_x, cell_y, 0)
    
    material = mp.Medium(index=n_core)
    
    # We'll construct the Y-junction using three blocks:
    # 1. Straight output waveguide (right side)
    # 2. Upper bent input arm
    # 3. Lower bent input arm
    
    geometry = []
    
    # 1. Output Waveguide (Straight part on the right)
    # Starts from x=0 to x=cell_x/2
    geometry.append(
        mp.Block(
            mp.Vector3(cell_x/2 + pml_thickness, wg_width, mp.inf),
            center=mp.Vector3(cell_x/4, 0, 0),
            material=material
        )
    )
    
    # For the branches, we can use simple rotated blocks for a "V" shape
    # or define a custom prism. For simplicity in Meep, rotated blocks work well.
    
    # Angle of branches
    # tan(theta) = (y_branch_sep/2) / y_branch_length
    angle_rad = np.arctan((y_branch_sep/2) / y_branch_length)
    length_arm = np.sqrt((y_branch_sep/2)**2 + y_branch_length**2) + pml_thickness
    
    # 2. Upper Arm (Input 1)
    geometry.append(
        mp.Block(
            mp.Vector3(length_arm, wg_width, mp.inf),
            center=mp.Vector3(-y_branch_length/2, y_branch_sep/4, 0),
            e1=mp.Vector3(np.cos(angle_rad), -np.sin(angle_rad), 0), # Rotated down towards center
            e2=mp.Vector3(np.sin(angle_rad), np.cos(angle_rad), 0),
            material=material
        )
    )
    
    # 3. Lower Arm (Input 2)
    geometry.append(
        mp.Block(
            mp.Vector3(length_arm, wg_width, mp.inf),
            center=mp.Vector3(-y_branch_length/2, -y_branch_sep/4, 0),
            e1=mp.Vector3(np.cos(angle_rad), np.sin(angle_rad), 0), # Rotated up towards center
            e2=mp.Vector3(-np.sin(angle_rad), np.cos(angle_rad), 0),
            material=material
        )
    )
    
    # -------------------------------------------------------------------------
    # 3. Simulation Config
    # -------------------------------------------------------------------------
    # Source 1: Upper Arm (Blue)
    # Calculate position based on rotation
    src_x = -0.5*cell_x + pml_thickness + 0.5
    # Linear interpolation for Y height at this X
    # Start of branch is at x = -y_branch_length (relative to center 0?)
    # Our branch ends at x=0. It starts approx at -y_branch_length.
    # We place source at left edge.
    
    sources = [
        mp.Source(
            mp.GaussianSource(fcen_blue, fwidth=df),
            component=mp.Ez,
            center=mp.Vector3(-y_branch_length, y_branch_sep/2, 0),
            size=mp.Vector3(0, wg_width, 0)
        ),
        mp.Source(
            mp.GaussianSource(fcen_red, fwidth=df),
            component=mp.Ez,
            center=mp.Vector3(-y_branch_length, -y_branch_sep/2, 0),
            size=mp.Vector3(0, wg_width, 0)
        )
    ]
    
    pml_layers = [mp.PML(pml_thickness)]
    
    sim = mp.Simulation(
        cell_size=cell_size,
        boundary_layers=pml_layers,
        geometry=geometry,
        sources=sources,
        resolution=resolution,
        filename_prefix='data/y_junction'
    )
    
    # -------------------------------------------------------------------------
    # 4. Monitors
    # -------------------------------------------------------------------------
    # Monitor at Output
    fcen_mon = (fcen_red + fcen_blue)/2
    df_mon = abs(fcen_blue - fcen_red) + 0.1
    
    trans = sim.add_flux(
        fcen_mon, df_mon, 500,
        mp.FluxRegion(
            center=mp.Vector3(0.5 * cell_x - pml_thickness - 0.5, 0),
            size=mp.Vector3(0, 2*wg_width, 0)
        )
    )
    
    # -------------------------------------------------------------------------
    # 5. Run
    # -------------------------------------------------------------------------
    print("Starting Y-Junction simulation...")
    
    # Save geometry to verify V-shape
    sim.plot2D(output_plane=mp.Volume(center=mp.Vector3(), size=mp.Vector3(cell_x, cell_y)))
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    geo_path = os.path.join(base_dir, 'data', "y_junction_geometry.png")
    plt.savefig(geo_path)
    print(f"Geometry saved to: {geo_path}")
    
    sim.run(until_after_sources=mp.stop_when_fields_decayed(
        50, mp.Ez, 
        mp.Vector3(0.5 * cell_x - pml_thickness - 0.5, 0), 
        1e-3)
    )
    
    # -------------------------------------------------------------------------
    # 6. Analysis
    # -------------------------------------------------------------------------
    freqs = mp.get_flux_freqs(trans)
    flux = mp.get_fluxes(trans)
    wvls = [1/f for f in freqs]
    
    plot_path = os.path.join(base_dir, 'data', "y_junction_spectrum.png")
    
    plt.figure()
    plt.plot(wvls, flux, 'k-', label='Output Flux')
    plt.axvline(x=wvl_red, color='r', linestyle='--', label='Input Red')
    plt.axvline(x=wvl_blue, color='b', linestyle='--', label='Input Blue')
    plt.xlabel("Wavelength (um)")
    plt.ylabel("Flux (a.u.)")
    plt.title("Y-Junction Combiner Output")
    plt.legend()
    plt.grid(True)
    plt.savefig(plot_path)
    print(f"Spectrum saved to: {plot_path}")

if __name__ == "__main__":
    run_y_junction_simulation()
