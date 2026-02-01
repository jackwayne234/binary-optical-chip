import os
import sys
import meep as mp
import numpy as np
import matplotlib.pyplot as plt

# Ensure we can import local modules if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_sfg_simulation():
    """
    Simulates Sum Frequency Generation (SFG) in a Lithium Niobate waveguide.
    Mixes two source frequencies and looks for the sum frequency at the output.
    """

    # -------------------------------------------------------------------------
    # 1. Physical Parameters
    # -------------------------------------------------------------------------
    resolution = 20        # pixels/um (Higher resolution needed for non-linear mixing)
    
    # Geometry dimensions
    cell_x = 20            # Length of domain in X
    cell_y = 6             # Width of domain in Y
    pml_thickness = 1.0    # Thickness of PML layers
    
    # Waveguide & Material (Lithium Niobate - LiNbO3)
    wg_width = 0.8         # slightly wider to support modes
    n_linbo3 = 2.2         # Linear refractive index
    # chi2 nonlinear susceptibility (arbitrary units for demonstration, usually small)
    # In real units, dependent on E-field scale. Here we pick a value to show effect.
    chi2_val = 0.5         
    
    # Sources
    # Signal A (e.g., Telecom)
    wvl_a = 1.55            
    freq_a = 1 / wvl_a
    
    # Signal B (e.g., ~1um)
    wvl_b = 1.0            
    freq_b = 1 / wvl_b
    
    # Target Sum Frequency
    freq_sum = freq_a + freq_b
    wvl_sum = 1 / freq_sum
    
    print(f"Freq A: {freq_a:.3f} (wvl: {wvl_a:.3f})")
    print(f"Freq B: {freq_b:.3f} (wvl: {wvl_b:.3f})")
    print(f"Target Sum Freq: {freq_sum:.3f} (wvl: {wvl_sum:.3f})")

    # Pulse parameters (using Gaussian pulse to look at spectrum)
    # We use a broad bandwidth to ensure we excite the modes
    df = 0.1 * freq_a

    # -------------------------------------------------------------------------
    # 2. Geometry Setup
    # -------------------------------------------------------------------------
    cell_size = mp.Vector3(cell_x, cell_y, 0)
    
    # Define Material with Nonlinearity
    # We apply chi2 (Pockels effect)
    # Note: For strict SFG, we might need to be careful about tensor directions,
    # but for a 2D demo, isotropic chi2 on the material works.
    linbo3_material = mp.Medium(index=n_linbo3, chi2=chi2_val)
    
    geometry = [
        mp.Block(
            mp.Vector3(mp.inf, wg_width, mp.inf),
            center=mp.Vector3(),
            material=linbo3_material
        )
    ]
    
    # -------------------------------------------------------------------------
    # 3. Simulation Configuration
    # -------------------------------------------------------------------------
    sources = [
        # Source A
        mp.Source(
            mp.GaussianSource(freq_a, fwidth=df),
            component=mp.Ez,
            center=mp.Vector3(-0.5 * cell_x + pml_thickness + 0.5, 0),
            size=mp.Vector3(0, wg_width, 0)
        ),
        # Source B (Same location, superimposed)
        mp.Source(
            mp.GaussianSource(freq_b, fwidth=df),
            component=mp.Ez,
            center=mp.Vector3(-0.5 * cell_x + pml_thickness + 0.5, 0),
            size=mp.Vector3(0, wg_width, 0)
        )
    ]
    
    pml_layers = [mp.PML(pml_thickness)]
    
    # Update file prefix to be absolute or relative to where script is run
    # Assuming script run from project root
    file_prefix = 'data/sfg_mixer'
    
    sim = mp.Simulation(
        cell_size=cell_size,
        boundary_layers=pml_layers,
        geometry=geometry,
        sources=sources,
        resolution=resolution,
        filename_prefix=file_prefix
    )

    # -------------------------------------------------------------------------
    # 4. Monitors (Flux)
    # -------------------------------------------------------------------------
    # We want to measure the spectrum at the END of the waveguide
    
    # Define the frequency range we want to plot (from 0 to just above sum freq)
    nfreq = 500
    fcen_mon = (freq_sum + freq_a)/2 # Center around expected range
    df_mon = freq_sum # Broad range to see all peaks
    
    # Flux monitor at output
    trans = sim.add_flux(
        fcen_mon, df_mon, nfreq,
        mp.FluxRegion(
            center=mp.Vector3(0.5 * cell_x - pml_thickness - 0.5, 0),
            size=mp.Vector3(0, 2*wg_width, 0)
        )
    )
    
    # -------------------------------------------------------------------------
    # 5. Run Simulation
    # -------------------------------------------------------------------------
    print(f"Starting SFG simulation...")
    
    # Run until sources are gone and fields propagate through
    sim.run(until_after_sources=mp.stop_when_fields_decayed(50, mp.Ez, mp.Vector3(0.5*cell_x - pml_thickness - 0.5, 0), 1e-4))
    
    print("Simulation finished. Analyzing spectrum...")
    
    # -------------------------------------------------------------------------
    # 6. Analysis
    # -------------------------------------------------------------------------
    freqs = mp.get_flux_freqs(trans)
    flux_spectrum = mp.get_fluxes(trans)
    
    # Save raw data for external plotting if needed
    # (Optional: save to .npy or .h5 in /data)
    
    # Plotting (saved to file)
    plt.figure(figsize=(10, 6))
    plt.plot(freqs, flux_spectrum, 'b-', label='Output Spectrum')
    
    # Mark expected frequencies
    plt.axvline(x=freq_a, color='r', linestyle='--', label=f'Input A ({freq_a:.2f})')
    plt.axvline(x=freq_b, color='g', linestyle='--', label=f'Input B ({freq_b:.2f})')
    plt.axvline(x=freq_sum, color='m', linestyle='-', linewidth=2, label=f'Sum Freq ({freq_sum:.2f})')
    
    plt.xlabel("Frequency (Meep units)")
    plt.ylabel("Flux (a.u.)")
    plt.title("Sum Frequency Generation Spectrum")
    plt.legend()
    plt.grid(True)
    
    # Save plot to current directory or data
    # Resolve absolute path to data directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    plot_path = os.path.join(data_dir, "sfg_spectrum.png")
    
    plt.savefig(plot_path)
    print(f"Spectrum plot saved to: {plot_path}")

if __name__ == "__main__":
    run_sfg_simulation()
