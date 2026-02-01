import os
import sys
import meep as mp
import matplotlib.pyplot as plt

# Ensure we can import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def generate_layout_diagram():
    """
    Generates a 2D layout diagram of the mixing simulation.
    Shows sources, PML, waveguide geometry, and monitor planes.
    """
    resolution = 25
    cell_x = 18
    cell_y = 5
    pml_thickness = 1.0
    wg_width = 1.1 # Optimized
    
    cell_size = mp.Vector3(cell_x, cell_y, 0)
    
    # Material
    geometry = [
        mp.Block(
            mp.Vector3(mp.inf, wg_width, mp.inf),
            center=mp.Vector3(),
            material=mp.Medium(index=2.2)
        )
    ]
    
    # Sources (Red and Blue locations)
    sources = [
        mp.Source(
            mp.GaussianSource(1/1.55, fwidth=0.1),
            component=mp.Ez,
            center=mp.Vector3(-0.5 * cell_x + pml_thickness + 0.5, 0),
            size=mp.Vector3(0, wg_width)
        )
    ]
    
    sim = mp.Simulation(
        cell_size=cell_size,
        boundary_layers=[mp.PML(pml_thickness)],
        geometry=geometry,
        sources=sources,
        resolution=resolution,
    )
    
    # Initialize to set up geometry
    sim.init_sim()
    
    # Plotting
    plt.figure(figsize=(10, 4))
    
    # Plot Epsilon (Structure)
    sim.plot2D(
        plot_sources_flag=True,
        plot_monitors_flag=True,
        eps_parameters={'cmap': 'binary', 'alpha': 0.3} # Light grey structure
    )
    
    # Add custom annotations for clarity
    plt.title("FDTD Simulation Domain: Nonlinear Mixer (L=18 $\mu$m)", fontsize=14)
    plt.xlabel("x ($\mu$m)")
    plt.ylabel("y ($\mu$m)")
    
    # Annotate Regions
    plt.text(-7, 1.5, "Input Sources\n($\lambda_1 + \lambda_2$)", color='red', fontsize=10, ha='center')
    plt.text(0, 0.8, "Nonlinear Waveguide\n($\chi^{(2)}$ Medium)", color='black', fontsize=10, ha='center')
    plt.text(7, 1.5, "Output Flux Plane\n(Measurement)", color='blue', fontsize=10, ha='center')
    
    # Arrows to show locations
    plt.arrow(-7, 1.2, 0, -0.6, head_width=0.3, color='red')
    plt.arrow(7, 1.2, 0, -0.6, head_width=0.3, color='blue')
    
    plt.tight_layout()
    
    # Save
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plot_path = os.path.join(base_dir, 'data', "simulation_setup.png")
    plt.savefig(plot_path, dpi=300)
    print(f"Diagram saved to: {plot_path}")

if __name__ == "__main__":
    generate_layout_diagram()
