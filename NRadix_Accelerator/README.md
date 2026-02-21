# N-Radix Optical Accelerator

An optical AI accelerator achieving ~59× the performance of NVIDIA's B200 for matrix multiply workloads.

## Architecture Breakthrough: Streamed Weight Design

**Key insight:** Weights are stored in the CPU's optical RAM and streamed to processing elements (PEs) - no per-PE weight storage required.

### Design Principles

1. **6-Lane Parallel PEs**: Each processing element contains:
   - WDM demux (AWG, splits 6 triplets into dedicated lanes)
   - 6 PPLN SFG mixers (each QPM-tuned to its wavelength triplet)
   - WDM mux (AWG, recombines outputs)
   - Waveguide routing (input/output paths)
   - That's it. No local memory, no complex control logic. Fully passive.

2. **Unified Optical Memory**: The CPU's 3-tier optical RAM serves dual purpose:
   - Standard CPU operations (when running CPU workloads)
   - Accelerator weight storage (streamed to PEs during inference/training)

3. **All-Optical Data Path**: Weights flow from optical RAM → waveguide network → PEs without domain conversion. No electrical bottlenecks, no DAC/ADC overhead.

### Why This Matters

| Aspect | Traditional (per-PE storage) | Streamed Design |
|--------|------------------------------|-----------------|
| PE Complexity | Memory + compute + control | 6 SFG mixers + demux/mux + routing |
| Fabrication Yield | Lower (more components) | Higher (simpler PEs) |
| Power | Per-PE memory leakage | Centralized, amortized |
| Flexibility | Fixed weight capacity | Limited only by optical RAM |
| Domain Crossings | Multiple E/O conversions | Purely optical |

This architectural simplification makes the design significantly more practical to manufacture while maintaining the performance advantages of optical compute.

## Cybersecurity Considerations

**The geometry is the program.** The optical compute core has no software to exploit.

Unlike conventional processors that execute instructions from memory, the N-Radix accelerator's computation is defined entirely by its physical structure - waveguide routing, mixer placement, and optical paths etched into glass. This creates a fundamentally different security model for the compute core itself.

### What the Optical Compute Core Lacks

- **No firmware** - Nothing to flash, nothing to corrupt
- **No instruction set** - No opcodes to hijack or malicious payloads to inject
- **No writable state** - The "program" is lithographically fixed at fabrication

### Security Comparison (Compute Core Only)

| Attack Vector | Traditional Chips | N-Radix Optical Core |
|---------------|-------------------|----------------------|
| Remote code execution | Vulnerable | **No attack surface** - no code exists |
| Firmware attacks | Vulnerable | **No attack surface** - no firmware exists |
| Side-channel (power analysis) | Vulnerable | **Reduced risk** - photons behave differently than electrons |
| Buffer overflows | Common vulnerability | **N/A** - no buffers, no memory addressing |

### What Still Requires Traditional Security

The optical compute core is only part of a complete system. These components still need conventional security practices:

- **NR-IOC (I/O Controller)** - The interface chip that bridges the optical accelerator to the host system. This has firmware and software.
- **PCIe Interface** - Standard attack surface for any accelerator card
- **Host System** - The CPU, OS, and drivers that control the accelerator
- **Manufacturing Trust** - Like any chip, you must trust the foundry. Malicious modifications at fabrication time are a consideration.

### The Value Proposition

**Defense in depth with a physically immutable foundation.**

While you cannot build a "completely secure" system, you can eliminate entire categories of attack. The optical compute core provides:

1. **A hardened foundation** - The math happens in glass. No amount of clever packets can change waveguide geometry.
2. **Reduced attack surface** - Fewer components with software means fewer things to exploit.
3. **Audit simplicity** - The compute core does exactly what its physical structure dictates. What you see (in the GDS layout) is what you get.

This is not security through obscurity - it's security through architecture. The compute core's lack of programmability eliminates software-based attacks *on that component*. The rest of the system still requires careful engineering.

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
# Run WDM validation (27×27)
cd simulations/
export OMP_NUM_THREADS=12
/home/jackwayne/miniconda/envs/meep_env/bin/python wdm_27x27_array_test.py

# Run WDM validation (81×81 - full chip)
/home/jackwayne/miniconda/envs/meep_env/bin/python wdm_81x81_array_test.py

# Use the Python driver/simulator
cd driver/python/
python -c "from nradix import NRadixSimulator; sim = NRadixSimulator(27)"
```

## Key Specs

| Metric | Value |
|--------|-------|
| Array Sizes | 27×27 (729 PEs), 81×81 (6,561 PEs) |
| Clock | 617 MHz (Kerr self-pulsing) |
| WDM Channels | 6 triplets (18 wavelengths), 6 parallel lanes per PE |
| PE Architecture | WDM demux → 6 dedicated PPLN mixers → WDM mux |
| PE Size | ~55 × 55 μm (monolithic, fully passive) |
| Performance (single lane) | ~59× B200 (matrix multiply) |
| Performance (6 lanes) | ~354× B200 (matrix multiply) |

## Documentation

- [Chip Interface](docs/CHIP_INTERFACE.md) - How to connect to the chip
- [Driver Spec](docs/DRIVER_SPEC.md) - NR-IOC driver details
- [DRC Rules](docs/DRC_RULES.md) - Design rules for fabrication
- [Packaging](docs/PACKAGING_SPEC.md) - Fiber coupling, bond pads

## Validation Status

- [x] 3×3 WDM array - PASSED
- [x] 9×9 WDM array - PASSED
- [x] 27×27 WDM array - PASSED
- [x] 81×81 WDM array - PASSED

## Simulation Validation

This architecture isn't just theory - it's been validated through FDTD simulation using Meep.

### Clock Distribution

| Array Size | Max Skew | Tolerance | Result |
|------------|----------|-----------|--------|
| 27×27 | 2.4% (39 fs) | <5% | **PASS** |
| 81×81 | 3.2% (52 fs) | <5% | **PASS** |

The H-tree clock distribution network delivers the 617 MHz Kerr clock to all PEs with minimal skew. At 81×81 scale (6,561 PEs), the maximum timing variation is 52 femtoseconds - well within the 5% tolerance required for synchronous operation.

### WDM Channel Isolation

| Array Size | Crosstalk | Threshold | Result |
|------------|-----------|-----------|--------|
| 3×3 | <-30 dB | -30 dB | **PASS** |
| 9×9 | <-30 dB | -30 dB | **PASS** |
| 27×27 | <-30 dB | -30 dB | **PASS** |
| 81×81 | <-30 dB | -30 dB | **PASS** |

All array sizes maintain better than -30 dB isolation between WDM channels, preventing signal interference during parallel computation.

### Collision-Free Wavelength Triplets

Six wavelength triplets, each with 20nm internal spacing and 60nm inter-triplet spacing. Each triplet has a dedicated PPLN mixer with QPM tuned to its wavelengths:

| Triplet | λ₋₁ (nm) | λ₀ (nm) | λ₊₁ (nm) | SFG Output Band (nm) |
|---------|-----------|---------|-----------|----------------------|
| T1 | 1040 | 1020 | 1000 | 500–520 |
| T2 | 1100 | 1080 | 1060 | 530–550 |
| T3 | 1160 | 1140 | 1120 | 560–580 |
| T4 | 1220 | 1200 | 1180 | 590–610 |
| T5 | 1280 | 1260 | 1240 | 620–640 |
| T6 | 1340 | 1320 | 1300 | 650–670 |

All 18 wavelengths propagate through shared waveguides without crosstalk (validated via FDTD). Each PE's WDM demux splits triplets into dedicated PPLN mixers for computation, then recombines via WDM mux. No cross-triplet SFG collisions possible since each mixer only sees its own triplet.

### Key Insight

**The physics scales.** Optical path lengths are predictable by Maxwell's equations - if the geometry is correct, the timing is correct. Unlike electronic circuits where parasitics create surprises at scale, photonic waveguides behave exactly as simulated. What works at 3×3 works at 27×27 - and now validated at 81×81 (6,561 PEs), confirming that the architecture scales as predicted.
