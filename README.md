# Wavelength-Division Ternary Optical Computer

**Project Status:** Active Development
**Date:** January 2026

This repository contains the research, simulation, and hardware implementation files for a novel Ternary (Base-3) Optical Computer that bypasses the radix economy penalty of electronic systems.

## 📂 Repository Structure

### **[`Phase1_Prototype/`](Phase1_Prototype/)**
**The "Macro" Demonstrator (Visible Light)**
*   **Status:** Parts Ordered / Construction Pending.
*   **Goal:** Prove the physical architecture using Red/Green/Blue lasers and 3D printed optics.
*   **Contents:**
    *   `firmware/`: ESP32 Logic Controller & Calibration.
    *   `hardware/`: BOM, 3D Print Files (SCAD), Assembly Guide.
    *   `NEXT_STEPS.md`: Build instructions.

### **[`Phase2_Fiber_Benchtop/`](Phase2_Fiber_Benchtop/)**
**The "Speed" Demonstrator (Telecom Fiber)**
*   **Status:** Procurement.
*   **Goal:** Prove 10GHz switching and passive logic using standard ITU C-Band fiber gear.
*   **Contents:**
    *   `firmware/`: Tuning scripts for SFP+ modules.
    *   `hardware/`: Wiring Schematics (Planned).

### **[`Phase3_Chip_Simulation/`](Phase3_Chip_Simulation/)**
**The "Final Result" (Silicon Photonics)**
*   **Status:** Pending Layout.
*   **Goal:** Miniaturize the design onto a Lithium Niobate (LiNbO3) chip.
*   **Contents:**
    *   Placeholder for future GDSII/Mask files.
    *   *(Note: Simulations have been moved to `Research/programs`)*

### **[`Research/`](Research/)**
**Theory, Data & Simulations**
*   **`papers/`**: Zenodo Publication, Drafts, and Theoretical Background (METHODS.md).
*   **`programs/`**: Python Meep/FDTD Simulation Scripts.
*   **`data/`**: Simulation outputs (Plots, HDF5 fields, CSVs).

## 🚀 Quick Start
*   **To Build Phase 1:** Go to `Phase1_Prototype/NEXT_STEPS.md`.
*   **To Tune Phase 2 Lasers:** Run `python3 Phase2_Fiber_Benchtop/firmware/sfp_tuner.py`.
*   **To Run Simulations:** Go to `Research/programs/`.
