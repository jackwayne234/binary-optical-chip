#!/usr/bin/env python3
"""
Storage IOA (Input/Output Adapter) for Ternary Optical Computer

Bridges the optical computing core to external electronic memory systems:
- NVMe SSDs for persistent storage
- DDR5 DRAM for large working memory
- HBM (High Bandwidth Memory) for high-throughput applications

This module enables the hybrid optical-electronic architecture where:
- Optical domain: ALU, optical RAM tiers (fast, limited capacity)
- Electronic domain: Mass storage (large capacity, standard interfaces)

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    STORAGE IOA                               │
    │                                                              │
    │   ┌──────────┐    ┌──────────┐    ┌──────────┐              │
    │   │  NVMe    │    │   DDR5   │    │   HBM    │              │
    │   │Controller│    │   PHY    │    │   PHY    │              │
    │   └────┬─────┘    └────┬─────┘    └────┬─────┘              │
    │        │               │               │                     │
    │        └───────────────┼───────────────┘                     │
    │                        │                                     │
    │                  ┌─────▼─────┐                               │
    │                  │  Memory   │                               │
    │                  │Controller │                               │
    │                  └─────┬─────┘                               │
    │                        │                                     │
    │                  ┌─────▼─────┐                               │
    │                  │    DMA    │                               │
    │                  │  Engine   │                               │
    │                  └─────┬─────┘                               │
    │                        │                                     │
    │                  ┌─────▼─────┐                               │
    │                  │  IOA Bus  │                               │
    │                  │ Interface │                               │
    │                  └─────┬─────┘                               │
    └────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
                      To IOC / Optical RAM Tiers

Author: Wavelength-Division Ternary Optical Computer Project
"""

import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.typings import LayerSpec
import numpy as np
from typing import Optional, Literal, List

# Activate PDK
gf.gpdk.PDK.activate()

# =============================================================================
# Layer Definitions
# =============================================================================

LAYER_WAVEGUIDE: LayerSpec = (1, 0)
LAYER_METAL1: LayerSpec = (12, 0)        # Signal routing
LAYER_METAL2: LayerSpec = (20, 0)        # Power/ground
LAYER_VIA: LayerSpec = (21, 0)           # Inter-layer vias
LAYER_PAD: LayerSpec = (22, 0)           # Bond pads
LAYER_NVME: LayerSpec = (30, 0)          # NVMe controller
LAYER_DDR: LayerSpec = (31, 0)           # DDR PHY
LAYER_HBM: LayerSpec = (32, 0)           # HBM PHY
LAYER_DMA: LayerSpec = (33, 0)           # DMA engine
LAYER_MEMCTRL: LayerSpec = (34, 0)       # Memory controller
LAYER_SERDES: LayerSpec = (23, 0)        # High-speed SerDes
LAYER_TEXT: LayerSpec = (100, 0)         # Labels

# =============================================================================
# Physical Constants
# =============================================================================

# Standard interface widths
NVME_LANES = 4              # PCIe lanes for NVMe
DDR5_WIDTH = 64             # Data bus width (bits)
DDR5_CHANNELS = 2           # Dual channel
HBM_WIDTH = 1024            # Per-stack width (bits)
HBM_CHANNELS = 8            # Channels per stack

# Speeds
NVME_GEN4_SPEED = 16        # GT/s per lane
DDR5_SPEED = 6400           # MT/s
HBM3_SPEED = 6400           # MT/s per pin


# =============================================================================
# NVMe CONTROLLER
# =============================================================================

@gf.cell
def nvme_serdes_lane() -> Component:
    """Single NVMe SerDes lane (TX + RX)."""
    c = gf.Component()

    width = 40.0
    height = 60.0

    # SerDes block
    serdes = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_SERDES
    )

    # TX section
    tx = c << gf.components.rectangle(size=(30, 20), layer=LAYER_METAL1)
    tx.dmove((5, 35))
    c.add_label("TX", position=(20, 45), layer=LAYER_TEXT)

    # RX section
    rx = c << gf.components.rectangle(size=(30, 20), layer=LAYER_METAL1)
    rx.dmove((5, 5))
    c.add_label("RX", position=(20, 15), layer=LAYER_TEXT)

    # High-speed pads
    tx_p = c << gf.components.rectangle(size=(8, 8), layer=LAYER_PAD)
    tx_p.dmove((-12, 40))
    tx_n = c << gf.components.rectangle(size=(8, 8), layer=LAYER_PAD)
    tx_n.dmove((-12, 50))

    rx_p = c << gf.components.rectangle(size=(8, 8), layer=LAYER_PAD)
    rx_p.dmove((-12, 5))
    rx_n = c << gf.components.rectangle(size=(8, 8), layer=LAYER_PAD)
    rx_n.dmove((-12, 15))

    # Ports
    c.add_port(name="tx", center=(-8, 48), width=20, orientation=180, layer=LAYER_PAD)
    c.add_port(name="rx", center=(-8, 13), width=20, orientation=180, layer=LAYER_PAD)
    c.add_port(name="parallel", center=(width, height/2), width=30, orientation=0, layer=LAYER_SERDES)

    return c


@gf.cell
def nvme_controller(
    lanes: int = 4,
    queue_depth: int = 64
) -> Component:
    """
    NVMe Controller for SSD interface.

    Implements NVMe 1.4 protocol with:
    - PCIe Gen4 x4 (64 GB/s bidirectional)
    - Multiple I/O queues for parallel access
    - Command/completion queue management

    Args:
        lanes: Number of PCIe lanes (1, 2, 4)
        queue_depth: Entries per queue
    """
    c = gf.Component()

    width = 200.0
    height = 150.0

    # Controller block
    ctrl = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_NVME
    )

    # SerDes lanes
    for i in range(lanes):
        serdes = c << nvme_serdes_lane()
        serdes.dmove((-60, 20 + i * 30))

    # Admin queue
    admin_q = c << gf.components.rectangle(size=(50, 30), layer=LAYER_METAL1)
    admin_q.dmove((20, 100))
    c.add_label("Admin Q", position=(45, 115), layer=LAYER_TEXT)

    # I/O submission queues
    sub_q = c << gf.components.rectangle(size=(50, 40), layer=LAYER_METAL1)
    sub_q.dmove((20, 50))
    c.add_label("Sub Q", position=(45, 70), layer=LAYER_TEXT)
    c.add_label(f"x{queue_depth}", position=(45, 60), layer=LAYER_TEXT)

    # I/O completion queues
    cpl_q = c << gf.components.rectangle(size=(50, 40), layer=LAYER_METAL1)
    cpl_q.dmove((80, 50))
    c.add_label("Cpl Q", position=(105, 70), layer=LAYER_TEXT)

    # Command processor
    cmd_proc = c << gf.components.rectangle(size=(60, 50), layer=LAYER_METAL2)
    cmd_proc.dmove((130, 80))
    c.add_label("CMD", position=(160, 105), layer=LAYER_TEXT)
    c.add_label("PROC", position=(160, 95), layer=LAYER_TEXT)

    # Data buffer
    data_buf = c << gf.components.rectangle(size=(60, 40), layer=LAYER_METAL2)
    data_buf.dmove((130, 20))
    c.add_label("DATA", position=(160, 40), layer=LAYER_TEXT)
    c.add_label("BUF", position=(160, 30), layer=LAYER_TEXT)

    # Labels
    c.add_label(f"NVMe Gen4 x{lanes}", position=(width/2, height + 15), layer=LAYER_TEXT)
    speed_gbs = lanes * NVME_GEN4_SPEED / 8 * 2  # Bidirectional GB/s
    c.add_label(f"{speed_gbs:.0f} GB/s", position=(width/2, height + 30), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="pcie", center=(-60, height/2), width=lanes * 30, orientation=180, layer=LAYER_PAD)
    c.add_port(name="mem_if", center=(width, height/2), width=60, orientation=0, layer=LAYER_NVME)

    return c


# =============================================================================
# DDR5 PHY
# =============================================================================

@gf.cell
def ddr5_data_lane() -> Component:
    """Single DDR5 data lane (DQ + DQS)."""
    c = gf.Component()

    width = 25.0
    height = 50.0

    # Lane block
    lane = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_DDR
    )

    # DQ pad
    dq = c << gf.components.rectangle(size=(10, 10), layer=LAYER_PAD)
    dq.dmove((7.5, -15))
    c.add_label("DQ", position=(12.5, -20), layer=LAYER_TEXT)

    # IO buffer
    io_buf = c << gf.components.rectangle(size=(15, 20), layer=LAYER_METAL1)
    io_buf.dmove((5, 15))

    # Ports
    c.add_port(name="dq", center=(12.5, -10), width=10, orientation=-90, layer=LAYER_PAD)
    c.add_port(name="internal", center=(12.5, height), width=15, orientation=90, layer=LAYER_DDR)

    return c


@gf.cell
def ddr5_byte_lane() -> Component:
    """DDR5 byte lane (8 DQ + DQS pair + DM)."""
    c = gf.Component()

    # 8 data lanes
    for i in range(8):
        lane = c << ddr5_data_lane()
        lane.dmove((i * 28, 0))

    # DQS differential pair
    dqs_p = c << gf.components.rectangle(size=(10, 10), layer=LAYER_PAD)
    dqs_p.dmove((8 * 28, -15))
    dqs_n = c << gf.components.rectangle(size=(10, 10), layer=LAYER_PAD)
    dqs_n.dmove((8 * 28 + 12, -15))
    c.add_label("DQS", position=(8 * 28 + 10, -25), layer=LAYER_TEXT)

    # DM (data mask)
    dm = c << gf.components.rectangle(size=(10, 10), layer=LAYER_PAD)
    dm.dmove((8 * 28 + 26, -15))
    c.add_label("DM", position=(8 * 28 + 31, -25), layer=LAYER_TEXT)

    # Byte lane controller
    ctrl = c << gf.components.rectangle(size=(8 * 28 + 40, 30), layer=LAYER_METAL1)
    ctrl.dmove((0, 55))
    c.add_label("BYTE LANE", position=(8 * 14, 70), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="dram", center=(8 * 14, -10), width=8 * 28 + 40, orientation=-90, layer=LAYER_PAD)
    c.add_port(name="internal", center=(8 * 14, 85), width=8 * 28, orientation=90, layer=LAYER_DDR)

    return c


@gf.cell
def ddr5_phy(
    channels: int = 2,
    ranks: int = 2
) -> Component:
    """
    DDR5 PHY for DRAM interface.

    Implements JEDEC DDR5 with:
    - Dual channel (2x 64-bit = 128-bit total)
    - Up to 6400 MT/s
    - On-die ECC

    Args:
        channels: Number of DDR channels
        ranks: DIMM ranks per channel
    """
    c = gf.Component()

    width = 350.0
    height = 200.0

    # PHY block
    phy = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_DDR
    )

    # Byte lanes (8 per channel for 64-bit)
    for ch in range(channels):
        for byte in range(8):
            lane = c << ddr5_byte_lane()
            lane.dmove((byte * 40 + ch * 180, -100))
            if byte == 0:
                c.add_label(f"CH{ch}", position=(byte * 40 + ch * 180 + 80, -130), layer=LAYER_TEXT)

    # Command/Address bus
    ca_bus = c << gf.components.rectangle(size=(100, 30), layer=LAYER_METAL1)
    ca_bus.dmove((20, 150))
    c.add_label("CA BUS", position=(70, 165), layer=LAYER_TEXT)

    # Clock generation
    clk_gen = c << gf.components.rectangle(size=(60, 30), layer=LAYER_METAL2)
    clk_gen.dmove((140, 150))
    c.add_label("CLK", position=(170, 165), layer=LAYER_TEXT)

    # Training engine
    train = c << gf.components.rectangle(size=(80, 50), layer=LAYER_METAL1)
    train.dmove((220, 130))
    c.add_label("TRAIN", position=(260, 155), layer=LAYER_TEXT)

    # FIFO buffers
    fifo = c << gf.components.rectangle(size=(100, 60), layer=LAYER_METAL2)
    fifo.dmove((20, 60))
    c.add_label("RD/WR", position=(70, 90), layer=LAYER_TEXT)
    c.add_label("FIFO", position=(70, 80), layer=LAYER_TEXT)

    # Refresh controller
    refresh = c << gf.components.rectangle(size=(60, 40), layer=LAYER_METAL1)
    refresh.dmove((140, 70))
    c.add_label("REF", position=(170, 90), layer=LAYER_TEXT)

    # Labels
    bandwidth = channels * 64 * DDR5_SPEED / 8 / 1000  # GB/s
    c.add_label(f"DDR5-{DDR5_SPEED} {channels}CH", position=(width/2, height + 20), layer=LAYER_TEXT)
    c.add_label(f"{bandwidth:.0f} GB/s", position=(width/2, height + 35), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="dimm", center=(width/2, -100), width=width * 0.9, orientation=-90, layer=LAYER_PAD)
    c.add_port(name="mem_if", center=(width, height/2), width=80, orientation=0, layer=LAYER_DDR)

    return c


# =============================================================================
# HBM PHY
# =============================================================================

@gf.cell
def hbm_channel() -> Component:
    """Single HBM channel (128-bit)."""
    c = gf.Component()

    width = 60.0
    height = 80.0

    # Channel block
    ch = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_HBM
    )

    # Micro-bump array (simplified)
    bump_rows = 4
    bump_cols = 8
    for row in range(bump_rows):
        for col in range(bump_cols):
            bump = c << gf.components.rectangle(size=(4, 4), layer=LAYER_PAD)
            bump.dmove((5 + col * 7, -10 - row * 6))

    # Channel logic
    logic = c << gf.components.rectangle(size=(40, 30), layer=LAYER_METAL1)
    logic.dmove((10, 40))
    c.add_label("128b", position=(30, 55), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="stack", center=(width/2, -20), width=50, orientation=-90, layer=LAYER_PAD)
    c.add_port(name="internal", center=(width/2, height), width=40, orientation=90, layer=LAYER_HBM)

    return c


@gf.cell
def hbm_phy(
    stacks: int = 2,
    channels_per_stack: int = 8
) -> Component:
    """
    HBM (High Bandwidth Memory) PHY.

    Implements HBM3 with:
    - 1024-bit interface per stack
    - 8 channels per stack
    - Up to 6.4 GT/s
    - 2.5D/3D stacking via interposer

    Args:
        stacks: Number of HBM stacks
        channels_per_stack: Channels per stack (typically 8)
    """
    c = gf.Component()

    total_channels = stacks * channels_per_stack

    width = 150.0 * stacks
    height = 250.0

    # PHY block
    phy = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_HBM
    )

    # HBM channels
    for stack in range(stacks):
        for ch in range(channels_per_stack):
            if ch < 4:
                x = stack * 150 + ch * 35 + 10
                y = -50
            else:
                x = stack * 150 + (ch - 4) * 35 + 10
                y = -120

            channel = c << hbm_channel()
            channel.dmove((x, y))

        c.add_label(f"Stack {stack}", position=(stack * 150 + 75, -150), layer=LAYER_TEXT)

    # Crossbar
    xbar = c << gf.components.rectangle(size=(width - 40, 50), layer=LAYER_METAL1)
    xbar.dmove((20, 170))
    c.add_label("CROSSBAR", position=(width/2, 195), layer=LAYER_TEXT)

    # Command processor
    cmd = c << gf.components.rectangle(size=(80, 40), layer=LAYER_METAL2)
    cmd.dmove((20, 110))
    c.add_label("CMD", position=(60, 130), layer=LAYER_TEXT)

    # Pseudo-channel controller
    pch = c << gf.components.rectangle(size=(100, 40), layer=LAYER_METAL2)
    pch.dmove((width - 130, 110))
    c.add_label("PCH CTRL", position=(width - 80, 130), layer=LAYER_TEXT)

    # ECC engine
    ecc = c << gf.components.rectangle(size=(60, 30), layer=LAYER_METAL1)
    ecc.dmove((width/2 - 30, 70))
    c.add_label("ECC", position=(width/2, 85), layer=LAYER_TEXT)

    # Labels
    bandwidth = stacks * HBM_WIDTH * HBM3_SPEED / 8 / 1000  # GB/s
    c.add_label(f"HBM3 {stacks}S", position=(width/2, height + 20), layer=LAYER_TEXT)
    c.add_label(f"{bandwidth:.0f} GB/s", position=(width/2, height + 35), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="stack", center=(width/2, -150), width=width * 0.9, orientation=-90, layer=LAYER_PAD)
    c.add_port(name="mem_if", center=(width, height/2), width=100, orientation=0, layer=LAYER_HBM)

    return c


# =============================================================================
# MEMORY CONTROLLER
# =============================================================================

@gf.cell
def unified_memory_controller() -> Component:
    """
    Unified Memory Controller.

    Manages all storage types with:
    - Address translation and mapping
    - Coherency management
    - Quality of Service (QoS)
    - Power management
    """
    c = gf.Component()

    width = 250.0
    height = 180.0

    # Controller block
    ctrl = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_MEMCTRL
    )

    # Address translation
    xlat = c << gf.components.rectangle(size=(70, 50), layer=LAYER_METAL1)
    xlat.dmove((20, 110))
    c.add_label("ADDR", position=(55, 135), layer=LAYER_TEXT)
    c.add_label("XLAT", position=(55, 125), layer=LAYER_TEXT)

    # Request scheduler
    sched = c << gf.components.rectangle(size=(70, 50), layer=LAYER_METAL1)
    sched.dmove((100, 110))
    c.add_label("REQ", position=(135, 135), layer=LAYER_TEXT)
    c.add_label("SCHED", position=(135, 125), layer=LAYER_TEXT)

    # QoS engine
    qos = c << gf.components.rectangle(size=(50, 50), layer=LAYER_METAL2)
    qos.dmove((180, 110))
    c.add_label("QoS", position=(205, 135), layer=LAYER_TEXT)

    # Coherency manager
    coh = c << gf.components.rectangle(size=(100, 40), layer=LAYER_METAL1)
    coh.dmove((20, 55))
    c.add_label("COHERENCY", position=(70, 75), layer=LAYER_TEXT)

    # Data mux
    mux = c << gf.components.rectangle(size=(80, 40), layer=LAYER_METAL2)
    mux.dmove((140, 55))
    c.add_label("DATA MUX", position=(180, 75), layer=LAYER_TEXT)

    # Interface ports (left side)
    c.add_label("NVMe", position=(-25, 140), layer=LAYER_TEXT)
    c.add_label("DDR5", position=(-25, 100), layer=LAYER_TEXT)
    c.add_label("HBM", position=(-25, 60), layer=LAYER_TEXT)

    for i, y in enumerate([140, 100, 60]):
        port_rect = c << gf.components.rectangle(size=(15, 25), layer=LAYER_METAL1)
        port_rect.dmove((-15, y - 12))

    # Labels
    c.add_label("UNIFIED MEMORY CONTROLLER", position=(width/2, height + 15), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="nvme_if", center=(0, 140), width=25, orientation=180, layer=LAYER_MEMCTRL)
    c.add_port(name="ddr_if", center=(0, 100), width=25, orientation=180, layer=LAYER_MEMCTRL)
    c.add_port(name="hbm_if", center=(0, 60), width=25, orientation=180, layer=LAYER_MEMCTRL)
    c.add_port(name="dma_if", center=(width, height/2), width=60, orientation=0, layer=LAYER_MEMCTRL)

    return c


# =============================================================================
# DMA ENGINE
# =============================================================================

@gf.cell
def scatter_gather_unit() -> Component:
    """Scatter-gather DMA unit for non-contiguous transfers."""
    c = gf.Component()

    width = 80.0
    height = 60.0

    # Unit block
    unit = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_DMA
    )

    # Descriptor fetch
    desc = c << gf.components.rectangle(size=(30, 25), layer=LAYER_METAL1)
    desc.dmove((5, 30))
    c.add_label("DESC", position=(20, 42), layer=LAYER_TEXT)

    # Address generator
    addr = c << gf.components.rectangle(size=(35, 25), layer=LAYER_METAL1)
    addr.dmove((40, 30))
    c.add_label("ADDR", position=(57, 42), layer=LAYER_TEXT)

    # Data mover
    mover = c << gf.components.rectangle(size=(70, 20), layer=LAYER_METAL2)
    mover.dmove((5, 5))
    c.add_label("DATA MOVER", position=(40, 15), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="ctrl", center=(0, height/2), width=20, orientation=180, layer=LAYER_DMA)
    c.add_port(name="data", center=(width, height/2), width=30, orientation=0, layer=LAYER_DMA)

    return c


@gf.cell
def dma_engine(
    channels: int = 8
) -> Component:
    """
    DMA Engine for autonomous data movement.

    Features:
    - Multi-channel parallel transfers
    - Scatter-gather support
    - Ternary-aware data packing/unpacking
    - Direct path to optical RAM tiers

    Args:
        channels: Number of DMA channels
    """
    c = gf.Component()

    width = 300.0
    height = 200.0

    # Engine block
    engine = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_DMA
    )

    # Scatter-gather units (2 shown, representing multiple)
    for i in range(2):
        sg = c << scatter_gather_unit()
        sg.dmove((20, 110 - i * 70))
        c.add_label(f"CH{i*4}-{i*4+3}", position=(60, 145 - i * 70), layer=LAYER_TEXT)

    # Ternary packer (converts between binary and ternary encoding)
    packer = c << gf.components.rectangle(size=(80, 60), layer=LAYER_METAL1)
    packer.dmove((120, 120))
    c.add_label("TERNARY", position=(160, 150), layer=LAYER_TEXT)
    c.add_label("PACKER", position=(160, 140), layer=LAYER_TEXT)
    c.add_label("81-trit ↔", position=(160, 125), layer=LAYER_TEXT)
    c.add_label("162-bit", position=(160, 115), layer=LAYER_TEXT)

    # Unpacker
    unpacker = c << gf.components.rectangle(size=(80, 60), layer=LAYER_METAL1)
    unpacker.dmove((120, 40))
    c.add_label("TERNARY", position=(160, 70), layer=LAYER_TEXT)
    c.add_label("UNPACKER", position=(160, 60), layer=LAYER_TEXT)

    # Optical RAM interface
    opt_if = c << gf.components.rectangle(size=(60, 80), layer=LAYER_METAL2)
    opt_if.dmove((220, 100))
    c.add_label("OPT", position=(250, 140), layer=LAYER_TEXT)
    c.add_label("RAM", position=(250, 130), layer=LAYER_TEXT)
    c.add_label("I/F", position=(250, 120), layer=LAYER_TEXT)

    # Tier indicators
    c.add_label("T1", position=(285, 160), layer=LAYER_TEXT)
    c.add_label("T2", position=(285, 140), layer=LAYER_TEXT)
    c.add_label("T3", position=(285, 120), layer=LAYER_TEXT)

    # Status/control
    status = c << gf.components.rectangle(size=(50, 30), layer=LAYER_METAL1)
    status.dmove((220, 20))
    c.add_label("STATUS", position=(245, 35), layer=LAYER_TEXT)

    # Labels
    c.add_label(f"DMA ENGINE ({channels} CH)", position=(width/2, height + 15), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="mem_if", center=(0, height/2), width=60, orientation=180, layer=LAYER_DMA)
    c.add_port(name="tier1", center=(width, 160), width=20, orientation=0, layer=LAYER_DMA)
    c.add_port(name="tier2", center=(width, 140), width=20, orientation=0, layer=LAYER_DMA)
    c.add_port(name="tier3", center=(width, 120), width=20, orientation=0, layer=LAYER_DMA)
    c.add_port(name="ioa_bus", center=(width/2, 0), width=80, orientation=-90, layer=LAYER_DMA)

    return c


# =============================================================================
# IOA BUS INTERFACE (for Storage IOA)
# =============================================================================

@gf.cell
def storage_ioa_bus_interface() -> Component:
    """
    IOA Bus interface for Storage IOA.

    Connects to the IOA controller alongside Electronic,
    Network, and Sensor IOAs.
    """
    c = gf.Component()

    width = 200.0
    height = 60.0

    # Bus region
    bus = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_METAL1
    )

    # Data signals
    data_region = c << gf.components.rectangle(size=(120, 40), layer=LAYER_METAL2)
    data_region.dmove((10, 10))
    c.add_label("DATA[161:0]", position=(70, 30), layer=LAYER_TEXT)

    # Control signals
    ctrl_region = c << gf.components.rectangle(size=(50, 40), layer=LAYER_METAL2)
    ctrl_region.dmove((140, 10))
    c.add_label("CTRL", position=(165, 30), layer=LAYER_TEXT)

    # Labels
    c.add_label("STORAGE IOA BUS", position=(width/2, height + 10), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="to_dma", center=(width/2, height), width=width * 0.8, orientation=90, layer=LAYER_METAL1)
    c.add_port(name="to_ioa_ctrl", center=(width/2, 0), width=width * 0.8, orientation=-90, layer=LAYER_METAL1)

    return c


# =============================================================================
# COMPLETE STORAGE IOA
# =============================================================================

@gf.cell
def storage_ioa(
    include_nvme: bool = True,
    include_ddr: bool = True,
    include_hbm: bool = True,
    nvme_lanes: int = 4,
    ddr_channels: int = 2,
    hbm_stacks: int = 2
) -> Component:
    """
    Complete Storage IOA.

    Integrates:
    - NVMe controller for SSDs (persistent storage)
    - DDR5 PHY for DRAM (large working memory)
    - HBM PHY for high-bandwidth memory (accelerator memory)
    - Unified memory controller
    - DMA engine with ternary packing
    - IOA bus interface

    Size: ~800 x 600 um

    Args:
        include_nvme: Include NVMe controller
        include_ddr: Include DDR5 PHY
        include_hbm: Include HBM PHY
        nvme_lanes: PCIe lanes for NVMe
        ddr_channels: DDR5 channels
        hbm_stacks: HBM stacks
    """
    c = gf.Component()

    # Title
    c.add_label("STORAGE IOA", position=(400, 580), layer=LAYER_TEXT)
    c.add_label("Hybrid Memory Interface for Ternary Optical Computer", position=(400, 560), layer=LAYER_TEXT)

    x_offset = 0

    # NVMe Controller
    if include_nvme:
        nvme = c << nvme_controller(lanes=nvme_lanes)
        nvme.dmove((20, 380))
        x_offset = 250

    # DDR5 PHY
    if include_ddr:
        ddr = c << ddr5_phy(channels=ddr_channels)
        ddr.dmove((x_offset + 20, 300))
        x_offset += 400

    # HBM PHY
    if include_hbm:
        hbm = c << hbm_phy(stacks=hbm_stacks)
        hbm.dmove((x_offset + 20, 280))

    # Unified Memory Controller
    mem_ctrl = c << unified_memory_controller()
    mem_ctrl.dmove((250, 120))

    # DMA Engine
    dma = c << dma_engine(channels=8)
    dma.dmove((250, -120))

    # IOA Bus Interface
    bus = c << storage_ioa_bus_interface()
    bus.dmove((300, -220))

    # Connection labels
    c.add_label("TO DIMM/STACK", position=(400, 620), layer=LAYER_TEXT)
    c.add_label("↑", position=(400, 600), layer=LAYER_TEXT)

    c.add_label("↓", position=(400, -180), layer=LAYER_TEXT)
    c.add_label("TO IOA CONTROLLER", position=(400, -250), layer=LAYER_TEXT)

    # Calculate total bandwidth
    bw_nvme = nvme_lanes * NVME_GEN4_SPEED / 8 * 2 if include_nvme else 0
    bw_ddr = ddr_channels * 64 * DDR5_SPEED / 8 / 1000 if include_ddr else 0
    bw_hbm = hbm_stacks * HBM_WIDTH * HBM3_SPEED / 8 / 1000 if include_hbm else 0
    total_bw = bw_nvme + bw_ddr + bw_hbm

    c.add_label(f"Total Bandwidth: {total_bw:.0f} GB/s", position=(400, 540), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="ioa_bus", port=bus.ports["to_ioa_ctrl"])
    c.add_port(name="tier1", port=dma.ports["tier1"])
    c.add_port(name="tier2", port=dma.ports["tier2"])
    c.add_port(name="tier3", port=dma.ports["tier3"])

    if include_nvme:
        c.add_port(name="nvme", port=nvme.ports["pcie"])
    if include_ddr:
        c.add_port(name="ddr", port=ddr.ports["dimm"])
    if include_hbm:
        c.add_port(name="hbm", port=hbm.ports["stack"])

    return c


# =============================================================================
# COMPLETE SYSTEM WITH STORAGE
# =============================================================================

@gf.cell
def storage_ioa_minimal(
    storage_type: Literal["nvme", "ddr", "hbm", "all"] = "ddr"
) -> Component:
    """
    Minimal Storage IOA for specific use case.

    Args:
        storage_type: Which storage to include
    """
    if storage_type == "nvme":
        return storage_ioa(include_nvme=True, include_ddr=False, include_hbm=False)
    elif storage_type == "ddr":
        return storage_ioa(include_nvme=False, include_ddr=True, include_hbm=False)
    elif storage_type == "hbm":
        return storage_ioa(include_nvme=False, include_ddr=False, include_hbm=True)
    else:
        return storage_ioa()


# =============================================================================
# CONVENIENCE GENERATORS
# =============================================================================

def generate_storage_ioa(output_path: Optional[str] = None) -> Component:
    """Generate complete Storage IOA."""
    chip = storage_ioa()
    if output_path:
        chip.write(output_path)
        print(f"Storage IOA saved to: {output_path}")
    return chip


def generate_nvme_only(output_path: Optional[str] = None) -> Component:
    """Generate NVMe-only Storage IOA."""
    chip = storage_ioa(include_nvme=True, include_ddr=False, include_hbm=False)
    if output_path:
        chip.write(output_path)
    return chip


def generate_ddr_only(output_path: Optional[str] = None) -> Component:
    """Generate DDR5-only Storage IOA."""
    chip = storage_ioa(include_nvme=False, include_ddr=True, include_hbm=False)
    if output_path:
        chip.write(output_path)
    return chip


def generate_hbm_only(output_path: Optional[str] = None) -> Component:
    """Generate HBM-only Storage IOA."""
    chip = storage_ioa(include_nvme=False, include_ddr=False, include_hbm=True)
    if output_path:
        chip.write(output_path)
    return chip


# =============================================================================
# INTERACTIVE CLI
# =============================================================================

def interactive_storage_ioa_generator():
    """Interactive CLI for generating Storage IOA components."""
    print("\n" + "="*60)
    print("  STORAGE IOA GENERATOR")
    print("  Memory Interface for Ternary Optical Computer")
    print("="*60)

    print("\nAvailable components:")
    print("  1. Complete Storage IOA (NVMe + DDR5 + HBM)")
    print("  2. NVMe Only (SSD interface)")
    print("  3. DDR5 Only (DRAM interface)")
    print("  4. HBM Only (High Bandwidth Memory)")
    print("  5. Custom configuration")
    print("  6. Individual sub-components")

    choice = input("\nSelect component (1-6): ").strip()

    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data', 'gds')
    os.makedirs(data_dir, exist_ok=True)

    if choice == "1":
        chip = storage_ioa()
        chip_name = "storage_ioa_complete"
    elif choice == "2":
        lanes = int(input("PCIe lanes (1/2/4) [4]: ").strip() or "4")
        chip = storage_ioa(include_nvme=True, include_ddr=False, include_hbm=False, nvme_lanes=lanes)
        chip_name = f"storage_ioa_nvme_x{lanes}"
    elif choice == "3":
        channels = int(input("DDR5 channels (1/2) [2]: ").strip() or "2")
        chip = storage_ioa(include_nvme=False, include_ddr=True, include_hbm=False, ddr_channels=channels)
        chip_name = f"storage_ioa_ddr5_{channels}ch"
    elif choice == "4":
        stacks = int(input("HBM stacks (1/2/4) [2]: ").strip() or "2")
        chip = storage_ioa(include_nvme=False, include_ddr=False, include_hbm=True, hbm_stacks=stacks)
        chip_name = f"storage_ioa_hbm_{stacks}s"
    elif choice == "5":
        print("\nCustom configuration:")
        inc_nvme = input("Include NVMe? (y/n) [y]: ").strip().lower() != "n"
        inc_ddr = input("Include DDR5? (y/n) [y]: ").strip().lower() != "n"
        inc_hbm = input("Include HBM? (y/n) [y]: ").strip().lower() != "n"
        chip = storage_ioa(include_nvme=inc_nvme, include_ddr=inc_ddr, include_hbm=inc_hbm)
        chip_name = "storage_ioa_custom"
    elif choice == "6":
        print("\nSub-components:")
        print("  a. NVMe Controller")
        print("  b. DDR5 PHY")
        print("  c. HBM PHY")
        print("  d. Memory Controller")
        print("  e. DMA Engine")

        sub = input("Select (a-e): ").strip().lower()

        if sub == "a":
            lanes = int(input("PCIe lanes [4]: ").strip() or "4")
            chip = nvme_controller(lanes=lanes)
            chip_name = f"nvme_controller_x{lanes}"
        elif sub == "b":
            ch = int(input("Channels [2]: ").strip() or "2")
            chip = ddr5_phy(channels=ch)
            chip_name = f"ddr5_phy_{ch}ch"
        elif sub == "c":
            stacks = int(input("Stacks [2]: ").strip() or "2")
            chip = hbm_phy(stacks=stacks)
            chip_name = f"hbm_phy_{stacks}s"
        elif sub == "d":
            chip = unified_memory_controller()
            chip_name = "unified_memory_controller"
        elif sub == "e":
            ch = int(input("DMA channels [8]: ").strip() or "8")
            chip = dma_engine(channels=ch)
            chip_name = f"dma_engine_{ch}ch"
        else:
            print("Invalid selection")
            return None
    else:
        print("Invalid selection")
        return None

    # Save GDS
    gds_path = os.path.join(data_dir, f"{chip_name}.gds")
    chip.write(gds_path)
    print(f"\nGDS file saved to: {gds_path}")

    # Offer to open in KLayout
    import subprocess
    show = input("Open in KLayout? (y/n): ").strip().lower()
    if show == "y":
        try:
            subprocess.Popen(["klayout", gds_path])
            print("KLayout launched!")
        except FileNotFoundError:
            print("KLayout not found in PATH")

    return chip


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    interactive_storage_ioa_generator()
