import os
import sys
import meep as mp
import numpy as np

# Ensure we can import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def sweep_width_for_efficiency():
    """
    Sweeps the waveguide width to optimize mixing efficiency for RED+BLUE.
    """
    wvl1 = 1.55 # Red
    wvl2 = 1.00 # Blue
    freq1 = 1/wvl1
    freq2 = 1/wvl2
    freq_sum = freq1 + freq2
    
    widths = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
    results = []
    
    print(f"--- OPTIMIZATION SWEEP: Waveguide Width ---")
    print(f"Goal: Fix low efficiency for Red ({wvl1}) + Blue ({wvl2})")
    
    for w in widths:
        # Run simplified simulation (no plotting, just flux)
        eff = run_single_sim(w, freq1, freq2, freq_sum)
        results.append((w, eff))
        print(f"Width: {w:.1f} um -> Efficiency: {eff:.4f}%")
        
    # Find best
    best_w, best_eff = max(results, key=lambda x: x[1])
    print(f"\n>>> BEST WIDTH: {best_w} um (Eff: {best_eff:.4f}%)")

def run_single_sim(wg_width, freq1, freq2, freq_sum):
    resolution = 20 # Lower res for fast sweep
    cell_x = 12
    cell_y = 4
    pml = 1.0
    
    geometry = [
        mp.Block(
            mp.Vector3(mp.inf, wg_width, mp.inf),
            center=mp.Vector3(),
            material=mp.Medium(index=2.2, chi2=0.5)
        )
    ]
    
    sources = [
        mp.Source(mp.GaussianSource(freq1, fwidth=0.05*freq1), component=mp.Ez, center=mp.Vector3(-0.5*cell_x+pml+0.5, 0), size=mp.Vector3(0, wg_width)),
        mp.Source(mp.GaussianSource(freq2, fwidth=0.05*freq2), component=mp.Ez, center=mp.Vector3(-0.5*cell_x+pml+0.5, 0), size=mp.Vector3(0, wg_width))
    ]
    
    sim = mp.Simulation(
        cell_size=mp.Vector3(cell_x, cell_y),
        boundary_layers=[mp.PML(pml)],
        geometry=geometry,
        sources=sources,
        resolution=resolution
    )
    
    trans = sim.add_flux(freq_sum, 0.1*freq_sum, 1, mp.FluxRegion(center=mp.Vector3(0.5*cell_x-pml-0.5, 0), size=mp.Vector3(0, 2*wg_width)))
    trans_in = sim.add_flux(freq1, freq2-freq1 + 0.1, 500, mp.FluxRegion(center=mp.Vector3(-0.4*cell_x, 0), size=mp.Vector3(0, 2*wg_width)))
    
    sim.run(until_after_sources=mp.stop_when_fields_decayed(50, mp.Ez, mp.Vector3(0,0), 1e-3))
    
    flux_out = mp.get_fluxes(trans)[0]
    
    # Approx input flux calculation
    # Just use raw output flux as proxy for optimization (higher is better)
    return flux_out * 100 # Scaling factor

if __name__ == "__main__":
    sweep_width_for_efficiency()
