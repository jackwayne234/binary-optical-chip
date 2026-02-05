# CPU Architecture - General-Purpose Computing Path

This folder contains the general-purpose computing components for ternary optical processing.

## Overview

While the systolic array path handles parallel matrix operations (ML/AI workloads), this path implements **sequential, instruction-driven computing** - the traditional CPU model adapted for optical ternary hardware.

## Key Components

### Core
- `ternary_isa_simulator.py` - Ternary instruction set architecture simulator
- `opu_controller.py` - Optical Processing Unit control logic

### Memory Hierarchy (`memory/`)
Three-tier optical RAM system:
- `ternary_tier1_ram_generator.py` - L1 cache equivalent (fastest, smallest)
- `ternary_tier2_ram_generator.py` - L2 cache equivalent (balanced)
- `ternary_tier3_ram_generator.py` - Main memory equivalent (largest, slower)

### General Purpose (`general_purpose/`)
Standard computer architecture components for general workloads.

## Design Philosophy

This path enables:
- **Branching & control flow** - Conditional execution based on ternary comparisons
- **Sequential operations** - Step-by-step instruction execution
- **Memory addressing** - Pointer arithmetic and indirect access
- **ISA abstraction** - High-level programming model

Contrasts with the systolic array path which is:
- Massively parallel but fixed-function
- Optimized for matrix multiply-accumulate
- Data-flow driven rather than instruction-driven

## Use Cases

- Operating system kernels
- Control logic and orchestration
- Workloads with unpredictable branching
- Memory-intensive random access patterns
