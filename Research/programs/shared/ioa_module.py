#!/usr/bin/env python3
"""
IOA (Input/Output Adapter) Module for Ternary Optical Computer

Modular adapters that connect the IOC to external systems:
1. Electronic IOA - PCIe/USB/GPIO for host computer integration
2. Network IOA - Ethernet/InfiniBand for distributed computing
3. Sensor IOA - ADC inputs for edge computing and signal processing

Architecture:
    External World
         │
    ┌────▼────┐
    │   IOA   │  (Electronic, Network, or Sensor)
    └────┬────┘
         │
    ┌────▼────┐
    │ IOA BUS │  (Standardized 162-bit + control interface)
    └────┬────┘
         │
    ┌────▼────┐
    │   IOC   │  (Input/Output Converter)
    └────┬────┘
         │
    ┌────▼────┐
    │   ALU   │  (81-Trit Optical Processor)
    └─────────┘

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

LAYER_WAVEGUIDE: LayerSpec = (1, 0)      # Optical waveguides
LAYER_HEATER: LayerSpec = (10, 0)        # Thermal tuning / RF
LAYER_METAL1: LayerSpec = (12, 0)        # Metal layer 1 (signals)
LAYER_METAL2: LayerSpec = (20, 0)        # Metal layer 2 (power/ground)
LAYER_VIA: LayerSpec = (21, 0)           # Vias between metal layers
LAYER_PAD: LayerSpec = (22, 0)           # Bond pads
LAYER_SERDES: LayerSpec = (23, 0)        # SerDes regions
LAYER_ADC: LayerSpec = (24, 0)           # ADC regions
LAYER_PHY: LayerSpec = (25, 0)           # PHY regions (Ethernet, etc.)
LAYER_PCIE: LayerSpec = (26, 0)          # PCIe regions
LAYER_TEXT: LayerSpec = (100, 0)         # Labels

# =============================================================================
# Physical Constants
# =============================================================================

# IOA Bus specification (matches IOC interface)
IOA_BUS_WIDTH = 162          # bits (81 trits × 2 bits each)
IOA_CTRL_WIDTH = 16          # Control signals
IOA_STATUS_WIDTH = 8         # Status signals

# Standard pad sizes
BOND_PAD_SIZE = 80.0         # um (for wire bonding)
BUMP_PAD_SIZE = 50.0         # um (for flip-chip)
FINE_PITCH_PAD = 30.0        # um (for high-density)


# =============================================================================
# IOA BUS INTERFACE (Standardized)
# =============================================================================

@gf.cell
def ioa_bus_interface(
    bus_width: int = IOA_BUS_WIDTH,
    ctrl_width: int = IOA_CTRL_WIDTH,
    pad_pitch: float = 10.0
) -> Component:
    """
    Standardized IOA Bus Interface.

    This is the internal interface between any IOA and the IOC.
    All IOAs must implement this interface for compatibility.

    Signals:
    - DATA[161:0]: 81-trit data bus (2 bits per trit)
    - CTRL[15:0]: Control signals (op_select, read/write, etc.)
    - STATUS[7:0]: Status signals (ready, valid, error, etc.)
    - CLK: System clock
    - RST_N: Active-low reset

    Args:
        bus_width: Data bus width in bits
        ctrl_width: Control bus width
        pad_pitch: Pitch between pads
    """
    c = gf.Component()

    # Calculate total width needed
    total_signals = bus_width + ctrl_width + IOA_STATUS_WIDTH + 2  # +2 for CLK, RST
    bus_height = 60.0
    bus_length = total_signals * pad_pitch / 4  # 4 rows of pads

    # Bus region outline
    bus_region = c << gf.components.rectangle(
        size=(bus_length, bus_height),
        layer=LAYER_METAL1
    )

    # Data bus pads (162 signals, arranged in rows)
    data_pads_per_row = bus_width // 4
    for row in range(4):
        for i in range(data_pads_per_row):
            if row * data_pads_per_row + i < bus_width:
                pad = c << gf.components.rectangle(
                    size=(pad_pitch * 0.6, pad_pitch * 0.6),
                    layer=LAYER_METAL1
                )
                pad.dmove((10 + i * pad_pitch, 5 + row * 12))

    # Control/status pads on the right side
    ctrl_start_x = bus_length - 50
    for i in range(ctrl_width + IOA_STATUS_WIDTH + 2):
        pad = c << gf.components.rectangle(
            size=(6, 6),
            layer=LAYER_METAL2
        )
        pad.dmove((ctrl_start_x + (i % 8) * 6, 5 + (i // 8) * 12))

    # Labels
    c.add_label("IOA_BUS", position=(bus_length/2, bus_height + 10), layer=LAYER_TEXT)
    c.add_label(f"DATA[{bus_width-1}:0]", position=(bus_length/4, bus_height + 5), layer=LAYER_TEXT)
    c.add_label("CTRL/STATUS", position=(ctrl_start_x + 20, bus_height + 5), layer=LAYER_TEXT)

    # Bus ports (directly as electrical ports in documentation here, geometry as above)
    c.add_port(
        name="data_bus",
        center=(bus_length/4, 0),
        width=bus_length/2,
        orientation=-90,
        layer=LAYER_METAL1
    )
    c.add_port(
        name="ctrl_bus",
        center=(ctrl_start_x + 20, 0),
        width=50,
        orientation=-90,
        layer=LAYER_METAL2
    )
    c.add_port(
        name="to_ioc",
        center=(bus_length/2, bus_height),
        width=bus_length,
        orientation=90,
        layer=LAYER_METAL1
    )

    return c


# =============================================================================
# ELECTRONIC IOA - PCIe/USB/GPIO
# =============================================================================

@gf.cell
def pcie_phy(
    lanes: int = 4,
    gen: int = 4
) -> Component:
    """
    PCIe PHY block (placeholder).

    Handles PCIe serialization/deserialization.
    Gen4 x4 = 64 GB/s bidirectional.

    Args:
        lanes: Number of PCIe lanes (1, 4, 8, 16)
        gen: PCIe generation (3, 4, 5)
    """
    c = gf.Component()

    width = 150.0
    height = 80.0

    # PHY block
    phy = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_PCIE
    )

    # SerDes blocks (one per lane)
    serdes_width = width / (lanes + 1)
    for i in range(lanes):
        serdes = c << gf.components.rectangle(
            size=(serdes_width * 0.8, height * 0.4),
            layer=LAYER_SERDES
        )
        serdes.dmove((serdes_width * (i + 0.6), height * 0.3))
        c.add_label(f"L{i}", position=(serdes_width * (i + 1), height * 0.5), layer=LAYER_TEXT)

    # High-speed differential pads (TX/RX per lane)
    for i in range(lanes):
        # TX pair
        tx_p = c << gf.components.rectangle(size=(8, 8), layer=LAYER_PAD)
        tx_p.dmove((serdes_width * (i + 0.7), -15))
        tx_n = c << gf.components.rectangle(size=(8, 8), layer=LAYER_PAD)
        tx_n.dmove((serdes_width * (i + 0.7) + 10, -15))

        # RX pair
        rx_p = c << gf.components.rectangle(size=(8, 8), layer=LAYER_PAD)
        rx_p.dmove((serdes_width * (i + 0.7), -30))
        rx_n = c << gf.components.rectangle(size=(8, 8), layer=LAYER_PAD)
        rx_n.dmove((serdes_width * (i + 0.7) + 10, -30))

    # Reference clock pad
    refclk = c << gf.components.rectangle(size=(10, 10), layer=LAYER_PAD)
    refclk.dmove((width - 20, -20))
    c.add_label("REFCLK", position=(width - 15, -35), layer=LAYER_TEXT)

    # Labels
    c.add_label(f"PCIe Gen{gen} x{lanes}", position=(width/2, height + 10), layer=LAYER_TEXT)
    speed = {3: 8, 4: 16, 5: 32}[gen]
    c.add_label(f"{speed * lanes} GT/s", position=(width/2, height + 25), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="pcie_lanes", center=(width/2, -25), width=width * 0.8,
               orientation=-90, layer=LAYER_PAD)
    c.add_port(name="parallel_data", center=(width/2, height), width=width * 0.8,
               orientation=90, layer=LAYER_SERDES)

    return c


@gf.cell
def usb_phy(
    version: Literal["2.0", "3.2", "4"] = "3.2"
) -> Component:
    """
    USB PHY block (placeholder).

    Args:
        version: USB version (2.0, 3.2, 4)
    """
    c = gf.Component()

    width = 100.0
    height = 60.0

    # PHY block
    phy = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_PHY
    )

    # Speed indicator
    speeds = {"2.0": "480 Mbps", "3.2": "20 Gbps", "4": "40 Gbps"}

    # USB connector pads
    if version == "2.0":
        # D+/D- only
        for i, name in enumerate(["D+", "D-", "VCC", "GND"]):
            pad = c << gf.components.rectangle(size=(12, 8), layer=LAYER_PAD)
            pad.dmove((20 + i * 18, -15))
            c.add_label(name, position=(26 + i * 18, -25), layer=LAYER_TEXT)
    else:
        # SuperSpeed lanes + USB 2.0
        for i in range(4):
            pad = c << gf.components.rectangle(size=(8, 8), layer=LAYER_PAD)
            pad.dmove((15 + i * 12, -15))
        for i in range(4):
            pad = c << gf.components.rectangle(size=(8, 8), layer=LAYER_PAD)
            pad.dmove((15 + i * 12, -28))

    # Labels
    c.add_label(f"USB {version}", position=(width/2, height + 10), layer=LAYER_TEXT)
    c.add_label(speeds[version], position=(width/2, height + 22), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="usb_conn", center=(width/2, -20), width=60,
               orientation=-90, layer=LAYER_PAD)
    c.add_port(name="parallel_data", center=(width/2, height), width=60,
               orientation=90, layer=LAYER_PHY)

    return c


@gf.cell
def gpio_bank(
    n_pins: int = 32,
    voltage: float = 3.3
) -> Component:
    """
    General Purpose I/O bank.

    Directly controllable pins for custom interfaces,
    debugging, or simple control signals.

    Args:
        n_pins: Number of GPIO pins
        voltage: I/O voltage level
    """
    c = gf.Component()

    pins_per_row = 16
    n_rows = (n_pins + pins_per_row - 1) // pins_per_row

    pad_size = 15.0
    pad_pitch = 20.0

    width = pins_per_row * pad_pitch
    height = n_rows * pad_pitch + 30

    # Bank outline
    outline = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_METAL1
    )

    # GPIO pads
    for i in range(n_pins):
        row = i // pins_per_row
        col = i % pins_per_row

        pad = c << gf.components.rectangle(
            size=(pad_size, pad_size),
            layer=LAYER_PAD
        )
        pad.dmove((col * pad_pitch + 2.5, row * pad_pitch + 5))

    # Labels
    c.add_label(f"GPIO[{n_pins-1}:0]", position=(width/2, height + 10), layer=LAYER_TEXT)
    c.add_label(f"{voltage}V LVCMOS", position=(width/2, height + 22), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="gpio_pins", center=(width/2, 0), width=width * 0.9,
               orientation=-90, layer=LAYER_PAD)
    c.add_port(name="internal", center=(width/2, height), width=width * 0.9,
               orientation=90, layer=LAYER_METAL1)

    return c


@gf.cell
def electronic_ioa(
    include_pcie: bool = True,
    pcie_lanes: int = 4,
    include_usb: bool = True,
    usb_version: str = "3.2",
    gpio_pins: int = 32
) -> Component:
    """
    Complete Electronic IOA for host computer integration.

    Combines PCIe, USB, and GPIO interfaces with the standardized
    IOA bus interface for connection to the IOC.

    Features:
    - PCIe Gen4 x4 for high-bandwidth data transfer
    - USB 3.2 for universal connectivity
    - 32 GPIO pins for control/debug
    - DMA controller for autonomous data movement

    Size: ~400 x 300 um

    Args:
        include_pcie: Include PCIe interface
        pcie_lanes: Number of PCIe lanes
        include_usb: Include USB interface
        usb_version: USB version string
        gpio_pins: Number of GPIO pins
    """
    c = gf.Component()

    y_offset = 0

    # Title
    c.add_label("ELECTRONIC IOA", position=(200, 280), layer=LAYER_TEXT)
    c.add_label("Host Computer Interface", position=(200, 265), layer=LAYER_TEXT)

    # PCIe PHY
    if include_pcie:
        pcie = c << pcie_phy(lanes=pcie_lanes, gen=4)
        pcie.dmove((20, 150))

    # USB PHY
    if include_usb:
        usb = c << usb_phy(version=usb_version)
        usb.dmove((200, 150))

    # GPIO Bank
    gpio = c << gpio_bank(n_pins=gpio_pins)
    gpio.dmove((320, 150))

    # DMA Controller (placeholder)
    dma_width = 120.0
    dma_height = 50.0
    dma = c << gf.components.rectangle(
        size=(dma_width, dma_height),
        layer=LAYER_METAL1
    )
    dma.dmove((140, 80))
    c.add_label("DMA CTRL", position=(200, 105), layer=LAYER_TEXT)
    c.add_label("Scatter/Gather", position=(200, 95), layer=LAYER_TEXT)

    # IOA Bus Interface (to IOC)
    bus = c << ioa_bus_interface()
    bus.dmove((50, 0))

    # Labels for data flow
    c.add_label("TO HOST", position=(200, 300), layer=LAYER_TEXT)
    c.add_label("↑", position=(200, 290), layer=LAYER_TEXT)
    c.add_label("↓", position=(200, 70), layer=LAYER_TEXT)
    c.add_label("TO IOC", position=(200, -20), layer=LAYER_TEXT)

    # Main ports
    c.add_port(name="ioa_bus", port=bus.ports["to_ioc"])
    if include_pcie:
        c.add_port(name="pcie", port=pcie.ports["pcie_lanes"])
    if include_usb:
        c.add_port(name="usb", port=usb.ports["usb_conn"])
    c.add_port(name="gpio", port=gpio.ports["gpio_pins"])

    return c


# =============================================================================
# NETWORK IOA - Ethernet/InfiniBand
# =============================================================================

@gf.cell
def ethernet_mac(
    speed: Literal["1G", "10G", "25G", "100G"] = "25G"
) -> Component:
    """
    Ethernet MAC block.

    Args:
        speed: Ethernet speed
    """
    c = gf.Component()

    width = 120.0
    height = 70.0

    # MAC block
    mac = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_PHY
    )

    # Sub-blocks
    tx_block = c << gf.components.rectangle(size=(40, 25), layer=LAYER_SERDES)
    tx_block.dmove((10, 35))
    c.add_label("TX", position=(30, 47), layer=LAYER_TEXT)

    rx_block = c << gf.components.rectangle(size=(40, 25), layer=LAYER_SERDES)
    rx_block.dmove((10, 5))
    c.add_label("RX", position=(30, 17), layer=LAYER_TEXT)

    fcs_block = c << gf.components.rectangle(size=(40, 55), layer=LAYER_METAL1)
    fcs_block.dmove((60, 8))
    c.add_label("FCS", position=(80, 35), layer=LAYER_TEXT)

    # Labels
    c.add_label(f"{speed} MAC", position=(width/2, height + 10), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="mii", center=(0, height/2), width=height * 0.8,
               orientation=180, layer=LAYER_PHY)
    c.add_port(name="host", center=(width, height/2), width=height * 0.8,
               orientation=0, layer=LAYER_METAL1)

    return c


@gf.cell
def ethernet_phy(
    speed: Literal["1G", "10G", "25G", "100G"] = "25G"
) -> Component:
    """
    Ethernet PHY with SerDes.

    Args:
        speed: Ethernet speed
    """
    c = gf.Component()

    # Number of lanes based on speed
    lanes = {"1G": 1, "10G": 1, "25G": 1, "100G": 4}[speed]

    width = 100.0
    height = 60.0 + lanes * 15

    # PHY block
    phy = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_PHY
    )

    # SerDes lanes
    for i in range(lanes):
        serdes = c << gf.components.rectangle(
            size=(width * 0.7, 12),
            layer=LAYER_SERDES
        )
        serdes.dmove((15, 10 + i * 15))
        c.add_label(f"Lane{i}", position=(50, 16 + i * 15), layer=LAYER_TEXT)

    # SFP+ / QSFP pads
    for i in range(lanes * 2):  # TX and RX per lane
        pad = c << gf.components.rectangle(size=(8, 8), layer=LAYER_PAD)
        pad.dmove((10 + i * 12, -15))

    # Labels
    c.add_label(f"{speed} PHY", position=(width/2, height + 10), layer=LAYER_TEXT)
    c.add_label(f"{lanes}x SerDes", position=(width/2, height + 22), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="optical", center=(width/2, -10), width=lanes * 24,
               orientation=-90, layer=LAYER_PAD)
    c.add_port(name="mii", center=(width/2, height), width=width * 0.8,
               orientation=90, layer=LAYER_PHY)

    return c


@gf.cell
def rdma_engine() -> Component:
    """
    RDMA (Remote Direct Memory Access) engine.

    Enables zero-copy data transfer between optical computers
    without CPU involvement.
    """
    c = gf.Component()

    width = 140.0
    height = 80.0

    # Engine block
    engine = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_METAL1
    )

    # Queue pairs
    qp_block = c << gf.components.rectangle(size=(50, 30), layer=LAYER_METAL2)
    qp_block.dmove((10, 40))
    c.add_label("QP", position=(35, 55), layer=LAYER_TEXT)

    # Completion queues
    cq_block = c << gf.components.rectangle(size=(50, 30), layer=LAYER_METAL2)
    cq_block.dmove((10, 5))
    c.add_label("CQ", position=(35, 20), layer=LAYER_TEXT)

    # Memory translation
    mtu_block = c << gf.components.rectangle(size=(50, 65), layer=LAYER_METAL2)
    mtu_block.dmove((70, 8))
    c.add_label("MTU", position=(95, 40), layer=LAYER_TEXT)

    # Labels
    c.add_label("RDMA ENGINE", position=(width/2, height + 10), layer=LAYER_TEXT)
    c.add_label("Zero-Copy DMA", position=(width/2, height + 22), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="network", center=(0, height/2), width=height * 0.8,
               orientation=180, layer=LAYER_METAL1)
    c.add_port(name="memory", center=(width, height/2), width=height * 0.8,
               orientation=0, layer=LAYER_METAL1)

    return c


@gf.cell
def network_ioa(
    speed: Literal["1G", "10G", "25G", "100G"] = "25G",
    ports: int = 2,
    include_rdma: bool = True
) -> Component:
    """
    Complete Network IOA for distributed computing.

    Provides high-speed network connectivity for:
    - Cluster computing with multiple optical computers
    - Data center integration
    - Remote processing nodes

    Features:
    - Dual 25G Ethernet (or configurable)
    - RDMA for zero-copy transfers
    - TCP/IP offload engine
    - Hardware packet filtering

    Size: ~450 x 350 um

    Args:
        speed: Network speed per port
        ports: Number of network ports
        include_rdma: Include RDMA engine
    """
    c = gf.Component()

    # Title
    c.add_label("NETWORK IOA", position=(225, 330), layer=LAYER_TEXT)
    c.add_label("Distributed Computing Interface", position=(225, 315), layer=LAYER_TEXT)

    # Ethernet PHYs
    for i in range(ports):
        phy = c << ethernet_phy(speed=speed)
        phy.dmove((20 + i * 120, 200))
        c.add_label(f"Port {i}", position=(70 + i * 120, 290), layer=LAYER_TEXT)

    # Ethernet MACs
    for i in range(ports):
        mac = c << ethernet_mac(speed=speed)
        mac.dmove((20 + i * 140, 110))

    # RDMA Engine
    if include_rdma:
        rdma = c << rdma_engine()
        rdma.dmove((300, 110))

    # TCP/IP Offload placeholder
    tcp_width = 100.0
    tcp_height = 50.0
    tcp = c << gf.components.rectangle(
        size=(tcp_width, tcp_height),
        layer=LAYER_METAL1
    )
    tcp.dmove((20, 50))
    c.add_label("TCP/IP", position=(70, 75), layer=LAYER_TEXT)
    c.add_label("Offload", position=(70, 65), layer=LAYER_TEXT)

    # Packet filter
    filter_block = c << gf.components.rectangle(
        size=(80, 50),
        layer=LAYER_METAL1
    )
    filter_block.dmove((140, 50))
    c.add_label("PKT", position=(180, 75), layer=LAYER_TEXT)
    c.add_label("FILTER", position=(180, 65), layer=LAYER_TEXT)

    # IOA Bus Interface
    bus = c << ioa_bus_interface()
    bus.dmove((80, -20))

    # Labels for data flow
    c.add_label("TO NETWORK", position=(120, 350), layer=LAYER_TEXT)
    c.add_label("↑", position=(120, 340), layer=LAYER_TEXT)
    c.add_label("↓", position=(200, 40), layer=LAYER_TEXT)
    c.add_label("TO IOC", position=(200, -40), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="ioa_bus", port=bus.ports["to_ioc"])
    for i in range(ports):
        c.add_port(
            name=f"eth{i}",
            center=(70 + i * 120, 185),
            width=50,
            orientation=-90,
            layer=LAYER_PAD
        )

    return c


# =============================================================================
# SENSOR IOA - ADC Inputs
# =============================================================================

@gf.cell
def adc_channel(
    resolution: int = 16,
    sample_rate_msps: float = 100.0,
    channel_id: int = 0
) -> Component:
    """
    Single ADC channel.

    Args:
        resolution: ADC resolution in bits
        sample_rate_msps: Sample rate in MSPS
        channel_id: Channel number
    """
    c = gf.Component()

    width = 80.0
    height = 50.0

    # ADC block
    adc = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_ADC
    )

    # Sample-and-hold
    sh = c << gf.components.rectangle(size=(20, 20), layer=LAYER_METAL1)
    sh.dmove((5, 15))
    c.add_label("S/H", position=(15, 25), layer=LAYER_TEXT)

    # Successive approximation / pipeline
    conv = c << gf.components.rectangle(size=(35, 30), layer=LAYER_METAL1)
    conv.dmove((30, 10))
    c.add_label("SAR", position=(47, 25), layer=LAYER_TEXT)

    # Input pad
    in_pad = c << gf.components.rectangle(size=(15, 15), layer=LAYER_PAD)
    in_pad.dmove((-20, height/2 - 7.5))

    # Labels
    c.add_label(f"CH{channel_id}", position=(width/2, height + 8), layer=LAYER_TEXT)
    c.add_label(f"{resolution}b", position=(width/2, -10), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="analog_in", center=(-12.5, height/2), width=15,
               orientation=180, layer=LAYER_PAD)
    c.add_port(name="digital_out", center=(width, height/2), width=20,
               orientation=0, layer=LAYER_METAL1)

    return c


@gf.cell
def anti_alias_filter(
    cutoff_mhz: float = 50.0
) -> Component:
    """
    Anti-aliasing filter for ADC input.

    Args:
        cutoff_mhz: Filter cutoff frequency
    """
    c = gf.Component()

    width = 60.0
    height = 30.0

    # Filter block
    filt = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_METAL1
    )

    # Labels
    c.add_label("AAF", position=(width/2, height/2 + 2), layer=LAYER_TEXT)
    c.add_label(f"{cutoff_mhz}MHz", position=(width/2, height/2 - 8), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="in", center=(0, height/2), width=10,
               orientation=180, layer=LAYER_METAL1)
    c.add_port(name="out", center=(width, height/2), width=10,
               orientation=0, layer=LAYER_METAL1)

    return c


@gf.cell
def signal_conditioner() -> Component:
    """
    Signal conditioning block (gain, offset, protection).
    """
    c = gf.Component()

    width = 70.0
    height = 40.0

    # Conditioner block
    cond = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_METAL1
    )

    # Sub-blocks
    pga = c << gf.components.rectangle(size=(25, 25), layer=LAYER_METAL2)
    pga.dmove((5, 7.5))
    c.add_label("PGA", position=(17, 20), layer=LAYER_TEXT)

    offset = c << gf.components.rectangle(size=(25, 25), layer=LAYER_METAL2)
    offset.dmove((35, 7.5))
    c.add_label("OFS", position=(47, 20), layer=LAYER_TEXT)

    # Labels
    c.add_label("COND", position=(width/2, height + 8), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="in", center=(0, height/2), width=15,
               orientation=180, layer=LAYER_METAL1)
    c.add_port(name="out", center=(width, height/2), width=15,
               orientation=0, layer=LAYER_METAL1)

    return c


@gf.cell
def ternary_quantizer() -> Component:
    """
    Ternary quantizer - converts analog to ternary encoding.

    Uses two comparators to produce 3-level output:
    - Below threshold_low: -1 (Red)
    - Between thresholds: 0 (Green)
    - Above threshold_high: +1 (Blue)
    """
    c = gf.Component()

    width = 90.0
    height = 50.0

    # Quantizer block
    quant = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_METAL1
    )

    # Comparators
    comp1 = c << gf.components.rectangle(size=(25, 18), layer=LAYER_METAL2)
    comp1.dmove((10, 25))
    c.add_label("CMP+", position=(22, 34), layer=LAYER_TEXT)

    comp2 = c << gf.components.rectangle(size=(25, 18), layer=LAYER_METAL2)
    comp2.dmove((10, 5))
    c.add_label("CMP-", position=(22, 14), layer=LAYER_TEXT)

    # Encoder
    enc = c << gf.components.rectangle(size=(30, 40), layer=LAYER_METAL2)
    enc.dmove((45, 5))
    c.add_label("2b", position=(60, 25), layer=LAYER_TEXT)
    c.add_label("ENC", position=(60, 18), layer=LAYER_TEXT)

    # Threshold adjust pads
    th_hi = c << gf.components.rectangle(size=(10, 10), layer=LAYER_PAD)
    th_hi.dmove((width + 5, 35))
    c.add_label("TH+", position=(width + 10, 50), layer=LAYER_TEXT)

    th_lo = c << gf.components.rectangle(size=(10, 10), layer=LAYER_PAD)
    th_lo.dmove((width + 5, 5))
    c.add_label("TH-", position=(width + 10, 0), layer=LAYER_TEXT)

    # Labels
    c.add_label("TERNARY QUANT", position=(width/2, height + 10), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="analog_in", center=(0, height/2), width=15,
               orientation=180, layer=LAYER_METAL1)
    c.add_port(name="trit_out", center=(width, height/2), width=10,
               orientation=0, layer=LAYER_METAL1)

    return c


@gf.cell
def sensor_ioa(
    n_channels: int = 8,
    resolution: int = 16,
    sample_rate_msps: float = 100.0,
    include_ternary_quant: bool = True
) -> Component:
    """
    Complete Sensor IOA for edge computing and signal processing.

    Provides multi-channel analog input for:
    - Sensor arrays (image, audio, RF)
    - Scientific instruments
    - Real-time signal processing
    - Direct ternary quantization

    Features:
    - 8 channels (configurable)
    - 16-bit resolution at 100 MSPS
    - Anti-aliasing filters
    - Signal conditioning (gain, offset)
    - Optional direct ternary quantization
    - Synchronous sampling

    Size: ~500 x 400 um

    Args:
        n_channels: Number of ADC channels
        resolution: ADC resolution in bits
        sample_rate_msps: Sample rate per channel
        include_ternary_quant: Include ternary quantizers
    """
    c = gf.Component()

    # Title
    c.add_label("SENSOR IOA", position=(250, 380), layer=LAYER_TEXT)
    c.add_label("Edge Computing Interface", position=(250, 365), layer=LAYER_TEXT)
    c.add_label(f"{n_channels}ch × {resolution}b @ {sample_rate_msps} MSPS",
                position=(250, 350), layer=LAYER_TEXT)

    # Channel spacing
    ch_spacing = 40.0
    ch_start_y = 280

    # Input connectors (sensor array)
    for i in range(n_channels):
        y_pos = ch_start_y - i * ch_spacing

        # Connector pad
        conn = c << gf.components.rectangle(size=(20, 15), layer=LAYER_PAD)
        conn.dmove((0, y_pos))
        c.add_label(f"S{i}", position=(10, y_pos + 20), layer=LAYER_TEXT)

    # Signal conditioners
    for i in range(n_channels):
        y_pos = ch_start_y - i * ch_spacing
        cond = c << signal_conditioner()
        cond.dmove((40, y_pos - 5))

    # Anti-alias filters
    for i in range(n_channels):
        y_pos = ch_start_y - i * ch_spacing
        aaf = c << anti_alias_filter(cutoff_mhz=sample_rate_msps / 2)
        aaf.dmove((130, y_pos))

    # ADC channels
    for i in range(n_channels):
        y_pos = ch_start_y - i * ch_spacing
        adc = c << adc_channel(resolution=resolution,
                               sample_rate_msps=sample_rate_msps,
                               channel_id=i)
        adc.dmove((210, y_pos - 10))

    # Ternary quantizers (optional)
    if include_ternary_quant:
        for i in range(n_channels):
            y_pos = ch_start_y - i * ch_spacing
            quant = c << ternary_quantizer()
            quant.dmove((310, y_pos - 10))

    # Sample clock distribution
    clk_dist = c << gf.components.rectangle(size=(80, 30), layer=LAYER_METAL2)
    clk_dist.dmove((350, 30))
    c.add_label("SAMPLE CLK", position=(390, 45), layer=LAYER_TEXT)

    # External trigger input
    trig_pad = c << gf.components.rectangle(size=(15, 15), layer=LAYER_PAD)
    trig_pad.dmove((440, 35))
    c.add_label("TRIG", position=(447, 55), layer=LAYER_TEXT)

    # IOA Bus Interface
    bus = c << ioa_bus_interface()
    bus.dmove((120, -30))

    # Labels for data flow
    c.add_label("FROM SENSORS", position=(10, 400), layer=LAYER_TEXT)
    c.add_label("↓", position=(10, 390), layer=LAYER_TEXT)
    c.add_label("↓", position=(250, 0), layer=LAYER_TEXT)
    c.add_label("TO IOC", position=(250, -50), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="ioa_bus", port=bus.ports["to_ioc"])

    # Sensor input ports
    for i in range(n_channels):
        y_pos = ch_start_y - i * ch_spacing
        c.add_port(
            name=f"sensor_{i}",
            center=(0, y_pos + 7.5),
            width=15,
            orientation=180,
            layer=LAYER_PAD
        )

    # Trigger port
    c.add_port(name="trigger", center=(447.5, 42.5), width=15,
               orientation=0, layer=LAYER_PAD)

    return c


# =============================================================================
# IOA CONTROLLER - Manages Multiple Adapters
# =============================================================================

@gf.cell
def ioa_arbiter(
    n_ports: int = 3
) -> Component:
    """
    IOA bus arbiter for multiple adapters.

    Manages access to the IOC from multiple IOAs using
    priority-based arbitration.

    Args:
        n_ports: Number of IOA ports to arbitrate
    """
    c = gf.Component()

    width = 120.0
    height = 80.0

    # Arbiter block
    arb = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_METAL1
    )

    # Priority encoder
    pri = c << gf.components.rectangle(size=(40, 30), layer=LAYER_METAL2)
    pri.dmove((10, 40))
    c.add_label("PRI", position=(30, 55), layer=LAYER_TEXT)

    # Mux
    mux = c << gf.components.rectangle(size=(40, 30), layer=LAYER_METAL2)
    mux.dmove((10, 5))
    c.add_label("MUX", position=(30, 20), layer=LAYER_TEXT)

    # State machine
    fsm = c << gf.components.rectangle(size=(40, 65), layer=LAYER_METAL2)
    fsm.dmove((60, 8))
    c.add_label("FSM", position=(80, 40), layer=LAYER_TEXT)

    # Input ports
    for i in range(n_ports):
        y_pos = height * (i + 1) / (n_ports + 1)
        pad = c << gf.components.rectangle(size=(10, 10), layer=LAYER_METAL1)
        pad.dmove((-15, y_pos - 5))
        c.add_label(f"P{i}", position=(-20, y_pos), layer=LAYER_TEXT)

    # Labels
    c.add_label("ARBITER", position=(width/2, height + 10), layer=LAYER_TEXT)

    # Ports
    for i in range(n_ports):
        y_pos = height * (i + 1) / (n_ports + 1)
        c.add_port(
            name=f"ioa_in_{i}",
            center=(-10, y_pos),
            width=10,
            orientation=180,
            layer=LAYER_METAL1
        )

    c.add_port(name="ioc_out", center=(width, height/2), width=30,
               orientation=0, layer=LAYER_METAL1)

    return c


@gf.cell
def ioa_controller(
    include_electronic: bool = True,
    include_network: bool = True,
    include_sensor: bool = True
) -> Component:
    """
    Complete IOA Controller managing multiple adapters.

    Coordinates access between Electronic, Network, and Sensor IOAs
    with priority arbitration and data routing.

    Features:
    - Priority-based arbitration (Sensor > Network > Electronic)
    - Buffered data paths
    - Status monitoring
    - Error handling

    Size: ~300 x 200 um

    Args:
        include_electronic: Include Electronic IOA port
        include_network: Include Network IOA port
        include_sensor: Include Sensor IOA port
    """
    c = gf.Component()

    n_ports = sum([include_electronic, include_network, include_sensor])

    # Title
    c.add_label("IOA CONTROLLER", position=(150, 180), layer=LAYER_TEXT)

    # Arbiter
    arbiter = c << ioa_arbiter(n_ports=n_ports)
    arbiter.dmove((90, 80))

    # Input buffers for each IOA type
    port_idx = 0
    port_labels = []

    if include_sensor:
        buf = c << gf.components.rectangle(size=(60, 30), layer=LAYER_METAL2)
        buf.dmove((10, 130))
        c.add_label("SENSOR", position=(40, 145), layer=LAYER_TEXT)
        c.add_label("(Priority 0)", position=(40, 125), layer=LAYER_TEXT)
        port_labels.append(("sensor_ioa", (0, 145)))
        port_idx += 1

    if include_network:
        buf = c << gf.components.rectangle(size=(60, 30), layer=LAYER_METAL2)
        buf.dmove((10, 90))
        c.add_label("NETWORK", position=(40, 105), layer=LAYER_TEXT)
        c.add_label("(Priority 1)", position=(40, 85), layer=LAYER_TEXT)
        port_labels.append(("network_ioa", (0, 105)))
        port_idx += 1

    if include_electronic:
        buf = c << gf.components.rectangle(size=(60, 30), layer=LAYER_METAL2)
        buf.dmove((10, 50))
        c.add_label("ELEC", position=(40, 65), layer=LAYER_TEXT)
        c.add_label("(Priority 2)", position=(40, 45), layer=LAYER_TEXT)
        port_labels.append(("electronic_ioa", (0, 65)))

    # Status register
    status = c << gf.components.rectangle(size=(50, 40), layer=LAYER_METAL1)
    status.dmove((230, 100))
    c.add_label("STATUS", position=(255, 120), layer=LAYER_TEXT)

    # Output to IOC
    ioc_out = c << gf.components.rectangle(size=(40, 50), layer=LAYER_METAL1)
    ioc_out.dmove((230, 40))
    c.add_label("TO", position=(250, 65), layer=LAYER_TEXT)
    c.add_label("IOC", position=(250, 55), layer=LAYER_TEXT)

    # Ports
    for name, pos in port_labels:
        c.add_port(
            name=name,
            center=pos,
            width=30,
            orientation=180,
            layer=LAYER_METAL1
        )

    c.add_port(name="ioc_bus", center=(270, 65), width=50,
               orientation=0, layer=LAYER_METAL1)
    c.add_port(name="status", center=(255, 140), width=20,
               orientation=90, layer=LAYER_METAL1)

    return c


# =============================================================================
# COMPLETE IOA SYSTEM
# =============================================================================

@gf.cell
def ioa_system_complete(
    include_electronic: bool = True,
    include_network: bool = True,
    include_sensor: bool = True,
    pcie_lanes: int = 4,
    eth_speed: str = "25G",
    n_sensor_channels: int = 8
) -> Component:
    """
    Complete IOA system with all adapters.

    Integrates:
    - Electronic IOA (PCIe x4, USB 3.2, 32 GPIO)
    - Network IOA (Dual 25G Ethernet, RDMA)
    - Sensor IOA (8-channel 16-bit ADC)
    - IOA Controller with arbitration

    Size: ~1200 x 500 um

    Args:
        include_electronic: Include Electronic IOA
        include_network: Include Network IOA
        include_sensor: Include Sensor IOA
        pcie_lanes: PCIe lane count
        eth_speed: Ethernet speed
        n_sensor_channels: Number of sensor channels
    """
    c = gf.Component()

    # Title
    c.add_label("COMPLETE IOA SYSTEM", position=(600, 480), layer=LAYER_TEXT)
    c.add_label("Input/Output Adapters for Ternary Optical Computer",
                position=(600, 460), layer=LAYER_TEXT)

    x_offset = 0

    # Electronic IOA
    if include_electronic:
        elec = c << electronic_ioa(pcie_lanes=pcie_lanes)
        elec.dmove((x_offset, 100))
        x_offset += 450

    # Network IOA
    if include_network:
        net = c << network_ioa(speed=eth_speed)
        net.dmove((x_offset, 100))
        x_offset += 480

    # Sensor IOA
    if include_sensor:
        sens = c << sensor_ioa(n_channels=n_sensor_channels)
        sens.dmove((x_offset, 50))
        x_offset += 520

    # IOA Controller
    ctrl = c << ioa_controller(
        include_electronic=include_electronic,
        include_network=include_network,
        include_sensor=include_sensor
    )
    ctrl.dmove((500, -150))

    # Connection labels
    c.add_label("↓ TO IOC ↓", position=(600, -180), layer=LAYER_TEXT)

    # Main output port
    c.add_port(name="ioc_bus", port=ctrl.ports["ioc_bus"])

    return c


# =============================================================================
# CONVENIENCE GENERATORS
# =============================================================================

def generate_electronic_ioa(output_path: Optional[str] = None) -> Component:
    """Generate Electronic IOA."""
    chip = electronic_ioa()
    if output_path:
        chip.write(output_path)
        print(f"Electronic IOA saved to: {output_path}")
    return chip


def generate_network_ioa(output_path: Optional[str] = None) -> Component:
    """Generate Network IOA."""
    chip = network_ioa()
    if output_path:
        chip.write(output_path)
        print(f"Network IOA saved to: {output_path}")
    return chip


def generate_sensor_ioa(output_path: Optional[str] = None) -> Component:
    """Generate Sensor IOA."""
    chip = sensor_ioa()
    if output_path:
        chip.write(output_path)
        print(f"Sensor IOA saved to: {output_path}")
    return chip


def generate_ioa_system(output_path: Optional[str] = None) -> Component:
    """Generate complete IOA system."""
    chip = ioa_system_complete()
    if output_path:
        chip.write(output_path)
        print(f"IOA System saved to: {output_path}")
    return chip


# =============================================================================
# INTERACTIVE CLI
# =============================================================================

def interactive_ioa_generator():
    """Interactive CLI for generating IOA components."""
    print("\n" + "="*60)
    print("  IOA MODULE GENERATOR")
    print("  Input/Output Adapters for Ternary Optical Computer")
    print("="*60)

    print("\nAvailable components:")
    print("  1. Electronic IOA (PCIe + USB + GPIO)")
    print("  2. Network IOA (Ethernet + RDMA)")
    print("  3. Sensor IOA (Multi-channel ADC)")
    print("  4. IOA Controller (Arbiter)")
    print("  5. Complete IOA System (All adapters)")
    print("  6. IOA Bus Interface (standardized)")
    print("  7. Individual sub-components")

    choice = input("\nSelect component (1-7): ").strip()

    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data', 'gds')
    os.makedirs(data_dir, exist_ok=True)

    if choice == "1":
        print("\nElectronic IOA Configuration:")
        lanes = int(input("  PCIe lanes (1/4/8/16) [4]: ").strip() or "4")
        chip = electronic_ioa(pcie_lanes=lanes)
        chip_name = f"electronic_ioa_pcie_x{lanes}"

    elif choice == "2":
        print("\nNetwork IOA Configuration:")
        print("  Speed options: 1G, 10G, 25G, 100G")
        speed = input("  Ethernet speed [25G]: ").strip() or "25G"
        ports = int(input("  Number of ports (1-4) [2]: ").strip() or "2")
        chip = network_ioa(speed=speed, ports=ports)
        chip_name = f"network_ioa_{speed}_x{ports}"

    elif choice == "3":
        print("\nSensor IOA Configuration:")
        channels = int(input("  Number of channels (1-16) [8]: ").strip() or "8")
        resolution = int(input("  ADC resolution (8/12/16/24) [16]: ").strip() or "16")
        chip = sensor_ioa(n_channels=channels, resolution=resolution)
        chip_name = f"sensor_ioa_{channels}ch_{resolution}b"

    elif choice == "4":
        chip = ioa_controller()
        chip_name = "ioa_controller"

    elif choice == "5":
        print("\nComplete IOA System Configuration:")
        include_elec = input("  Include Electronic IOA? (y/n) [y]: ").strip().lower() != "n"
        include_net = input("  Include Network IOA? (y/n) [y]: ").strip().lower() != "n"
        include_sens = input("  Include Sensor IOA? (y/n) [y]: ").strip().lower() != "n"
        chip = ioa_system_complete(
            include_electronic=include_elec,
            include_network=include_net,
            include_sensor=include_sens
        )
        chip_name = "ioa_system_complete"

    elif choice == "6":
        chip = ioa_bus_interface()
        chip_name = "ioa_bus_interface"

    elif choice == "7":
        print("\nSub-components:")
        print("  a. PCIe PHY")
        print("  b. USB PHY")
        print("  c. GPIO Bank")
        print("  d. Ethernet MAC")
        print("  e. Ethernet PHY")
        print("  f. RDMA Engine")
        print("  g. ADC Channel")
        print("  h. Ternary Quantizer")
        print("  i. IOA Arbiter")

        sub = input("Select (a-i): ").strip().lower()

        if sub == "a":
            lanes = int(input("  PCIe lanes [4]: ").strip() or "4")
            gen = int(input("  PCIe gen (3/4/5) [4]: ").strip() or "4")
            chip = pcie_phy(lanes=lanes, gen=gen)
            chip_name = f"pcie_phy_gen{gen}_x{lanes}"
        elif sub == "b":
            ver = input("  USB version (2.0/3.2/4) [3.2]: ").strip() or "3.2"
            chip = usb_phy(version=ver)
            chip_name = f"usb_phy_{ver.replace('.', '_')}"
        elif sub == "c":
            pins = int(input("  GPIO pins [32]: ").strip() or "32")
            chip = gpio_bank(n_pins=pins)
            chip_name = f"gpio_bank_{pins}"
        elif sub == "d":
            speed = input("  Speed (1G/10G/25G/100G) [25G]: ").strip() or "25G"
            chip = ethernet_mac(speed=speed)
            chip_name = f"ethernet_mac_{speed}"
        elif sub == "e":
            speed = input("  Speed (1G/10G/25G/100G) [25G]: ").strip() or "25G"
            chip = ethernet_phy(speed=speed)
            chip_name = f"ethernet_phy_{speed}"
        elif sub == "f":
            chip = rdma_engine()
            chip_name = "rdma_engine"
        elif sub == "g":
            res = int(input("  Resolution (8/12/16/24) [16]: ").strip() or "16")
            chip = adc_channel(resolution=res)
            chip_name = f"adc_channel_{res}b"
        elif sub == "h":
            chip = ternary_quantizer()
            chip_name = "ternary_quantizer"
        elif sub == "i":
            ports = int(input("  Number of ports [3]: ").strip() or "3")
            chip = ioa_arbiter(n_ports=ports)
            chip_name = f"ioa_arbiter_{ports}p"
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
    interactive_ioa_generator()
