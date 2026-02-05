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

| Configuration | Base Mode | 3^3 Matrix Multiply (~1.8×) | 3^3 Pure ADD (9×) |
|--------------|-----------|----------------------------|-------------------|
| 27×27 array | 65 TFLOPS | ~117 TFLOPS | 583 TFLOPS |
| 243×243 array | 5.2 PFLOPS | ~9.4 PFLOPS | 47 PFLOPS |
| 960×960 array | 82 PFLOPS | ~148 PFLOPS | 738 PFLOPS |

**Frontier comparison (1,200 PFLOPS):**
- Base mode: 15 chips = Frontier
- 3^3 matrix multiply: **8 chips = Frontier** (realistic AI workloads)
- 3^3 pure ADD: 2 chips = Frontier (accumulation-heavy workloads only)

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

| PE Type | Baseline Level | Scaled Encoding | Trit Represents |
|---------|---------------|-----------------|-----------------|
| **ADD/SUB PE** | 0 (linear) | 3^3 | trit³ |
| **MUL/DIV PE** | 1 (log) | 3^3 | trit³ (in log domain) |

**Practical decision:** Both PE types use **3^3 encoding**. The IOC interprets them differently based on PE type.

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

**The practical solution:** Both use **3^3 encoding**. The IOC interprets based on PE type:
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
- The IOC would need to encode/decode numbers larger than atoms in the universe

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

**What this means for Frontier comparisons:**

| Mode | 960×960 Performance | Chips to match Frontier (1,200 PFLOPS) |
|------|---------------------|---------------------------------------|
| Base (no 3^3) | 82 PFLOPS | 15 chips |
| **3^3 matrix multiply** | **~148 PFLOPS** | **8 chips** |
| 3^3 pure ADD | 738 PFLOPS | 2 chips |

**Key takeaways:**
- **For realistic AI workloads (matrix multiply): 8 chips = Frontier**
- The "2 chips = Frontier" claim only holds for pure ADD workloads (e.g., accumulation loops)
- The 9× number is mathematically correct but applies to a limited subset of operations
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

### The North Star: Frontier on a Laptop

Here's what tower scaling makes possible. Consider a **27×27 chip** (~729 PEs):

| Tower Levels | Effective Throughput (Pure ADD) | Effective Throughput (Matrix Multiply) | Equivalent To |
|--------------|--------------------------------|---------------------------------------|---------------|
| Base (3) | ~65 TFLOPS | ~65 TFLOPS | High-end GPU |
| +1 level (3^3) | ~583 TFLOPS | ~117 TFLOPS | Small cluster |
| +2 levels | ~5.2 PFLOPS | ~1.0 PFLOPS | Supercomputer node |
| +3 levels | ~47 PFLOPS | ~9.4 PFLOPS | Major HPC system |
| +4-5 levels | ~400-1,200 PFLOPS | ~80-240 PFLOPS | **Frontier** (pure ADD only) |

*Note: Matrix multiply throughput is ~1.8× base due to Amdahl's Law (50% ADD at 9×, 50% MUL at 1×). Pure ADD workloads get the full tower multiplier.*

**Frontier today:**
- 9,400 nodes, 37,000 GPUs
- 21 megawatts, warehouse-sized
- Oak Ridge National Lab

**Frontier on a laptop (if IOC hits ~5 levels):**
- One 27×27 optical chip
- ~10-50 watts, battery-powered
- Fits in your backpack

The optical hardware doesn't know it's small - it's just adding wavelengths. The IOC decides whether each operation means "trit + trit" or "tower + tower." Validating how high the IOC can climb is the key engineering challenge.

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
