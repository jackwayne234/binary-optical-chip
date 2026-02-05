# HOME AI

## Tier 2: Consumer/Prosumer AI Accelerator

```
Specifications:
- Systolic Array: 243x243 (59,049 PEs)
- WDM Channels: 8 (C-band, 1530-1565nm)
- Peak Throughput: ~291 TFLOPS
- Comparison: 3.5x faster than RTX 4090
- Power: ~50W estimated

Round Table Config:
- 1 Kerr Clock (617 MHz)
- 1-4 Supercomputers
- 1-2 Super IOCs
- 1-2 IOAs
```

## Use Cases

- Local LLM inference (Llama, Mistral, etc.)
- Edge AI applications
- Home server AI acceleration
- Small business AI workloads
- Real-time video/audio processing
- Scientific computing (personal scale)

## Key Files

| File | Purpose |
|------|---------|
| `home_ai_generator.py` | Generate Home AI GDS |
| `../c_band_wdm_systolic.py` | WDM systolic array |
| `../shared_components/` | IOC, IOA, backplane modules |

## Generate Command

```bash
cd /home/jackwayne/Desktop/Optical_computing
.mamba_env/bin/python3 Research/programs/home_ai/home_ai_generator.py
```

## Performance Benchmarks

| Workload | Time | Effective TFLOPS |
|----------|------|------------------|
| GEMM 4096x4096 | 470μs | 291 |
| Transformer Layer | 3.4ms | 260 |
| Mandelbrot 8K | 1.2s | 245 |

## Output Files

- `Research/data/gds/home_ai/` - All GDS files
- `Research/data/gds/round_table_small.gds` - Backplane (4 SC)
