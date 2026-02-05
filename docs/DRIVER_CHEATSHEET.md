# IOC Driver Cheat Sheet

**One page. Everything you need.**

---

## The Job

```
Binary (PCIe) → IOC → Optical Chip → IOC → Binary (PCIe)
     ↑                                           ↑
  You encode                               You decode
```

---

## Trit Values

| Value | Wavelength | Packed |
|-------|------------|--------|
| -1 | 1550nm | 0 |
| 0 | 1310nm | 1 |
| +1 | 1064nm | 2 |

---

## Encoding

**3^3 for everything.** IOC interprets based on PE type.

```python
# Float [-1,1] → 9 trits
def encode(val, num_trits=9):
    max_val = (3**num_trits - 1) // 2
    n = int(round(val * max_val))
    trits = []
    for _ in range(num_trits):
        r = n % 3
        if r == 2:
            trits.append(-1)
            n = (n + 1) // 3
        else:
            trits.append(r)
            n //= 3
    return trits
```

**Pack 5 trits per byte:** `(t0+1) + (t1+1)*3 + (t2+1)*9 + (t3+1)*27 + (t4+1)*81`

---

## Commands

```c
IOC_LOAD_WEIGHTS  0x01   // Load weights to PEs
IOC_STREAM_INPUT  0x02   // Stream activations
IOC_COMPUTE       0x03   // Do the math
IOC_READ_OUTPUT   0x04   // Get results
IOC_RESET         0x0F   // Reset
```

**Typical flow:** `LOAD_WEIGHTS → STREAM_INPUT → READ_OUTPUT`

---

## Timing

| What | Time |
|------|------|
| IOC conversion | 6.5ns |
| Weight load 27×27 | ~5ns |
| Weight load 81×81 | ~131ns |
| PCIe (per KB) | ~1μs |

---

## Performance

| Workload | Boost |
|----------|-------|
| Matrix mul | **~1.8×** |
| Attention | ~2.1× |
| Pure add | 9× |

**Why not 9× for everything?** MUL stays at baseline. Only ADD gets the boost.

---

## Buffers

- **Alignment:** 64 bytes
- **Packing:** 5 trits/byte
- **Layout:** Row-major

---

## Status Codes

| Code | Meaning |
|------|---------|
| 0x00 | OK |
| 0x01 | Busy |
| 0x10 | Overflow |
| 0x11 | Alignment error |
| 0x12 | Size error |
| 0x20 | Timeout |

---

## That's It

Full spec: `docs/DRIVER_SPEC.md`
Architecture: `Research/programs/nradix_architecture/README.md`
Questions: chrisriner45@gmail.com
