# Driver Specification — Binary IOC (NB-IOC)

**Version:** 1.0
**Last updated:** 2026-02-27

---

## Overview

The Binary IOC (NB-IOC) driver controls the electronic interface to the binary optical chip:
- 18 MZI encoder channels (9 activation + 9 weight)
- 9 photodetector output channels
- Mode configuration (AND / OR / XOR)
- Calibration storage

The driver is a thin C library with Python bindings, following the same pattern as the ternary NR-IOC driver.

---

## Architecture

```
Python script / user code
        │
        ▼
   binary_ioc.py  (Python bindings via ctypes)
        │
        ▼
   nb_ioc.c / nb_ioc.h  (C driver, platform-agnostic)
        │
        ▼
   FPGA HAL  (Hardware Abstraction Layer)
        │
      SPI/I2C
        │
        ▼
   DAC (18ch MZI control) + ADC (9ch detector readout)
        │
        ▼
   BINARY OPTICAL CHIP
```

---

## C API

### Header: `nb_ioc.h`

```c
#ifndef NB_IOC_H
#define NB_IOC_H

#include <stdint.h>

// ============================================================
// Types
// ============================================================

typedef enum {
    NB_IOC_AND = 0,   // Direct SFG AND gate (hardware default)
    NB_IOC_OR  = 1,   // De Morgan: NOT(NOT(a) AND NOT(b))
    NB_IOC_XOR = 2,   // 3-AND composition: (a AND NOT(b)) OR (NOT(a) AND b)
} nb_ioc_mode_t;

typedef struct {
    float v_pi[18];       // Calibrated Vπ per MZI channel (V)
    float dark_current[9]; // Dark current baseline per detector (μA)
    float laser_power[2]; // Measured input power (mW): [0]=1310nm, [1]=1550nm
} nb_ioc_cal_t;

typedef struct {
    int bits[9];          // Output bit values (0 or 1)
    float current_ua[9];  // Raw detector current (μA)
} nb_ioc_output_t;

// ============================================================
// Functions
// ============================================================

// Initialize device on given serial port
int nb_ioc_init(const char* port);

// Encode activation vector (9 bits) via MZI channels
int nb_ioc_set_activation(const int bits[9]);

// Encode weight matrix (9x9 bits) via MZI channels
int nb_ioc_set_weights(const int weights[9][9]);

// Set operation mode (AND/OR/XOR)
int nb_ioc_set_mode(nb_ioc_mode_t mode);

// Read 9 detector outputs — returns decoded bit vector
nb_ioc_output_t nb_ioc_read_outputs(void);

// Calibrate: measure Vπ for each MZI channel
int nb_ioc_calibrate(nb_ioc_cal_t* cal);

// Load calibration from file
int nb_ioc_load_calibration(const char* path);

// Save calibration to file
int nb_ioc_save_calibration(const char* path, const nb_ioc_cal_t* cal);

// Close device
void nb_ioc_close(void);

#endif // NB_IOC_H
```

---

## Python Bindings: `binary_ioc.py`

```python
"""
binary_ioc.py — Python interface to Binary IOC (NB-IOC) driver
"""
import ctypes
import os
import numpy as np


class BinaryIOC:
    """
    Python interface to the binary optical chip.

    Wraps nb_ioc.so (C library) via ctypes.
    """

    def __init__(self, port: str = "/dev/ttyUSB0", cal_file: str = None):
        """
        Initialize connection to binary optical chip.

        Args:
            port: Serial port for FPGA communication
            cal_file: Path to calibration file (optional; defaults to ~/.config/nb_ioc_cal.json)
        """
        # Load C library
        lib_path = os.path.join(os.path.dirname(__file__), "nb_ioc.so")
        self._lib = ctypes.CDLL(lib_path)

        ret = self._lib.nb_ioc_init(port.encode())
        if ret != 0:
            raise RuntimeError(f"Failed to initialize NB-IOC on {port}")

        self._mode = "AND"

        if cal_file:
            self._lib.nb_ioc_load_calibration(cal_file.encode())

    def set_activation(self, bits: list[int]) -> None:
        """
        Set 9-element activation bit vector.

        Args:
            bits: List of 9 integers, each 0 or 1

        Example:
            ioc.set_activation([1, 0, 1, 0, 1, 0, 1, 0, 1])
        """
        assert len(bits) == 9 and all(b in (0, 1) for b in bits), \
            "bits must be list of 9 values, each 0 or 1"
        arr = (ctypes.c_int * 9)(*bits)
        self._lib.nb_ioc_set_activation(arr)

    def set_weights(self, matrix: list[list[int]]) -> None:
        """
        Set 9×9 weight matrix.

        Args:
            matrix: 9×9 list of lists, each value 0 or 1

        Example:
            W = [[1,0,...], [0,1,...], ...]  # 9 rows × 9 cols
            ioc.set_weights(W)
        """
        assert len(matrix) == 9 and all(len(row) == 9 for row in matrix)
        # Flatten row-major
        flat = [matrix[r][c] for r in range(9) for c in range(9)]
        arr = (ctypes.c_int * 81)(*flat)
        self._lib.nb_ioc_set_weights(arr)

    def set_mode(self, mode: str) -> None:
        """
        Set logic operation mode.

        Args:
            mode: "AND" | "OR" | "XOR"

        The physical glass never changes. Only the MZI encoding changes:
          AND: Direct encoding.
          OR:  Pre-invert inputs (De Morgan): NOT(NOT(a) AND NOT(b)).
          XOR: Three-AND composition — requires 3 passes or dual routing.
        """
        mode_map = {"AND": 0, "OR": 1, "XOR": 2}
        assert mode in mode_map, f"mode must be AND, OR, or XOR (got {mode})"
        self._lib.nb_ioc_set_mode(mode_map[mode])
        self._mode = mode

    def read_outputs(self) -> list[int]:
        """
        Read 9 output bit values.

        Returns:
            List of 9 integers (0 or 1), one per column.

        Uses detector threshold: current > 0.5 μA → bit 1.
        """
        # Call C function
        out = self._lib.nb_ioc_read_outputs()
        return list(out.bits)

    def compute(self, x: list[int], W: list[list[int]], mode: str = "AND") -> list[int]:
        """
        One-shot: encode → wait → read.

        Args:
            x: 9-element activation vector
            W: 9×9 weight matrix
            mode: "AND" | "OR" | "XOR"

        Returns:
            9-element output bit vector

        Example:
            y = ioc.compute([1,0,1,...], [[1,0,...], ...])
        """
        self.set_mode(mode)
        self.set_weights(W)
        self.set_activation(x)
        # Propagation time through chip: ~7.4 ps (negligible)
        # FPGA ADC read latency: ~1 μs
        return self.read_outputs()

    def calibrate(self, cal_file: str = None) -> dict:
        """
        Measure Vπ for all 18 MZI channels.

        Returns calibration dict and optionally saves to file.
        """
        # Call C calibration routine
        cal = ctypes.create_string_buffer(256)
        self._lib.nb_ioc_calibrate(cal)

        if cal_file:
            self._lib.nb_ioc_save_calibration(cal_file.encode(), cal)

        return {"calibrated": True}

    def close(self):
        self._lib.nb_ioc_close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
```

---

## Timing Specification

| Event | Time | Notes |
|-------|------|-------|
| Optical propagation through chip | ~7.4 ps | 1035μm / v_group |
| MZI switching (EO) | < 100 ps | TFLN bandwidth >10 GHz |
| DAC settling | < 1 μs | 18-channel DAC |
| ADC read | < 1 μs | 9-channel ADC |
| Total encode-compute-read cycle | **< 3 μs** | At 1 MHz operation |
| Maximum clock rate | **~333 MHz** | (1/3μs cycle) |

---

## Mode Descriptions

### AND Mode (default)

Direct SFG encoding. Physical chip computes AND directly.

```
y[j] = OR_i ( x[i] AND w[i][j] )
```

No pre-processing. MZI encodes bit as-is (0→1310nm, 1→1550nm).

### OR Mode

Uses De Morgan's theorem: `a OR b = NOT(NOT(a) AND NOT(b))`

Driver pre-inverts inputs before encoding:
- bit 0 → 1550nm (inverted)
- bit 1 → 1310nm (inverted)

Column output is then inverted in software.

### XOR Mode

`a XOR b = (a AND NOT(b)) OR (NOT(a) AND b)`

Requires two passes through the array:
1. Pass 1: x = activation, w = NOT(weight) → partial result P1
2. Pass 2: x = NOT(activation), w = weight → partial result P2
3. Result = P1 OR P2

XOR is slower (2× latency) due to two passes.

---

## Calibration File Format (JSON)

```json
{
  "version": 1,
  "chip_id": "NB-9x9-001",
  "timestamp": "2026-02-27T12:00:00Z",
  "temperature_c": 25.0,
  "v_pi": {
    "ACT_0": 2.05, "ACT_1": 1.98, "ACT_2": 2.12,
    "ACT_3": 2.01, "ACT_4": 2.08, "ACT_5": 1.95,
    "ACT_6": 2.11, "ACT_7": 2.03, "ACT_8": 1.99,
    "WT_0": 2.07,  "WT_1": 2.00,  "WT_2": 2.09,
    "WT_3": 2.04,  "WT_4": 2.06,  "WT_5": 1.97,
    "WT_6": 2.10,  "WT_7": 2.02,  "WT_8": 2.05
  },
  "dark_current_ua": {
    "DET_0": 0.12, "DET_1": 0.09, "DET_2": 0.11,
    "DET_3": 0.10, "DET_4": 0.13, "DET_5": 0.08,
    "DET_6": 0.12, "DET_7": 0.11, "DET_8": 0.10
  },
  "detection_threshold_ua": 0.5
}
```

---

## Error Codes

| Code | Name | Description |
|------|------|-------------|
| 0 | OK | Success |
| -1 | NB_ERR_INIT | Failed to open serial port |
| -2 | NB_ERR_TIMEOUT | FPGA communication timeout |
| -3 | NB_ERR_CAL | Calibration out of spec |
| -4 | NB_ERR_BITS | Invalid bit value (not 0 or 1) |
| -5 | NB_ERR_MODE | Invalid mode |
| -6 | NB_ERR_LASER | Laser power too low (below threshold) |
