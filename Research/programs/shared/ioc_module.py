#!/usr/bin/env python3
"""
IOC (Input/Output Converter) Module for Ternary Optical Computer

Bridges electronic and optical domains for the 81-trit ternary optical computer.

Functions:
1. ENCODE: Electronic ternary values -> RGB wavelength-encoded optical signals
2. DECODE: 5-level photodetector outputs -> electronic ternary values + carry
3. BUFFER/SYNC: Handle timing between fast optical ALU (~1.6ns) and electronic control

Specifications:
- Power Budget:
  - Laser input: 10 dBm per wavelength
  - MZI modulator loss: 3 dB
  - Combiner loss: 3 dB
  - Available at ALU: +4 dBm
  - Margin above -30 dBm detector: 18+ dB

- Timing:
  - Encode latency: ~1.7 ns
  - Decode latency: ~1.2 ns
  - FIFO latency: 1.6-6.5 ns (configurable)
  - Compatible with 20 ps inter-trit, 617 MHz word rate

Author: Wavelength-Division Ternary Optical Computer Project
"""

import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.typings import LayerSpec
from gdsfactory.routing import route_single
import numpy as np
from typing import Optional, Literal

# Import IOA bus interface for external connectivity
try:
    from ioa_module import ioa_bus_interface
    IOA_AVAILABLE = True
except ImportError:
    IOA_AVAILABLE = False

# Activate PDK
gf.gpdk.PDK.activate()

# Default cross-section for routing
XS = gf.cross_section.strip(width=0.5)

# =============================================================================
# Layer Definitions
# =============================================================================

LAYER_WAVEGUIDE: LayerSpec = (1, 0)      # Main optical waveguides
LAYER_HEATER: LayerSpec = (10, 0)        # Thermal tuning heaters / RF pads
LAYER_CARRY: LayerSpec = (11, 0)         # Carry chain elements
LAYER_METAL_PAD: LayerSpec = (12, 0)     # Electrical contact pads
LAYER_LOG: LayerSpec = (13, 0)           # Log converter / saturable absorber
LAYER_GAIN: LayerSpec = (14, 0)          # SOA / gain regions
LAYER_AWG: LayerSpec = (15, 0)           # AWG demux regions
LAYER_DETECTOR: LayerSpec = (16, 0)      # Photodetector regions
LAYER_LASER: LayerSpec = (17, 0)         # Laser source regions
LAYER_FIFO: LayerSpec = (18, 0)          # FIFO / buffer regions
LAYER_TEXT: LayerSpec = (100, 0)         # Labels

# =============================================================================
# Physical Constants
# =============================================================================

WAVEGUIDE_WIDTH = 0.5           # um
BEND_RADIUS = 5.0               # um
MZI_ARM_LENGTH = 50.0           # um
MZI_ARM_SPACING = 10.0          # um

# Ternary wavelengths
WAVELENGTH_RED = 1.550          # um (NEG, -1)
WAVELENGTH_GREEN = 1.216        # um (ZERO, 0)
WAVELENGTH_BLUE = 1.000         # um (POS, +1)

# Output wavelengths from SFG mixer (5 channels)
OUTPUT_WAVELENGTHS = {
    'NEG2': 0.775,    # R+R = -2 (overflow)
    'NEG1': 0.681,    # R+G = -1
    'ZERO': 0.608,    # R+B or G+G = 0
    'POS1': 0.549,    # G+B = +1
    'POS2': 0.500,    # B+B = +2 (overflow)
}


# =============================================================================
# ENCODE STAGE COMPONENTS
# =============================================================================

@gf.cell
def ioc_laser_source(
    wavelength_um: float = 1.55,
    width: float = 200.0,
    height: float = 100.0,
    label: str = "DFB"
) -> Component:
    """
    DFB laser source placeholder for 3-wavelength CW laser array.

    In actual implementation, this would be a III-V bonded DFB laser
    or an external laser coupled via edge coupler.

    Args:
        wavelength_um: Laser wavelength in micrometers
        width: Component width in um
        height: Component height in um
        label: Label for the laser (R/G/B)
    """
    c = gf.Component()

    # Laser cavity region
    laser_body = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_LASER
    )

    # Output taper
    taper_length = 30.0
    taper = c << gf.components.taper(
        length=taper_length,
        width1=10.0,
        width2=WAVEGUIDE_WIDTH
    )
    taper.move((width, height/2 - 5))

    # Electrical contacts for current injection
    contact_width = width * 0.7
    contact_height = 15.0

    top_contact = c << gf.components.rectangle(
        size=(contact_width, contact_height),
        layer=LAYER_METAL_PAD
    )
    top_contact.move((width * 0.15, height + 5))

    bottom_contact = c << gf.components.rectangle(
        size=(contact_width, contact_height),
        layer=LAYER_METAL_PAD
    )
    bottom_contact.move((width * 0.15, -contact_height - 5))

    # Labels
    wl_nm = int(wavelength_um * 1000)
    c.add_label(f"{label}", position=(width/2, height/2), layer=LAYER_TEXT)
    c.add_label(f"{wl_nm}nm", position=(width/2, height/2 - 15), layer=LAYER_TEXT)
    c.add_label("DFB", position=(width/2, height + contact_height + 10), layer=LAYER_TEXT)

    # Output port
    c.add_port(
        name="output",
        center=(width + taper_length, height/2 - 5 + WAVEGUIDE_WIDTH/2),
        width=WAVEGUIDE_WIDTH,
        orientation=0,
        layer=LAYER_WAVEGUIDE
    )

    # Electrical ports
    c.add_port(
        name="current_p",
        center=(width/2, height + 5 + contact_height/2),
        width=contact_width,
        orientation=90,
        layer=LAYER_METAL_PAD
    )
    c.add_port(
        name="current_n",
        center=(width/2, -5 - contact_height/2),
        width=contact_width,
        orientation=-90,
        layer=LAYER_METAL_PAD
    )

    return c


@gf.cell
def ioc_mzi_modulator(
    arm_length: float = MZI_ARM_LENGTH,
    arm_spacing: float = MZI_ARM_SPACING,
    heater_length: float = 30.0,
    heater_width: float = 2.0
) -> Component:
    """
    MZI-based intensity modulator for wavelength gating.

    Uses thermo-optic or electro-optic effect for high-speed modulation.
    RF input pads allow GHz modulation rates for 617 MHz word rate.

    Args:
        arm_length: Length of each MZI arm (um)
        arm_spacing: Vertical spacing between arms (um)
        heater_length: Length of heater/electrode region (um)
        heater_width: Width of heater strip (um)
    """
    c = gf.Component()

    coupler_length = 10.0

    # Input 3dB coupler (MMI-based)
    coupler_in = c << gf.components.mmi1x2()
    coupler_in.dmove((0, 0))

    # Upper arm waveguide
    arm_upper = c << gf.components.straight(length=arm_length, width=WAVEGUIDE_WIDTH)
    arm_upper.dmove((coupler_length + 5, arm_spacing / 2))

    # Lower arm waveguide
    arm_lower = c << gf.components.straight(length=arm_length, width=WAVEGUIDE_WIDTH)
    arm_lower.dmove((coupler_length + 5, -arm_spacing / 2))

    # Route input coupler to arms
    route_single(c, cross_section=XS, port1=coupler_in.ports["o2"], port2=arm_upper.ports["o1"])
    route_single(c, cross_section=XS, port1=coupler_in.ports["o3"], port2=arm_lower.ports["o1"])

    # Output 3dB coupler (2x2 MMI for two outputs)
    coupler_out = c << gf.components.mmi2x2()
    coupler_out.dmove((coupler_length + arm_length + 15, 0))

    # Route arms to output coupler
    route_single(c, cross_section=XS, port1=arm_upper.ports["o2"], port2=coupler_out.ports["o1"])
    route_single(c, cross_section=XS, port1=arm_lower.ports["o2"], port2=coupler_out.ports["o2"])

    # RF electrode on upper arm (for electro-optic phase control)
    heater_x = coupler_length + 5 + (arm_length - heater_length) / 2
    heater_y = arm_spacing / 2 + 1.0  # Offset above waveguide
    c.add_polygon(
        [
            (heater_x, heater_y),
            (heater_x + heater_length, heater_y),
            (heater_x + heater_length, heater_y + heater_width),
            (heater_x, heater_y + heater_width)
        ],
        layer=LAYER_HEATER
    )

    # RF signal pad (large for high-speed)
    rf_pad_size = 20.0
    c.add_polygon(
        [
            (heater_x + heater_length/2 - rf_pad_size/2, heater_y + heater_width + 5),
            (heater_x + heater_length/2 + rf_pad_size/2, heater_y + heater_width + 5),
            (heater_x + heater_length/2 + rf_pad_size/2, heater_y + heater_width + 5 + rf_pad_size),
            (heater_x + heater_length/2 - rf_pad_size/2, heater_y + heater_width + 5 + rf_pad_size)
        ],
        layer=LAYER_METAL_PAD
    )

    # Ground pad
    c.add_polygon(
        [
            (heater_x - 5, -arm_spacing/2 - 5),
            (heater_x + heater_length + 5, -arm_spacing/2 - 5),
            (heater_x + heater_length + 5, -arm_spacing/2 - 5 - 10),
            (heater_x - 5, -arm_spacing/2 - 5 - 10)
        ],
        layer=LAYER_METAL_PAD
    )

    # Labels
    c.add_label("MZI_MOD", position=(coupler_length + arm_length/2, arm_spacing + 10), layer=LAYER_TEXT)
    c.add_label("RF", position=(heater_x + heater_length/2, heater_y + heater_width + rf_pad_size + 8), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="input", port=coupler_in.ports["o1"])
    c.add_port(name="bar", port=coupler_out.ports["o3"])
    c.add_port(name="cross", port=coupler_out.ports["o4"])
    c.add_port(name="output", port=coupler_out.ports["o3"])  # Alias

    # RF control port
    c.add_port(
        name="rf_in",
        center=(heater_x + heater_length/2, heater_y + heater_width + 5 + rf_pad_size/2),
        width=rf_pad_size,
        orientation=90,
        layer=LAYER_METAL_PAD
    )

    return c


@gf.cell
def ioc_wavelength_combiner(
    n_inputs: int = 3,
    input_spacing: float = 30.0
) -> Component:
    """
    Wavelength combiner using cascaded MMI combiners.

    Combines R/G/B wavelengths onto single waveguide for ALU input.

    Args:
        n_inputs: Number of wavelength inputs (3 for R/G/B)
        input_spacing: Vertical spacing between inputs (um)
    """
    c = gf.Component()

    # First stage: combine first two inputs
    mmi1 = c << gf.components.mmi2x2()
    mmi1.dmove((0, input_spacing/2))

    # Second stage: combine with third input
    mmi2 = c << gf.components.mmi2x2()
    mmi2.dmove((50, 0))

    # Route first combiner to second
    route_single(c, cross_section=XS, port1=mmi1.ports["o3"], port2=mmi2.ports["o1"])

    # Input waveguides
    wg_top = c << gf.components.straight(length=30, width=WAVEGUIDE_WIDTH)
    wg_top.dmove((-30, input_spacing))

    wg_mid = c << gf.components.straight(length=30, width=WAVEGUIDE_WIDTH)
    wg_mid.dmove((-30, 0))

    wg_bot = c << gf.components.straight(length=30, width=WAVEGUIDE_WIDTH)
    wg_bot.dmove((-30, -input_spacing))

    # Route inputs to combiners
    route_single(c, cross_section=XS, port1=wg_top.ports["o2"], port2=mmi1.ports["o1"])
    route_single(c, cross_section=XS, port1=wg_mid.ports["o2"], port2=mmi1.ports["o2"])
    route_single(c, cross_section=XS, port1=wg_bot.ports["o2"], port2=mmi2.ports["o2"])

    # Labels
    c.add_label("WL_COMB", position=(25, input_spacing + 15), layer=LAYER_TEXT)
    c.add_label("R", position=(-35, input_spacing), layer=LAYER_TEXT)
    c.add_label("G", position=(-35, 0), layer=LAYER_TEXT)
    c.add_label("B", position=(-35, -input_spacing), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="in_r", port=wg_top.ports["o1"])
    c.add_port(name="in_g", port=wg_mid.ports["o1"])
    c.add_port(name="in_b", port=wg_bot.ports["o1"])
    c.add_port(name="output", port=mmi2.ports["o3"])

    return c


@gf.cell
def ioc_encoder_unit(
    trit_id: int = 0
) -> Component:
    """
    Single trit encoder: electronic ternary -> optical wavelength.

    Contains:
    - 3 MZI modulators (one per wavelength)
    - Wavelength combiner
    - Electronic control pads (2-bit ternary encoding)

    Size: ~150 x 80 um

    Args:
        trit_id: Trit index for labeling
    """
    c = gf.Component()

    spacing = 35.0

    # Three MZI modulators for R/G/B
    mzi_r = c << ioc_mzi_modulator()
    mzi_r.dmove((0, spacing))

    mzi_g = c << ioc_mzi_modulator()
    mzi_g.dmove((0, 0))

    mzi_b = c << ioc_mzi_modulator()
    mzi_b.dmove((0, -spacing))

    # Wavelength combiner
    combiner = c << ioc_wavelength_combiner(n_inputs=3, input_spacing=spacing)
    combiner.dmove((120, 0))

    # Route MZI outputs to combiner inputs
    route_single(c, cross_section=XS, port1=mzi_r.ports["output"], port2=combiner.ports["in_r"])
    route_single(c, cross_section=XS, port1=mzi_g.ports["output"], port2=combiner.ports["in_g"])
    route_single(c, cross_section=XS, port1=mzi_b.ports["output"], port2=combiner.ports["in_b"])

    # Electronic control pads (2-bit encoding: 00=R, 01=G, 10=B)
    ctrl_pad_width = 25.0
    ctrl_pad_height = 15.0

    # Bit 0 pad
    c.add_polygon(
        [
            (50, spacing + 50),
            (50 + ctrl_pad_width, spacing + 50),
            (50 + ctrl_pad_width, spacing + 50 + ctrl_pad_height),
            (50, spacing + 50 + ctrl_pad_height)
        ],
        layer=LAYER_METAL_PAD
    )
    c.add_label("D0", position=(50 + ctrl_pad_width/2, spacing + 50 + ctrl_pad_height + 5), layer=LAYER_TEXT)

    # Bit 1 pad
    c.add_polygon(
        [
            (85, spacing + 50),
            (85 + ctrl_pad_width, spacing + 50),
            (85 + ctrl_pad_width, spacing + 50 + ctrl_pad_height),
            (85, spacing + 50 + ctrl_pad_height)
        ],
        layer=LAYER_METAL_PAD
    )
    c.add_label("D1", position=(85 + ctrl_pad_width/2, spacing + 50 + ctrl_pad_height + 5), layer=LAYER_TEXT)

    # Labels
    c.add_label(f"ENC_T{trit_id}", position=(75, spacing + 75), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="laser_r", port=mzi_r.ports["input"])
    c.add_port(name="laser_g", port=mzi_g.ports["input"])
    c.add_port(name="laser_b", port=mzi_b.ports["input"])
    c.add_port(name="output", port=combiner.ports["output"])

    # Control ports
    c.add_port(
        name="ctrl_d0",
        center=(50 + ctrl_pad_width/2, spacing + 50 + ctrl_pad_height/2),
        width=ctrl_pad_width,
        orientation=90,
        layer=LAYER_METAL_PAD
    )
    c.add_port(
        name="ctrl_d1",
        center=(85 + ctrl_pad_width/2, spacing + 50 + ctrl_pad_height/2),
        width=ctrl_pad_width,
        orientation=90,
        layer=LAYER_METAL_PAD
    )

    return c


# =============================================================================
# DECODE STAGE COMPONENTS
# =============================================================================

@gf.cell
def ioc_awg_demux(
    n_channels: int = 5,
    channel_spacing: float = 25.0,
    awg_length: float = 80.0,
    awg_width: float = 60.0
) -> Component:
    """
    Arrayed Waveguide Grating demultiplexer for 5-channel output separation.

    Separates the 5 SFG output wavelengths:
    - 500 nm (B+B = +2)
    - 549 nm (G+B = +1)
    - 608 nm (R+B/G+G = 0)
    - 681 nm (R+G = -1)
    - 775 nm (R+R = -2)

    Args:
        n_channels: Number of output channels (5 for ternary SFG outputs)
        channel_spacing: Spacing between output channels (um)
        awg_length: Length of AWG region (um)
        awg_width: Width of AWG region (um)
    """
    c = gf.Component()

    # AWG slab region (placeholder)
    awg_body = c << gf.components.rectangle(
        size=(awg_length, awg_width),
        layer=LAYER_AWG
    )

    # Input waveguide
    input_wg = c << gf.components.taper(
        length=20.0,
        width1=WAVEGUIDE_WIDTH,
        width2=5.0
    )
    input_wg.dmove((-20, awg_width/2 - 2.5))

    # Output waveguides (5 channels)
    output_y_start = (awg_width - (n_channels - 1) * channel_spacing) / 2

    for i in range(n_channels):
        y_pos = output_y_start + i * channel_spacing

        taper = c << gf.components.taper(
            length=20.0,
            width1=5.0,
            width2=WAVEGUIDE_WIDTH
        )
        taper.dmove((awg_length, y_pos - 2.5))

        # Channel wavelength label
        wavelengths = ['500', '549', '608', '681', '775']
        values = ['+2', '+1', '0', '-1', '-2']
        c.add_label(f"{wavelengths[i]}nm", position=(awg_length + 25, y_pos), layer=LAYER_TEXT)
        c.add_label(f"({values[i]})", position=(awg_length + 35, y_pos - 8), layer=LAYER_TEXT)

        # Output ports
        c.add_port(
            name=f"ch{i}",
            center=(awg_length + 20, y_pos),
            width=WAVEGUIDE_WIDTH,
            orientation=0,
            layer=LAYER_WAVEGUIDE
        )

    # Labels
    c.add_label("AWG_5CH", position=(awg_length/2, awg_width + 10), layer=LAYER_TEXT)
    c.add_label("DEMUX", position=(awg_length/2, -10), layer=LAYER_TEXT)

    # Input port
    c.add_port(
        name="input",
        center=(-20, awg_width/2 - 2.5 + WAVEGUIDE_WIDTH/2),
        width=WAVEGUIDE_WIDTH,
        orientation=180,
        layer=LAYER_WAVEGUIDE
    )

    return c


@gf.cell
def ioc_photodetector(
    detector_width: float = 30.0,
    detector_length: float = 50.0,
    channel_id: int = 0
) -> Component:
    """
    Single photodetector with TIA output pad.

    Ge-on-Si or III-V photodetector with -30 dBm sensitivity.
    Integrated with transimpedance amplifier (TIA) pad.

    Args:
        detector_width: Width of active region (um)
        detector_length: Length of active region (um)
        channel_id: Channel index for labeling
    """
    c = gf.Component()

    # Input taper
    taper_length = 15.0
    taper = c << gf.components.taper(
        length=taper_length,
        width1=WAVEGUIDE_WIDTH,
        width2=detector_width/3
    )

    # Detector active region
    detector = c << gf.components.rectangle(
        size=(detector_length, detector_width),
        layer=LAYER_DETECTOR
    )
    detector.dmove((taper_length, -detector_width/2 + detector_width/6))

    # Metal contacts
    top_contact = c << gf.components.rectangle(
        size=(detector_length * 0.8, 10),
        layer=LAYER_METAL_PAD
    )
    top_contact.dmove((taper_length + detector_length * 0.1, detector_width/2 + 5))

    bottom_contact = c << gf.components.rectangle(
        size=(detector_length * 0.8, 10),
        layer=LAYER_METAL_PAD
    )
    bottom_contact.dmove((taper_length + detector_length * 0.1, -detector_width/2 - 15))

    # TIA output pad
    tia_pad_size = 25.0
    tia_pad = c << gf.components.rectangle(
        size=(tia_pad_size, tia_pad_size),
        layer=LAYER_METAL_PAD
    )
    tia_pad.dmove((taper_length + detector_length + 10, -tia_pad_size/2))

    # Labels
    c.add_label(f"PD{channel_id}", position=(taper_length + detector_length/2, detector_width/2 + 20), layer=LAYER_TEXT)
    c.add_label("TIA", position=(taper_length + detector_length + 10 + tia_pad_size/2, tia_pad_size/2 + 5), layer=LAYER_TEXT)

    # Ports
    c.add_port(
        name="input",
        center=(0, WAVEGUIDE_WIDTH/2),
        width=WAVEGUIDE_WIDTH,
        orientation=180,
        layer=LAYER_WAVEGUIDE
    )
    c.add_port(
        name="tia_out",
        center=(taper_length + detector_length + 10 + tia_pad_size/2, 0),
        width=tia_pad_size,
        orientation=0,
        layer=LAYER_METAL_PAD
    )

    return c


@gf.cell
def ioc_result_encoder() -> Component:
    """
    5-to-3 digital encoder logic (electronic representation).

    Converts 5-channel photodetector outputs to:
    - 2-bit ternary result
    - 1-bit carry output

    This is a placeholder for electronic logic - represented as a labeled block.
    """
    c = gf.Component()

    width = 80.0
    height = 60.0

    # Logic block
    block = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_METAL_PAD
    )

    # Input pads (5 channels from photodetectors)
    for i in range(5):
        y_pos = height * (i + 1) / 6
        pad = c << gf.components.rectangle(
            size=(10, 8),
            layer=LAYER_METAL_PAD
        )
        pad.dmove((-15, y_pos - 4))
        c.add_label(f"D{i}", position=(-20, y_pos), layer=LAYER_TEXT)

    # Output pads
    # Result bits (2-bit ternary)
    for i in range(2):
        y_pos = height * (i + 2) / 4
        pad = c << gf.components.rectangle(
            size=(10, 8),
            layer=LAYER_METAL_PAD
        )
        pad.dmove((width + 5, y_pos - 4))
        c.add_label(f"R{i}", position=(width + 20, y_pos), layer=LAYER_TEXT)

    # Carry output
    carry_pad = c << gf.components.rectangle(
        size=(10, 8),
        layer=LAYER_METAL_PAD
    )
    carry_pad.dmove((width + 5, height * 3/4 - 4))
    c.add_label("Cout", position=(width + 20, height * 3/4), layer=LAYER_TEXT)

    # Labels
    c.add_label("5→3", position=(width/2, height/2 + 5), layer=LAYER_TEXT)
    c.add_label("ENCODER", position=(width/2, height/2 - 10), layer=LAYER_TEXT)

    return c


@gf.cell
def ioc_decoder_unit(
    trit_id: int = 0
) -> Component:
    """
    Complete decoder unit: optical 5-channel -> electronic ternary + carry.

    Contains:
    - 5-channel AWG demux
    - 5 photodetector array with TIAs
    - 5-to-3 encoder logic block

    Size: ~180 x 100 um

    Args:
        trit_id: Trit index for labeling
    """
    c = gf.Component()

    # AWG demultiplexer
    awg = c << ioc_awg_demux(n_channels=5, channel_spacing=20.0)
    awg.dmove((0, 0))

    # Photodetector array (5 channels)
    pd_spacing = 20.0
    pd_start_y = 10.0

    for i in range(5):
        pd = c << ioc_photodetector(channel_id=i)
        pd.dmove((120, pd_start_y + i * pd_spacing))

    # Result encoder logic
    encoder = c << ioc_result_encoder()
    encoder.dmove((220, 20))

    # Labels
    c.add_label(f"DEC_T{trit_id}", position=(150, 130), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="optical_in", port=awg.ports["input"])

    # Electronic output ports (from encoder block)
    c.add_port(
        name="result_0",
        center=(300 + 10, 20 + 60 * 2/4),
        width=10,
        orientation=0,
        layer=LAYER_METAL_PAD
    )
    c.add_port(
        name="result_1",
        center=(300 + 10, 20 + 60 * 3/4),
        width=10,
        orientation=0,
        layer=LAYER_METAL_PAD
    )
    c.add_port(
        name="carry_out",
        center=(300 + 10, 20 + 60 * 3/4),
        width=10,
        orientation=0,
        layer=LAYER_METAL_PAD
    )

    return c


# =============================================================================
# BUFFER/SYNC STAGE COMPONENTS
# =============================================================================

@gf.cell
def ioc_timing_sync(
    width: float = 100.0,
    height: float = 50.0
) -> Component:
    """
    Timing synchronization unit.

    Taps optical clock from Kerr resonator and generates electronic
    PLL-locked clock for FIFO synchronization.

    Contains:
    - Optical tap coupler
    - High-speed photodetector
    - PLL circuit placeholder (electronic)

    Size: ~100 x 50 um
    """
    c = gf.Component()

    # Optical clock tap (directional coupler)
    tap_coupler = c << gf.components.coupler(length=15.0, gap=0.3)
    tap_coupler.dmove((0, height/2))

    # Photodetector for clock extraction
    clock_pd = c << ioc_photodetector(detector_width=15, detector_length=25, channel_id=99)
    clock_pd.dmove((30, 5))

    # PLL block (electronic placeholder)
    pll_block = c << gf.components.rectangle(
        size=(40, 30),
        layer=LAYER_METAL_PAD
    )
    pll_block.dmove((55, height/2 - 15))

    # Clock output pad
    clk_out_pad = c << gf.components.rectangle(
        size=(15, 15),
        layer=LAYER_METAL_PAD
    )
    clk_out_pad.dmove((100, height/2 - 7.5))

    # Labels
    c.add_label("TIMING_SYNC", position=(50, height + 5), layer=LAYER_TEXT)
    c.add_label("PLL", position=(75, height/2), layer=LAYER_TEXT)
    c.add_label("CLK", position=(107, height/2 + 10), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="kerr_in", port=tap_coupler.ports["o1"])
    c.add_port(name="kerr_thru", port=tap_coupler.ports["o3"])
    c.add_port(
        name="clk_out",
        center=(115, height/2),
        width=15,
        orientation=0,
        layer=LAYER_METAL_PAD
    )

    return c


@gf.cell
def ioc_elastic_buffer(
    depth: int = 4,
    width: float = 80.0,
    height: float = 40.0
) -> Component:
    """
    Elastic FIFO buffer for rate matching.

    Electronic FIFO that absorbs timing variations between
    optical ALU (1.6ns) and external interface.

    Configurable depth: 1.6-6.5ns latency range.

    Args:
        depth: FIFO depth (4 = 4x word buffer)
        width: Block width (um)
        height: Block height (um)
    """
    c = gf.Component()

    # FIFO block (electronic placeholder)
    fifo_block = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_FIFO
    )

    # Data input pad
    data_in = c << gf.components.rectangle(
        size=(10, 15),
        layer=LAYER_METAL_PAD
    )
    data_in.dmove((-15, height/2 - 7.5))

    # Data output pad
    data_out = c << gf.components.rectangle(
        size=(10, 15),
        layer=LAYER_METAL_PAD
    )
    data_out.dmove((width + 5, height/2 - 7.5))

    # Clock input
    clk_in = c << gf.components.rectangle(
        size=(10, 10),
        layer=LAYER_METAL_PAD
    )
    clk_in.dmove((width/2 - 5, -15))

    # Labels
    c.add_label(f"FIFO_{depth}x", position=(width/2, height/2 + 5), layer=LAYER_TEXT)
    c.add_label("ELASTIC", position=(width/2, height/2 - 10), layer=LAYER_TEXT)
    c.add_label("DIN", position=(-20, height/2), layer=LAYER_TEXT)
    c.add_label("DOUT", position=(width + 20, height/2), layer=LAYER_TEXT)
    c.add_label("CLK", position=(width/2, -25), layer=LAYER_TEXT)

    # Ports
    c.add_port(
        name="data_in",
        center=(-15 + 5, height/2),
        width=15,
        orientation=180,
        layer=LAYER_METAL_PAD
    )
    c.add_port(
        name="data_out",
        center=(width + 5 + 5, height/2),
        width=15,
        orientation=0,
        layer=LAYER_METAL_PAD
    )
    c.add_port(
        name="clk",
        center=(width/2, -15 + 5),
        width=10,
        orientation=-90,
        layer=LAYER_METAL_PAD
    )

    return c


@gf.cell
def ioc_shift_register_81trit() -> Component:
    """
    81-trit shift register for serial-to-parallel conversion.

    Electronic shift register that accumulates serial trit data
    into 81-trit words for batch processing.

    Size: ~200 x 80 um (placeholder block)
    """
    c = gf.Component()

    width = 200.0
    height = 80.0

    # Main block
    block = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_FIFO
    )

    # Serial input
    ser_in = c << gf.components.rectangle(
        size=(10, 15),
        layer=LAYER_METAL_PAD
    )
    ser_in.dmove((-15, height/2 - 7.5))

    # Parallel outputs (represented as bus)
    par_out = c << gf.components.rectangle(
        size=(10, 50),
        layer=LAYER_METAL_PAD
    )
    par_out.dmove((width + 5, height/2 - 25))

    # Clock input
    clk_in = c << gf.components.rectangle(
        size=(10, 10),
        layer=LAYER_METAL_PAD
    )
    clk_in.dmove((width/2 - 5, -15))

    # Labels
    c.add_label("81-TRIT SHIFT REG", position=(width/2, height/2 + 10), layer=LAYER_TEXT)
    c.add_label("162-bit parallel", position=(width/2, height/2 - 15), layer=LAYER_TEXT)
    c.add_label("SER", position=(-20, height/2), layer=LAYER_TEXT)
    c.add_label("PAR[161:0]", position=(width + 30, height/2), layer=LAYER_TEXT)

    # Ports
    c.add_port(
        name="serial_in",
        center=(-10, height/2),
        width=15,
        orientation=180,
        layer=LAYER_METAL_PAD
    )
    c.add_port(
        name="parallel_out",
        center=(width + 10, height/2),
        width=50,
        orientation=0,
        layer=LAYER_METAL_PAD
    )
    c.add_port(
        name="clk",
        center=(width/2, -10),
        width=10,
        orientation=-90,
        layer=LAYER_METAL_PAD
    )

    return c


# =============================================================================
# RAM TIER ADAPTERS
# =============================================================================

@gf.cell
def tier1_adapter() -> Component:
    """
    Tier 1 (Hot Register) adapter - optical-only interface.

    Direct optical passthrough with MZI register select.
    Minimal latency for accumulator operations.

    Size: ~60 x 40 um
    """
    c = gf.Component()

    # MZI switch for register select
    mzi = c << ioc_mzi_modulator(arm_length=30, arm_spacing=8)
    mzi.dmove((0, 0))

    # Labels
    c.add_label("TIER1_ADAPT", position=(40, 30), layer=LAYER_TEXT)
    c.add_label("HOT REG", position=(40, -15), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="write_in", port=mzi.ports["input"])
    c.add_port(name="read_a", port=mzi.ports["bar"])
    c.add_port(name="read_b", port=mzi.ports["cross"])
    c.add_port(name="reg_select", port=mzi.ports["rf_in"])

    return c


@gf.cell
def tier2_adapter() -> Component:
    """
    Tier 2 (Working Register) adapter - optical + SOA gate timing.

    Adds SOA gate control for pulsed refresh timing.

    Size: ~100 x 60 um
    """
    c = gf.Component()

    # MZI switch for register select
    mzi = c << ioc_mzi_modulator(arm_length=35, arm_spacing=8)
    mzi.dmove((0, 0))

    # SOA gate control pad
    soa_gate_pad = c << gf.components.rectangle(
        size=(20, 15),
        layer=LAYER_METAL_PAD
    )
    soa_gate_pad.dmove((80, -25))

    # Timing pad
    timing_pad = c << gf.components.rectangle(
        size=(15, 15),
        layer=LAYER_METAL_PAD
    )
    timing_pad.dmove((105, -25))

    # Labels
    c.add_label("TIER2_ADAPT", position=(50, 35), layer=LAYER_TEXT)
    c.add_label("WORKING REG", position=(50, -40), layer=LAYER_TEXT)
    c.add_label("SOA", position=(90, -45), layer=LAYER_TEXT)
    c.add_label("TMG", position=(112, -45), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="write_in", port=mzi.ports["input"])
    c.add_port(name="read_a", port=mzi.ports["bar"])
    c.add_port(name="read_b", port=mzi.ports["cross"])
    c.add_port(name="reg_select", port=mzi.ports["rf_in"])
    c.add_port(
        name="soa_gate",
        center=(90, -17.5),
        width=20,
        orientation=-90,
        layer=LAYER_METAL_PAD
    )
    c.add_port(
        name="timing",
        center=(112.5, -17.5),
        width=15,
        orientation=-90,
        layer=LAYER_METAL_PAD
    )

    return c


@gf.cell
def tier3_adapter() -> Component:
    """
    Tier 3 (Parking Register) adapter - electrical address + optical data.

    5-bit address decoder for 32 registers + optical data interface.

    Size: ~120 x 80 um
    """
    c = gf.Component()

    # MZI switch for data path
    mzi = c << ioc_mzi_modulator(arm_length=35, arm_spacing=8)
    mzi.dmove((0, 20))

    # Address decoder block (electronic)
    addr_decoder = c << gf.components.rectangle(
        size=(50, 40),
        layer=LAYER_METAL_PAD
    )
    addr_decoder.dmove((0, -50))

    # Address input pads (5-bit)
    for i in range(5):
        addr_pad = c << gf.components.rectangle(
            size=(8, 8),
            layer=LAYER_METAL_PAD
        )
        addr_pad.dmove((-15, -45 + i * 8))
        c.add_label(f"A{i}", position=(-25, -41 + i * 8), layer=LAYER_TEXT)

    # Read/Write control
    rw_pad = c << gf.components.rectangle(
        size=(15, 10),
        layer=LAYER_METAL_PAD
    )
    rw_pad.dmove((55, -45))

    # Labels
    c.add_label("TIER3_ADAPT", position=(50, 55), layer=LAYER_TEXT)
    c.add_label("PARKING REG", position=(50, -70), layer=LAYER_TEXT)
    c.add_label("ADDR[4:0]", position=(25, -30), layer=LAYER_TEXT)
    c.add_label("R/W", position=(62, -35), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="data_in", port=mzi.ports["input"])
    c.add_port(name="data_out", port=mzi.ports["bar"])
    c.add_port(name="data_select", port=mzi.ports["rf_in"])

    # Address bus port
    c.add_port(
        name="addr",
        center=(-11, -30),
        width=40,
        orientation=180,
        layer=LAYER_METAL_PAD
    )
    c.add_port(
        name="rw_ctrl",
        center=(62.5, -40),
        width=15,
        orientation=0,
        layer=LAYER_METAL_PAD
    )

    return c


# =============================================================================
# COMPLETE IOC MODULE
# =============================================================================

@gf.cell
def ioc_module_complete(
    n_trits: int = 1,
    include_laser_sources: bool = True,
    include_ioa_bus: bool = True
) -> Component:
    """
    Complete IOC module assembly.

    Integrates all IOC stages:
    - Encode stage (laser sources + MZI modulators + combiner)
    - Decode stage (AWG demux + photodetectors + encoder)
    - Buffer/Sync stage (timing sync + elastic FIFO + shift register)
    - RAM tier adapters (Tier 1/2/3)
    - IOA bus interface (optional, for external adapters)

    Size: ~800 x 400 um

    Args:
        n_trits: Number of trit channels (1 for single, 81 for full)
        include_laser_sources: Whether to include laser source blocks
        include_ioa_bus: Whether to include IOA bus interface
    """
    c = gf.Component()

    y_offset = 0

    # === TITLE ===
    c.add_label("IOC MODULE", position=(400, 380), layer=LAYER_TEXT)
    c.add_label("Input/Output Converter", position=(400, 360), layer=LAYER_TEXT)

    # === ENCODE STAGE ===
    c.add_label("ENCODE STAGE", position=(100, 340), layer=LAYER_TEXT)

    if include_laser_sources:
        # Laser sources (R/G/B)
        laser_r = c << ioc_laser_source(wavelength_um=WAVELENGTH_RED, label="R")
        laser_r.dmove((0, 250))

        laser_g = c << ioc_laser_source(wavelength_um=WAVELENGTH_GREEN, label="G")
        laser_g.dmove((0, 140))

        laser_b = c << ioc_laser_source(wavelength_um=WAVELENGTH_BLUE, label="B")
        laser_b.dmove((0, 30))

    # Encoder unit
    encoder = c << ioc_encoder_unit(trit_id=0)
    encoder.dmove((250, 100))

    # Route lasers to encoder if present (visual waveguide connections)
    if include_laser_sources:
        # Draw simple waveguide paths from lasers to encoder
        # Red laser to encoder
        wg_r = c << gf.components.straight(length=20, width=WAVEGUIDE_WIDTH)
        wg_r.dmove((230, 295))
        c.add_label("R->ENC", position=(240, 300), layer=LAYER_TEXT)

        # Green laser to encoder
        wg_g = c << gf.components.straight(length=20, width=WAVEGUIDE_WIDTH)
        wg_g.dmove((230, 185))
        c.add_label("G->ENC", position=(240, 190), layer=LAYER_TEXT)

        # Blue laser to encoder
        wg_b = c << gf.components.straight(length=20, width=WAVEGUIDE_WIDTH)
        wg_b.dmove((230, 75))
        c.add_label("B->ENC", position=(240, 80), layer=LAYER_TEXT)

    # === DECODE STAGE ===
    c.add_label("DECODE STAGE", position=(550, 340), layer=LAYER_TEXT)

    decoder = c << ioc_decoder_unit(trit_id=0)
    decoder.dmove((480, 180))

    # === BUFFER/SYNC STAGE ===
    c.add_label("BUFFER/SYNC", position=(100, -30), layer=LAYER_TEXT)

    timing = c << ioc_timing_sync()
    timing.dmove((0, -100))

    fifo = c << ioc_elastic_buffer(depth=4)
    fifo.dmove((130, -100))

    shift_reg = c << ioc_shift_register_81trit()
    shift_reg.dmove((250, -110))

    # Connect timing to FIFO clock (electrical - shown as label connection)
    c.add_label("CLK_ROUTE", position=(115, -75), layer=LAYER_TEXT)

    # === RAM TIER ADAPTERS ===
    c.add_label("RAM ADAPTERS", position=(550, -30), layer=LAYER_TEXT)

    tier1 = c << tier1_adapter()
    tier1.dmove((500, -80))

    tier2 = c << tier2_adapter()
    tier2.dmove((620, -80))

    tier3 = c << tier3_adapter()
    tier3.dmove((500, -180))

    # === MAIN PORTS ===
    # Laser output to ALU
    c.add_port(name="laser_out", port=encoder.ports["output"])

    # Detector input from ALU
    c.add_port(name="detect_in", port=decoder.ports["optical_in"])

    # Electronic control ports
    c.add_port(name="ctrl_trit_a", port=encoder.ports["ctrl_d0"])
    c.add_port(name="ctrl_trit_b", port=encoder.ports["ctrl_d1"])
    c.add_port(name="result_out", port=decoder.ports["result_0"])
    c.add_port(name="carry_out", port=decoder.ports["carry_out"])

    # Timing ports
    c.add_port(name="kerr_clock_in", port=timing.ports["kerr_in"])
    c.add_port(name="kerr_clock_thru", port=timing.ports["kerr_thru"])

    # RAM tier ports
    c.add_port(name="tier1_bus", port=tier1.ports["write_in"])
    c.add_port(name="tier2_bus", port=tier2.ports["write_in"])
    c.add_port(name="tier3_addr", port=tier3.ports["addr"])
    c.add_port(name="tier3_data", port=tier3.ports["data_in"])

    # === IOA BUS INTERFACE (External Adapter Connection) ===
    if include_ioa_bus and IOA_AVAILABLE:
        c.add_label("IOA BUS", position=(750, -30), layer=LAYER_TEXT)
        ioa_bus = c << ioa_bus_interface()
        ioa_bus.dmove((700, -150))
        c.add_port(name="ioa_bus", port=ioa_bus.ports["to_ioc"])
        c.add_label("TO IOA ADAPTERS", position=(820, -180), layer=LAYER_TEXT)
    elif include_ioa_bus:
        # Add placeholder if ioa_module not available
        c.add_label("IOA BUS (placeholder)", position=(750, -100), layer=LAYER_TEXT)
        ioa_placeholder = c << gf.components.rectangle(size=(150, 60), layer=LAYER_METAL_PAD)
        ioa_placeholder.dmove((700, -150))
        c.add_port(
            name="ioa_bus",
            center=(775, -120),
            width=150,
            orientation=-90,
            layer=LAYER_METAL_PAD
        )

    # Add bounding box label
    c.add_label("~900 x 400 um", position=(400, -220), layer=LAYER_TEXT)

    return c


# =============================================================================
# CONVENIENCE GENERATORS
# =============================================================================

def generate_ioc_module(
    output_path: Optional[str] = None,
    include_lasers: bool = True
) -> Component:
    """
    Generate and optionally save the complete IOC module.

    Args:
        output_path: Path to save GDS file (optional)
        include_lasers: Whether to include laser source blocks

    Returns:
        Generated Component
    """
    chip = ioc_module_complete(n_trits=1, include_laser_sources=include_lasers)

    if output_path:
        chip.write(output_path)
        print(f"IOC module saved to: {output_path}")

    return chip


def generate_encoder_only(output_path: Optional[str] = None) -> Component:
    """Generate just the encode stage."""
    chip = ioc_encoder_unit(trit_id=0)
    if output_path:
        chip.write(output_path)
    return chip


def generate_decoder_only(output_path: Optional[str] = None) -> Component:
    """Generate just the decode stage."""
    chip = ioc_decoder_unit(trit_id=0)
    if output_path:
        chip.write(output_path)
    return chip


# =============================================================================
# INTERACTIVE CLI
# =============================================================================

def interactive_ioc_generator():
    """Interactive CLI for generating IOC components."""
    print("\n" + "="*60)
    print("  IOC MODULE GENERATOR")
    print("  Input/Output Converter for Ternary Optical Computer")
    print("="*60)

    print("\nAvailable components:")
    print("  1. Complete IOC Module (with laser sources)")
    print("  2. Complete IOC Module (without laser sources)")
    print("  3. Encoder Unit only")
    print("  4. Decoder Unit only")
    print("  5. Timing Sync Unit")
    print("  6. Elastic Buffer")
    print("  7. 81-Trit Shift Register")
    print("  8. Tier 1 Adapter (Hot Register)")
    print("  9. Tier 2 Adapter (Working Register)")
    print(" 10. Tier 3 Adapter (Parking Register)")
    print(" 11. All RAM Adapters")

    choice = input("\nSelect component (1-11): ").strip()

    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data', 'gds')
    os.makedirs(data_dir, exist_ok=True)

    if choice == "1":
        chip = ioc_module_complete(include_laser_sources=True)
        chip_name = "ioc_module_complete"
    elif choice == "2":
        chip = ioc_module_complete(include_laser_sources=False)
        chip_name = "ioc_module_no_lasers"
    elif choice == "3":
        chip = ioc_encoder_unit(trit_id=0)
        chip_name = "ioc_encoder"
    elif choice == "4":
        chip = ioc_decoder_unit(trit_id=0)
        chip_name = "ioc_decoder"
    elif choice == "5":
        chip = ioc_timing_sync()
        chip_name = "ioc_timing_sync"
    elif choice == "6":
        chip = ioc_elastic_buffer(depth=4)
        chip_name = "ioc_elastic_buffer"
    elif choice == "7":
        chip = ioc_shift_register_81trit()
        chip_name = "ioc_shift_register"
    elif choice == "8":
        chip = tier1_adapter()
        chip_name = "tier1_adapter"
    elif choice == "9":
        chip = tier2_adapter()
        chip_name = "tier2_adapter"
    elif choice == "10":
        chip = tier3_adapter()
        chip_name = "tier3_adapter"
    elif choice == "11":
        # Create combined adapter component
        c = gf.Component("all_ram_adapters")
        t1 = c << tier1_adapter()
        t1.dmove((0, 0))
        t2 = c << tier2_adapter()
        t2.dmove((150, 0))
        t3 = c << tier3_adapter()
        t3.dmove((300, 0))
        c.add_label("ALL RAM TIER ADAPTERS", position=(200, 80), layer=LAYER_TEXT)
        chip = c
        chip_name = "all_ram_adapters"
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
    interactive_ioc_generator()
