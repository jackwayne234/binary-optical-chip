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

## How Weights Are Stored: Bistable Kerr Flip-Flops

Each Processing Element (PE) contains a **9-trit weight register** built from bistable Kerr resonators. Here's how it works:

### The Mechanism

A Kerr resonator exploits the optical Kerr effect (χ³ nonlinearity) where the refractive index changes with light intensity. At the right power levels, the resonator has **two stable states** - it "locks" into one or the other based on input.

For ternary storage, each trit uses **wavelength presence** to encode three states:

| Stored Value | Wavelength Present | Physical State |
|--------------|-------------------|----------------|
| **-1** | 1550nm (Red) | Resonator locked to λ_red |
| **0** | 1310nm (Green) | Resonator locked to λ_green |
| **+1** | 1064nm (Blue) | Resonator locked to λ_blue |

### Writing a Weight (Setting the Flip-Flop)

To write a value to a PE's weight register:

1. **Assert the WRITE_ENABLE line** for that PE (optical pulse on the write bus)
2. **Inject the desired wavelength** at high power (above bistability threshold)
3. **Remove WRITE_ENABLE** - the resonator stays locked to that wavelength

The write operation takes ~10ns (a few clock cycles at 617 MHz).

### Example: Loading a 3×3 Weight Matrix

Say we want to load this weight matrix into a 3×3 section of the systolic array:

```
W = | +1  -1   0 |
    |  0  +1  +1 |
    | -1   0  -1 |
```

**Step 1: Address the PEs**

The weight loading bus addresses PEs row by row:
```
Clock 1: Select Row 0 (PE[0,0], PE[0,1], PE[0,2])
Clock 2: Select Row 1 (PE[1,0], PE[1,1], PE[1,2])
Clock 3: Select Row 2 (PE[2,0], PE[2,1], PE[2,2])
```

**Step 2: Inject wavelengths for each row**

```
Clock 1, Row 0: Inject 1064nm → PE[0,0]  (+1)
                Inject 1550nm → PE[0,1]  (-1)
                Inject 1310nm → PE[0,2]  (0)

Clock 2, Row 1: Inject 1310nm → PE[1,0]  (0)
                Inject 1064nm → PE[1,1]  (+1)
                Inject 1064nm → PE[1,2]  (+1)

Clock 3, Row 2: Inject 1550nm → PE[2,0]  (-1)
                Inject 1310nm → PE[2,1]  (0)
                Inject 1550nm → PE[2,2]  (-1)
```

**Total load time for 3×3:** 3 clock cycles = ~4.9ns

**For an 81×81 array:** 81 clock cycles = ~131ns (~0.13μs)

### Reading the Weight (During Compute)

During matrix operations, each PE continuously outputs its stored wavelength at low power. The mixer combines this with the streaming input:

```
          Input activation (streaming)
                    ↓
    ┌───────────────────────────────┐
    │              PE               │
    │   ┌───────────────────────┐   │
    │   │  Kerr Bistable Cell   │   │
    │   │  (stores weight λ)    │───┼──→ Weight wavelength (continuous)
    │   └───────────────────────┘   │
    │              ↓                │
    │         SFG Mixer             │
    │    (input × weight = output)  │
    │              ↓                │
    └───────────────────────────────┘
                    ↓
           Output (to next PE)
```

The weight doesn't need to be "read" in a traditional sense - it's always present, always mixing with the input stream. This is why systolic arrays are so efficient: **weights are stationary, data flows through**.

### Persistence

Bistable Kerr resonators maintain their state indefinitely as long as:
- Minimum holding power is maintained (~1mW)
- No write pulse is applied

No refresh cycles needed (unlike DRAM). Weights persist until explicitly overwritten.

---

## Performance Targets

| Configuration | Peak Performance | Notes |
|--------------|------------------|-------|
| 27x27 array | 583 TFLOPS | Single chip, base |
| 243x243 array | 47 PFLOPS | Multi-chiplet |
| 960x960 array | 738 PFLOPS | Full scale |

*Performance scales with array size squared and WDM channel count*

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

In the standard TPU architecture, we have two types of Processing Elements:

| PE Type | Operating Level | What it does | Physical operation |
|---------|-----------------|--------------|-------------------|
| **ADD/SUB PE** | Level 0 (linear) | Addition, Subtraction | Add/Subtract |
| **MUL/DIV PE** | Level 1 (log) | Multiplication, Division | Add/Subtract (in log domain) |

Both PE types perform the **same physical operation** (optical add/subtract). The difference is interpretation:
- ADD/SUB PEs work on linear-encoded numbers
- MUL/DIV PEs work on log-encoded numbers (where add = multiply, subtract = divide)

### Scaled Configuration for More Compute

To increase compute density, we push each PE type up the tower:

| PE Type | Baseline Level | Scaled Level | New capability | States |
|---------|---------------|--------------|----------------|--------|
| **ADD/SUB PE** | 0 → | 2 | Power towers (via add) | 3^3 = 27 |
| **MUL/DIV PE** | 1 → | 3 | Hyper operations (via add) | 3^3^3 |

**Critical detail:** Notice that ADD/SUB jumps from 0 to 2 (skipping 1), and MUL/DIV jumps from 1 to 3 (skipping 2). This isn't arbitrary - it's necessary.

### Why the Asymmetry? The Alternating Pattern

The levels alternate between "add/sub friendly" and "mul/div required":

```
Level 0: Linear domain
         ├─ Addition → add         ✓ (add/sub hardware works)
         └─ Multiplication → ???   ✗ (needs mul hardware)

Level 1: Log domain
         ├─ Multiplication → add   ✓ (add/sub hardware works)
         └─ Exponentiation → ???   ✗ (needs mul hardware)

Level 2: Log-log domain
         ├─ Exponentiation → add   ✓ (add/sub hardware works)
         └─ Power tower → ???      ✗ (needs mul hardware)

Level 3: Log-log-log domain
         ├─ Power tower → add      ✓ (add/sub hardware works)
         └─ Hyper-4 → ???          ✗ (needs mul hardware)
```

**The rule:** At each level, ONE class of operations becomes add/subtract, while the NEXT harder class still requires multiplication.

So when scaling:
- **ADD/SUB PEs** must land on EVEN levels (0, 2, 4...) where addition IS addition
- **MUL/DIV PEs** must land on ODD levels (1, 3, 5...) where multiplication IS addition

Jumping to an intermediate level would require actual multiply hardware, which defeats the purpose.

### The Hardware Doesn't Change

This is the beautiful part. After scaling:

| Component | Before scaling | After scaling |
|-----------|---------------|---------------|
| PE internals | Add/subtract circuits | Add/subtract circuits (same) |
| Optical paths | Unchanged | Unchanged |
| Clock rate | 617 MHz | 617 MHz (same) |
| Physical states | 3 | 3 (same) |
| **IOC** | Interprets trit as trit | Interprets trit as trit³ (or higher) |

The PEs are completely oblivious to the tower level. They just see optical signals and add/subtract them. All the intelligence is in the **IOC (Integrated Optical Converter)**, which:

1. Knows which PE type it's feeding (ADD/SUB or MUL/DIV)
2. Applies the correct encoding for that PE's tower level
3. Decodes the result back to linear domain for output

### The IOC Is the Limit

The IOC conversion time is approximately **6.5ns** - negligible compared to compute cycles. This means:

- Using bigger number representations (tower encodings) is essentially **free**
- The throughput multiplier comes from each operation handling larger values (trit³ = 9× the value range)
- The practical limit is how many tower levels the IOC can accurately encode/decode

**Open questions for future work:**
- What's the maximum tower height the IOC can handle before precision degrades?
- Can we dynamically switch tower levels based on workload?
- Is there a "sweet spot" beyond which additional levels don't help?

Theoretically, we could keep going: 3^3^3^3, 3^3^3^3^3, etc. Each level multiplies effective throughput. Testing the IOC to find its practical ceiling is future research.

### Finding the Optimal Tower Height: Bottleneck Engineering

The system has three potential bottlenecks, tested in sequence:

```
Optical Compute → IOC → Transistor Interface (PCIe/Host)
   (unlimited)     (?)         (?)
```

**Step 1: Test the IOC ceiling**
- Push tower height until IOC precision degrades
- Find max encoding/decoding accuracy

**Step 2: Test the transistor interface**
- PCIe bandwidth, host CPU/memory capabilities
- What's the largest number representation it can handle efficiently?

**Step 3: Optimize to the weakest link**
- If IOC maxes out at 3^3^3^3 but PCIe chokes at 3^3^3 → use 3^3^3
- No point over-engineering one stage if another bottlenecks first

The optical compute is effectively unlimited - it just does add/subtract regardless of tower height. The real engineering challenge is matching the IOC to what the electronic interface can actually consume.

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
2. **Pushes complexity to IOC** - Encoding/decoding happens at the boundary
3. **Respects the alternating pattern** - ADD/SUB on even levels, MUL/DIV on odd levels
4. **Scales multiplicatively** - Each tower level multiplies effective throughput
5. **Is essentially free** - IOC conversion time (6.5ns) is negligible

The limit isn't the optical compute - it's how high we can push the tower before IOC precision degrades. Finding that ceiling is the next frontier.

---

## vs General-Purpose Path

The `standard_computer/` directory contains the von Neumann architecture path (fetch-decode-execute, branching, etc.). This TPU path trades flexibility for raw throughput on tensor operations.

**Use TPU path for:** Training, inference, any matrix-heavy workload
**Use CPU path for:** Control flow, I/O handling, general compute
