# STANDARD COMPUTER

## Tier 1: General Purpose Ternary Computer

```
Specifications:
- Systolic Array: 81x81 (6,561 PEs)
- Peak Throughput: ~4.0 TFLOPS equivalent
- WDM Channels: 1 (single wavelength set)
- Power: ~5W estimated

Round Table Config:
- 1 Kerr Clock (617 MHz)
- 1 Supercomputer
- 1 Super IOC
- 1 IOA
```

## Use Cases

- General ternary computing research
- Educational demonstrations
- Algorithm development
- Component testing
- Edge computing applications

## Key Files

| File | Purpose |
|------|---------|
| `standard_generator.py` | Generate Standard Computer GDS |
| `../shared_components/` | IOC, IOA, backplane modules |
| `../optical_systolic_array.py` | 81x81 array generator |

## Generate Command

```bash
cd /home/jackwayne/Desktop/Optical_computing
.mamba_env/bin/python3 Research/programs/standard_computer/standard_generator.py
```

## Output Files

- `Research/data/gds/standard_computer/` - All GDS files
- `Research/data/gds/round_table_minimum.gds` - Backplane
