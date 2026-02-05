# TPU Architecture - AI Accelerator Path

This directory contains the optical tensor processing unit (TPU) implementation - optimized for AI/ML workloads using systolic array architecture.

## Core Concept

**Streaming matrix operations via WDM parallel processing**

Unlike the general-purpose CPU path, this architecture is purpose-built for:
- Matrix multiplication (GEMM operations)
- Convolutions
- Transformer attention patterns
- Any operation that can be expressed as systolic data flow

## Key Files

### Core Systolic Array
- **`optical_systolic_array.py`** - Base systolic array implementation using ternary optical elements
- **`c_band_wdm_systolic.py`** - WDM-enhanced version using C-band wavelength channels for parallel lanes
- **`super_ioc_module.py`** - Super integrated optical compute module (scaled-up IOC)
- **`integrated_supercomputer.py`** - Full system integration with memory hierarchy

### Application-Specific Generators
- **`home_ai/`** - Home AI accelerator designs (edge inference)
- **`supercomputer/`** - Exascale supercomputer configurations

## Architecture Highlights

1. **Systolic Data Flow** - Data streams through a 2D array of processing elements, maximizing reuse
2. **WDM Parallelism** - Multiple wavelength channels operate simultaneously (up to 80 channels in C-band)
3. **Ternary Advantage** - 3-state encoding (1550nm/1310nm/1064nm) provides log3/log2 = 1.58x density improvement
4. **Streaming Architecture** - Continuous data flow, no fetch-decode-execute overhead

## Performance Targets

| Configuration | Peak Performance | Notes |
|--------------|------------------|-------|
| 27x27 array | 583 TFLOPS | Single chip, base |
| 243x243 array | 47 PFLOPS | Multi-chiplet |
| 960x960 array | 738 PFLOPS | Full scale |

*Performance scales with array size squared and WDM channel count*

## vs General-Purpose Path

The `standard_computer/` directory contains the von Neumann architecture path (fetch-decode-execute, branching, etc.). This TPU path trades flexibility for raw throughput on tensor operations.

**Use TPU path for:** Training, inference, any matrix-heavy workload
**Use CPU path for:** Control flow, I/O handling, general compute
