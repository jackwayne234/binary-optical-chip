# Wavelength-Division Ternary Optical Computer
### Prototype v1 (24" x 24" Modular Breadboard)

This project implements a **Ternary (Base-3) Computer** using light wavelengths (-1=Red, 0=Green, +1=Blue) instead of voltage. This prototype proves that we can "bypass the radix economy penalty" by using cheap optics and chromatic mixing.

## 📂 Project Structure

*   **`NEXT_STEPS.md`** -> **START HERE.** Your immediate checklist for the build.
*   **`hardware/`**
    *   `BOM_24x24_Prototype.md` -> Shopping list (Lasers, Sensor, ESP32).
    *   `ASSEMBLY_INSTRUCTIONS.md` -> How to drill the board and wire it up.
    *   `scad/` -> 3D printable files (Turrets, Mixer, Sensor Housing).
*   **`firmware/`**
    *   `ternary_logic_controller/` -> Arduino/ESP32 code to run the computer.
*   **`ternary_optical_adder_prototype_plan.txt`** -> The original research & theory.

## 🚀 Quick Start
1.  **Print** the parts in `hardware/scad`.
2.  **Assemble** using the guide in `hardware/ASSEMBLY_INSTRUCTIONS.md`.
3.  **Flash** the firmware in `firmware/ternary_logic_controller`.
4.  **Run** command `ADD 1 -1` in the Serial Monitor.

## ⚠️ Build Notes
*   **Pipes:** If you bought 10-inch pipes, you may need to cut them down to **~8-9 inches** to fit comfortably on the 24-inch board.
*   **Safety:** Always wear laser safety glasses when aligning the beams.
