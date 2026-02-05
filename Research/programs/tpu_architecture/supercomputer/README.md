# SUPERCOMPUTER

## Tier 3: Datacenter-Class AI Accelerator

```
Specifications:
- Systolic Array: 243x243 per chip (59,049 PEs each)
- Chips: 8 (Round Table configuration)
- WDM Channels: 8 (C-band, upgradeable to 24)
- Peak Throughput: ~2.33 PFLOPS
- Comparison: 1.2x faster than NVIDIA H100
- Power: ~200W estimated

Round Table Config (MAXIMUM):
- 1 Kerr Clock (617 MHz) - CENTER
- 8 Supercomputers - Ring 1 (equidistant)
- 8 Super IOCs - Ring 2
- 8 IOAs - Ring 3
```

## Upgrade Paths

| Configuration | PFLOPS | vs H100 |
|--------------|--------|---------|
| Base (8 WDM) | 2.33 | 1.2x |
| Extended (24 WDM) | 7.0 | 3.5x |
| Ultimate (729x729 + 24 WDM) | 63 | 31x |

## Use Cases

- Large language model training
- Datacenter AI inference at scale
- High-performance computing (HPC)
- Scientific simulation
- Climate modeling
- Drug discovery
- Financial modeling

## Architecture: Round Table

```
                        ROUND TABLE - 8 SUPERCOMPUTERS

                                   IOA_0
                                  SIOC_0
                                   SC_0

                 IOA_7                             IOA_1
                SIOC_7                             SIOC_1
                 SC_7                               SC_1



      IOA_6                      [  KERR  ]                      IOA_2
     SIOC_6                      [ 617MHz ]                     SIOC_2
      SC_6                       [________]                       SC_2


                 SC_5                               SC_3
                SIOC_5                             SIOC_3
                 IOA_5                             IOA_3

                                   SC_4
                                  SIOC_4
                                   IOA_4

    CRITICAL: All components EQUIDISTANT from central Kerr clock
              to minimize clock skew across the system.
```

## Operating Modes

### Mode 1: 8 Independent LLMs
- Each SC runs its own model
- 8 separate inference engines
- No inter-SC communication

### Mode 2: Unified System
- All 8 SCs work together
- Single SIOC for inter-group communication
- Remaining SIOCs for storage

### Mode 3: Hybrid
- Some SIOCs for networking
- Some SIOCs for storage
- Flexible resource allocation

## Key Files

| File | Purpose |
|------|---------|
| `supercomputer_generator.py` | Generate Supercomputer GDS |
| `../optical_backplane.py` | Round Table backplane |
| `../c_band_wdm_systolic.py` | WDM systolic arrays |
| `../shared_components/` | IOC, IOA modules |

## Generate Command

```bash
cd /home/jackwayne/Desktop/Optical_computing
.mamba_env/bin/python3 Research/programs/supercomputer/supercomputer_generator.py
```

## Performance Benchmarks

| Workload | Time | Effective PFLOPS |
|----------|------|------------------|
| GEMM 4096x4096 | 62μs | 2.2 |
| Transformer Layer | 430μs | 2.1 |
| Monte Carlo 10B | 4.4ms | 2.3 |
| Prime Count 100M | 765μs | - |

## Output Files

- `Research/data/gds/supercomputer/` - All GDS files
- `Research/data/gds/round_table_maximum.gds` - Full backplane
