# Supplementary Material: Simulation of Wavelength-Division Ternary Logic Gates

## 1. Simulation Methodology

### 1.1 Computational Framework
The photonic logic gates were simulated using the **Finite-Difference Time-Domain (FDTD)** method via the open-source software package **Meep** (v1.25.0) [1]. The simulations were performed in a two-dimensional (2D) computational domain, assuming invariance in the z-direction ($ \partial/\partial z = 0 $), to model the TE-polarized ($ E_z $) light propagation in planar waveguide structures.

### 1.2 Simulation Parameters

**Domain & Discretization**
*   **Resolution:** A spatial resolution of **25 pixels/$\mu$m** was employed, corresponding to a grid spacing of $\Delta x = 40$ nm. This ensures sufficient sampling of the shortest operational wavelength ($\lambda_{sum} \approx 0.56 \mu m$, where $\lambda/10 \approx 56$ nm).
*   **Boundary Conditions:** Perfectly Matched Layers (PML) with a thickness of **1.0 $\mu$m** were applied at all domain boundaries to simulate an open system and prevent non-physical reflections.

**Material Properties**
*   **Waveguides:** The linear regions of the photonic circuit were modeled as generic high-index waveguides ($ n = 2.2 $) with a width of $ w = 0.8 \mu m $, simulating Lithium Niobate (LiNbO$_3$) or Silicon Nitride (Si$_3$N$_4$) on Silica.
*   **Nonlinear Medium:** For the mixing region, a second-order nonlinear susceptibility $\chi^{(2)}$ was introduced to the material definition to enable Sum Frequency Generation (SFG).
    *   **$\chi^{(2)}$ Value:** The simulation utilized a normalized susceptibility parameter `chi2 = 0.5` (Meep units) to demonstrate efficient mixing within the short simulation domain length ($ L \approx 18 \mu m $).

**Source Configuration (Ternary States)**
*   **Logic -1 (Red):** $\lambda = 1.55 \mu m$ (C-Band Telecom)
*   **Logic 1 (Blue):** $\lambda = 1.00 \mu m$
*   **Logic State 3 (Green):** $\lambda = 1.30 \mu m$ (O-Band Telecom)

### 1.3 AI Usage Statement
The novel ternary logic architecture, including the specific configuration of ring-resonator selectors and sum-frequency generation mixers, was conceived by the authors. An AI coding assistant (Google Gemini-3-Pro-Preview) was utilized solely for the implementation of the Python simulation scripts based on the authors' specified design parameters and physics requirements.

## 2. Experimental Results

The Sum Frequency Generation (SFG) mixer was evaluated for all three pairwise combinations of the ternary input states. The transmitted power flux was measured at the output waveguide.

### 2.1 Summary of Mixing Operations

The table below summarizes the conversion efficiency for the optimized waveguide geometry ($w = 1.1 \mu m$).

| Date | Input Combinations | Target Sum Wvl ($\mu m$) | Measured Peak Flux (a.u.) | Conversion Efficiency* | Signal Quality |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-01-28 | **Blue** (1.00) + **Green** (1.30) | 0.5652 | 1.2875e+00 | 4.57% | **Excellent** |
| 2026-01-28 | **Red** (1.55) + **Blue** (1.00) | 0.6078 | 2.7652e-01 | 0.73% | **Good** |
| 2026-01-28 | **Red** (1.55) + **Green** (1.30) | 0.7070 | 1.6764e-01 | 0.40% | **Adequate** |

*\*Efficiency calculated as $P_{sum} / (P_{in1} + P_{in2})$.*

### 2.2 Feasibility Analysis & Power Scaling
The lowest observed efficiency (0.40% for Red+Green) represents the marginal case for the system. Assuming standard on-chip laser sources with 1 mW (0 dBm) input power, the generated sum-frequency signal would be **-24 dBm (4.0 $\mu$W)**. While lower than the other states, this is still above the noise floor of standard Germanium photodiodes (typically -30 dBm).

Furthermore, since SFG is a nonlinear process where $P_{sum} \propto P_{1} P_{2}$, the output signal strength can be significantly enhanced by increasing the input power. For example, increasing the input sources to **10 mW** would theoretically increase the output signal by a factor of 100, boosting the conversion efficiency and ensuring robust detection even for the marginal Red+Green case. Thus, the system is scalable for high-reliability operations.

### 2.3 Spectral Data
Raw spectral data for each mixing operation is available in the supplementary CSV files:
*   `mixer_data_RED_BLUE.csv`
*   `mixer_data_RED_GREEN.csv`
*   `mixer_data_BLUE_GREEN.csv`

## References
[1] A. F. Oskooi, et al., "Meep: A flexible free-software package for electromagnetic simulations by the FDTD method," Computer Physics Communications, vol. 181, no. 3, pp. 687-702, 2010.
