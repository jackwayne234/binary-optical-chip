import os
import sys
import meep as mp
import numpy as np
import matplotlib.pyplot as plt

# Ensure we can import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_photodetector_simulation():
    """
    Simulates a Waveguide-coupled Photodetector (Germanium).
    Calculates absorbed power and estimates photocurrent.
    """

    # -------------------------------------------------------------------------
    # 1. Physical Parameters
    # -------------------------------------------------------------------------
    resolution = 30        # pixels/um
    
    # Input Light: The "Purple" Answer (Sum Freq from previous step)
    # Freq sum was ~ 1.645 (wvl ~ 0.608 um)
    wvl_purple = 0.608
    fcen = 1 / wvl_purple
    df = 0.05 * fcen
    
    # Geometry
    cell_x = 10
    cell_y = 4
    pml_thickness = 1.0
    
    wg_width = 0.5
    
    # Materials
    # Silicon Waveguide (transparent at 1.55, but we are using 0.6um here?)
    # At 0.6um, Si is actually absorbing! But let's assume a delivery waveguide 
    # of SiN or SiO2 (transparent) delivering to a Ge detector.
    n_delivery = 2.0       # SiN approx
    
    # Germanium (Detector) parameters at ~0.6um
    # Ge has high absorption in visible/NIR
    # n ~ 4.0, k ~ 0.1 (simplified values for demo)
    # k > 0 means absorption (imaginary part)
    n_ge = 4.0
    k_ge = 0.5             # Higher k = more absorption
    
    # Detector Dimensions
    det_length = 2.0       # Length of Ge block
    
    # -------------------------------------------------------------------------
    # 2. Geometry Setup
    # -------------------------------------------------------------------------
    cell_size = mp.Vector3(cell_x, cell_y, 0)
    
    # Material Definitions
    # Standard dielectric for waveguide
    mat_wg = mp.Medium(index=n_delivery)
    # Absorbing material for detector (using conductivity or complex index)
    # Meep uses D-conductivity. simpler to use D_conductivity or mp.Medium(epsilon=...) with conductivity
    # complex index N = n + ik. epsilon = N^2 = (n^2 - k^2) + i(2nk)
    # conductivity sigma = 2 * pi * f * epsilon_imag / (unit conversions...)
    # Easier way in Meep: use mp.Medium(index=n, k=k) *if supported* or standard LorentzDrude
    # Actually, simpler way: define conductivity.
    # sigma = 2 * pi * f * 2 * n * k (in meep units where epsilon0=1)
    # f = fcen.
    
    # However, simpler approximation for Meep Python interface:
    # Just use mp.Medium(index=n, D_conductivity=...)?
    # Let's use the explicit epsilon and D-conductivity formula
    # epsilon_real = n_ge**2 - k_ge**2
    # epsilon_imag = 2 * n_ge * k_ge
    # D_conductivity = 2 * np.pi * fcen * epsilon_imag / epsilon_real
    
    epsilon_real = n_ge**2 - k_ge**2
    epsilon_imag = 2 * n_ge * k_ge
    cond = 2 * np.pi * fcen * epsilon_imag / epsilon_real
    
    mat_det = mp.Medium(epsilon=epsilon_real, D_conductivity=cond)
    
    geometry = []
    
    # 1. Delivery Waveguide (Left side)
    geometry.append(
        mp.Block(
            mp.Vector3(cell_x/2 + pml_thickness, wg_width, mp.inf),
            center=mp.Vector3(-cell_x/4, 0, 0),
            material=mat_wg
        )
    )
    
    # 2. Detector Block (Right side, abutting waveguide)
    # Placed after x=0
    geometry.append(
        mp.Block(
            mp.Vector3(det_length, wg_width, mp.inf),
            center=mp.Vector3(det_length/2, 0, 0),
            material=mat_det
        )
    )
    
    # -------------------------------------------------------------------------
    # 3. Simulation Config
    # -------------------------------------------------------------------------
    sources = [
        mp.Source(
            mp.GaussianSource(fcen, fwidth=df),
            component=mp.Ez,
            center=mp.Vector3(-0.5 * cell_x + pml_thickness + 0.5, 0),
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
        filename_prefix='data/photodetector'
    )
    
    # -------------------------------------------------------------------------
    # 4. Monitors (Power Budget)
    # -------------------------------------------------------------------------
    # Monitor 1: Incident Power (Before Detector)
    # At x = -0.5
    mon_inc = sim.add_flux(
        fcen, df, 1,
        mp.FluxRegion(center=mp.Vector3(-0.5, 0, 0), size=mp.Vector3(0, 2*wg_width, 0))
    )
    
    # Monitor 2: Transmitted Power (After Detector - leakage)
    # At x = det_length + 0.5
    mon_trans = sim.add_flux(
        fcen, df, 1,
        mp.FluxRegion(center=mp.Vector3(det_length + 0.5, 0, 0), size=mp.Vector3(0, 2*wg_width, 0))
    )
    
    # -------------------------------------------------------------------------
    # 5. Run
    # -------------------------------------------------------------------------
    print("Starting Photodetector simulation...")
    print(f"Detecting 'Purple' wavelength: {wvl_purple:.3f} um")
    
    sim.run(until_after_sources=mp.stop_when_fields_decayed(
        50, mp.Ez, 
        mp.Vector3(det_length/2, 0, 0), 
        1e-3)
    )
    
    # -------------------------------------------------------------------------
    # 6. Analysis
    # -------------------------------------------------------------------------
    flux_in = mp.get_fluxes(mon_inc)[0]
    flux_out = mp.get_fluxes(mon_trans)[0]
    
    # Absorbed Power = In - Out (approx, ignoring scattering/reflection for now)
    # Better: Absorbed = In - (Reflection + Transmission). 
    # We didn't measure reflection here, assuming matched interface or simplified.
    # Let's just look at transmission drop.
    
    absorbed_flux = flux_in - flux_out
    absorption_ratio = absorbed_flux / flux_in if flux_in > 0 else 0
    
    print("\n--- DETECTOR ANALYSIS ---")
    print(f"Incident Flux: {flux_in:.4e}")
    print(f"Transmitted Flux: {flux_out:.4e}")
    print(f"Absorbed Flux: {absorbed_flux:.4e}")
    print(f"Absorption Efficiency: {absorption_ratio*100:.2f}%")
    
    # Estimate Photocurrent
    # Responsivity R = eta * q / (h * nu)
    # eta (quantum efficiency) ~ absorption efficiency
    # q = 1.6e-19 C
    # h*nu = energy of photon.
    # In Meep, flux is arbitrary units. We can't get absolute Amps without calibrating input power.
    # But we can calculate Responsivity Factor.
    
    # Energy of photon at 0.6um ~ 2 eV.
    # Ideal R ~ 0.5 A/W.
    estimated_responsivity = 0.5 * absorption_ratio
    print(f"Estimated Responsivity: {estimated_responsivity:.3f} A/W")
    
    if absorption_ratio > 0.5:
        print(">> Logic 0 (Purple) DETECTED SUCCESSFULLY")
    else:
        print(">> Detection signal weak - lengthen detector or increase absorption.")

if __name__ == "__main__":
    run_photodetector_simulation()
