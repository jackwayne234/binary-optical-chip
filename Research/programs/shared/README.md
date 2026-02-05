# Shared Components

Reusable modules for both CPU and TPU optical computing architectures.

## Directory Structure

```
shared/
├── README.md
├── optical_backplane.py   # Round Table and legacy backplane layouts
├── ioc_module.py          # Input/Output Converter (Electronic ↔ Optical)
├── ioa_module.py          # Input/Output Adapters (PCIe, Ethernet)
├── storage_ioa.py         # Storage interfaces (NVMe, DDR5, HBM)
└── photonics/             # Low-level photonic building blocks
    ├── sfg_mixer.py           # Sum-Frequency Generation for ternary ops
    ├── universal_mixer.py     # General-purpose optical mixer
    ├── optical_selector.py    # Wavelength routing/selection
    ├── refined_selector.py    # Optimized selector design
    ├── polymer_selector.py    # Polymer-based selector variant
    ├── y_junction.py          # Waveguide Y-splitters
    ├── photodetector.py       # Optical-to-electrical conversion
    └── straight_waveguide.py  # Basic waveguide segments
```

## Architecture Independence

These components are designed to work with:
- **CPU architecture** - General-purpose ternary optical processor
- **TPU architecture** - Tensor/matrix-focused systolic arrays

Both share the same underlying photonic primitives and infrastructure modules.

## Core Design Principle

```
████████████████████████████████████████████████████████████████████
█                                                                  █
█   ALL COMPONENTS MUST BE COMPATIBLE WITH ROUND TABLE LAYOUT      █
█   - Central Kerr clock (617 MHz)                                 █
█   - Equidistant placement from clock                             █
█   - Minimal clock skew across all modules                        █
█                                                                  █
████████████████████████████████████████████████████████████████████
```

## Usage

```python
# Import infrastructure
from shared.optical_backplane import round_table_backplane
from shared.ioc_module import ioc_module
from shared.ioa_module import ioa_module

# Import photonics
from shared.photonics.sfg_mixer import sfg_mixer
from shared.photonics.y_junction import y_junction
from shared.photonics.photodetector import photodetector
```
