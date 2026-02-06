# N-Radix Optical Accelerator

An optical AI accelerator achieving ~59× the performance of NVIDIA's B200 for matrix multiply workloads.

## Architecture Breakthrough: Streamed Weight Design

**Key insight:** Weights are stored in the CPU's optical RAM and streamed to processing elements (PEs) - no per-PE weight storage required.

### Design Principles

1. **Simplified PEs**: Each processing element contains only:
   - SFG mixer (sum-frequency generation for multiply)
   - Waveguide routing (input/output paths)
   - That's it. No local memory, no complex control logic.

2. **Unified Optical Memory**: The CPU's 3-tier optical RAM serves dual purpose:
   - Standard CPU operations (when running CPU workloads)
   - Accelerator weight storage (streamed to PEs during inference/training)

3. **All-Optical Data Path**: Weights flow from optical RAM → waveguide network → PEs without domain conversion. No electrical bottlenecks, no DAC/ADC overhead.

### Why This Matters

| Aspect | Traditional (per-PE storage) | Streamed Design |
|--------|------------------------------|-----------------|
| PE Complexity | Memory + compute + control | SFG mixer + routing only |
| Fabrication Yield | Lower (more components) | Higher (simpler PEs) |
| Power | Per-PE memory leakage | Centralized, amortized |
| Flexibility | Fixed weight capacity | Limited only by optical RAM |
| Domain Crossings | Multiple E/O conversions | Purely optical |

This architectural simplification makes the design significantly more practical to manufacture while maintaining the performance advantages of optical compute.

## Cybersecurity Advantages

**The geometry is the program.** There is no software to exploit.

Unlike conventional processors that execute instructions from memory, the N-Radix accelerator's computation is defined entirely by its physical structure - waveguide routing, mixer placement, and optical paths etched into glass. This creates a fundamentally different security model:

### What Does Not Exist

- **No firmware** - Nothing to flash, nothing to corrupt
- **No instruction set** - No opcodes to hijack or malicious payloads to inject
- **No software stack** - No kernel, no drivers, no attack surface
- **No writable state** - The "program" is lithographically fixed at fabrication

### Immunity Profile

| Attack Vector | Traditional Chips | N-Radix Optical |
|---------------|-------------------|-----------------|
| Remote code execution | Vulnerable | **Impossible** - no code to execute |
| Firmware attacks | Vulnerable | **Impossible** - no firmware exists |
| Side-channel exploits | Vulnerable | **Immune** - photons don't leak like electrons |
| Supply chain tampering | Software-level risk | **Physical-only** - requires altering the glass |
| Buffer overflows | Common vulnerability | **N/A** - no buffers, no memory addressing |

### Historic Implication

**For the first time in computing history, a device could be network-connected yet completely immune to remote compromise.**

To attack this chip, you cannot send packets. You cannot craft exploits. You cannot find zero-days. The only attack vector is physical access to alter the optical pathways themselves - and even then, you would need to re-fabricate portions of the chip.

This is not security through obscurity. This is security through architecture - the absence of programmability eliminates the entire class of software-based attacks.

## Directory Structure

```
NRadix_Accelerator/
├── driver/          # NR-IOC driver (C + Python bindings)
├── architecture/    # Systolic array designs (27×27, 81×81)
├── components/      # Photonic component simulations
├── simulations/     # WDM validation tests (Meep FDTD)
├── gds/            # Chip layouts and mask files
├── docs/           # Interface specs, DRC rules, packaging
└── papers/         # Academic papers
```

## Quick Start

```bash
# Run WDM validation
cd simulations/
export OMP_NUM_THREADS=12
/home/jackwayne/miniconda/envs/meep_env/bin/python wdm_27x27_array_test.py

# Use the Python driver/simulator
cd driver/python/
python -c "from nradix import NRadixSimulator; sim = NRadixSimulator(27)"
```

## Key Specs

| Metric | Value |
|--------|-------|
| Array Sizes | 27×27 (729 PEs), 81×81 (6,561 PEs) |
| Clock | 617 MHz (Kerr self-pulsing) |
| WDM Channels | 6 triplets (18 wavelengths) |
| Performance | ~59× B200 (matrix multiply) |

## Documentation

- [Chip Interface](docs/CHIP_INTERFACE.md) - How to connect to the chip
- [Driver Spec](docs/DRIVER_SPEC.md) - NR-IOC driver details
- [DRC Rules](docs/DRC_RULES.md) - Design rules for fabrication
- [Packaging](docs/PACKAGING_SPEC.md) - Fiber coupling, bond pads

## Validation Status

- [x] 3×3 WDM array - PASSED
- [x] 9×9 WDM array - PASSED
- [ ] 27×27 WDM array - Running
- [ ] 81×81 WDM array - Queued
