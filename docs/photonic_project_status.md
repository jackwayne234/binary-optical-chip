# Project Status: Optical Ternary Computing

**Date:** January 29, 2026
**Architect:** User
**Engineer:** Assistant (Gemini-3-Pro)

## 1. Research Track (Simulation)
*Location:* `Optical_computing/Wavelength_Ternary_Computing/` & `Optical_computing/scripts/`
*Status:* **Submission Ready**
*Methodology:* FDTD Simulation (Meep) of Chip-Scale Photonics.
*Key Components:*
*   **Selectors:** Ring Resonators (Switching logic).
*   **Mixer:** Non-Linear SFG Waveguides ($\chi^{(2)}$ material).
*   **Logic:** Balanced Ternary (-1, 0, 1) using Telecom Wavelengths (1.55, 1.30, 1.00 $\mu m$).

## 2. Prototype Track (Hardware Build)
*Location:* `Optical_computing/Prototype_Build/` (Proposed)
*Status:* **Procurement Phase**
*Methodology:* Macroscopic Optical Analog (Additive Synthesis) for Desktop Demonstration.
*Key Components:*
*   **Selectors:** Arduino-controlled Laser Modules (PWM Intensity).
*   **Mixer:** X-Cube Prism (Combiner).
*   **Logic:** Balanced Ternary mapped to Visible Spectrum (Red, Green, Blue).

### Hardware Specifications (12"x12" Device)
*   **Controller:** Arduino Uno R3.
*   **Inputs:** Red (650nm), Green (520nm), Blue (405nm) Lasers.
*   **Combiner:** 20mm X-Cube Prism.
*   **Detector:** TCS34725 RGB Sensor.
*   **Logic Map:**
    *   Red $\rightarrow$ -1
    *   Green $\rightarrow$ 0
    *   Blue $\rightarrow$ +1

### Action Items
- [x] Generate Bill of Materials (Saved to `Optical_computing/photonic_computer_bom.txt`).
- [ ] User: Acquire Hardware.
- [ ] Engineer: Create Wiring Diagram (Schematic).
- [ ] Engineer: Write Arduino Firmware (PWM Driver).
- [ ] Engineer: Write Python Controller (Integration with `scripts/` if possible).

## Notes for Next Session
- The prototype is a physical demonstration of the logic simulated in `Wavelength_Ternary_Computing`.
- Ensure the Python Controller for the hardware respects the logic tables defined in `METHODS.md` (adapted for visible light).
