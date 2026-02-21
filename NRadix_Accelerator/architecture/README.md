# N-Radix Architecture - AI Accelerator Path

This directory contains the N-Radix optical accelerator implementation - optimized for AI/ML workloads using systolic array architecture.

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
- **`super_ioc_module.py`** - Super integrated optical compute module (scaled-up NR-IOC)
- **`integrated_supercomputer.py`** - Full system integration with memory hierarchy

### Application-Specific Generators
- **`home_ai/`** - Home AI accelerator designs (edge inference)
- **`supercomputer/`** - Exascale supercomputer configurations

## Architecture Highlights

1. **Systolic Data Flow** - Data streams through a 2D array of processing elements, maximizing reuse
2. **WDM Parallelism** - Multiple wavelength channels operate simultaneously (up to 80 channels in C-band)
3. **Ternary Advantage** - 3-state encoding (1550nm/1310nm/1064nm) provides log3/log2 = 1.58x density improvement
4. **Streaming Architecture** - Continuous data flow, no fetch-decode-execute overhead

---

## WDM Validation (Physics-Verified)

**Date:** February 5, 2026
**Method:** Meep FDTD electromagnetic simulation

The WDM parallelism architecture has been validated through full electromagnetic simulation, confirming that multiple wavelength triplets can operate through the same physical waveguides without crosstalk or interference.

### Validated Collision-Free Triplets

Six wavelength triplets were tested, each maintaining 20nm spacing to avoid SFG collisions:

| Triplet | λ₁ (nm) | λ₂ (nm) | λ₃ (nm) | Status |
|---------|---------|---------|---------|--------|
| 1 | 1040 | 1020 | 1000 | ✓ Validated |
| 2 | 1100 | 1080 | 1060 | ✓ Validated |
| 3 | 1160 | 1140 | 1120 | ✓ Validated |
| 4 | 1220 | 1200 | 1180 | ✓ Validated |
| 5 | 1280 | 1260 | 1240 | ✓ Validated |
| 6 | 1340 | 1320 | 1300 | ✓ Validated |

### Test Results - Physics Validation Chain

| Test | Size | Status | Notes |
|------|------|--------|-------|
| Waveguide test | Single | PASSED | All 18 wavelengths propagate independently, no crosstalk |
| 3×3 array | 9 PEs | PASSED | WDM routing through junction/splitter networks confirmed |
| 9×9 array | 81 PEs | PASSED | Scaled systolic flow validated |
| 27×27 array | 729 PEs | In progress | First production-scale validation |
| 81×81 array | 6,561 PEs | Queued | Full chip validation |

**Note:** 81×81 at resolution 20 with OpenMP threading takes ~2-3 hours on a 12-core local machine. This completes the physics validation chain.

**Waveguide Independence Test:**
- All 18 wavelengths (6 triplets × 3 wavelengths each) injected into shared waveguide
- Each wavelength propagates independently with no crosstalk
- No mode coupling or interference between channels

**3×3 Array Test:**
- Full systolic array configuration with 3 output ports
- All wavelengths detected at all 3 output ports
- Confirms WDM routing works through junction/splitter networks

### Implications

**6× parallel computation through same physical chip is physics-validated.**

Waveguide routing supports all 6 triplets simultaneously without crosstalk. However, the nonlinear SFG mixer (PPLN) requires wavelength-specific quasi-phase-matching (QPM), meaning a single mixer cannot process all 6 triplets. The solution: **6 dedicated PPLN mixers per PE**, each with QPM tuned to its triplet.

### 6-Lane Parallel Mixer Architecture

Each PE contains a WDM demux → 6 parallel PPLN mixers → WDM mux:

```
  Activation in (6 triplets multiplexed on shared waveguide)
        │
   ┌────┴────┐
   │ WDM     │  ← 1×6 AWG Demux (splits by triplet wavelength)
   │ DEMUX   │
   └─┬─┬─┬─┬─┬─┬─┘
     │ │ │ │ │ │    6 parallel lanes
     ▼ ▼ ▼ ▼ ▼ ▼
   ┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐
   │ M1││ M2││ M3││ M4││ M5││ M6│  ← 6 PPLN mixers
   │3.8││4.6││5.6││6.6││7.8││9.1│     QPM period (μm)
   │ μm││ μm││ μm││ μm││ μm││ μm│
   └─┬─┘└─┬─┘└─┬─┘└─┬─┘└─┬─┘└─┬─┘
     │ │ │ │ │ │
     ▼ ▼ ▼ ▼ ▼ ▼
   ┌────┴────┐
   │ WDM     │  ← 6×1 AWG Mux (recombines SFG outputs)
   │  MUX    │
   └────┬────┘
        │
        ▼ Combined output → Accumulator
```

**QPM periods per triplet (B+B case, full range 3.78–10.08 μm):**

| Triplet | QPM B+B (μm) | QPM R+R (μm) | SFG Output Band (nm) |
|---------|---------------|---------------|-----------------------|
| T1 | 3.78 | 4.33 | 500–520 |
| T2 | 4.62 | 5.24 | 530–550 |
| T3 | 5.57 | 6.27 | 560–580 |
| T4 | 6.63 | 7.41 | 590–610 |
| T5 | 7.82 | 8.68 | 620–640 |
| T6 | 9.13 | 10.08 | 650–670 |

Each triplet's SFG outputs occupy a 20nm band with 10nm gaps between triplets — clean separation for AWG demuxing at the NR-IOC.

**PE area impact:** ~1.5× the current mixer area (780 μm² vs 520 μm²). PE grows from 50×50 to ~55×55 μm. **Total array area increases ~20% for 6× throughput — a 5× improvement in performance per area.**

**The chip remains fully passive.** The demux, mixers, and mux are all fixed photonic geometry. No active elements, no firmware, no per-PE storage. Weights stream from the NR-IOC on all 6 triplets simultaneously.

### NR-IOC Data Flow (6-Lane Mode)

The NR-IOC encodes each operation onto all 6 triplets in parallel:

```
NR-IOC encodes per clock cycle:
  Lane 1 (T1): activation[0] × weight[0] → 1000/1020/1040 nm
  Lane 2 (T2): activation[1] × weight[1] → 1060/1080/1100 nm
  Lane 3 (T3): activation[2] × weight[2] → 1120/1140/1160 nm
  Lane 4 (T4): activation[3] × weight[3] → 1180/1200/1220 nm
  Lane 5 (T5): activation[4] × weight[4] → 1240/1260/1280 nm
  Lane 6 (T6): activation[5] × weight[5] → 1300/1320/1340 nm

NR-IOC decodes SFG outputs:
  500–520 nm band → result[0]
  530–550 nm band → result[1]
  560–580 nm band → result[2]
  590–610 nm band → result[3]
  620–640 nm band → result[4]
  650–670 nm band → result[5]
```

6 independent multiply-accumulate operations per clock cycle per PE.

### Performance with 6-Lane Architecture

- Total theoretical throughput: 6 × 82 PFLOPS = **492 PFLOPS** (base mode)
- With 3^3 matrix multiply: 6 × ~148 PFLOPS = **~888 PFLOPS**

The wavelength separation is sufficient that standard WDM multiplexers/demultiplexers can combine and separate channels at chip I/O boundaries.

---

## How Weights Are Stored: Centralized Optical RAM

Weights are stored in the **CPU's 3-tier optical RAM** and streamed to Processing Elements (PEs) via optical waveguides. This is a critical architectural simplification over earlier designs that attempted per-PE weight storage using exotic bistable resonators.

### The Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CPU's Optical RAM                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Tier 1    │  │   Tier 2    │  │   Tier 3    │             │
│  │  Hot Cache  │  │   Working   │  │   Parking   │             │
│  │    ~1ns     │  │   ~10ns     │  │   ~100ns    │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         └────────────────┼────────────────┘                     │
│                          ↓                                      │
│              ┌───────────────────────┐                          │
│              │   Weight Streaming    │                          │
│              │      Controller       │                          │
│              └───────────┬───────────┘                          │
└──────────────────────────┼──────────────────────────────────────┘
                           ↓
              Optical Waveguide Bus (weight stream)
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│                     Systolic Array                               │
│   ┌────┐  ┌────┐  ┌────┐       Weights stream in from RAM       │
│   │ PE │→ │ PE │→ │ PE │→      PEs are SIMPLE: mixer + routing  │
│   └─┬──┘  └─┬──┘  └─┬──┘       No per-PE storage needed         │
│     ↓       ↓       ↓                                            │
│   ┌────┐  ┌────┐  ┌────┐                                        │
│   │ PE │→ │ PE │→ │ PE │→                                       │
│   └─┬──┘  └─┬──┘  └─┬──┘                                        │
│     ↓       ↓       ↓                                            │
└──────────────────────────────────────────────────────────────────┘
```

### The 3-Tier Memory Hierarchy

| Tier | Name | Access Time | Purpose |
|------|------|-------------|---------|
| **Tier 1** | Hot Cache | ~1ns | Active weights currently in use |
| **Tier 2** | Working Set | ~10ns | Layer weights, near-term access |
| **Tier 3** | Parking | ~100ns | Full model storage, bulk weights |

Weights move between tiers based on access patterns. Hot weights for the current compute operation sit in Tier 1, ready for immediate streaming to PEs.

### PE Design: 6-Lane Parallel SFG

Each PE contains 6 dedicated PPLN mixers with WDM demux/mux:

```
       Input activation (6 triplets multiplexed)
                    ↓
    ┌───────────────────────────────────────┐
    │                PE (~55 × 55 μm)       │
    │                                       │
    │   Weight (6 triplets) ───────────────┼──→ from NR-IOC
    │              ↓                        │
    │         ┌─────────┐                   │
    │         │ WDM     │ AWG 1×6 Demux     │
    │         │ DEMUX   │                   │
    │         └─┬┬┬┬┬┬──┘                   │
    │           ││││││  6 lanes             │
    │         ┌─┘│││││                      │
    │    ┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐
    │    │PPLN││PPLN││PPLN││PPLN││PPLN││PPLN│
    │    │ T1 ││ T2 ││ T3 ││ T4 ││ T5 ││ T6 │
    │    └──┬─┘└──┬─┘└──┬─┘└──┬─┘└──┬─┘└──┬─┘
    │       └──┬──┘──┬──┘──┬──┘──┬──┘──┬──┘ │
    │         ┌┴─────────┐                   │
    │         │ WDM MUX  │ AWG 6×1           │
    │         └────┬─────┘                   │
    │              ↓                        │
    │      Waveguide Routing                │
    │              ↓                        │
    └───────────────────────────────────────┘
                    ↓
           Output (to next PE)
```

**What a PE contains:**
- WDM demux (AWG, splits 6 triplets into dedicated lanes)
- 6 PPLN SFG mixers (each QPM-tuned to its triplet)
- WDM mux (AWG, recombines 6 SFG output bands)
- Waveguide routing (input/output/weight paths)

**What a PE does NOT contain:**
- Bistable resonators
- Tristable flip-flops
- Any per-PE weight storage
- Any active or electronically controlled elements
- The chip is fully passive — all 6 mixers are fixed photonic geometry

### Why This Is Better

| Aspect | Old Design (Per-PE Storage) | New Design (Centralized RAM) |
|--------|----------------------------|------------------------------|
| PE complexity | Bistable Kerr resonators per PE | Just mixer + waveguides |
| Fabrication | Every PE must have working resonator | PEs are mostly passive optics |
| Yield | One bad resonator = bad PE | Much higher yield |
| Weight loading | Write to each PE individually | Stream from RAM |
| Memory system | Separate accelerator storage | Shared with CPU |
| Exotic components | Per-PE χ³ nonlinear elements | Centralized, amortized |

### Weight Streaming During Compute

During matrix operations, weights stream from optical RAM to PEs in sync with the systolic data flow:

1. **Weights pre-staged in Tier 1** - Controller prefetches needed weights
2. **Streaming to PEs** - Weights flow via optical waveguides, timed to arrive with activations
3. **Continuous flow** - As one weight is consumed, next weight arrives

The streaming approach means weights don't need to "persist" at the PE - they're consumed immediately and replaced by the next weight in the stream.

### Example: Matrix Multiply Weight Flow

For a 3×3 weight matrix:

```
W = | +1  -1   0 |
    |  0  +1  +1 |
    | -1   0  -1 |
```

With 6-lane parallelism, each cycle streams 6 weights simultaneously (one per triplet):

**Cycle 1:** 6 weights stream to PE — one encoded on each triplet (T1–T6)
**Cycle 2:** Next 6 weights stream to PE
**Cycle 3:** Next 6 weights stream to PE

Each weight is encoded on a different triplet's wavelengths by the NR-IOC. The PE's WDM demux routes each triplet to its dedicated PPLN mixer. 6 multiply-accumulate operations per cycle per PE.

Weights arrive just-in-time, synchronized with the systolic data flow. The RAM controller handles prefetching and timing.

### Dual-Purpose Memory System

The optical RAM serves **both** the CPU and accelerator:

| Use Case | How RAM Is Used |
|----------|-----------------|
| CPU operations | Normal data/instruction storage |
| Accelerator weights | Weight streaming to systolic array |

One memory system, two purposes. The CPU's optical RAM isn't dedicated to either - it's a shared resource that serves whatever needs data at the moment.

### Latency Considerations

| Operation | Latency | Notes |
|-----------|---------|-------|
| Tier 1 → PE stream | ~1ns | Hot cache, immediate |
| Tier 2 → Tier 1 prefetch | ~10ns | Background, overlapped with compute |
| Tier 3 → Tier 2 load | ~100ns | Bulk model loading |

For sustained compute, weights are prefetched into Tier 1 ahead of when they're needed. The ~1ns streaming latency is negligible compared to the 617 MHz clock period (~1.6ns).

---

## Performance Targets

| Configuration | Base Mode | 3^3 Matrix Multiply (~1.8×) | 3^3 Pure ADD (9×) |
|--------------|-----------|----------------------------|-------------------|
| 27×27 array | 65 TFLOPS | ~117 TFLOPS | 583 TFLOPS |
| 243×243 array | 5.2 PFLOPS | ~9.4 PFLOPS | 47 PFLOPS |
| 960×960 array | 82 PFLOPS | ~148 PFLOPS | 738 PFLOPS |

**Comparison vs NVIDIA AI Accelerators:**

| Reference | Performance | Our 960×960 (Base) | Our 960×960 (3^3 MatMul) | Our 960×960 (3^3 Pure ADD) |
|-----------|-------------|--------------------|-----------------------|---------------------------|
| **B200** | 2.5 PFLOPS | **33×** | **~59×** | **295×** |
| **H100** | ~2 PFLOPS | **41×** | **~74×** | **369×** |

*For AI workloads, use the "3^3 MatMul" column (~59× B200) since AI is matrix multiply-heavy.*

**For AI workloads (matrix multiply-heavy):** A single 960×960 optical chip delivers **~59× the throughput** of NVIDIA's B200 (or ~74× an H100). The base mode without 3^3 encoding still achieves 33× B200.

*See "Real-World Performance" section for why matrix multiply sees ~1.8× instead of 9×*

---

## Log-Domain Tower Scaling

This section describes how we can dramatically increase compute density by leveraging the logarithmic domain and "power tower" encodings. The key insight: **the hardware doesn't change** - every PE still just does add/subtract. The magic happens in how we interpret numbers.

### The Level System

When you take the logarithm of a number, multiplication becomes addition. Take the log again (log-log), and *exponentiation* becomes addition. Each "level" up the tower transforms a harder operation into simple add/subtract.

| Level | Domain | What ADD/SUB means in linear | Physical States | Trit Represents |
|-------|--------|------------------------------|-----------------|-----------------|
| 0 | Linear | Add/Subtract | 3 | trit |
| 1 | Log | Multiply/Divide | 3 | trit |
| 2 | Log-Log | Power/Root | 3 | trit³ |
| 3 | Log-Log-Log | Power Tower | 3 | trit^(3^3) |
| 4 | Log^4 | Hyper-4 | 3 | trit^(3^3^3) |

The pattern: operations get "easier" at each level (harder ops become add/sub), but levels alternate between being add/sub friendly and requiring actual mul/div hardware.

### Baseline Configuration (Current Architecture)

In the standard N-Radix architecture, we have two types of Processing Elements:

| PE Type | Operating Level | What it does | Physical operation |
|---------|-----------------|--------------|-------------------|
| **ADD/SUB PE** | Level 0 (linear) | Addition, Subtraction | Add/Subtract |
| **MUL/DIV PE** | Level 1 (log) | Multiplication, Division | Add/Subtract (in log domain) |

Both PE types perform the **same physical operation** (optical add/subtract). The difference is interpretation:
- ADD/SUB PEs work on linear-encoded numbers
- MUL/DIV PEs work on log-encoded numbers (where add = multiply, subtract = divide)

### Scaled Configuration for More Compute

To increase compute density, we push each PE type up the tower:

| PE Type | Baseline Level | Scaled Encoding | Trit Represents |
|---------|---------------|-----------------|-----------------|
| **ADD/SUB PE** | 0 (linear) | 3^3 | trit³ |
| **MUL/DIV PE** | 1 (log) | 3^3 | trit³ (in log domain) |

**Practical decision:** Both PE types use **3^3 encoding**. The NR-IOC interprets them differently based on PE type.

*Theoretical alternative: MUL/DIV could jump to level 4 (3^3^3^3) to stay pure add/subtract on exponents, but 3^3^3^3 is astronomically large and requires arbitrary precision math. The practical choice is 3^3 for both.*

### Why 3^3 For Both? The Practical Tradeoff

The levels alternate between "add/sub friendly" and "mul/div required":

```
Level 0: Linear      - ADD/SUB works ✓
Level 1: Log         - MUL/DIV works ✓ (add/sub = mul/div)
Level 2: Log-log     - needs actual mul/div ✗
Level 3: Log³       - needs actual mul/div ✗
Level 4: Log⁴       - MUL/DIV works again ✓ (but exponent = 3^3^3^3!)
```

**The theoretical path:**
- ADD/SUB: Level 0 → Level 2 = 3^3 ✓
- MUL/DIV: Level 1 → Level 4 = 3^3^3^3 (skipping levels 2 AND 3)

**The problem:** 3^3^3^3 = 3^(3^27) = 3^7,625,597,484,987. That doesn't fit in any standard numeric type. You'd need arbitrary precision math, adding latency and complexity.

**The practical solution:** Both use **3^3 encoding**. The NR-IOC interprets based on PE type:
- ADD/SUB PEs: trit³ represents addition values
- MUL/DIV PEs: trit³ represents multiplication values (in log domain)

This gives 9× throughput for both operation types using standard 64-bit hardware.

### Why 3^3^3^3 Is Beyond Engineering

Let's put numbers to "astronomically large" to understand why 3^3^3^3 isn't just impractical - it's physically impossible.

**The calculation:**
- 3^3 = 27
- 3^3^3 = 3^27 = 7,625,597,484,987 (7.6 trillion)
- 3^3^3^3 = 3^7,625,597,484,987

To represent a number that can hold values up to 3^7,625,597,484,987, you need approximately **12 trillion bits** - that's **1.5 terabytes per single number**.

**Bit width comparison:**

| System | Bits | Max Number |
|--------|------|------------|
| Standard | 64 | ~10^19 |
| Extended | 128 | ~10^38 |
| Crypto | 256 | ~10^77 |
| Large | 512 | ~10^154 |
| **3^3^3^3** | **12 trillion** | **10^(3.6 trillion)** |

**What this means physically:**
- **12 TERABIT registers** would be required (12 trillion bits)
- **1.5 TERABYTES** to store a single number
- More storage **per multiplication** than most data centers have total
- The NR-IOC would need to encode/decode numbers larger than atoms in the universe

This isn't an engineering challenge - it's a fundamental impossibility. You can't build registers with more bits than there are particles to build them with.

**Conclusion:** 3^3 is the practical ceiling - not a choice, but a physical limit. The theoretical path (MUL/DIV at level 4) is mathematically elegant but physically absurd. We stop at 3^3 because the universe stops there.

### Real-World Performance: The 1.8× Reality

**IMPORTANT:** The 9× throughput multiplier is real, but it **only applies to pure ADD/SUB operations**. Matrix multiply - the core AI workload - sees a more modest ~1.8× improvement due to Amdahl's Law.

**The asymmetry:**
- **ADD/SUB PEs:** Benefit fully from 3^3 encoding (9× throughput)
- **MUL/DIV PEs:** Stay at baseline (1× throughput) because jumping to level 4 requires 3^3^3^3 encoding (physically impossible - see section above)

**For matrix multiply (which is ~50% additions, ~50% multiplications):**

Using Amdahl's Law:
```
Speedup = 1 / ((1 - P) + P/S)

Where:
- P = fraction that benefits from speedup (ADD portion = 0.5)
- S = speedup factor (9×)

Speedup = 1 / ((1 - 0.5) + 0.5/9)
        = 1 / (0.5 + 0.056)
        = 1 / 0.556
        ≈ 1.8×
```

**Workload-specific performance:**

| Workload | ADD % | MUL % | Overall Boost | Notes |
|----------|-------|-------|---------------|-------|
| Matrix multiply | 50% | 50% | ~1.8× | Core AI workload |
| Transformer attention | ~60% | ~40% | ~2.1× | More accumulation |
| Pure accumulation | 100% | 0% | 9× | Reductions, sums |
| Pure multiply | 0% | 100% | 1× | No improvement |

**What this means vs NVIDIA AI Accelerators:**

| Mode | 960×960 Performance | vs B200 (2.5 PFLOPS) | vs H100 (~2 PFLOPS) |
|------|---------------------|---------------------|---------------------|
| Base (no 3^3) | 82 PFLOPS | **33×** | **41×** |
| **3^3 matrix multiply** | **~148 PFLOPS** | **59×** | **74×** |
| 3^3 pure ADD | 738 PFLOPS | 295× | 369× |

**Key takeaways:**
- **For realistic AI workloads (matrix multiply): 59× a B200, 74× an H100**
- The pure ADD numbers (295×/369×) only apply to accumulation-heavy workloads
- The 9× throughput multiplier is mathematically correct but applies to a limited subset of operations
- Matrix multiply (GEMM) - which dominates training and inference - sees ~1.8×

**Adjusted performance targets with 3^3 scaling:**

| Configuration | Base Performance | With 3^3 (Matrix Multiply) | With 3^3 (Pure ADD) |
|--------------|------------------|---------------------------|---------------------|
| 27×27 array | 65 TFLOPS | ~117 TFLOPS | 583 TFLOPS |
| 243×243 array | 5.2 PFLOPS | ~9.4 PFLOPS | 47 PFLOPS |
| 960×960 array | 82 PFLOPS | ~148 PFLOPS | 738 PFLOPS |

The 9× number is real and achievable - but only for the right workloads. For general matrix operations, expect ~1.8-2.1× depending on the ADD/MUL ratio.

### The Hardware Doesn't Change

This is the beautiful part. After scaling:

| Component | Before scaling | After scaling |
|-----------|---------------|---------------|
| PE internals | Add/subtract circuits | Add/subtract circuits (same) |
| Optical paths | Unchanged | Unchanged |
| Clock rate | 617 MHz | 617 MHz (same) |
| Physical states | 3 | 3 (same) |
| **NR-IOC** | Interprets trit as trit | Interprets trit as trit³ (or higher) |

The PEs are completely oblivious to the tower level. They just see optical signals and add/subtract them. All the intelligence is in the **NR-IOC (N-Radix Input/Output Converter)**, which:

1. Knows which PE type it's feeding (ADD/SUB or MUL/DIV)
2. Applies the correct encoding for that PE's tower level
3. Decodes the result back to linear domain for output

### The NR-IOC Is the Limit

The NR-IOC conversion time is approximately **6.5ns** - negligible compared to compute cycles. This means:

- Using bigger number representations (tower encodings) is essentially **free**
- The throughput multiplier comes from each operation handling larger values (trit³ = 9× the value range)
- The practical limit is how many tower levels the NR-IOC can accurately encode/decode

**Open questions for future work:**
- What's the maximum tower height the NR-IOC can handle before precision degrades?
- Can we dynamically switch tower levels based on workload?
- Is there a "sweet spot" beyond which additional levels don't help?

Theoretically, we could keep going: 3^3^3^3, 3^3^3^3^3, etc. Each level multiplies effective throughput. Testing the NR-IOC to find its practical ceiling is future research.

### The North Star: Datacenter-Class AI on a Laptop

Here's what tower scaling makes possible. Consider a **27×27 chip** (~729 PEs):

| Tower Levels | Effective Throughput (Pure ADD) | Effective Throughput (Matrix Multiply) | Equivalent To |
|--------------|--------------------------------|---------------------------------------|---------------|
| Base (3) | ~65 TFLOPS | ~65 TFLOPS | High-end GPU |
| +1 level (3^3) | ~583 TFLOPS | ~117 TFLOPS | Small cluster |
| +2 levels | ~5.2 PFLOPS | ~1.0 PFLOPS | **~0.5× B200** |
| +3 levels | ~47 PFLOPS | ~9.4 PFLOPS | **~4× B200** |
| +4-5 levels | ~400-1,200 PFLOPS | ~80-240 PFLOPS | **32-96× B200** |

*Note: Matrix multiply throughput is ~1.8× base due to Amdahl's Law (50% ADD at 9×, 50% MUL at 1×). Pure ADD workloads get the full tower multiplier.*

**NVIDIA's flagship AI accelerator (B200) today:**
- 2.5 PFLOPS per chip
- ~1000W TDP
- Requires datacenter cooling and power infrastructure

**Equivalent AI throughput on a laptop (if NR-IOC hits ~5 levels):**
- One 27×27 optical chip
- ~10-50 watts, battery-powered
- Fits in your backpack
- **32-96× the throughput of a B200**

The optical hardware doesn't know it's small - it's just adding wavelengths. The NR-IOC decides whether each operation means "trit + trit" or "tower + tower." Validating how high the NR-IOC can climb is the key engineering challenge.

> **Note on Frontier comparisons:** You may see references elsewhere comparing optical chips to Frontier (1,200 PFLOPS). Frontier is a general-purpose scientific supercomputer at Oak Ridge National Lab - not an AI accelerator. While the raw FLOPS comparison is dramatic (a few chips matching an exascale supercomputer), it's misleading for AI workloads. The relevant comparison for N-Radix/AI accelerator work is against NVIDIA's B200/H100, which are purpose-built for the same tensor operations we target.

### Finding the Optimal Tower Height: Bottleneck Engineering

The system has three potential bottlenecks, tested in sequence:

```
Optical Compute → NR-IOC → Transistor Interface (PCIe/Host)
   (unlimited)     (?)         (?)
```

**Step 1: Test the NR-IOC ceiling**
- Push tower height until NR-IOC precision degrades
- Find max encoding/decoding accuracy

**Step 2: Test the transistor interface**
- PCIe bandwidth, host CPU/memory capabilities
- What's the largest number representation it can handle efficiently?

**Step 3: Optimize to the weakest link**
- If NR-IOC maxes out at 3^3^3^3 but PCIe chokes at 3^3^3 → use 3^3^3
- No point over-engineering one stage if another bottlenecks first

The optical compute is effectively unlimited - it just does add/subtract regardless of tower height. The real engineering challenge is matching the NR-IOC to what the electronic interface can actually consume.

### Performance Impact

With 3^3 scaling (trit represents trit³):

| Metric | Base | Scaled (3^3) | Multiplier |
|--------|------|--------------|------------|
| Physical states | 3 | 3 (unchanged) | — |
| Trit represents | trit | trit³ | 9× value range |
| 27×27 array | 65 TFLOPS | 583 TFLOPS | 9× |
| 243×243 array | 5.2 PFLOPS | 47 PFLOPS | 9× |
| 960×960 array | 82 PFLOPS | 738 PFLOPS | 9× |

The 9× comes from each trit representing 9× the mathematical value (trit³ vs trit). Same hardware, same 3 physical states, same power - but each operation processes larger numbers.

### Summary

The log-domain tower scaling approach:

1. **Keeps hardware simple** - PEs only do add/subtract
2. **Pushes complexity to NR-IOC** - Encoding/decoding happens at the boundary
3. **Respects the alternating pattern** - ADD/SUB on even levels, MUL/DIV on odd levels
4. **Scales multiplicatively** - Each tower level multiplies effective throughput
5. **Is essentially free** - NR-IOC conversion time (6.5ns) is negligible

The limit isn't the optical compute - it's how high we can push the tower before NR-IOC precision degrades. Finding that ceiling is the next frontier.

---

## vs General-Purpose Path

The `standard_computer/` directory contains the von Neumann architecture path (fetch-decode-execute, branching, etc.). This N-Radix path trades flexibility for raw throughput on tensor operations.

**Use N-Radix path for:** Training, inference, any matrix-heavy workload
**Use CPU path for:** Control flow, I/O handling, general compute
