# N-Radix Driver Specification

**Version:** 1.0
**Date:** February 5, 2026
**Author:** Christopher Riner
**For:** Driver Developer

---

## Executive Summary

This document specifies the software driver interface for the Wavelength-Division Ternary N-Radix accelerator. The driver's job is to bridge standard binary computing (PCIe/host) with the optical ternary chip via the NR-IOC (N-Radix Input/Output Converter).

**The simple version:** Binary data goes in, gets converted to optical ternary, the chip does matrix math at light speed, results come back as binary.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HOST SYSTEM                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │   User      │    │   Driver    │    │    PCIe     │             │
│  │   App       │───▶│  (YOU ARE   │───▶│  Interface  │             │
│  │             │    │   HERE)     │    │             │             │
│  └─────────────┘    └─────────────┘    └──────┬──────┘             │
└─────────────────────────────────────────────────┼───────────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   NR-IOC (N-Radix Input/Output Converter)            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                                                               │   │
│  │   Binary Input ──▶ [ENCODE 3^3] ──▶ Ternary Optical Signals  │   │
│  │                                                               │   │
│  │   Binary Output ◀── [DECODE 3^3] ◀── Ternary Optical Signals │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Conversion time: ~6.5ns (negligible)                               │
└─────────────────────────────────────────────────────────────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       N-RADIX OPTICAL CHIP                          │
│                                                                      │
│    Systolic array of Processing Elements (PEs)                      │
│    All PEs do add/subtract on optical signals                       │
│    Weights stored in bistable Kerr resonators                       │
│    Clock: 617 MHz (central Kerr optical clock)                      │
│                                                                      │
│    *** DRIVER DOESN'T TOUCH THIS - IT'S ALL PHOTONS ***             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## What the Driver Does

### Primary Functions

1. **Memory Management**
   - Allocate buffers for input matrices (activations)
   - Allocate buffers for weight matrices
   - Allocate buffers for output results
   - Handle DMA transfers to/from NR-IOC

2. **Encoding (Host → NR-IOC)**
   - Convert floating-point matrices to balanced ternary
   - Apply 3^3 scaling (each trit represents trit³)
   - Pack trits efficiently for PCIe transfer

3. **Decoding (NR-IOC → Host)**
   - Receive ternary results from NR-IOC
   - Apply inverse 3^3 scaling
   - Convert back to floating-point

4. **Command Interface**
   - Load weights to PE array
   - Stream activations through array
   - Trigger computation
   - Collect results

5. **Synchronization**
   - Wait for weight loading complete
   - Wait for computation complete
   - Handle interrupts from NR-IOC

---

## Encoding Specification

### Balanced Ternary Basics

Each **trit** has three values:

| Trit Value | Meaning | Optical Wavelength |
|------------|---------|-------------------|
| **-1** | Negative | 1550nm (Red) |
| **0** | Zero | 1310nm (Green) |
| **+1** | Positive | 1064nm (Blue) |

### Converting Float to Balanced Ternary

```python
def float_to_balanced_ternary(value, num_trits=9):
    """
    Convert a floating-point value to balanced ternary.

    Args:
        value: Float in range [-1.0, 1.0] (normalized)
        num_trits: Number of trits (default 9 = ~14 bits precision)

    Returns:
        List of trits [-1, 0, or 1]
    """
    # Scale to integer range
    max_val = (3 ** num_trits - 1) // 2
    scaled = int(round(value * max_val))

    trits = []
    for _ in range(num_trits):
        remainder = scaled % 3
        if remainder == 0:
            trits.append(0)
            scaled = scaled // 3
        elif remainder == 1:
            trits.append(1)
            scaled = scaled // 3
        else:  # remainder == 2, treat as -1 carry 1
            trits.append(-1)
            scaled = (scaled + 1) // 3

    return trits
```

### 3^3 Encoding (The Key Part)

The NR-IOC applies **3^3 encoding** - each trit represents **trit³** worth of value.

**Driver responsibility:** The driver does NOT do the 3^3 math. The driver just:
1. Converts floats to balanced ternary
2. Sends trits to NR-IOC
3. NR-IOC handles the 3^3 interpretation internally

**Why this matters:** The optical hardware operates on trits. The NR-IOC interprets those trits as trit³. The driver just needs to know the input/output value ranges are cubed.

```python
# Example: Sending value 0.5 to an ADD/SUB PE
#
# Driver converts: 0.5 → balanced ternary trits
# Driver sends: trits to NR-IOC
# NR-IOC interprets: each trit as trit³ (3^3 encoding)
# Optical chip: does add/subtract on optical signals
# NR-IOC returns: result trits
# Driver converts: trits → float (accounting for 3^3 range)
```

### Value Ranges

| Mode | Trit Represents | Effective Range | Precision |
|------|-----------------|-----------------|-----------|
| Base (no scaling) | trit | [-1, +1] | ~1.58 bits/trit |
| 3^3 encoding | trit³ | [-1, +1] | Same, but 9× compute density |

**Note:** The *range* stays [-1, +1] for normalized values. The 3^3 encoding affects how much *computational work* each operation represents, not the numeric range.

---

## PE Types and Interpretation

The chip has two types of Processing Elements:

| PE Type | What It Does | NR-IOC Interpretation |
|---------|--------------|-------------------|
| **ADD/SUB** | Optical add/subtract | trit³ = addition value |
| **MUL/DIV** | Optical add/subtract (in log domain) | trit³ = multiplication value |

**Both use the same 3^3 encoding.** The NR-IOC knows which PE type it's talking to and interprets accordingly.

**Driver responsibility:** Tag each operation with its type (ADD or MUL) so the NR-IOC applies correct interpretation.

---

## Command Interface

### Command Structure

```c
typedef struct {
    uint32_t command;       // Command type (see below)
    uint32_t flags;         // Operation flags
    uint64_t src_addr;      // Source buffer address
    uint64_t dst_addr;      // Destination buffer address
    uint32_t width;         // Matrix width
    uint32_t height;        // Matrix height
    uint32_t pe_type;       // 0 = ADD/SUB, 1 = MUL/DIV
} nrioc_command_t;
```

### Commands

| Command | Value | Description |
|---------|-------|-------------|
| `NR_LOAD_WEIGHTS` | 0x01 | Load weight matrix to PE array |
| `NR_STREAM_INPUT` | 0x02 | Stream activation matrix through array |
| `NR_COMPUTE` | 0x03 | Trigger computation (weights × inputs) |
| `NR_READ_OUTPUT` | 0x04 | Read results from output edge |
| `NR_RESET` | 0x0F | Reset NR-IOC state |

### Typical Operation Sequence

```c
// 1. Load weights (done once per layer)
nrioc_command_t cmd = {
    .command = NR_LOAD_WEIGHTS,
    .src_addr = weight_buffer,
    .width = 27,
    .height = 27,
    .pe_type = PE_TYPE_MUL  // Weights are for multiplication
};
nrioc_submit(&cmd);
nrioc_wait_complete();

// 2. Stream inputs and compute (done per batch)
cmd.command = NR_STREAM_INPUT;
cmd.src_addr = input_buffer;
cmd.pe_type = PE_TYPE_ADD;  // Accumulation is addition
nrioc_submit(&cmd);
nrioc_wait_complete();

// 3. Read outputs
cmd.command = NR_READ_OUTPUT;
cmd.dst_addr = output_buffer;
nrioc_submit(&cmd);
nrioc_wait_complete();
```

---

## Timing Budget

| Operation | Time | Notes |
|-----------|------|-------|
| PCIe transfer (per KB) | ~1 μs | PCIe Gen4 x16 |
| NR-IOC encode (per trit) | ~0.5 ns | Part of 6.5ns total |
| NR-IOC decode (per trit) | ~0.5 ns | Part of 6.5ns total |
| **NR-IOC total conversion** | **~6.5 ns** | Negligible |
| Weight load (27×27) | ~4.9 ns | 3 clocks @ 617 MHz |
| Weight load (81×81) | ~131 ns | 81 clocks @ 617 MHz |
| Compute (systolic pass) | ~N clocks | N = array dimension |

**Key insight:** The NR-IOC conversion (6.5ns) is negligible. PCIe transfer dominates for small batches. For large batches, compute dominates.

---

## Performance Expectations

### Raw Numbers

| Array Size | Base Performance | With 3^3 (ADD-heavy) | With 3^3 (Matrix Mul) |
|------------|------------------|----------------------|----------------------|
| 27×27 | 65 TFLOPS | 583 TFLOPS | ~117 TFLOPS |
| 81×81 | 583 TFLOPS | 5.2 PFLOPS | ~1.0 PFLOPS |
| 243×243 | 5.2 PFLOPS | 47 PFLOPS | ~9.4 PFLOPS |

### Why Matrix Multiply is ~1.8×, Not 9×

Matrix multiply is 50% multiply operations, 50% add operations.
- ADD portion: 9× speedup (benefits from 3^3)
- MUL portion: 1× (no speedup, stays at baseline)
- Combined: ~1.8× using Amdahl's Law

| Workload | ADD % | MUL % | Overall Boost |
|----------|-------|-------|---------------|
| Matrix multiply | 50% | 50% | ~1.8× |
| Transformer attention | 60% | 40% | ~2.1× |
| Pure accumulation | 100% | 0% | 9× |
| Pure multiply | 0% | 100% | 1× |

---

## Error Handling

### NR-IOC Status Codes

| Status | Value | Meaning |
|--------|-------|---------|
| `NR_OK` | 0x00 | Success |
| `NR_BUSY` | 0x01 | Operation in progress |
| `NR_ERR_OVERFLOW` | 0x10 | Arithmetic overflow |
| `NR_ERR_ALIGNMENT` | 0x11 | Buffer alignment error |
| `NR_ERR_SIZE` | 0x12 | Matrix size exceeds array |
| `NR_ERR_TIMEOUT` | 0x20 | Operation timeout |

### Overflow Handling

Ternary arithmetic can overflow (e.g., 1 + 1 = 2, which doesn't fit in one trit). The NR-IOC handles carries automatically within the systolic array. The driver should:

1. Normalize inputs to [-1, +1] range
2. Check for `NR_ERR_OVERFLOW` on output
3. Implement saturation or scaling if overflow occurs

---

## Memory Layout

### Buffer Alignment

- All buffers must be 64-byte aligned (cache line)
- Minimum allocation: 4KB (page aligned preferred)

### Trit Packing

Pack 5 trits per byte (3^5 = 243 < 256):

```c
// Packing: 5 trits → 1 byte
// Trit values: -1, 0, +1 mapped to 0, 1, 2
uint8_t pack_trits(int8_t t0, int8_t t1, int8_t t2, int8_t t3, int8_t t4) {
    return (t0 + 1) +
           (t1 + 1) * 3 +
           (t2 + 1) * 9 +
           (t3 + 1) * 27 +
           (t4 + 1) * 81;
}

// Unpacking: 1 byte → 5 trits
void unpack_trits(uint8_t packed, int8_t *trits) {
    trits[0] = (packed % 3) - 1;
    trits[1] = ((packed / 3) % 3) - 1;
    trits[2] = ((packed / 9) % 3) - 1;
    trits[3] = ((packed / 27) % 3) - 1;
    trits[4] = ((packed / 81) % 3) - 1;
}
```

### Matrix Storage

Row-major order, packed trits:

```
Matrix[H][W] where each element is 9 trits (2 bytes packed)

Memory layout:
[row0_col0][row0_col1]...[row0_colW-1]
[row1_col0][row1_col1]...[row1_colW-1]
...
[rowH-1_col0]...[rowH-1_colW-1]
```

---

## API Summary

### Initialization

```c
int nrioc_init(void);                    // Initialize driver
int nrioc_get_array_size(int *w, int *h); // Get PE array dimensions
void nrioc_shutdown(void);               // Cleanup
```

### Memory

```c
void* nrioc_alloc(size_t size);          // Allocate NR-IOC-accessible buffer
void nrioc_free(void *ptr);              // Free buffer
int nrioc_memcpy_to(void *dst, void *src, size_t n);   // Host → NR-IOC
int nrioc_memcpy_from(void *dst, void *src, size_t n); // NR-IOC → Host
```

### Operations

```c
int nrioc_load_weights(void *weights, int w, int h);
int nrioc_compute(void *input, void *output, int w, int h);
int nrioc_wait(int timeout_ms);
int nrioc_get_status(void);
```

### Conversion Helpers

```c
int float_matrix_to_ternary(float *src, void *dst, int w, int h);
int ternary_to_float_matrix(void *src, float *dst, int w, int h);
```

---

## Quick Reference Card

```
┌────────────────────────────────────────────────────────────────┐
│                NR-IOC DRIVER QUICK REFERENCE                    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TRIT VALUES:  -1 (1550nm)  |  0 (1310nm)  |  +1 (1064nm)     │
│                                                                 │
│  ENCODING:     3^3 for both ADD/SUB and MUL/DIV PEs           │
│                NR-IOC handles interpretation                    │
│                                                                 │
│  PRECISION:    9 trits ≈ 14 bits                               │
│                                                                 │
│  TIMING:       NR-IOC conversion: 6.5ns (negligible)           │
│                Weight load 27×27: ~5ns                         │
│                Weight load 81×81: ~131ns                       │
│                                                                 │
│  PERFORMANCE:  Matrix multiply: ~1.8× boost                    │
│                Pure accumulation: 9× boost                      │
│                                                                 │
│  COMMANDS:     LOAD_WEIGHTS → STREAM_INPUT → READ_OUTPUT       │
│                                                                 │
│  BUFFERS:      64-byte aligned, 5 trits/byte packing          │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Files to Reference

| File | Description |
|------|-------------|
| `Research/programs/nradix_architecture/README.md` | Full architecture documentation |
| `Research/programs/nradix_architecture/nrioc_tower_test.py` | NR-IOC encoding test code |
| `Research/programs/shared/nrioc_module.py` | NR-IOC module design |
| `docs/analytical_scaling_results.md` | Performance projections |

---

## Questions?

Contact: chrisriner45@gmail.com

---

*Document generated with assistance from Claude Opus 4.5*
