# Simulation Methodology

## 1. Computational Framework
The photonic logic gates were simulated using the **Finite-Difference Time-Domain (FDTD)** method via the open-source software package **Meep** (v1.25.0) [1]. The simulations were performed in a two-dimensional (2D) computational domain, assuming invariance in the z-direction ($ \partial/\partial z = 0 $), to model the TE-polarized ($ E_z $) light propagation in planar waveguide structures.

## 2. Simulation Parameters

### 2.1 Domain & Discretization
*   **Resolution:** A spatial resolution of **25 pixels/$\mu$m** was employed, corresponding to a grid spacing of $\Delta x = 40$ nm. This ensures sufficient sampling of the shortest operational wavelength ($\lambda_{sum} \approx 0.56 \mu m$, where $\lambda/10 \approx 56$ nm).
*   **Boundary Conditions:** Perfectly Matched Layers (PML) with a thickness of **1.0 $\mu$m** were applied at all domain boundaries to simulate an open system and prevent non-physical reflections.

### 2.2 Material Properties
*   **Waveguides:** The linear regions of the photonic circuit were modeled as generic high-index waveguides ($ n = 2.2 $) with a width of $ w = 0.8 \mu m $, simulating Lithium Niobate (LiNbO$_3$) or Silicon Nitride (Si$_3$N$_4$) on Silica.
*   **Nonlinear Medium:** For the mixing region, a second-order nonlinear susceptibility $\chi^{(2)}$ was introduced to the material definition to enable Sum Frequency Generation (SFG).
    *   **$\chi^{(2)}$ Value:** The simulation utilized a normalized susceptibility parameter `chi2 = 0.5` (Meep units) to demonstrate efficient mixing within the short simulation domain length ($ L \approx 18 \mu m $).
*   **Active Selectors:** The ring resonators were modeled with a base refractive index $ n_{eff} = 2.2 $. The "Active/Voltage" state was simulated by applying a uniform index shift of $\Delta n = +0.01$, representing the electro-optic Pockels effect induced by an external electric field.

### 2.3 Sources
*   **Type:** Gaussian-profiled Continuous Wave (CW) sources were used to inject signals.
*   **Bandwidth:** A fractional bandwidth of $ df/f = 0.05 $ was defined to visualize spectral separation while maintaining quasi-monochromatic operation.
*   **Wavelengths (Ternary States):**
    *   **Logic -1 (Red):** $\lambda = 1.55 \mu m$ (C-Band Telecom)
    *   **Logic 1 (Blue):** $\lambda = 1.00 \mu m$
    *   **Logic State 3 (Green):** $\lambda = 1.30 \mu m$ (O-Band Telecom)

## 3. Data Analysis
Spectral analysis was performed using Fourier-transformed flux planes positioned at the waveguide output. The transmitted power flux $ P(\omega) $ was normalized against reference simulations where applicable. The mixing efficiency is reported as the relative magnitude of the generated sum-frequency peak ($ \omega_{sum} = \omega_1 + \omega_2 $) compared to the residual input fundamentals.

## 4. AI Usage Statement
The novel ternary logic architecture, including the specific configuration of ring-resonator selectors and sum-frequency generation mixers, was conceived by the authors. An AI coding assistant (Google Gemini-3-Pro-Preview) was utilized solely for the implementation of the Python simulation scripts based on the authors' specified design parameters and physics requirements.

## References
[1] A. F. Oskooi, et al., "Meep: A flexible free-software package for electromagnetic simulations by the FDTD method," Computer Physics Communications, vol. 181, no. 3, pp. 687-702, 2010.
