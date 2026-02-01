# Phase 2: Fiber Optic Ternary Benchtop
**Status:** Procurement & Planning
**Goal:** Prove 10GHz Balanced Ternary Logic using passive fiber optics.

## Hardware Stack (The "Shopping List")
*   **Source:** 3x Finisar FTLX6872MCC (Tunable SFP+)
*   **Logic:** 2x DWDM Mux/DeMux (100GHz Grid, Ch30-Ch40)
*   **Mixer:** 2x 50/50 Fused Fiber Couplers (SMF-28)
*   **Control:** FPGA or SFP+ Breakout Board (I2C Master)

## Wavelength Architecture (ITU Grid)
*   **Trit -1:** Channel 30 (1553.33 nm / 193.00 THz)
*   **Trit  0:** Channel 35 (1549.32 nm / 193.50 THz)
*   **Trit +1:** Channel 40 (1545.32 nm / 194.00 THz)

## Logical Experiments
1.  **The Passive Inverter:** Physical fiber swap of Ch30 and Ch40 paths.
2.  **The Trit Eye:** Visualizing 3-level density on a standard scope.
