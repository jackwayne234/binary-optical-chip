import os
import sys
import meep as mp
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation

# Ensure we can import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_selector_animation():
    """
    Creates an animation of the Optical Selector in the "ON" state.
    Shows the field propagating through the ring and passing to the output.
    """

    # -------------------------------------------------------------------------
    # 1. Physical Parameters
    # -------------------------------------------------------------------------
    resolution = 25        # slightly lower res for speed in animation
    
    # Material
    n_core = 2.21          # ON state (2.2 + 0.01)
    n_clad = 1.0           # Air
    
    # Geometry
    pad = 2
    dpml = 1.0
    wg_width = 0.5
    gap = 0.15
    
    target_wvl = 1.0
    fcen = 1 / target_wvl
    df = 0.1 * fcen
    
    # Ring Design
    mode_num = 10 
    r_ring = (mode_num * target_wvl) / (2 * np.pi * 2.2) # approx base radius
    
    cell_x = 2 * r_ring + 6
    cell_y = 2 * r_ring + 4
    cell_size = mp.Vector3(cell_x, cell_y, 0)
    
    # -------------------------------------------------------------------------
    # 2. Geometry Setup
    # -------------------------------------------------------------------------
    material = mp.Medium(index=n_core)
    
    geometry = [
        mp.Block(
            mp.Vector3(mp.inf, wg_width, mp.inf),
            center=mp.Vector3(0, -(r_ring + gap + wg_width), 0),
            material=material
        ),
        mp.Cylinder(
            radius=r_ring + wg_width/2,
            height=mp.inf,
            axis=mp.Vector3(0, 0, 1),
            material=material
        ),
        mp.Cylinder(
            radius=r_ring - wg_width/2,
            height=mp.inf,
            axis=mp.Vector3(0, 0, 1),
            material=mp.Medium(index=n_clad)
        )
    ]
    
    # -------------------------------------------------------------------------
    # 3. Simulation Config
    # -------------------------------------------------------------------------
    sources = [
        mp.Source(
            mp.ContinuousSource(frequency=fcen), # CW source for nice steady flow animation
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
    )
    
    # -------------------------------------------------------------------------
    # 4. Animation Setup
    # -------------------------------------------------------------------------
    # Prepare the figure
    fig = plt.figure(figsize=(10,6))
    ax = plt.gca()
    
    # Initialize simulation
    sim.init_sim()
    
    # Create an Animate2D object
    # This captures the field Ez at every 'f' time units
    # real_time=True tries to render in real time, but saving to mp4 is better
    # normalize=True creates a consistent color scale
    anim = mp.Animate2D(
        sim, 
        fields=mp.Ez, 
        realtime=False, 
        normalize=True,
        eps_parameters={'contour': True, 'alpha': 0.2} # Draw geometry structure
    )
    
    print("Starting Animation Run...")
    # Run for enough time to see the light fill the ring and exit
    # We record ~10 seconds of simulation time
    sim.run(mp.at_every(0.5, anim), until=60)
    
    print("Saving Animation to MP4...")
    # Save the animation
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    video_path = os.path.join(base_dir, 'data', "selector_ON.mp4")
    
    # Ensure ffmpeg from our environment is in the PATH
    # The ffmpeg binary is in the same bin/ directory as the python executable running this script
    env_bin = os.path.dirname(sys.executable)
    if env_bin not in os.environ["PATH"]:
        os.environ["PATH"] = env_bin + os.pathsep + os.environ["PATH"]
    
    anim.to_mp4(10, video_path) # 10 fps
    print(f"Video saved to: {video_path}")

if __name__ == "__main__":
    run_selector_animation()
