import os
import sys
import argparse
import meep as mp
import numpy as np
import matplotlib.pyplot as plt

# Ensure we can import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_mixer(wvl1, wvl2, label1="Input 1", label2="Input 2"):
    """
    Universally mixes ANY two wavelengths in a nonlinear waveguide.
    """
    print(f"\n--- UNIVERSAL MIXER SIMULATION ---")
    print(f"mixing {label1} ({wvl1} um) + {label2} ({wvl2} um)")

    # -------------------------------------------------------------------------
    # 1. Physical Parameters
    # -------------------------------------------------------------------------
    resolution = 25
    
    # Calculate Frequencies
    freq1 = 1.0 / wvl1
    freq2 = 1.0 / wvl2
    
    # Target Sum Frequency
    freq_sum = freq1 + freq2
    wvl_sum = 1.0 / freq_sum
    
    print(f"Target Sum Output: {wvl_sum:.4f} um (Freq: {freq_sum:.4f})")
    
    # Geometry dimensions
    cell_x = 18
    cell_y = 5
    pml_thickness = 1.0
    wg_width = 1.1 # Optimized width for phase matching (improved from 0.8)
    
    # Material (LiNbO3)
    n_linbo3 = 2.2
    chi2_val = 0.5 
    
    # -------------------------------------------------------------------------
    # 2. Simulation Setup
    # -------------------------------------------------------------------------
    cell_size = mp.Vector3(cell_x, cell_y, 0)
    material = mp.Medium(index=n_linbo3, chi2=chi2_val)
    
    geometry = [
        mp.Block(
            mp.Vector3(mp.inf, wg_width, mp.inf),
            center=mp.Vector3(),
            material=material
        )
    ]
    
    # Sources (Broadband pulses to ensure coverage)
    # Using df = 0.05 * freq ensures distinct peaks but enough width
    sources = [
        mp.Source(
            mp.GaussianSource(freq1, fwidth=0.05*freq1),
            component=mp.Ez,
            center=mp.Vector3(-0.5 * cell_x + pml_thickness + 0.5, 0),
            size=mp.Vector3(0, wg_width, 0)
        ),
        mp.Source(
            mp.GaussianSource(freq2, fwidth=0.05*freq2),
            component=mp.Ez,
            center=mp.Vector3(-0.5 * cell_x + pml_thickness + 0.5, 0),
            size=mp.Vector3(0, wg_width, 0)
        )
    ]
    
    sim = mp.Simulation(
        cell_size=cell_size,
        boundary_layers=[mp.PML(pml_thickness)],
        geometry=geometry,
        sources=sources,
        resolution=resolution,
        # Suppress some output for cleaner CLI
    )
    
    # -------------------------------------------------------------------------
    # 3. Monitors
    # -------------------------------------------------------------------------
    # Measure spectrum at output
    # Cover the whole range from lowest freq input to sum freq + margin
    f_min = min(freq1, freq2) * 0.8
    f_max = freq_sum * 1.2
    fcen_mon = (f_min + f_max) / 2
    df_mon = (f_max - f_min)
    
    trans = sim.add_flux(
        fcen_mon, df_mon, 600,
        mp.FluxRegion(center=mp.Vector3(0.5 * cell_x - pml_thickness - 0.5, 0), size=mp.Vector3(0, 2*wg_width, 0))
    )
    
    # -------------------------------------------------------------------------
    # 4. Run
    # -------------------------------------------------------------------------
    print("Running FDTD Simulation...")
    sim.run(until_after_sources=mp.stop_when_fields_decayed(50, mp.Ez, mp.Vector3(0,0,0), 1e-4))
    
    # -------------------------------------------------------------------------
    # 5. Analysis & Plotting (IEEE Style)
    # -------------------------------------------------------------------------
    freqs = mp.get_flux_freqs(trans)
    flux = mp.get_fluxes(trans)
    wvls = [1/f for f in freqs]
    
    # Save Raw Data to CSV
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_filename = f"mixer_data_{label1}_{label2}.csv".replace(" ", "")
    csv_path = os.path.join(base_dir, 'data', csv_filename)
    
    header = "Frequency (Meep),Wavelength (um),Flux (a.u.)"
    data = np.column_stack((freqs, wvls, flux))
    np.savetxt(csv_path, data, delimiter=",", header=header, comments='')
    print(f"Raw data saved to: {csv_path}")

    # Plotting style for publication
    plt.style.use('default') # Reset to clean style
    plt.rcParams.update({
        'font.size': 12,
        'font.family': 'serif',
        'axes.linewidth': 1.5,
        'lines.linewidth': 2.0
    })
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Plot Data
    ax.plot(wvls, flux, 'k-', label='Output Spectrum')
    
    # Annotate Inputs (Vertical Lines)
    ax.axvline(x=wvl1, color='#D55E00', linestyle='--', linewidth=1.5, alpha=0.8, label=f'{label1} ({wvl1} $\mu$m)')
    ax.axvline(x=wvl2, color='#0072B2', linestyle='--', linewidth=1.5, alpha=0.8, label=f'{label2} ({wvl2} $\mu$m)')
    
    # Annotate Output
    ax.axvline(x=wvl_sum, color='#CC79A7', linestyle='-', linewidth=2.5, alpha=0.9, label=f'Sum ({wvl_sum:.3f} $\mu$m)')
    
    # Formatting
    ax.set_xlabel("Wavelength ($\mu$m)", fontsize=14)
    ax.set_ylabel("Power Flux (a.u.)", fontsize=14)
    ax.set_title(f"SFG Mixer Output: {label1} + {label2}", fontsize=16, fontweight='bold', pad=15)
    
    # Grid and Legend
    ax.grid(True, which='major', linestyle='-', alpha=0.2)
    ax.legend(frameon=True, fancybox=False, edgecolor='black', fontsize=10, loc='upper right')
    
    # Invert X axis? Usually spectra are plotted low-to-high wavelength.
    # But Meep freqs are high-to-low wavelength. 
    # Let's ensure the X-axis is sorted naturally (low wvl left)
    # matplotlib handles numerical axes automatically.
    
    plt.tight_layout()
    
    output_filename = f"mixer_result_{label1}_{label2}.png".replace(" ", "")
    plot_path = os.path.join(base_dir, 'data', output_filename)
    plt.savefig(plot_path, dpi=300) # High DPI for print
    print(f"High-res plot saved to: {plot_path}")

    # -------------------------------------------------------------------------
    # 6. Append to Lab Notebook (RESULTS_SUMMARY.md)
    # -------------------------------------------------------------------------
    import datetime
    
    # Convert list to array for math
    freqs_arr = np.array(freqs)
    flux_arr = np.array(flux)
    
    # Find flux at Sum Frequency peak (approx)
    # Find index closest to freq_sum
    idx_sum = (np.abs(freqs_arr - freq_sum)).argmin()
    flux_sum = flux_arr[idx_sum]
    
    # Find flux at inputs
    idx_1 = (np.abs(freqs_arr - freq1)).argmin()
    idx_2 = (np.abs(freqs_arr - freq2)).argmin()
    flux_in_total = flux_arr[idx_1] + flux_arr[idx_2]
    
    # Simple efficiency metric
    eff = (flux_sum / flux_in_total) * 100 if flux_in_total > 0 else 0
    
    summary_path = os.path.join(base_dir, 'RESULTS_SUMMARY.md')
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create header if file doesn't exist
    if not os.path.exists(summary_path):
        with open(summary_path, 'w') as f:
            f.write("# Photonic Mixer Simulation Log\n\n")
            f.write("| Timestamp | Inputs | Target Sum Wvl | Peak Flux (Sum) | Conversion Eff (%) |\n")
            f.write("|-----------|--------|----------------|-----------------|--------------------|\n")
            
    # Append row
    row = f"| {timestamp} | {label1} ({wvl1}) + {label2} ({wvl2}) | {wvl_sum:.4f} um | {flux_sum:.4e} | {eff:.2f}% |\n"
    with open(summary_path, 'a') as f:
        f.write(row)
    
    print(f"Results appended to: {summary_path}")
    
    # Open the image automatically (works on Linux)
    try:
        import subprocess
        subprocess.run(["xdg-open", plot_path], stderr=subprocess.DEVNULL)
    except:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Universal Photonic Mixer')
    parser.add_argument('--wvl1', type=float, required=True, help='Wavelength 1 (um)')
    parser.add_argument('--wvl2', type=float, required=True, help='Wavelength 2 (um)')
    parser.add_argument('--label1', type=str, default="Input 1", help='Label for Input 1')
    parser.add_argument('--label2', type=str, default="Input 2", help='Label for Input 2')
    
    args = parser.parse_args()
    
    run_mixer(args.wvl1, args.wvl2, args.label1, args.label2)
