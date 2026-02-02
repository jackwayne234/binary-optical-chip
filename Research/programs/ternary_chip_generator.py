# Copyright (c) 2026 Christopher Riner
# Licensed under the MIT License. See LICENSE file for details.
#
# Wavelength-Division Ternary Optical Computer
# High-Level Chip Generator
#
# Automatically generates photonic chip layouts from high-level specifications.
# Specify the logic operation you want, and this generates the full chip.

import gdsfactory as gf
from gdsfactory.routing import route_single
import numpy as np
from typing import List, Dict, Optional, Literal

# Activate the generic PDK
gf.gpdk.PDK.activate()

# Default cross-section for routing
XS = gf.cross_section.strip(width=0.5)

# Dedicated layer for labels (toggle visibility in KLayout)
LABEL_LAYER = (100, 0)

# Layer for MZI heaters/electrodes
HEATER_LAYER = (10, 0)

# =============================================================================
# TERNARY ENCODING: Wavelength -> Value
# =============================================================================
# Input wavelengths chosen so that R+B and G+G produce same SFG output (both = 0)
# Green = harmonic mean of Red and Blue: λ_G = 2*λ_R*λ_B/(λ_R+λ_B) = 1.216 μm
TERNARY_ENCODING = {
    'NEG':   {'value': -1, 'wavelength_um': 1.550, 'color': 'red',   'name': 'Red'},
    'ZERO':  {'value':  0, 'wavelength_um': 1.216, 'color': 'green', 'name': 'Green'},
    'POS':   {'value': +1, 'wavelength_um': 1.000, 'color': 'blue',  'name': 'Blue'},
}

# SFG Output wavelengths (verified by simulation)
# These are what the detectors need to sense
OUTPUT_ENCODING = {
    'NEG2':  {'value': -2, 'wavelength_um': 0.775, 'name': 'Overflow-'},  # R+R
    'NEG':   {'value': -1, 'wavelength_um': 0.681, 'name': 'Result-1'},   # R+G
    'ZERO':  {'value':  0, 'wavelength_um': 0.608, 'name': 'Result0'},    # R+B or G+G
    'POS':   {'value': +1, 'wavelength_um': 0.549, 'name': 'Result+1'},   # G+B
    'POS2':  {'value': +2, 'wavelength_um': 0.500, 'name': 'Overflow+'},  # B+B
}

# Material parameters (from your simulations)
MATERIALS = {
    'LiNbO3': {'n_core': 2.2, 'n_clad': 1.0, 'chi2': 0.5},
    'SU8':    {'n_core': 1.57, 'n_clad': 1.0, 'chi2': 0.0},
    'Polymer': {'n_core': 1.50, 'n_clad': 1.0, 'chi2': 0.3},
}

# =============================================================================
# COMPONENT LIBRARY: Ternary Photonic Building Blocks
# =============================================================================

def mzi_switch(
    arm_length: float = 50.0,
    arm_spacing: float = 10.0,
    coupler_length: float = 10.0,
    heater_length: float = 30.0,
    heater_width: float = 2.0,
    name: str = "mzi_switch"
) -> gf.Component:
    """
    Creates a Mach-Zehnder Interferometer (MZI) switch.

    MZI advantages over ring resonators:
    - Better extinction ratio (>30dB vs ~20dB)
    - More tolerant to fabrication variations
    - Broader wavelength bandwidth
    - Simpler tuning (voltage-based phase control)

    Structure:
        Input → 3dB Coupler → Upper Arm (with heater) → 3dB Coupler → Bar Output
                           → Lower Arm              →             → Cross Output

    The control voltage on the heater creates a phase shift via thermo-optic
    effect, switching light between the bar and cross outputs.

    Args:
        arm_length: Length of each MZI arm (um)
        arm_spacing: Vertical spacing between arms (um)
        coupler_length: Length of 3dB MMI couplers (um)
        heater_length: Length of heater/electrode region (um)
        heater_width: Width of heater strip (um)
        name: Component name
    """
    c = gf.Component(name)

    # Input 3dB coupler (MMI-based)
    coupler_in = c << gf.components.mmi1x2()
    coupler_in.dmove((0, 0))

    # Upper arm waveguide
    arm_upper = c << gf.components.straight(length=arm_length, width=0.5)
    arm_upper.dmove((coupler_length + 5, arm_spacing / 2))

    # Lower arm waveguide
    arm_lower = c << gf.components.straight(length=arm_length, width=0.5)
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

    # Heater/electrode on upper arm (for thermo-optic phase control)
    heater_x = coupler_length + 5 + (arm_length - heater_length) / 2
    heater_y = arm_spacing / 2 + 1.0  # Offset above waveguide
    c.add_polygon(
        [
            (heater_x, heater_y),
            (heater_x + heater_length, heater_y),
            (heater_x + heater_length, heater_y + heater_width),
            (heater_x, heater_y + heater_width)
        ],
        layer=HEATER_LAYER
    )

    # Contact pads for heater
    pad_size = 5.0
    # Left pad
    c.add_polygon(
        [
            (heater_x - pad_size, heater_y),
            (heater_x, heater_y),
            (heater_x, heater_y + heater_width + pad_size),
            (heater_x - pad_size, heater_y + heater_width + pad_size)
        ],
        layer=HEATER_LAYER
    )
    # Right pad
    c.add_polygon(
        [
            (heater_x + heater_length, heater_y),
            (heater_x + heater_length + pad_size, heater_y),
            (heater_x + heater_length + pad_size, heater_y + heater_width + pad_size),
            (heater_x + heater_length, heater_y + heater_width + pad_size)
        ],
        layer=HEATER_LAYER
    )

    # Labels
    c.add_label("MZI", position=(coupler_length + arm_length / 2, arm_spacing + 5), layer=LABEL_LAYER)
    c.add_label("HTR", position=(heater_x + heater_length / 2, heater_y + heater_width + 2), layer=LABEL_LAYER)

    # Ports
    c.add_port(name="input", port=coupler_in.ports["o1"])
    c.add_port(name="bar", port=coupler_out.ports["o3"])    # Straight-through when heater OFF
    c.add_port(name="cross", port=coupler_out.ports["o4"])  # Cross output when heater ON
    # Alias for compatibility
    c.add_port(name="output", port=coupler_out.ports["o3"])

    return c


def wavelength_selector_mzi(
    wavelength_um: float,
    arm_length: float = 50.0,
    arm_spacing: float = 10.0,
    name: str = "selector_mzi"
) -> gf.Component:
    """
    Creates an MZI-based wavelength selector (gating switch).

    Unlike ring resonators which filter by wavelength, MZI switches gate
    light on/off. For wavelength selection, use with an upstream AWG demux
    that separates wavelengths, then MZI switches gate each channel.

    MZI advantages over ring resonators:
    - Better extinction ratio (>30dB vs ~20dB for rings)
    - More tolerant to fabrication variations (no critical gap)
    - Broader wavelength bandwidth (works across entire channel)
    - Simpler tuning (just voltage, no resonance tracking)

    Args:
        wavelength_um: Target wavelength (for labeling/documentation)
        arm_length: MZI arm length (um)
        arm_spacing: Spacing between MZI arms (um)
        name: Component name

    Note: The wavelength_um parameter is primarily for labeling. The MZI
    itself is broadband and will switch any wavelength. Wavelength
    selectivity comes from the upstream AWG demux.
    """
    c = gf.Component(name)

    # MZI switch core
    mzi = c << mzi_switch(
        arm_length=arm_length,
        arm_spacing=arm_spacing,
        name=f"mzi_core_{name}"
    )

    # Add wavelength label for documentation
    wl_nm = int(wavelength_um * 1000)
    c.add_label(f"MZI_{wl_nm}", position=(0, arm_spacing + 10), layer=LABEL_LAYER)

    # Expose ports
    c.add_port(name="input", port=mzi.ports["input"])
    c.add_port(name="output", port=mzi.ports["output"])
    c.add_port(name="bar", port=mzi.ports["bar"])
    c.add_port(name="cross", port=mzi.ports["cross"])

    return c


def wavelength_selector(
    wavelength_um: float,
    radius: float = 5.0,
    gap: float = 0.15,
    name: str = "selector"
) -> gf.Component:
    """
    Creates a ring resonator wavelength selector.

    This selects a specific wavelength from a multi-wavelength input.
    When voltage is applied, it shifts the resonance (ON/OFF control).

    Args:
        wavelength_um: Target wavelength to select
        radius: Ring radius (larger = sharper filter)
                Note: Simulation optimal is 0.8um for LiNbO3, but generic PDK
                requires min 5.0um. Use foundry PDK for actual values.
        gap: Coupling gap (simulation: 0.15um)
        name: Component name
    """
    c = gf.Component(name)

    # Ring resonator - the core selector element
    ring = c << gf.components.ring_single(radius=radius, gap=gap)

    # Add labels for clarity
    wl_nm = int(wavelength_um * 1000)
    c.add_label(f"SEL_{wl_nm}", position=(0, radius + 2), layer=LABEL_LAYER)

    # Expose ports
    c.add_port(name="input", port=ring.ports["o1"])
    c.add_port(name="output", port=ring.ports["o2"])

    return c


def wavelength_inverter(
    name: str = "inverter"
) -> gf.Component:
    """
    Creates a wavelength inverter for ternary negation.

    Swaps Red (1.55μm, -1) ↔ Blue (1.00μm, +1), Green (0) unchanged.
    This enables subtraction: A - B = A + (-B)

    Implementation: Uses wavelength-selective crossings
    - Red and Blue paths cross over
    - Green path passes straight through
    """
    c = gf.Component(name)

    # Three parallel paths with crossover for Red and Blue
    # Red input (top) -> Blue output (bottom)
    # Green input (middle) -> Green output (middle)
    # Blue input (bottom) -> Red output (top)

    spacing = 5
    length = 30

    # Input waveguides
    wg_top = c << gf.components.straight(length=10, width=0.5)
    wg_top.dmove((0, spacing))

    wg_mid = c << gf.components.straight(length=length, width=0.5)
    wg_mid.dmove((0, 0))

    wg_bot = c << gf.components.straight(length=10, width=0.5)
    wg_bot.dmove((0, -spacing))

    # Crossing region (Red↔Blue swap)
    cross = c << gf.components.crossing()
    cross.dmove((15, 0))
    cross.drotate(45)

    # Output waveguides
    wg_top_out = c << gf.components.straight(length=10, width=0.5)
    wg_top_out.dmove((length - 10, spacing))

    wg_bot_out = c << gf.components.straight(length=10, width=0.5)
    wg_bot_out.dmove((length - 10, -spacing))

    c.add_label("INV", position=(15, spacing + 3), layer=LABEL_LAYER)

    # Ports
    c.add_port(name="input", port=wg_mid.ports["o1"])
    c.add_port(name="output", port=wg_mid.ports["o2"])

    return c


def dfg_divider(
    length: float = 40.0,
    width: float = 0.8,
    name: str = "dfg_divider"
) -> gf.Component:
    """
    Creates a Difference-Frequency Generation divider.

    Uses DFG (χ² nonlinearity) for frequency subtraction.
    Division in ternary is implemented as repeated DFG operations.

    Note: True division requires multiple stages with feedback.
    This is a single-stage approximation.
    """
    c = gf.Component(name)

    # Longer waveguide for DFG (needs more interaction length)
    wg = c << gf.components.straight(length=length, width=width)

    # Visual marker for DFG region
    c.add_polygon(
        [(0, -width), (length, -width), (length, -width-0.5), (0, -width-0.5)],
        layer=(4, 0)  # Different layer for DFG marker
    )
    c.add_label("DFG", position=(length/2, -width - 1), layer=LABEL_LAYER)

    c.add_port(name="input", port=wg.ports["o1"])
    c.add_port(name="output", port=wg.ports["o2"])

    return c


def sfg_mixer(
    length: float = 20.0,
    width: float = 0.8,
    name: str = "sfg_mixer"
) -> gf.Component:
    """
    Creates a Sum-Frequency Generation mixer for ADDITION.

    Mixes two wavelengths via χ² nonlinearity to produce sum frequency.
    Output wavelength: λ_out = 1/(1/λ1 + 1/λ2)
    This effectively computes A + B in ternary.

    Args:
        length: Mixer waveguide length (longer = more mixing)
        width: Waveguide width
        name: Component name
    """
    c = gf.Component(name)

    # Straight waveguide with nonlinear material
    wg = c << gf.components.straight(length=length, width=width)

    # Add a visual marker for the nonlinear region
    c.add_polygon(
        [(0, -width), (length, -width), (length, -width-0.5), (0, -width-0.5)],
        layer=(2, 0)  # Different layer for χ² region marker
    )
    c.add_label("SFG", position=(length/2, -width - 1), layer=LABEL_LAYER)

    c.add_port(name="input", port=wg.ports["o1"])
    c.add_port(name="output", port=wg.ports["o2"])

    return c


def dfg_mixer(
    length: float = 25.0,
    width: float = 0.8,
    name: str = "dfg_mixer"
) -> gf.Component:
    """
    Creates a Difference-Frequency Generation mixer for SUBTRACTION.

    Uses DFG (χ² nonlinearity) for frequency subtraction.
    Output wavelength: λ_out = 1/(1/λ1 - 1/λ2)
    This effectively computes A - B in ternary.

    The DFG process requires slightly longer interaction length than SFG
    for efficient conversion.

    Args:
        length: Mixer waveguide length (longer = more mixing)
        width: Waveguide width
        name: Component name
    """
    c = gf.Component(name)

    # Longer waveguide for DFG (needs more interaction length)
    wg = c << gf.components.straight(length=length, width=width)

    # Visual marker for DFG region (layer 4)
    c.add_polygon(
        [(0, -width), (length, -width), (length, -width-0.5), (0, -width-0.5)],
        layer=(4, 0)  # Different layer for DFG marker
    )
    c.add_label("DFG", position=(length/2, -width - 1), layer=LABEL_LAYER)

    c.add_port(name="input", port=wg.ports["o1"])
    c.add_port(name="output", port=wg.ports["o2"])

    return c


def mul_mixer(
    length: float = 30.0,
    width: float = 0.8,
    name: str = "mul_mixer"
) -> gf.Component:
    """
    Creates a multiplication mixer using Kerr effect (χ³ nonlinearity).

    Implements balanced ternary multiplication:
      (-1) × (-1) = +1
      (-1) × ( 0) =  0
      (-1) × (+1) = -1
      ( 0) × (-1) =  0
      ( 0) × ( 0) =  0
      ( 0) × (+1) =  0
      (+1) × (-1) = -1
      (+1) × ( 0) =  0
      (+1) × (+1) = +1

    The Kerr effect (third-order nonlinearity) enables intensity-dependent
    phase modulation. Combined with wavelength encoding:
      - Same sign inputs (R+R or B+B) -> cross-phase modulation -> same sign output
      - Opposite sign inputs (R+B) -> destructive interference -> opposite sign output
      - Zero input (G) -> no phase shift -> zero output

    Requires longer interaction length for χ³ compared to χ² processes.

    Args:
        length: Mixer waveguide length (χ³ needs longer length)
        width: Waveguide width
        name: Component name
    """
    c = gf.Component(name)

    # Longer waveguide for Kerr effect (χ³ needs more interaction)
    wg = c << gf.components.straight(length=length, width=width)

    # Visual marker for Kerr/χ³ region (layer 7)
    c.add_polygon(
        [(0, -width), (length, -width), (length, -width-0.5), (0, -width-0.5)],
        layer=(7, 0)  # Different layer for χ³ region marker
    )
    c.add_label("MUL", position=(length/2, -width - 1), layer=LABEL_LAYER)

    c.add_port(name="input", port=wg.ports["o1"])
    c.add_port(name="output", port=wg.ports["o2"])

    return c


# =============================================================================
# OPTICAL CARRY CHAIN COMPONENTS
# =============================================================================
# These components enable fully optical carry propagation between trits,
# eliminating the need for electronic carry logic.

# GDS layer for optical carry components
CARRY_LAYER = (11, 0)

def optical_delay_line(
    delay_ps: float = 10.0,
    name: str = "delay_line"
) -> gf.Component:
    """
    Creates an optical delay line for carry timing synchronization.

    The delay allows the current trit's computation to complete before
    the carry from the previous trit arrives.

    Args:
        delay_ps: Desired delay in picoseconds
        name: Component name

    Delay calculation:
        Length = delay_ps × c / n_eff
        For LiNbO3 (n_eff ≈ 2.2): 10 ps ≈ 1.36 mm
    """
    c = gf.Component(name)

    # Calculate length: L = t × c / n
    # c = 3e8 m/s = 3e5 μm/ps, n_eff ≈ 2.2
    n_eff = 2.2
    length_um = delay_ps * 300 / n_eff  # μm

    # Use spiral or serpentine to fit long delay in compact area
    # For simplicity, use a serpentine with multiple bends
    n_segments = max(1, int(length_um / 200))  # 200 μm per segment
    segment_length = length_um / n_segments
    spacing = 15  # μm between segments

    if n_segments == 1:
        wg = c << gf.components.straight(length=segment_length)
        c.add_port(name="input", port=wg.ports["o1"])
        c.add_port(name="output", port=wg.ports["o2"])
    else:
        # Create serpentine path
        current_y = 0
        prev_port = None

        for i in range(n_segments):
            seg = c << gf.components.straight(length=segment_length)
            if i % 2 == 0:
                seg.dmove((0, current_y))
            else:
                seg.dmove((0, current_y))
                seg.dmirror()

            if prev_port is not None:
                # Add bend to connect segments
                bend = c << gf.components.bend_euler(radius=5, angle=180)
                bend.dmove((segment_length if i % 2 == 1 else 0, current_y - spacing/2))
                route_single(c, cross_section=XS, port1=prev_port, port2=bend.ports["o1"])
                route_single(c, cross_section=XS, port1=bend.ports["o2"], port2=seg.ports["o1"])

            if i == 0:
                c.add_port(name="input", port=seg.ports["o1"])
            if i == n_segments - 1:
                c.add_port(name="output", port=seg.ports["o2"])

            prev_port = seg.ports["o2"]
            current_y -= spacing

    # Visual marker
    c.add_polygon(
        [(-5, 5), (segment_length + 5, 5), (segment_length + 5, current_y - 5), (-5, current_y - 5)],
        layer=CARRY_LAYER
    )
    c.add_label(f"DLY_{delay_ps:.0f}ps", position=(segment_length/2, 10), layer=LABEL_LAYER)

    return c


def carry_tap(
    name: str = "carry_tap"
) -> gf.Component:
    """
    Extracts carry wavelengths from mixer output.

    Uses add-drop ring resonators to tap:
      - 0.500 μm (carry +1, from B+B = +2)
      - 0.775 μm (borrow -1, from R+R = -2)

    Main signal continues to output stage for detection.
    Carry signals route to wavelength converter.

    Structure:
        Input ──→ Ring_pos (0.500 μm) ──→ Ring_neg (0.775 μm) ──→ thru
                      │ drop                  │ drop
                      ↓                       ↓
                  carry_pos               carry_neg
    """
    c = gf.Component(name)

    # Add-drop ring for carry +1 (0.500 μm)
    # Using ring_double which has add-drop configuration
    ring_pos = c << gf.components.ring_double(radius=5.0, gap=0.15)
    ring_pos.dmove((0, 0))

    # Add-drop ring for borrow -1 (0.775 μm) - cascaded after first ring
    ring_neg = c << gf.components.ring_double(radius=5.0, gap=0.15)
    ring_neg.dmove((40, 0))

    # Route thru port of first ring to input of second
    route_single(c, cross_section=XS, port1=ring_pos.ports["o2"], port2=ring_neg.ports["o1"])

    # Labels
    c.add_label("TAP_500nm", position=(0, 15), layer=LABEL_LAYER)
    c.add_label("TAP_775nm", position=(40, 15), layer=LABEL_LAYER)

    # Ports
    c.add_port(name="input", port=ring_pos.ports["o1"])      # Main input
    c.add_port(name="thru", port=ring_neg.ports["o2"])       # Main signal continues
    c.add_port(name="carry_pos", port=ring_pos.ports["o4"])  # +1 carry (drop port)
    c.add_port(name="carry_neg", port=ring_neg.ports["o4"])  # -1 borrow (drop port)

    c.add_label("CARRY_TAP", position=(20, 25), layer=LABEL_LAYER)

    return c


def wavelength_converter_opa(
    input_wavelength_um: float = 0.500,
    output_wavelength_um: float = 1.000,
    length: float = 30.0,
    name: str = "opa_converter"
) -> gf.Component:
    """
    Converts carry wavelength to input wavelength using Optical Parametric Amplification.

    OPA uses a pump laser to convert signal wavelength:
        ω_signal + ω_pump → ω_idler (conservation of energy)

    For carry conversion:
        0.500 μm (carry +1) + pump → 1.000 μm (Blue = +1)
        0.775 μm (borrow -1) + pump → 1.550 μm (Red = -1)

    The pump wavelength is calculated from:
        1/λ_pump = 1/λ_signal - 1/λ_output

    Args:
        input_wavelength_um: Carry signal wavelength
        output_wavelength_um: Desired output wavelength (input encoding)
        length: Interaction length
        name: Component name
    """
    c = gf.Component(name)

    # Calculate pump wavelength
    pump_wavelength = 1 / (1/input_wavelength_um - 1/output_wavelength_um)

    # OPA crystal/waveguide
    wg = c << gf.components.straight(length=length, width=0.8)

    # Pump input coupler (from side)
    pump_coupler = c << gf.components.mmi1x2()
    pump_coupler.dmove((length/2, -15))
    pump_coupler.drotate(90)

    # Visual marker for OPA region
    c.add_polygon(
        [(0, -2), (length, -2), (length, 2), (0, 2)],
        layer=CARRY_LAYER
    )
    c.add_label(f"OPA", position=(length/2, 5), layer=LABEL_LAYER)
    c.add_label(f"{input_wavelength_um:.3f}→{output_wavelength_um:.3f}",
                position=(length/2, -5), layer=LABEL_LAYER)

    c.add_port(name="input", port=wg.ports["o1"])
    c.add_port(name="output", port=wg.ports["o2"])
    c.add_port(name="pump", port=pump_coupler.ports["o1"])

    return c


def carry_injector(
    name: str = "carry_injector"
) -> gf.Component:
    """
    Injects optical carry signal into next trit's computation.

    Structure:
        carry_in ──→ Combiner ──→ output (to next trit's mixer input)
        signal_in ─┘

    The carry signal (now at input wavelength after OPA conversion)
    is combined with the next trit's A+B signal before the mixer.
    """
    c = gf.Component(name)

    # 2x1 combiner (carry + signal)
    combiner = c << gf.components.mmi2x2()

    c.add_port(name="signal_in", port=combiner.ports["o1"])
    c.add_port(name="carry_in", port=combiner.ports["o2"])
    c.add_port(name="output", port=combiner.ports["o3"])

    c.add_label("CARRY_INJ", position=(10, 10), layer=LABEL_LAYER)

    return c


def optical_carry_unit(
    name: str = "carry_unit",
    uid: str = ""
) -> gf.Component:
    """
    Complete optical carry unit for one trit.

    Handles both carry-out (to next trit) and carry-in (from previous trit).

    Structure:
        carry_in_pos ──→ OPA ──→ ┐
        carry_in_neg ──→ OPA ──→ ├→ Injector ──→ to_mixer
                    signal_in ──→ ┘

        from_mixer ──→ Carry Tap ──→ thru (to detectors)
                              ├──→ carry_out_pos (0.500 μm)
                              └──→ carry_out_neg (0.775 μm)

        carry_out_pos ──→ OPA ──→ Delay ──→ to_next_trit_pos
        carry_out_neg ──→ OPA ──→ Delay ──→ to_next_trit_neg
    """
    import uuid
    if not uid:
        uid = str(uuid.uuid4())[:8]

    c = gf.Component(name)

    # === CARRY INPUT (from previous trit) ===

    # OPA converters for incoming carry
    opa_in_pos = c << wavelength_converter_opa(
        input_wavelength_um=0.500,
        output_wavelength_um=1.000,  # Blue = +1
        name=f"opa_in_pos_{uid}"
    )
    opa_in_pos.dmove((0, 30))

    opa_in_neg = c << wavelength_converter_opa(
        input_wavelength_um=0.775,
        output_wavelength_um=1.550,  # Red = -1
        name=f"opa_in_neg_{uid}"
    )
    opa_in_neg.dmove((0, -30))

    # Carry injector
    injector = c << carry_injector(name=f"injector_{uid}")
    injector.dmove((50, 0))

    # Combiner for pos and neg carry signals
    carry_combine = c << gf.components.mmi2x2()
    carry_combine.dmove((35, 0))

    route_single(c, cross_section=XS, port1=opa_in_pos.ports["output"], port2=carry_combine.ports["o1"])
    route_single(c, cross_section=XS, port1=opa_in_neg.ports["output"], port2=carry_combine.ports["o2"])
    route_single(c, cross_section=XS, port1=carry_combine.ports["o3"], port2=injector.ports["carry_in"])

    # === CARRY OUTPUT (to next trit) ===

    # Carry tap extracts carry wavelengths from mixer output
    tap = c << carry_tap(name=f"tap_{uid}")
    tap.dmove((150, 0))

    # OPA converters for outgoing carry
    opa_out_pos = c << wavelength_converter_opa(
        input_wavelength_um=0.500,
        output_wavelength_um=1.000,
        name=f"opa_out_pos_{uid}"
    )
    opa_out_pos.dmove((200, 30))

    opa_out_neg = c << wavelength_converter_opa(
        input_wavelength_um=0.775,
        output_wavelength_um=1.550,
        name=f"opa_out_neg_{uid}"
    )
    opa_out_neg.dmove((200, -30))

    # Delay lines for timing
    delay_pos = c << optical_delay_line(delay_ps=5.0, name=f"delay_pos_{uid}")
    delay_pos.dmove((250, 30))

    delay_neg = c << optical_delay_line(delay_ps=5.0, name=f"delay_neg_{uid}")
    delay_neg.dmove((250, -30))

    # Route carry tap outputs through OPA and delay
    route_single(c, cross_section=XS, port1=tap.ports["carry_pos"], port2=opa_out_pos.ports["input"])
    route_single(c, cross_section=XS, port1=tap.ports["carry_neg"], port2=opa_out_neg.ports["input"])
    route_single(c, cross_section=XS, port1=opa_out_pos.ports["output"], port2=delay_pos.ports["input"])
    route_single(c, cross_section=XS, port1=opa_out_neg.ports["output"], port2=delay_neg.ports["input"])

    # === PORTS ===

    # Carry inputs (from previous trit)
    c.add_port(name="carry_in_pos", port=opa_in_pos.ports["input"])
    c.add_port(name="carry_in_neg", port=opa_in_neg.ports["input"])

    # Signal path
    c.add_port(name="signal_in", port=injector.ports["signal_in"])
    c.add_port(name="to_mixer", port=injector.ports["output"])
    c.add_port(name="from_mixer", port=tap.ports["input"])
    c.add_port(name="to_detectors", port=tap.ports["thru"])

    # Carry outputs (to next trit)
    c.add_port(name="carry_out_pos", port=delay_pos.ports["output"])
    c.add_port(name="carry_out_neg", port=delay_neg.ports["output"])

    # Pump inputs for OPA
    c.add_port(name="pump_in_pos", port=opa_in_pos.ports["pump"])
    c.add_port(name="pump_in_neg", port=opa_in_neg.ports["pump"])
    c.add_port(name="pump_out_pos", port=opa_out_pos.ports["pump"])
    c.add_port(name="pump_out_neg", port=opa_out_neg.ports["pump"])

    c.add_label("OPTICAL_CARRY", position=(150, 50), layer=LABEL_LAYER)

    return c


def wavelength_combiner(
    n_inputs: int = 3,
    name: str = "combiner"
) -> gf.Component:
    """
    Creates a wavelength combiner (multiplexer).

    Combines multiple wavelengths into a single waveguide.
    Uses cascaded Y-junctions or MMI.
    """
    c = gf.Component(name)

    if n_inputs == 2:
        # Simple 2x2 MMI used as combiner (2 in -> 1 out, ignore 4th port)
        mmi = c << gf.components.mmi2x2()
        c.add_port(name="in1", port=mmi.ports["o1"])
        c.add_port(name="in2", port=mmi.ports["o2"])
        c.add_port(name="output", port=mmi.ports["o3"])
    else:
        # Cascaded combiners for 3+ inputs
        # First combine inputs 1 and 2
        mmi1 = c << gf.components.mmi2x2()
        mmi1.dmove((0, 10))

        # Then combine with input 3
        mmi2 = c << gf.components.mmi2x2()
        mmi2.dmove((30, 0))

        # Route first combiner output to second combiner
        route_single(c, cross_section=XS, port1=mmi1.ports["o3"], port2=mmi2.ports["o1"])

        c.add_port(name="in1", port=mmi1.ports["o1"])
        c.add_port(name="in2", port=mmi1.ports["o2"])
        c.add_port(name="in3", port=mmi2.ports["o2"])
        c.add_port(name="output", port=mmi2.ports["o3"])

    return c


def wavelength_splitter(
    n_outputs: int = 3,
    name: str = "splitter"
) -> gf.Component:
    """
    Creates a wavelength splitter (demultiplexer / AWG-like).

    Splits input into separate wavelength channels.
    Supports 2, 3, 4, or 5 outputs via cascaded 1x2 MMIs.
    """
    c = gf.Component(name)

    if n_outputs == 2:
        mmi = c << gf.components.mmi1x2()
        c.add_port(name="input", port=mmi.ports["o1"])
        c.add_port(name="out1", port=mmi.ports["o2"])
        c.add_port(name="out2", port=mmi.ports["o3"])
    elif n_outputs == 3:
        # Cascaded splitters: 1->2, then one branch ->2 more
        mmi1 = c << gf.components.mmi1x2()
        mmi2 = c << gf.components.mmi1x2()
        mmi2.dmove((30, -10))

        route_single(c, cross_section=XS, port1=mmi1.ports["o3"], port2=mmi2.ports["o1"])

        c.add_port(name="input", port=mmi1.ports["o1"])
        c.add_port(name="out1", port=mmi1.ports["o2"])
        c.add_port(name="out2", port=mmi2.ports["o2"])
        c.add_port(name="out3", port=mmi2.ports["o3"])
    elif n_outputs == 4:
        # Binary tree: 1->2->4
        mmi1 = c << gf.components.mmi1x2()
        mmi2 = c << gf.components.mmi1x2()
        mmi3 = c << gf.components.mmi1x2()
        mmi2.dmove((30, 10))
        mmi3.dmove((30, -10))

        route_single(c, cross_section=XS, port1=mmi1.ports["o2"], port2=mmi2.ports["o1"])
        route_single(c, cross_section=XS, port1=mmi1.ports["o3"], port2=mmi3.ports["o1"])

        c.add_port(name="input", port=mmi1.ports["o1"])
        c.add_port(name="out1", port=mmi2.ports["o2"])
        c.add_port(name="out2", port=mmi2.ports["o3"])
        c.add_port(name="out3", port=mmi3.ports["o2"])
        c.add_port(name="out4", port=mmi3.ports["o3"])
    elif n_outputs == 5:
        # 1->2, then each ->2 (gives 4), then one more split on center
        # Structure: 1->2->4, plus one extra split = 5
        mmi1 = c << gf.components.mmi1x2()
        mmi2 = c << gf.components.mmi1x2()
        mmi3 = c << gf.components.mmi1x2()
        mmi4 = c << gf.components.mmi1x2()
        mmi2.dmove((30, 15))
        mmi3.dmove((30, -15))
        mmi4.dmove((60, -5))  # Extra split from mmi3 upper output

        route_single(c, cross_section=XS, port1=mmi1.ports["o2"], port2=mmi2.ports["o1"])
        route_single(c, cross_section=XS, port1=mmi1.ports["o3"], port2=mmi3.ports["o1"])
        route_single(c, cross_section=XS, port1=mmi3.ports["o2"], port2=mmi4.ports["o1"])

        c.add_port(name="input", port=mmi1.ports["o1"])
        c.add_port(name="out1", port=mmi2.ports["o2"])   # Top
        c.add_port(name="out2", port=mmi2.ports["o3"])
        c.add_port(name="out3", port=mmi4.ports["o2"])   # Center (from extra split)
        c.add_port(name="out4", port=mmi4.ports["o3"])
        c.add_port(name="out5", port=mmi3.ports["o3"])   # Bottom
    else:
        raise ValueError(f"n_outputs must be 2, 3, 4, or 5, got {n_outputs}")

    return c


def photodetector(
    width: float = 0.5,
    length: float = 2.0,
    name: str = "detector"
) -> gf.Component:
    """
    Creates a photodetector for reading output.
    """
    c = gf.Component(name)

    # Input taper
    taper = c << gf.components.taper(length=5, width1=0.5, width2=width)

    # Detector region (absorbing)
    det = c << gf.components.rectangle(size=(length, width), layer=(3, 0))
    det.dmove((5, -width/2))

    c.add_label("PD", position=(10, -width), layer=LABEL_LAYER)
    c.add_port(name="input", port=taper.ports["o1"])

    return c


def kerr_resonator(
    radius: float = 10.0,
    gap: float = 0.15,
    name: str = "kerr_clock"
) -> gf.Component:
    """
    Creates a Kerr resonator for optical clock/timing synchronization.

    The Kerr effect (third-order nonlinearity) creates self-phase modulation,
    enabling optical timing synchronization without electronics.

    Args:
        radius: Ring radius (larger = higher Q, sharper timing)
        gap: Coupling gap
        name: Component name
    """
    c = gf.Component(name)

    # Ring resonator with Kerr nonlinearity marker
    ring = c << gf.components.ring_single(radius=radius, gap=gap)

    # Visual marker for Kerr region (layer 5)
    c.add_polygon(
        [(- radius - 1, -1), (radius + 1, -1), (radius + 1, 1), (-radius - 1, 1)],
        layer=(5, 0)
    )

    c.add_label("CLK", position=(0, radius + 3), layer=LABEL_LAYER)

    c.add_port(name="input", port=ring.ports["o1"])
    c.add_port(name="output", port=ring.ports["o2"])

    return c


def y_junction(
    name: str = "y_split"
) -> gf.Component:
    """
    Creates a Y-junction beam splitter.

    Splits input beam into two equal-power outputs for A and B operand paths.
    Uses MMI-based 1x2 splitter for broadband operation.
    """
    c = gf.Component(name)

    # 1x2 MMI splitter
    mmi = c << gf.components.mmi1x2()

    c.add_label("Y", position=(0, 5), layer=LABEL_LAYER)

    c.add_port(name="input", port=mmi.ports["o1"])
    c.add_port(name="out_a", port=mmi.ports["o2"])
    c.add_port(name="out_b", port=mmi.ports["o3"])

    return c


def awg_demux(
    n_channels: int = 3,
    name: str = "awg"
) -> gf.Component:
    """
    Creates an Arrayed Waveguide Grating (AWG) demultiplexer.

    Separates input wavelengths into separate output channels.
    For ternary input: separates R (1.55um), G (1.216um), B (1.00um).
    For output detection: separates 5 SFG wavelengths (0.775, 0.681, 0.608, 0.549, 0.500 um).

    Args:
        n_channels: Number of output wavelength channels (3 or 5)
        name: Component name
    """
    c = gf.Component(name)

    if n_channels == 3:
        # 3-channel AWG for input demux (R/G/B)
        input_mmi = c << gf.components.mmi1x2()
        input_mmi.dmove((0, 0))

        mmi2 = c << gf.components.mmi1x2()
        mmi2.dmove((30, -10))

        route_single(c, cross_section=XS, port1=input_mmi.ports["o3"], port2=mmi2.ports["o1"])

        # AWG body marker (layer 6)
        c.add_polygon(
            [(10, -25), (50, -25), (50, 15), (10, 15)],
            layer=(6, 0)
        )
        c.add_label("AWG_3ch", position=(30, 20), layer=LABEL_LAYER)

        c.add_port(name="input", port=input_mmi.ports["o1"])
        c.add_port(name="out_1", port=input_mmi.ports["o2"])
        c.add_port(name="out_2", port=mmi2.ports["o2"])
        c.add_port(name="out_3", port=mmi2.ports["o3"])
        # Legacy port names for compatibility
        c.add_port(name="out_r", port=input_mmi.ports["o2"])
        c.add_port(name="out_g", port=mmi2.ports["o2"])
        c.add_port(name="out_b", port=mmi2.ports["o3"])

    elif n_channels == 5:
        # 5-channel AWG for output demux (SFG wavelengths)
        # Structure: 1->2->4, then one branch splits again for 5th channel
        mmi1 = c << gf.components.mmi1x2()
        mmi2 = c << gf.components.mmi1x2()
        mmi3 = c << gf.components.mmi1x2()
        mmi4 = c << gf.components.mmi1x2()

        mmi1.dmove((0, 0))
        mmi2.dmove((30, 12))
        mmi3.dmove((30, -12))
        mmi4.dmove((60, 0))

        route_single(c, cross_section=XS, port1=mmi1.ports["o2"], port2=mmi2.ports["o1"])
        route_single(c, cross_section=XS, port1=mmi1.ports["o3"], port2=mmi3.ports["o1"])
        route_single(c, cross_section=XS, port1=mmi3.ports["o2"], port2=mmi4.ports["o1"])

        # AWG body marker (layer 6) - larger for 5-channel
        c.add_polygon(
            [(5, -30), (80, -30), (80, 30), (5, 30)],
            layer=(6, 0)
        )
        c.add_label("AWG_5ch", position=(40, 35), layer=LABEL_LAYER)

        c.add_port(name="input", port=mmi1.ports["o1"])
        c.add_port(name="out_1", port=mmi2.ports["o2"])   # 0.775 μm (DET_-2)
        c.add_port(name="out_2", port=mmi2.ports["o3"])   # 0.681 μm (DET_-1)
        c.add_port(name="out_3", port=mmi4.ports["o2"])   # 0.608 μm (DET_0)
        c.add_port(name="out_4", port=mmi4.ports["o3"])   # 0.549 μm (DET_+1)
        c.add_port(name="out_5", port=mmi3.ports["o3"])   # 0.500 μm (DET_+2)

    else:
        raise ValueError(f"n_channels must be 3 or 5, got {n_channels}")

    return c


def ternary_output_stage_simple(
    name: str = "output_simple",
    uid: str = "",
    include_carry_ports: bool = False
) -> gf.Component:
    """
    SIMPLIFIED output stage using single AWG demux instead of 5 ring filters.

    Structure: Input -> AWG (5-ch) -> 5x Photodetectors

    This replaces:
      - 1x 5-way splitter
      - 5x ring resonator filters
    With:
      - 1x 5-channel AWG demux

    Component reduction: 6 components -> 1 component (per ALU)
    Total savings for 81 ALUs: 405 ring resonators eliminated

    Output channels (SFG wavelengths):
      - Ch1 (0.775 μm): Result = -2 (borrow) -> CARRY_OUT_NEG
      - Ch2 (0.681 μm): Result = -1
      - Ch3 (0.608 μm): Result = 0
      - Ch4 (0.549 μm): Result = +1
      - Ch5 (0.500 μm): Result = +2 (carry) -> CARRY_OUT_POS

    Args:
        include_carry_ports: If True, adds electrical carry output pads for
                            carry chain wiring between adjacent trits.

    Carry Chain (Electronic Approach):
    ---------------------------------
    The DET_-2 (borrow) and DET_+2 (carry) photodetector outputs are
    exposed as electrical pads (CARRY_OUT_NEG, CARRY_OUT_POS) that can
    be wired to firmware GPIO or the next trit's carry input.

    Firmware Carry Propagation Algorithm:
      1. Read all photodetector outputs simultaneously
      2. For each trit position N (from LSB to MSB):
         a. Check CARRY_OUT_POS from trit N-1: if active, add +1 to current sum
         b. Check CARRY_OUT_NEG from trit N-1: if active, add -1 to current sum
      3. The result at each trit is: A[N] + B[N] + carry_in mod 3
      4. Generate new carry for trit N+1

    Signal Naming Convention:
      - CARRY_OUT_POS: Positive overflow (+2 detected) -> add +1 to next trit
      - CARRY_OUT_NEG: Negative overflow (-2 detected) -> add -1 to next trit (borrow)
      - CARRY_IN: Combined carry input from previous trit (active-high logic)
    """
    import uuid
    if not uid:
        uid = str(uuid.uuid4())[:8]

    c = gf.Component(name)

    # Single 5-channel AWG demux replaces splitter + 5 ring filters
    awg = c << awg_demux(n_channels=5, name=f"awg_out_{uid}")

    # 5 photodetectors directly connected to AWG outputs
    DETECTOR_CONFIG = [
        {'value': -2, 'wavelength_um': 0.775, 'name': 'Neg2', 'port': 'out_1', 'is_carry': True},
        {'value': -1, 'wavelength_um': 0.681, 'name': 'Neg1', 'port': 'out_2', 'is_carry': False},
        {'value':  0, 'wavelength_um': 0.608, 'name': 'Zero', 'port': 'out_3', 'is_carry': False},
        {'value': +1, 'wavelength_um': 0.549, 'name': 'Pos1', 'port': 'out_4', 'is_carry': False},
        {'value': +2, 'wavelength_um': 0.500, 'name': 'Pos2', 'port': 'out_5', 'is_carry': True},
    ]

    y_positions = [24, 12, 0, -12, -24]  # Match AWG output positions

    for i, det_info in enumerate(DETECTOR_CONFIG):
        det = c << photodetector(
            width=0.5,
            length=2.0,
            name=f"det_{det_info['name']}_{uid}"
        )
        det.dmove((95, y_positions[i]))

        # Route AWG output directly to detector
        route_single(c, cross_section=XS,
                    port1=awg.ports[det_info['port']],
                    port2=det.ports["input"])

        # Label
        label_suffix = "_C" if det_info['is_carry'] else ""
        c.add_label(f"D{det_info['value']:+d}{label_suffix}",
                   position=(110, y_positions[i]), layer=LABEL_LAYER)

    # Input port
    c.add_port(name="input", port=awg.ports["input"])

    # Add electrical carry output pads if requested
    if include_carry_ports:
        # CARRY_OUT_NEG pad: electrical output from DET_-2 (borrow signal)
        # Position: right side of DET_-2, top of output stage
        c.add_polygon(
            [(120, y_positions[0] - 3), (130, y_positions[0] - 3),
             (130, y_positions[0] + 3), (120, y_positions[0] + 3)],
            layer=HEATER_LAYER  # Using heater layer for electrical pads
        )
        c.add_label("CARRY_OUT_NEG", position=(125, y_positions[0] + 7), layer=LABEL_LAYER)

        # CARRY_OUT_POS pad: electrical output from DET_+2 (carry signal)
        # Position: right side of DET_+2, bottom of output stage
        c.add_polygon(
            [(120, y_positions[4] - 3), (130, y_positions[4] - 3),
             (130, y_positions[4] + 3), (120, y_positions[4] + 3)],
            layer=HEATER_LAYER
        )
        c.add_label("CARRY_OUT_POS", position=(125, y_positions[4] - 9), layer=LABEL_LAYER)

        # CARRY_IN pad: electrical input for carry from previous trit
        # Position: left side of output stage, near optical input
        c.add_polygon(
            [(-15, -3), (-5, -3), (-5, 3), (-15, 3)],
            layer=HEATER_LAYER
        )
        c.add_label("CARRY_IN", position=(-10, 7), layer=LABEL_LAYER)

    c.add_label("OUT_AWG", position=(50, 40), layer=LABEL_LAYER)

    return c


def optical_frontend(
    name: str = "frontend",
    uid: str = ""
) -> gf.Component:
    """
    Creates the complete optical frontend/input conditioning stage.

    Structure:
      CW Laser Input -> Kerr Resonator (clock) -> Y-Junction (split A/B)
                                                      |
                                          +-----------+-----------+
                                          |                       |
                                        AWG_A                   AWG_B
                                       (demux)                 (demux)
                                          |                       |
                                    R_A, G_A, B_A           R_B, G_B, B_B

    Returns component with ports for laser input and 6 wavelength outputs
    (3 for operand A, 3 for operand B).
    """
    import uuid
    if not uid:
        uid = str(uuid.uuid4())[:8]

    c = gf.Component(name)

    # 1. Kerr resonator for timing
    clk = c << kerr_resonator(name=f"clk_{uid}")
    clk.dmove((0, 0))

    # 2. Y-junction to split to A and B paths
    ysplit = c << y_junction(name=f"ysplit_{uid}")
    ysplit.dmove((40, 0))

    route_single(c, cross_section=XS, port1=clk.ports["output"], port2=ysplit.ports["input"])

    # 3. AWG for operand A (upper path)
    awg_a = c << awg_demux(name=f"awg_a_{uid}")
    awg_a.dmove((80, 30))

    route_single(c, cross_section=XS, port1=ysplit.ports["out_a"], port2=awg_a.ports["input"])

    # 4. AWG for operand B (lower path)
    awg_b = c << awg_demux(name=f"awg_b_{uid}")
    awg_b.dmove((80, -30))

    route_single(c, cross_section=XS, port1=ysplit.ports["out_b"], port2=awg_b.ports["input"])

    # Labels
    c.add_label("FRONTEND", position=(60, 60), layer=LABEL_LAYER)
    c.add_label("CW_IN", position=(-15, 0), layer=LABEL_LAYER)

    # Ports
    c.add_port(name="laser_in", port=clk.ports["input"])

    # Operand A outputs
    c.add_port(name="a_red", port=awg_a.ports["out_r"])
    c.add_port(name="a_green", port=awg_a.ports["out_g"])
    c.add_port(name="a_blue", port=awg_a.ports["out_b"])

    # Operand B outputs
    c.add_port(name="b_red", port=awg_b.ports["out_r"])
    c.add_port(name="b_green", port=awg_b.ports["out_g"])
    c.add_port(name="b_blue", port=awg_b.ports["out_b"])

    return c


def ternary_output_stage(
    name: str = "output_stage",
    uid: str = "",
    include_carry: bool = True
) -> gf.Component:
    """
    Creates a wavelength-discriminating output stage for SFG mixer results.

    Structure: Input -> Splitter -> 5x Filters -> 5x Photodetectors

    The mixer SFG output hits all five filtered detectors simultaneously.
    Each detector is tuned to a specific SFG OUTPUT wavelength (not input wavelength).

    Full detector mapping (all 5 results, verified by simulation):
      - Det -2 (0.775 μm): Result = -2 (from R+R mixing) - CARRY/BORROW
      - Det -1 (0.681 μm): Result = -1 (from R+G mixing)
      - Det  0 (0.608 μm): Result =  0 (from R+B or G+G mixing)
      - Det +1 (0.549 μm): Result = +1 (from G+B mixing)
      - Det +2 (0.500 μm): Result = +2 (from B+B mixing) - CARRY

    Args:
        include_carry: If True, includes all 5 detectors (-2 to +2).
                      If False, only 3 detectors (-1, 0, +1).
    """
    import uuid
    if not uid:
        uid = str(uuid.uuid4())[:8]

    c = gf.Component(name)

    # Full detector configuration for all 5 SFG output wavelengths (verified by simulation)
    DETECTOR_CONFIG_FULL = [
        {'value': -2, 'wavelength_um': 0.775, 'name': 'Neg2', 'is_carry': True},   # R+R → -2 (borrow)
        {'value': -1, 'wavelength_um': 0.681, 'name': 'Neg1', 'is_carry': False},  # R+G → -1
        {'value':  0, 'wavelength_um': 0.608, 'name': 'Zero', 'is_carry': False},  # R+B or G+G → 0
        {'value': +1, 'wavelength_um': 0.549, 'name': 'Pos1', 'is_carry': False},  # G+B → +1
        {'value': +2, 'wavelength_um': 0.500, 'name': 'Pos2', 'is_carry': True},   # B+B → +2 (carry)
    ]

    DETECTOR_CONFIG_BASIC = [
        {'value': -1, 'wavelength_um': 0.681, 'name': 'Neg1', 'is_carry': False},
        {'value':  0, 'wavelength_um': 0.608, 'name': 'Zero', 'is_carry': False},
        {'value': +1, 'wavelength_um': 0.549, 'name': 'Pos1', 'is_carry': False},
    ]

    detector_config = DETECTOR_CONFIG_FULL if include_carry else DETECTOR_CONFIG_BASIC
    n_detectors = len(detector_config)

    # Splitter to send light to all detector paths
    splitter = c << wavelength_splitter(n_outputs=n_detectors, name=f"output_split_{uid}")

    # Filtered detector channels
    y_spacing = 25
    detector_x = 100 if include_carry else 80
    center_index = n_detectors // 2

    for i, det_info in enumerate(detector_config):
        y_pos = (i - center_index) * y_spacing

        # Ring resonator filter tuned to SFG output wavelength
        filt = c << wavelength_selector(
            wavelength_um=det_info['wavelength_um'],
            radius=5.0,
            gap=0.15,
            name=f"filter_{det_info['name']}_{uid}"
        )
        filt.dmove((50, y_pos))

        # Photodetector after filter
        det = c << photodetector(
            width=0.5,
            length=2.0,
            name=f"detect_{det_info['name']}_{uid}"
        )
        det.dmove((detector_x, y_pos))

        # Route splitter -> filter -> detector
        route_single(c, cross_section=XS,
                    port1=splitter.ports[f"out{i+1}"],
                    port2=filt.ports["input"])
        route_single(c, cross_section=XS,
                    port1=filt.ports["output"],
                    port2=det.ports["input"])

        # Label each detector with result value (mark carry/borrow)
        label_suffix = "_C" if det_info['is_carry'] else ""
        c.add_label(f"DET_{det_info['value']:+d}{label_suffix}",
                   position=(detector_x + 15, y_pos), layer=LABEL_LAYER)

    # Input port
    c.add_port(name="input", port=splitter.ports["input"])

    # Labels
    c.add_label("OUT_FULL" if include_carry else "OUT",
               position=(60, (center_index + 1) * y_spacing), layer=LABEL_LAYER)

    return c


# =============================================================================
# HIGH-LEVEL CHIP GENERATORS
# =============================================================================

def ternary_input_stage(
    operand_name: str = "A",
    y_offset: float = 0,
    uid: str = "",
    selector_type: Literal['ring', 'mzi'] = 'ring'
) -> gf.Component:
    """
    Creates an input stage for one ternary operand.

    Structure: Input -> Splitter -> 3x Selectors (R/G/B)
    Each selector can be individually enabled to set the ternary value.

    Args:
        operand_name: Name for this operand (e.g., "A" or "B")
        y_offset: Vertical offset for positioning
        uid: Unique identifier suffix
        selector_type: Type of wavelength selector to use:
            - 'ring': Ring resonator (default, wavelength-selective)
            - 'mzi': MZI switch (better extinction, broader bandwidth)
    """
    c = gf.Component(f"input_{operand_name}_{uid}")

    # Input splitter (1 -> 3 wavelengths)
    splitter = c << wavelength_splitter(n_outputs=3, name=f"split_{operand_name}_{uid}")

    # Three selectors for R, G, B
    y_spacing = 30 if selector_type == 'ring' else 40  # MZI needs more vertical space
    x_offset = 60 if selector_type == 'ring' else 60
    selectors = []

    for i, (trit, info) in enumerate(TERNARY_ENCODING.items()):
        if selector_type == 'mzi':
            sel = c << wavelength_selector_mzi(
                wavelength_um=info['wavelength_um'],
                name=f"sel_{operand_name}_{info['name']}_{uid}"
            )
        else:
            sel = c << wavelength_selector(
                wavelength_um=info['wavelength_um'],
                name=f"sel_{operand_name}_{info['name']}_{uid}"
            )
        sel.dmove((x_offset, (i - 1) * y_spacing))
        selectors.append(sel)

        # Route splitter to selector
        route_single(c, cross_section=XS, port1=splitter.ports[f"out{i+1}"], port2=sel.ports["input"])

    # Combiner to merge selected wavelengths
    combiner_x = 130 if selector_type == 'ring' else 180  # MZI is wider
    combiner = c << wavelength_combiner(n_inputs=3, name=f"comb_{operand_name}_{uid}")
    combiner.dmove((combiner_x, 0))

    # Route selectors to combiner
    for i, sel in enumerate(selectors):
        route_single(c, cross_section=XS, port1=sel.ports["output"], port2=combiner.ports[f"in{i+1}"])

    # Final output port
    c.add_port(name="input", port=splitter.ports["input"])
    c.add_port(name="output", port=combiner.ports["output"])

    # Move entire stage
    c.dmove((0, y_offset))

    return c


def generate_ternary_alu(
    operations: List[str] = ["add"],
    name: str = "TernaryALU",
    selector_type: Literal['ring', 'mzi'] = 'ring'
) -> gf.Component:
    """
    Generates a complete Ternary ALU chip.

    Args:
        operations: List of operations to support ['add', 'multiply', 'compare']
        name: Chip name
        selector_type: Type of wavelength selector to use:
            - 'ring': Ring resonator (default, wavelength-selective)
            - 'mzi': MZI switch (better extinction ratio, broader bandwidth,
                     more tolerant to fabrication variations)

    Returns:
        Complete chip layout
    """
    import uuid
    uid = str(uuid.uuid4())[:8]

    c = gf.Component(name)

    # =========================
    # 1. INPUT STAGES (2 operands)
    # =========================
    input_a = c << ternary_input_stage("A", y_offset=50, uid=uid, selector_type=selector_type)
    input_b = c << ternary_input_stage("B", y_offset=-50, uid=uid, selector_type=selector_type)

    # =========================
    # 2. OPERATION COMBINER
    # =========================
    # Merge both operands into single waveguide for mixing
    op_combiner = c << gf.components.mmi2x2()
    op_combiner.dmove((200, 0))

    route_single(c, cross_section=XS, port1=input_a.ports["output"], port2=op_combiner.ports["o2"])
    route_single(c, cross_section=XS, port1=input_b.ports["output"], port2=op_combiner.ports["o3"])

    # =========================
    # 3. SFG MIXER (The brain!)
    # =========================
    mixer = c << sfg_mixer(length=20, name=f"alu_mixer_{uid}")
    mixer.dmove((250, 0))

    route_single(c, cross_section=XS, port1=op_combiner.ports["o1"], port2=mixer.ports["input"])

    # =========================
    # 4. OUTPUT DETECTION (3-channel)
    # =========================
    output_stage = c << ternary_output_stage(name=f"output_{uid}", uid=uid)
    output_stage.dmove((300, 0))

    route_single(c, cross_section=XS, port1=mixer.ports["output"], port2=output_stage.ports["input"])

    # =========================
    # 5. LABELS & METADATA
    # =========================
    c.add_label("ALU", position=(150, 100), layer=LABEL_LAYER)
    c.add_label("A", position=(0, 80), layer=LABEL_LAYER)
    c.add_label("B", position=(0, -80), layer=LABEL_LAYER)
    c.add_label("Q", position=(300, 40), layer=LABEL_LAYER)

    # Add input ports
    c.add_port(name="input_a", port=input_a.ports["input"])
    c.add_port(name="input_b", port=input_b.ports["input"])

    return c


def generate_ternary_adder() -> gf.Component:
    """
    Generates a ternary adder chip.

    Truth table (simplified):
      A + B = Result
     -1 + -1 = -2 (overflow to -1 with carry)
     -1 +  0 = -1
     -1 + +1 =  0
      0 + -1 = -1
      0 +  0 =  0
      0 + +1 = +1
     +1 + -1 =  0
     +1 +  0 = +1
     +1 + +1 = +2 (overflow to +1 with carry)
    """
    return generate_ternary_alu(operations=["add"], name="TernaryAdder")


def generate_ternary_subtractor() -> gf.Component:
    """
    Generates a ternary subtractor chip.

    A - B is implemented as A + (-B) where -B swaps Red↔Blue wavelengths.

    Truth table:
      A - B = Result
     -1 - -1 =  0
     -1 -  0 = -1
     -1 - +1 = -2 (overflow)
      0 - -1 = +1
      0 -  0 =  0
      0 - +1 = -1
     +1 - -1 = +2 (overflow)
     +1 -  0 = +1
     +1 - +1 =  0
    """
    return generate_ternary_alu(operations=["subtract"], name="TernarySubtractor")


def generate_ternary_divider() -> gf.Component:
    """
    Generates a ternary divider chip.

    Uses DFG (Difference Frequency Generation) for division.
    Note: Integer division in ternary, rounds toward zero.

    This is a single-trit divider. Multi-trit division requires
    cascaded stages with feedback.
    """
    return generate_ternary_alu(operations=["divide"], name="TernaryDivider")


def generate_ternary_multiplier() -> gf.Component:
    """
    Generates a ternary multiplier chip.

    Uses SFG mixing where wavelength multiplication corresponds to
    frequency addition, mapping to ternary value multiplication.
    """
    return generate_ternary_alu(operations=["multiply"], name="TernaryMultiplier")


def generate_full_processor(
    n_trits: int = 3,
    name: str = "TernaryProcessor"
) -> gf.Component:
    """
    Generates a complete N-trit ternary processor.

    Args:
        n_trits: Number of trits per operand (3 = 27 values, 9 = 19683 values)
        name: Chip name
    """
    import uuid
    c = gf.Component(name)

    # Create array of ALU units
    y_spacing = 200

    for i in range(n_trits):
        # Use unique ID suffix to avoid name collisions
        uid = str(uuid.uuid4())[:8]
        alu = c << generate_ternary_alu(
            operations=["add", "multiply"],
            name=f"ALU_trit{i}_{uid}"
        )
        alu.dmove((0, i * y_spacing))

    c.add_label(f"CPU_{n_trits}T", position=(150, n_trits * y_spacing + 50), layer=LABEL_LAYER)

    return c


def generate_complete_alu(
    name: str = "TernaryComplete",
    simplified_output: bool = True,
    operation: Literal['add', 'sub', 'mul'] = 'add',
    selector_type: Literal['ring', 'mzi'] = 'ring'
) -> gf.Component:
    """
    Generates a complete single-trit ALU with optical frontend and output stage.

    Complete signal path:
      CW Laser → Kerr Clock → Y-Split → AWG_A → Selectors_A → Combiner
                                     → AWG_B → Selectors_B → Combiner
                                                                  ↓
                                                            Mixer (SFG/DFG/MUL)
                                                                  ↓
                                                         Output Stage (5 detectors)
                                                                  ↓
                                                         DET_-2 to DET_+2

    Args:
        name: Component name.
        simplified_output: If True, uses single AWG demux (fewer components).
                          If False, uses 5 ring filters (more precise but complex).
        operation: The arithmetic operation to perform:
                   - 'add': Addition using SFG (Sum Frequency Generation)
                   - 'sub': Subtraction using DFG (Difference Frequency Generation)
                   - 'mul': Multiplication using Kerr effect (χ³ nonlinearity)
        selector_type: Type of wavelength selector to use:
                   - 'ring': Ring resonator (default, wavelength-selective)
                   - 'mzi': MZI switch (better extinction ratio, broader bandwidth,
                            more tolerant to fabrication variations, voltage-tuned)
    """
    import uuid
    uid = str(uuid.uuid4())[:8]

    c = gf.Component(name)

    # =========================
    # 1. OPTICAL FRONTEND
    # =========================
    frontend = c << optical_frontend(name=f"frontend_{uid}", uid=uid)
    frontend.dmove((0, 0))

    # =========================
    # 2. INPUT SELECTORS FOR A
    # =========================
    # Three selectors for R, G, B on operand A
    # Selector function and positioning based on selector_type
    if selector_type == 'mzi':
        sel_a_r = c << wavelength_selector_mzi(wavelength_um=1.550, name=f"sel_a_r_{uid}")
        sel_a_g = c << wavelength_selector_mzi(wavelength_um=1.216, name=f"sel_a_g_{uid}")
        sel_a_b = c << wavelength_selector_mzi(wavelength_um=1.000, name=f"sel_a_b_{uid}")
        # MZI needs more spacing due to larger footprint
        sel_a_r.dmove((200, 80))
        sel_a_g.dmove((200, 40))
        sel_a_b.dmove((200, 0))
        comb_a_x = 320  # Combiner positioned further for MZI
        comb_a_y = 40
    else:
        sel_a_r = c << wavelength_selector(wavelength_um=1.550, name=f"sel_a_r_{uid}")
        sel_a_g = c << wavelength_selector(wavelength_um=1.216, name=f"sel_a_g_{uid}")
        sel_a_b = c << wavelength_selector(wavelength_um=1.000, name=f"sel_a_b_{uid}")
        sel_a_r.dmove((200, 60))
        sel_a_g.dmove((200, 30))
        sel_a_b.dmove((200, 0))
        comb_a_x = 280
        comb_a_y = 30

    # Route frontend AWG_A outputs to selectors
    route_single(c, cross_section=XS, port1=frontend.ports["a_red"], port2=sel_a_r.ports["input"])
    route_single(c, cross_section=XS, port1=frontend.ports["a_green"], port2=sel_a_g.ports["input"])
    route_single(c, cross_section=XS, port1=frontend.ports["a_blue"], port2=sel_a_b.ports["input"])

    # Combiner for A
    comb_a = c << wavelength_combiner(n_inputs=3, name=f"comb_a_{uid}")
    comb_a.dmove((comb_a_x, comb_a_y))

    route_single(c, cross_section=XS, port1=sel_a_r.ports["output"], port2=comb_a.ports["in1"])
    route_single(c, cross_section=XS, port1=sel_a_g.ports["output"], port2=comb_a.ports["in2"])
    route_single(c, cross_section=XS, port1=sel_a_b.ports["output"], port2=comb_a.ports["in3"])

    # =========================
    # 3. INPUT SELECTORS FOR B
    # =========================
    if selector_type == 'mzi':
        sel_b_r = c << wavelength_selector_mzi(wavelength_um=1.550, name=f"sel_b_r_{uid}")
        sel_b_g = c << wavelength_selector_mzi(wavelength_um=1.216, name=f"sel_b_g_{uid}")
        sel_b_b = c << wavelength_selector_mzi(wavelength_um=1.000, name=f"sel_b_b_{uid}")
        # MZI needs more spacing
        sel_b_r.dmove((200, -40))
        sel_b_g.dmove((200, -80))
        sel_b_b.dmove((200, -120))
        comb_b_x = 320
        comb_b_y = -80
    else:
        sel_b_r = c << wavelength_selector(wavelength_um=1.550, name=f"sel_b_r_{uid}")
        sel_b_g = c << wavelength_selector(wavelength_um=1.216, name=f"sel_b_g_{uid}")
        sel_b_b = c << wavelength_selector(wavelength_um=1.000, name=f"sel_b_b_{uid}")
        sel_b_r.dmove((200, -60))
        sel_b_g.dmove((200, -30))
        sel_b_b.dmove((200, 0 - 60))
        comb_b_x = 280
        comb_b_y = -60

    # Route frontend AWG_B outputs to selectors
    route_single(c, cross_section=XS, port1=frontend.ports["b_red"], port2=sel_b_r.ports["input"])
    route_single(c, cross_section=XS, port1=frontend.ports["b_green"], port2=sel_b_g.ports["input"])
    route_single(c, cross_section=XS, port1=frontend.ports["b_blue"], port2=sel_b_b.ports["input"])

    # Combiner for B
    comb_b = c << wavelength_combiner(n_inputs=3, name=f"comb_b_{uid}")
    comb_b.dmove((comb_b_x, comb_b_y))

    route_single(c, cross_section=XS, port1=sel_b_r.ports["output"], port2=comb_b.ports["in1"])
    route_single(c, cross_section=XS, port1=sel_b_g.ports["output"], port2=comb_b.ports["in2"])
    route_single(c, cross_section=XS, port1=sel_b_b.ports["output"], port2=comb_b.ports["in3"])

    # =========================
    # 4. OPERATION COMBINER
    # =========================
    op_combiner = c << gf.components.mmi2x2()
    op_combiner.dmove((380, 0))

    route_single(c, cross_section=XS, port1=comb_a.ports["output"], port2=op_combiner.ports["o1"])
    route_single(c, cross_section=XS, port1=comb_b.ports["output"], port2=op_combiner.ports["o2"])

    # =========================
    # 5. MIXER (operation-dependent)
    # =========================
    # Select mixer type based on operation
    if operation == 'add':
        # SFG mixer for addition: λ_out = 1/(1/λ1 + 1/λ2)
        mixer = c << sfg_mixer(length=20, name=f"sfg_mixer_{uid}")
        op_label = "ADD_SFG"
    elif operation == 'sub':
        # DFG mixer for subtraction: λ_out = 1/(1/λ1 - 1/λ2)
        mixer = c << dfg_mixer(length=25, name=f"dfg_mixer_{uid}")
        op_label = "SUB_DFG"
    elif operation == 'mul':
        # Kerr/χ³ mixer for multiplication
        mixer = c << mul_mixer(length=30, name=f"mul_mixer_{uid}")
        op_label = "MUL_KERR"
    else:
        raise ValueError(f"Unknown operation '{operation}'. Must be 'add', 'sub', or 'mul'.")

    mixer.dmove((430, 0))

    route_single(c, cross_section=XS, port1=op_combiner.ports["o3"], port2=mixer.ports["input"])

    # =========================
    # 6. OUTPUT STAGE (5 detectors)
    # =========================
    if simplified_output:
        output = c << ternary_output_stage_simple(name=f"output_{uid}", uid=uid)
    else:
        output = c << ternary_output_stage(name=f"output_{uid}", uid=uid)
    output.dmove((480, 0))

    route_single(c, cross_section=XS, port1=mixer.ports["output"], port2=output.ports["input"])

    # =========================
    # 7. LABELS
    # =========================
    c.add_label(f"ALU_{op_label}", position=(250, 100), layer=LABEL_LAYER)
    c.add_label("LASER_IN", position=(-20, 0), layer=LABEL_LAYER)

    # Add port for laser input
    c.add_port(name="laser_in", port=frontend.ports["laser_in"])

    return c


def generate_optical_carry_alu(
    name: str = "TernaryOpticalCarry",
    operation: Literal['add', 'sub', 'mul'] = 'add',
    selector_type: Literal['ring', 'mzi'] = 'ring'
) -> gf.Component:
    """
    Generates a single-trit ALU with FULLY OPTICAL carry propagation.

    This ALU includes the optical carry chain components:
      - Carry input (from previous trit) via OPA wavelength conversion
      - Carry output (to next trit) via carry tap + OPA + delay line

    The carry signals are wavelength-converted and time-delayed so that
    multi-trit arithmetic happens entirely in the optical domain.
    The controlling computer just loads operands and reads results.

    Signal flow:
      carry_in_pos ──→ OPA ──┐
      carry_in_neg ──→ OPA ──┼→ Injector ──┐
                             │             │
      CW Laser → Frontend → AWG → Selectors → Combiner ──→ Injector → Mixer
                                                                        ↓
      carry_out_pos ←── OPA ←── Delay ←── Carry Tap ←── Mixer Output
      carry_out_neg ←── OPA ←── Delay ←──────┘              ↓
                                                      Output Stage
                                                           ↓
                                                    DET_-2 to DET_+2

    Args:
        name: Component name
        operation: 'add', 'sub', or 'mul'
        selector_type: 'ring' or 'mzi'
    """
    import uuid
    uid = str(uuid.uuid4())[:8]

    c = gf.Component(name)

    # =========================
    # 1. OPTICAL FRONTEND
    # =========================
    frontend = c << optical_frontend(name=f"frontend_{uid}", uid=uid)
    frontend.dmove((0, 0))

    # =========================
    # 2. WAVELENGTH SELECTORS FOR OPERAND A
    # =========================
    if selector_type == 'ring':
        sel_a_r = c << wavelength_selector(wavelength_um=1.550, name=f"sel_a_r_{uid}")
        sel_a_g = c << wavelength_selector(wavelength_um=1.216, name=f"sel_a_g_{uid}")
        sel_a_b = c << wavelength_selector(wavelength_um=1.000, name=f"sel_a_b_{uid}")
    else:  # mzi
        sel_a_r = c << wavelength_selector_mzi(wavelength_um=1.550, name=f"sel_a_r_{uid}")
        sel_a_g = c << wavelength_selector_mzi(wavelength_um=1.216, name=f"sel_a_g_{uid}")
        sel_a_b = c << wavelength_selector_mzi(wavelength_um=1.000, name=f"sel_a_b_{uid}")

    sel_a_r.dmove((180, 50))
    sel_a_g.dmove((180, 25))
    sel_a_b.dmove((180, 0))

    route_single(c, cross_section=XS, port1=frontend.ports["a_red"], port2=sel_a_r.ports["input"])
    route_single(c, cross_section=XS, port1=frontend.ports["a_green"], port2=sel_a_g.ports["input"])
    route_single(c, cross_section=XS, port1=frontend.ports["a_blue"], port2=sel_a_b.ports["input"])

    # Combiner for A
    comb_a = c << wavelength_combiner(n_inputs=3, name=f"comb_a_{uid}")
    comb_a.dmove((280, 25))

    route_single(c, cross_section=XS, port1=sel_a_r.ports["output"], port2=comb_a.ports["in1"])
    route_single(c, cross_section=XS, port1=sel_a_g.ports["output"], port2=comb_a.ports["in2"])
    route_single(c, cross_section=XS, port1=sel_a_b.ports["output"], port2=comb_a.ports["in3"])

    # =========================
    # 3. WAVELENGTH SELECTORS FOR OPERAND B
    # =========================
    if selector_type == 'ring':
        sel_b_r = c << wavelength_selector(wavelength_um=1.550, name=f"sel_b_r_{uid}")
        sel_b_g = c << wavelength_selector(wavelength_um=1.216, name=f"sel_b_g_{uid}")
        sel_b_b = c << wavelength_selector(wavelength_um=1.000, name=f"sel_b_b_{uid}")
    else:  # mzi
        sel_b_r = c << wavelength_selector_mzi(wavelength_um=1.550, name=f"sel_b_r_{uid}")
        sel_b_g = c << wavelength_selector_mzi(wavelength_um=1.216, name=f"sel_b_g_{uid}")
        sel_b_b = c << wavelength_selector_mzi(wavelength_um=1.000, name=f"sel_b_b_{uid}")

    sel_b_r.dmove((180, -25))
    sel_b_g.dmove((180, -50))
    sel_b_b.dmove((180, -75))

    route_single(c, cross_section=XS, port1=frontend.ports["b_red"], port2=sel_b_r.ports["input"])
    route_single(c, cross_section=XS, port1=frontend.ports["b_green"], port2=sel_b_g.ports["input"])
    route_single(c, cross_section=XS, port1=frontend.ports["b_blue"], port2=sel_b_b.ports["input"])

    # Combiner for B
    comb_b = c << wavelength_combiner(n_inputs=3, name=f"comb_b_{uid}")
    comb_b.dmove((280, -50))

    route_single(c, cross_section=XS, port1=sel_b_r.ports["output"], port2=comb_b.ports["in1"])
    route_single(c, cross_section=XS, port1=sel_b_g.ports["output"], port2=comb_b.ports["in2"])
    route_single(c, cross_section=XS, port1=sel_b_b.ports["output"], port2=comb_b.ports["in3"])

    # =========================
    # 4. OPERATION COMBINER (A + B)
    # =========================
    op_combiner = c << gf.components.mmi2x2()
    op_combiner.dmove((380, -10))

    route_single(c, cross_section=XS, port1=comb_a.ports["output"], port2=op_combiner.ports["o1"])
    route_single(c, cross_section=XS, port1=comb_b.ports["output"], port2=op_combiner.ports["o2"])

    # =========================
    # 5. OPTICAL CARRY CHAIN
    # =========================
    carry_unit = c << optical_carry_unit(name=f"carry_{uid}", uid=uid)
    carry_unit.dmove((420, -10))

    # Route operation combiner output to carry unit signal input
    route_single(c, cross_section=XS, port1=op_combiner.ports["o3"], port2=carry_unit.ports["signal_in"])

    # =========================
    # 6. MIXER (operation-dependent)
    # =========================
    if operation == 'add':
        mixer = c << sfg_mixer(length=20, name=f"sfg_mixer_{uid}")
        op_label = "ADD_SFG"
    elif operation == 'sub':
        mixer = c << dfg_mixer(length=25, name=f"dfg_mixer_{uid}")
        op_label = "SUB_DFG"
    elif operation == 'mul':
        mixer = c << mul_mixer(length=30, name=f"mul_mixer_{uid}")
        op_label = "MUL_KERR"
    else:
        raise ValueError(f"Unknown operation '{operation}'")

    mixer.dmove((520, -10))

    # Route carry unit to mixer and back
    route_single(c, cross_section=XS, port1=carry_unit.ports["to_mixer"], port2=mixer.ports["input"])
    route_single(c, cross_section=XS, port1=mixer.ports["output"], port2=carry_unit.ports["from_mixer"])

    # =========================
    # 7. OUTPUT STAGE (5 detectors)
    # =========================
    output = c << ternary_output_stage_simple(name=f"output_{uid}", uid=uid)
    output.dmove((700, -10))

    route_single(c, cross_section=XS, port1=carry_unit.ports["to_detectors"], port2=output.ports["input"])

    # =========================
    # 8. LABELS AND PORTS
    # =========================
    c.add_label(f"ALU_OPTICAL_CARRY_{op_label}", position=(400, 100), layer=LABEL_LAYER)
    c.add_label("LASER_IN", position=(-20, 0), layer=LABEL_LAYER)

    # External ports
    c.add_port(name="laser_in", port=frontend.ports["laser_in"])

    # Carry chain ports (connect to adjacent trits)
    c.add_port(name="carry_in_pos", port=carry_unit.ports["carry_in_pos"])
    c.add_port(name="carry_in_neg", port=carry_unit.ports["carry_in_neg"])
    c.add_port(name="carry_out_pos", port=carry_unit.ports["carry_out_pos"])
    c.add_port(name="carry_out_neg", port=carry_unit.ports["carry_out_neg"])

    # Pump laser ports for OPA (external pump sources needed)
    c.add_port(name="pump_in_pos", port=carry_unit.ports["pump_in_pos"])
    c.add_port(name="pump_in_neg", port=carry_unit.ports["pump_in_neg"])
    c.add_port(name="pump_out_pos", port=carry_unit.ports["pump_out_pos"])
    c.add_port(name="pump_out_neg", port=carry_unit.ports["pump_out_neg"])

    return c


def generate_81_trit_processor(
    name: str = "Ternary81"
) -> gf.Component:
    """
    Generates the optimal 81-trit (3^4) ternary processor.

    Architecture:
      - 81 trits = 128-bit equivalent
      - Organized as 9×9 grid of nonads (9-trit units)
      - Each nonad contains 3 trytes (3-trit units)
      - Hierarchical: 81 = 3 × 27 = 9 × 9 = 27 × 3

    Layout:
      +---------------------------+
      | Nonad | Nonad | Nonad |   Row 0 (trits 0-26)
      | 0-8   | 9-17  | 18-26 |
      +---------------------------+
      | Nonad | Nonad | Nonad |   Row 1 (trits 27-53)
      | 27-35 | 36-44 | 45-53 |
      +---------------------------+
      | Nonad | Nonad | Nonad |   Row 2 (trits 54-80)
      | 54-62 | 63-71 | 72-80 |
      +---------------------------+
    """
    import uuid
    c = gf.Component(name)

    # 81-trit processor organized as 3x3 grid of 27-trit "heptacosas"
    # Each heptacosa contains 3x3 = 9 trytes
    # Each tryte contains 3 trits

    x_spacing = 400  # Horizontal spacing between columns
    y_spacing = 200  # Vertical spacing between rows

    trit_index = 0

    # Create 3 rows of 3 heptacosas (27 trits each)
    for row in range(3):  # 3 heptacosas vertically
        for col in range(3):  # 3 nonads per heptacosa horizontally
            for sub in range(3):  # 3 trytes per nonad
                for trit in range(3):  # 3 trits per tryte
                    uid = str(uuid.uuid4())[:8]
                    alu = c << generate_ternary_alu(
                        operations=["add", "subtract", "multiply", "divide"],
                        name=f"ALU_t{trit_index}_{uid}"
                    )

                    # Position: spread across grid
                    x_pos = col * x_spacing + sub * 120
                    y_pos = row * (y_spacing * 9) + trit * y_spacing

                    alu.dmove((x_pos, y_pos))
                    trit_index += 1

    # Add hierarchical labels
    c.add_label("CPU_81T", position=(600, -100), layer=LABEL_LAYER)

    # Label the three 27-trit sections
    for row in range(3):
        y_label = row * (y_spacing * 9) + y_spacing * 4
        c.add_label(f"H{row}", position=(-100, y_label), layer=LABEL_LAYER)

    return c


def cascaded_splitter_1to9(
    name: str = "split_1to9",
    uid: str = ""
) -> gf.Component:
    """
    Creates a 1-to-9 splitter tree using cascaded 1x3 stages.

    Structure: 1 → 3 → 9
    """
    import uuid
    if not uid:
        uid = str(uuid.uuid4())[:8]

    c = gf.Component(name)

    # First stage: 1 to 3
    split1 = c << wavelength_splitter(n_outputs=3, name=f"s1_{uid}")
    split1.dmove((0, 0))

    # Second stage: 3 splitters, each 1 to 3
    outputs = []
    for i in range(3):
        split2 = c << wavelength_splitter(n_outputs=3, name=f"s2_{i}_{uid}")
        y_offset = (i - 1) * 80
        split2.dmove((80, y_offset))

        # Route from first stage
        route_single(c, cross_section=XS,
                    port1=split1.ports[f"out{i+1}"],
                    port2=split2.ports["input"])

        # Collect output ports
        for j in range(3):
            outputs.append((split2, f"out{j+1}", i * 3 + j))

    # Input port
    c.add_port(name="input", port=split1.ports["input"])

    # Output ports (9 total)
    for split2, port_name, idx in outputs:
        c.add_port(name=f"out{idx}", port=split2.ports[port_name])

    return c


def generate_complete_81_trit(
    name: str = "Ternary81_Complete",
    simplified_output: bool = True,
    operation: Literal['add', 'sub', 'mul'] = 'add',
    selector_type: Literal['ring', 'mzi'] = 'ring'
) -> gf.Component:
    """
    Generates a complete 81-trit processor with CENTERED optical frontend.

    Architecture:
      - Frontend at chip center for minimal signal degradation
      - Splitter trees radiate outward in all directions
      - 81 ALUs arranged in 9×9 grid around the center
      - 3×3 zone structure (9 zones × 9 ALUs each)

    Args:
        name: Component name.
        simplified_output: If True (default), uses single AWG demux per ALU.
                          Reduces component count by ~40% (405 fewer ring resonators).
                          If False, uses 5 ring filters per ALU (more precise).
        operation: The arithmetic operation to perform:
                   - 'add': Addition using SFG (Sum Frequency Generation)
                   - 'sub': Subtraction using DFG (Difference Frequency Generation)
                   - 'mul': Multiplication using Kerr effect (χ³ nonlinearity)
        selector_type: Type of wavelength selector to use:
                   - 'ring': Ring resonator (default, wavelength-selective)
                   - 'mzi': MZI switch (better extinction ratio, broader bandwidth,
                            more tolerant to fabrication variations, voltage-tuned)

    Signal flow:
      CW Laser → Kerr Clock → Y-Junction (center of chip)
                                  ├→ A splitter tree (radiates outward) → AWG_A → Sel_A → Comb_A ─┐
                                  │                                                                ├→ OpComb → Mixer → Output
                                  └→ B splitter tree (radiates outward) → AWG_B → Sel_B → Comb_B ─┘

    Mixer types by operation:
      - add: SFG mixer (λ_out = 1/(1/λ1 + 1/λ2))
      - sub: DFG mixer (λ_out = 1/(1/λ1 - 1/λ2))
      - mul: Kerr/χ³ mixer (sign multiplication)

    Selector types:
      - ring: Ring resonators (compact, wavelength-selective, but sensitive to fab)
      - mzi: MZI switches (better extinction, fab-tolerant, voltage-tuned, broader BW)

    Benefits of centered layout:
      - Reduces maximum path length by ~50%
      - Equalizes signal power across all ALUs
      - More symmetric power distribution
      - Lower total insertion loss

    This is the full chip ready for fabrication.
    """
    import uuid
    c = gf.Component(name)

    # Grid parameters
    zone_spacing = 1200      # Spacing between zone centers
    alu_spacing = 380        # Spacing between ALUs within a zone
    chip_center_x = 1500     # Center of chip X
    chip_center_y = 1500     # Center of chip Y

    # =========================
    # 1. CENTERED OPTICAL FRONTEND
    # =========================

    # 1a. Kerr resonator for timing (master clock) - at chip center
    clk = c << kerr_resonator(name="master_clk")
    clk.dmove((chip_center_x - 60, chip_center_y))

    c.add_label("LASER_IN", position=(chip_center_x - 100, chip_center_y), layer=LABEL_LAYER)
    c.add_label("MASTER_CLK", position=(chip_center_x - 60, chip_center_y + 30), layer=LABEL_LAYER)

    # 1b. Y-junction to split into A and B master paths
    ysplit_master = c << y_junction(name="master_ysplit")
    ysplit_master.dmove((chip_center_x, chip_center_y))

    route_single(c, cross_section=XS,
                port1=clk.ports["output"],
                port2=ysplit_master.ports["input"])

    # =========================
    # 2. ZONE-BASED SPLITTER TREES
    # =========================
    # Split into 9 zones (3×3), then each zone splits to 9 ALUs
    # Zone layout (centered on chip_center):
    #   Zone(0,2)  Zone(1,2)  Zone(2,2)   <- top row
    #   Zone(0,1)  Zone(1,1)  Zone(2,1)   <- middle row (center zone)
    #   Zone(0,0)  Zone(1,0)  Zone(2,0)   <- bottom row

    # 2a. First-stage A splitter (1→9 for zones)
    split_a_zones = c << cascaded_splitter_1to9(name="split_a_zones")
    split_a_zones.dmove((chip_center_x + 60, chip_center_y + 40))

    route_single(c, cross_section=XS,
                port1=ysplit_master.ports["out_a"],
                port2=split_a_zones.ports["input"])

    # 2b. First-stage B splitter (1→9 for zones)
    split_b_zones = c << cascaded_splitter_1to9(name="split_b_zones")
    split_b_zones.dmove((chip_center_x + 60, chip_center_y - 40))

    route_single(c, cross_section=XS,
                port1=ysplit_master.ports["out_b"],
                port2=split_b_zones.ports["input"])

    # =========================
    # 3. ZONES AND ALUs
    # =========================
    trit_index = 0

    # Iterate through 9 zones (3×3 arrangement)
    for zone_row in range(3):
        for zone_col in range(3):
            zone_idx = zone_row * 3 + zone_col
            zone_uid = str(uuid.uuid4())[:8]

            # Zone center position (offset from chip center)
            zone_center_x = chip_center_x + (zone_col - 1) * zone_spacing
            zone_center_y = chip_center_y + (zone_row - 1) * zone_spacing

            # 3a. Zone-level A splitter (1→9 for ALUs in this zone)
            split_a_alu = c << cascaded_splitter_1to9(name=f"split_a_z{zone_idx}_{zone_uid}")
            split_a_alu.dmove((zone_center_x - 150, zone_center_y + 30))

            route_single(c, cross_section=XS,
                        port1=split_a_zones.ports[f"out{zone_idx}"],
                        port2=split_a_alu.ports["input"])

            # 3b. Zone-level B splitter (1→9 for ALUs in this zone)
            split_b_alu = c << cascaded_splitter_1to9(name=f"split_b_z{zone_idx}_{zone_uid}")
            split_b_alu.dmove((zone_center_x - 150, zone_center_y - 30))

            route_single(c, cross_section=XS,
                        port1=split_b_zones.ports[f"out{zone_idx}"],
                        port2=split_b_alu.ports["input"])

            # Zone label
            c.add_label(f"ZONE_{zone_idx}", position=(zone_center_x - 100, zone_center_y + 150), layer=LABEL_LAYER)

            # 3c. Create 9 ALUs within this zone (3×3)
            for alu_row in range(3):
                for alu_col in range(3):
                    alu_idx = alu_row * 3 + alu_col
                    uid = str(uuid.uuid4())[:8]

                    # ALU position within zone
                    x_pos = zone_center_x + (alu_col - 1) * alu_spacing
                    y_pos = zone_center_y + (alu_row - 1) * alu_spacing * 0.8

                    # --- AWG for A (demux into R, G, B) ---
                    awg_a = c << awg_demux(name=f"awg_a_t{trit_index}_{uid}")
                    awg_a.dmove((x_pos, y_pos + 35))

                    route_single(c, cross_section=XS,
                                port1=split_a_alu.ports[f"out{alu_idx}"],
                                port2=awg_a.ports["input"])

                    # --- AWG for B (demux into R, G, B) ---
                    awg_b = c << awg_demux(name=f"awg_b_t{trit_index}_{uid}")
                    awg_b.dmove((x_pos, y_pos - 35))

                    route_single(c, cross_section=XS,
                                port1=split_b_alu.ports[f"out{alu_idx}"],
                                port2=awg_b.ports["input"])

                    # --- Selectors for A (R, G, B) ---
                    # Use MZI or ring based on selector_type parameter
                    if selector_type == 'mzi':
                        sel_a_r = c << wavelength_selector_mzi(wavelength_um=1.550, name=f"sel_a_r_t{trit_index}_{uid}")
                        sel_a_g = c << wavelength_selector_mzi(wavelength_um=1.216, name=f"sel_a_g_t{trit_index}_{uid}")
                        sel_a_b = c << wavelength_selector_mzi(wavelength_um=1.000, name=f"sel_a_b_t{trit_index}_{uid}")
                        # MZI needs more spacing (larger footprint)
                        sel_a_r.dmove((x_pos + 70, y_pos + 75))
                        sel_a_g.dmove((x_pos + 70, y_pos + 40))
                        sel_a_b.dmove((x_pos + 70, y_pos + 5))
                        comb_a_x_offset = 180  # Combiner further out for MZI
                    else:
                        sel_a_r = c << wavelength_selector(wavelength_um=1.550, name=f"sel_a_r_t{trit_index}_{uid}")
                        sel_a_g = c << wavelength_selector(wavelength_um=1.216, name=f"sel_a_g_t{trit_index}_{uid}")
                        sel_a_b = c << wavelength_selector(wavelength_um=1.000, name=f"sel_a_b_t{trit_index}_{uid}")
                        sel_a_r.dmove((x_pos + 70, y_pos + 60))
                        sel_a_g.dmove((x_pos + 70, y_pos + 35))
                        sel_a_b.dmove((x_pos + 70, y_pos + 10))
                        comb_a_x_offset = 140

                    route_single(c, cross_section=XS, port1=awg_a.ports["out_r"], port2=sel_a_r.ports["input"])
                    route_single(c, cross_section=XS, port1=awg_a.ports["out_g"], port2=sel_a_g.ports["input"])
                    route_single(c, cross_section=XS, port1=awg_a.ports["out_b"], port2=sel_a_b.ports["input"])

                    # --- Selectors for B (R, G, B) ---
                    if selector_type == 'mzi':
                        sel_b_r = c << wavelength_selector_mzi(wavelength_um=1.550, name=f"sel_b_r_t{trit_index}_{uid}")
                        sel_b_g = c << wavelength_selector_mzi(wavelength_um=1.216, name=f"sel_b_g_t{trit_index}_{uid}")
                        sel_b_b = c << wavelength_selector_mzi(wavelength_um=1.000, name=f"sel_b_b_t{trit_index}_{uid}")
                        # MZI needs more spacing
                        sel_b_r.dmove((x_pos + 70, y_pos - 5))
                        sel_b_g.dmove((x_pos + 70, y_pos - 40))
                        sel_b_b.dmove((x_pos + 70, y_pos - 75))
                        comb_b_x_offset = 180
                    else:
                        sel_b_r = c << wavelength_selector(wavelength_um=1.550, name=f"sel_b_r_t{trit_index}_{uid}")
                        sel_b_g = c << wavelength_selector(wavelength_um=1.216, name=f"sel_b_g_t{trit_index}_{uid}")
                        sel_b_b = c << wavelength_selector(wavelength_um=1.000, name=f"sel_b_b_t{trit_index}_{uid}")
                        sel_b_r.dmove((x_pos + 70, y_pos - 10))
                        sel_b_g.dmove((x_pos + 70, y_pos - 35))
                        sel_b_b.dmove((x_pos + 70, y_pos - 60))
                        comb_b_x_offset = 140

                    route_single(c, cross_section=XS, port1=awg_b.ports["out_r"], port2=sel_b_r.ports["input"])
                    route_single(c, cross_section=XS, port1=awg_b.ports["out_g"], port2=sel_b_g.ports["input"])
                    route_single(c, cross_section=XS, port1=awg_b.ports["out_b"], port2=sel_b_b.ports["input"])

                    # --- Combiner for A ---
                    comb_a = c << wavelength_combiner(n_inputs=3, name=f"comb_a_t{trit_index}_{uid}")
                    comb_a.dmove((x_pos + comb_a_x_offset, y_pos + 35))

                    route_single(c, cross_section=XS, port1=sel_a_r.ports["output"], port2=comb_a.ports["in1"])
                    route_single(c, cross_section=XS, port1=sel_a_g.ports["output"], port2=comb_a.ports["in2"])
                    route_single(c, cross_section=XS, port1=sel_a_b.ports["output"], port2=comb_a.ports["in3"])

                    # --- Combiner for B ---
                    comb_b = c << wavelength_combiner(n_inputs=3, name=f"comb_b_t{trit_index}_{uid}")
                    comb_b.dmove((x_pos + comb_b_x_offset, y_pos - 35))

                    route_single(c, cross_section=XS, port1=sel_b_r.ports["output"], port2=comb_b.ports["in1"])
                    route_single(c, cross_section=XS, port1=sel_b_g.ports["output"], port2=comb_b.ports["in2"])
                    route_single(c, cross_section=XS, port1=sel_b_b.ports["output"], port2=comb_b.ports["in3"])

                    # --- Operation Combiner (merges A and B) ---
                    op_comb = c << gf.components.mmi2x2()
                    op_comb.dmove((x_pos + 220, y_pos))

                    route_single(c, cross_section=XS, port1=comb_a.ports["output"], port2=op_comb.ports["o1"])
                    route_single(c, cross_section=XS, port1=comb_b.ports["output"], port2=op_comb.ports["o2"])

                    # --- Mixer (operation-dependent) ---
                    if operation == 'add':
                        # SFG mixer for addition
                        mixer = c << sfg_mixer(length=20, name=f"sfg_t{trit_index}_{uid}")
                    elif operation == 'sub':
                        # DFG mixer for subtraction
                        mixer = c << dfg_mixer(length=25, name=f"dfg_t{trit_index}_{uid}")
                    elif operation == 'mul':
                        # Kerr/χ³ mixer for multiplication
                        mixer = c << mul_mixer(length=30, name=f"mul_t{trit_index}_{uid}")
                    else:
                        raise ValueError(f"Unknown operation '{operation}'. Must be 'add', 'sub', or 'mul'.")

                    mixer.dmove((x_pos + 270, y_pos))

                    route_single(c, cross_section=XS, port1=op_comb.ports["o3"], port2=mixer.ports["input"])

                    # --- Output Stage (5-channel detector with carry ports) ---
                    if simplified_output:
                        output = c << ternary_output_stage_simple(
                            name=f"out_t{trit_index}_{uid}",
                            uid=uid,
                            include_carry_ports=True  # Enable carry chain wiring
                        )
                    else:
                        output = c << ternary_output_stage(name=f"out_t{trit_index}_{uid}", uid=uid)
                    output.dmove((x_pos + 320, y_pos))

                    route_single(c, cross_section=XS, port1=mixer.ports["output"], port2=output.ports["input"])

                    # --- ALU Label ---
                    c.add_label(f"T{trit_index}", position=(x_pos + 180, y_pos + 80), layer=LABEL_LAYER)

                    # --- Carry Chain Labels ---
                    # Label the carry signals for firmware wiring documentation
                    # These identify the electrical connections between adjacent trits
                    if trit_index > 0:
                        # Mark carry input from previous trit
                        c.add_label(f"CIN_T{trit_index}<-T{trit_index-1}",
                                   position=(x_pos + 305, y_pos + 10), layer=LABEL_LAYER)
                    if trit_index < 80:  # Not the MSB
                        # Mark carry outputs to next trit
                        c.add_label(f"COUT_T{trit_index}->T{trit_index+1}",
                                   position=(x_pos + 450, y_pos - 30), layer=LABEL_LAYER)

                    trit_index += 1

    # =========================
    # 4. CARRY CHAIN DOCUMENTATION
    # =========================
    # Add carry chain wiring guide at chip edge
    carry_doc_x = chip_center_x - zone_spacing - 200
    carry_doc_y = chip_center_y + zone_spacing + 100

    c.add_label("CARRY_CHAIN_WIRING:", position=(carry_doc_x, carry_doc_y), layer=LABEL_LAYER)
    c.add_label("T0->T1->T2->...->T80 (LSB to MSB)", position=(carry_doc_x, carry_doc_y - 20), layer=LABEL_LAYER)
    c.add_label("Wire: CARRY_OUT_POS[N] -> CARRY_IN[N+1] (positive carry)", position=(carry_doc_x, carry_doc_y - 40), layer=LABEL_LAYER)
    c.add_label("Wire: CARRY_OUT_NEG[N] -> CARRY_IN[N+1] (borrow)", position=(carry_doc_x, carry_doc_y - 60), layer=LABEL_LAYER)
    c.add_label("Firmware: Handle via GPIO or dedicated carry logic", position=(carry_doc_x, carry_doc_y - 80), layer=LABEL_LAYER)

    # =========================
    # 5. CHIP LABELS
    # =========================
    # Operation-specific label
    op_labels = {'add': 'ADD_SFG', 'sub': 'SUB_DFG', 'mul': 'MUL_KERR'}
    op_label = op_labels.get(operation, 'UNKNOWN')

    # Selector type label
    sel_label = 'MZI' if selector_type == 'mzi' else 'RING'

    c.add_label(f"81T_{op_label}_{sel_label}", position=(chip_center_x, chip_center_y + zone_spacing + 200), layer=LABEL_LAYER)
    c.add_label("9_ZONES_x_9_ALUs", position=(chip_center_x, chip_center_y + zone_spacing + 150), layer=LABEL_LAYER)
    c.add_label("WITH_CARRY_CHAIN", position=(chip_center_x, chip_center_y + zone_spacing + 100), layer=LABEL_LAYER)
    c.add_label(f"SELECTORS: {sel_label}", position=(chip_center_x, chip_center_y + zone_spacing + 50), layer=LABEL_LAYER)
    c.add_label("FRONTEND_CENTER", position=(chip_center_x, chip_center_y - 80), layer=LABEL_LAYER)

    # Add master clock port
    c.add_port(name="laser_in", port=clk.ports["input"])

    return c


def generate_power_of_3_processor(
    power: int = 4,
    name: str = None
) -> gf.Component:
    """
    Generates a processor with 3^power trits.

    Args:
        power: The exponent (1=3, 2=9, 3=27, 4=81, 5=243)
        name: Optional custom name

    Common configurations:
      - power=1:   3 trits (tryte)
      - power=2:   9 trits (nonad)
      - power=3:  27 trits (heptacosa)
      - power=4:  81 trits (optimal word)
      - power=5: 243 trits (vector/SIMD)
    """
    n_trits = 3 ** power
    if name is None:
        name = f"Ternary3pow{power}"

    if power <= 3:
        # Small processors: linear layout
        return generate_full_processor(n_trits=n_trits, name=name)
    elif power == 4:
        # 81-trit: use optimized layout
        return generate_81_trit_processor(name=name)
    else:
        # Large processors: would need tiled layout
        # For now, use linear (will be very large)
        return generate_full_processor(n_trits=n_trits, name=name)


# =============================================================================
# 81-TRIT PROCESSOR WITH FULLY OPTICAL CARRY CHAIN
# =============================================================================

def generate_81_trit_optical_carry(
    name: str = "Ternary81_OpticalCarry",
    operation: Literal['add', 'sub', 'mul'] = 'add'
) -> gf.Component:
    """
    Generates a complete 81-trit processor with FULLY OPTICAL carry propagation.

    This is the ultimate "ask and answer" computer:
    - Computer loads operands A and B (sets wavelength selectors)
    - Light propagates through all 81 trits
    - Optical carry chain handles all arithmetic overflow automatically
    - Computer reads 81 detector outputs

    NO FIRMWARE MATH - all logic is optical.

    Architecture:
    - Centered frontend (Kerr clock + Y-junction)
    - 81 optical carry ALUs arranged in 9×9 grid
    - Carry chain: Trit[n].carry_out → OPA → Delay → Trit[n+1].carry_in
    - LSB (Trit 0) has no carry_in, MSB (Trit 80) carry_out goes to overflow detector

    Timing:
    - Each trit adds ~10ps delay for carry propagation
    - Total propagation time: ~800ps for 81 trits
    - Clock rate: ~1 GHz for pipelined operation

    Args:
        name: Component name
        operation: 'add', 'sub', or 'mul'
    """
    import uuid
    c = gf.Component(name)

    # Grid parameters
    alu_spacing_x = 800   # Wider for optical carry components
    alu_spacing_y = 200
    chip_center_x = 4000
    chip_center_y = 2000

    # Store ALU references for carry routing
    alus = []

    # =========================
    # 1. MASTER CLOCK AND SPLITTER
    # =========================
    clk = c << kerr_resonator(name="master_clk")
    clk.dmove((chip_center_x - 200, chip_center_y))
    c.add_label("LASER_IN", position=(chip_center_x - 250, chip_center_y), layer=LABEL_LAYER)

    # Master splitter (1→81 via cascaded splits)
    # Using 3-stage: 1→9→81
    master_split = c << cascaded_splitter_1to9(name="master_1to9")
    master_split.dmove((chip_center_x - 100, chip_center_y))
    route_single(c, cross_section=XS, port1=clk.ports["output"], port2=master_split.ports["input"])

    # =========================
    # 2. CREATE 81 OPTICAL CARRY ALUs
    # =========================
    # Arrange in 9 rows × 9 columns
    # Carry flows: row-major order (left to right, bottom to top)

    trit_index = 0
    for row in range(9):
        for col in range(9):
            uid = str(uuid.uuid4())[:8]

            # Create optical carry ALU
            alu = c << optical_carry_unit(name=f"carry_unit_t{trit_index}_{uid}", uid=uid)

            # Position
            x_pos = (col - 4) * alu_spacing_x + chip_center_x
            y_pos = (row - 4) * alu_spacing_y + chip_center_y

            alu.dmove((x_pos, y_pos))
            alus.append(alu)

            # Create mixer based on operation
            if operation == 'add':
                mixer = c << sfg_mixer(length=20, name=f"sfg_t{trit_index}_{uid}")
            elif operation == 'sub':
                mixer = c << dfg_mixer(length=25, name=f"dfg_t{trit_index}_{uid}")
            else:  # mul
                mixer = c << mul_mixer(length=30, name=f"mul_t{trit_index}_{uid}")

            mixer.dmove((x_pos + 100, y_pos))

            # Route carry unit to mixer
            route_single(c, cross_section=XS, port1=alu.ports["to_mixer"], port2=mixer.ports["input"])
            route_single(c, cross_section=XS, port1=mixer.ports["output"], port2=alu.ports["from_mixer"])

            # Output stage
            output = c << ternary_output_stage_simple(name=f"out_t{trit_index}_{uid}", uid=uid)
            output.dmove((x_pos + 200, y_pos))
            route_single(c, cross_section=XS, port1=alu.ports["to_detectors"], port2=output.ports["input"])

            # Trit label
            c.add_label(f"T{trit_index}", position=(x_pos, y_pos + 50), layer=LABEL_LAYER)

            trit_index += 1

    # =========================
    # 3. OPTICAL CARRY CHAIN ROUTING
    # =========================
    # Connect carry_out of each trit to carry_in of next trit

    for i in range(80):  # 0 to 79 (80 connections for 81 trits)
        # Route positive carry
        route_single(c, cross_section=XS,
                    port1=alus[i].ports["carry_out_pos"],
                    port2=alus[i+1].ports["carry_in_pos"])

        # Route negative carry (borrow)
        route_single(c, cross_section=XS,
                    port1=alus[i].ports["carry_out_neg"],
                    port2=alus[i+1].ports["carry_in_neg"])

    # =========================
    # 4. TERMINATIONS
    # =========================
    # LSB (Trit 0): No carry in - terminate with dummy load
    c.add_label("LSB_NO_CARRY_IN", position=(alus[0].dxmin - 50, alus[0].dymin), layer=LABEL_LAYER)

    # MSB (Trit 80): Carry out goes to overflow detector
    overflow_det = c << photodetector(name="overflow_detector")
    overflow_det.dmove((alus[80].dxmax + 50, alus[80].dy))
    c.add_label("MSB_OVERFLOW", position=(alus[80].dxmax + 50, alus[80].dy + 20), layer=LABEL_LAYER)

    # =========================
    # 5. CHIP LABELS
    # =========================
    op_names = {'add': 'ADD', 'sub': 'SUB', 'mul': 'MUL'}
    c.add_label(f"81T_OPTICAL_CARRY_{op_names[operation]}", position=(chip_center_x, chip_center_y + 1000), layer=LABEL_LAYER)
    c.add_label("FULLY_OPTICAL_ARITHMETIC", position=(chip_center_x, chip_center_y + 950), layer=LABEL_LAYER)
    c.add_label("NO_FIRMWARE_MATH", position=(chip_center_x, chip_center_y + 900), layer=LABEL_LAYER)

    # Carry chain info
    c.add_label("CARRY_CHAIN: T0→T1→T2→...→T80", position=(chip_center_x - 500, chip_center_y - 1000), layer=LABEL_LAYER)
    c.add_label("Propagation: ~800ps total", position=(chip_center_x - 500, chip_center_y - 1050), layer=LABEL_LAYER)

    return c


# =============================================================================
# INTERACTIVE GENERATOR
# =============================================================================

def interactive_generator():
    """
    Interactive CLI for generating chips.
    """
    print("\n" + "="*60)
    print("  TERNARY OPTICAL CHIP GENERATOR")
    print("  Wavelength-Division Ternary Computer")
    print("="*60)

    print("\nAvailable chip templates:")
    print("  1. Ternary Adder (A + B)")
    print("  2. Ternary Subtractor (A - B)")
    print("  3. Ternary Multiplier (A × B)")
    print("  4. Ternary Divider (A ÷ B)")
    print("  5. Single ALU (configurable)")
    print("  6. Full N-trit Processor")
    print("  7. Power-of-3 Processor (3^N trits)")
    print("  8. 81-Trit Processor (3^4 - optimal)")
    print("  9. Custom component")
    print(" 10. COMPLETE ALU (frontend + ALU + output)")
    print(" 11. FULL 81-TRIT CHIP (complete with frontend) [RECOMMENDED]")

    choice = input("\nSelect template (1-11): ").strip()

    if choice == "1":
        chip = generate_ternary_adder()
        chip_name = "ternary_adder"
    elif choice == "2":
        chip = generate_ternary_subtractor()
        chip_name = "ternary_subtractor"
    elif choice == "3":
        chip = generate_ternary_multiplier()
        chip_name = "ternary_multiplier"
    elif choice == "4":
        chip = generate_ternary_divider()
        chip_name = "ternary_divider"
    elif choice == "5":
        ops = input("Operations (comma-separated, e.g., add,subtract,multiply,divide): ").strip().split(",")
        chip = generate_ternary_alu(operations=[o.strip() for o in ops])
        chip_name = "ternary_alu"
    elif choice == "6":
        n = int(input("Number of trits (e.g., 3): ").strip())
        chip = generate_full_processor(n_trits=n)
        chip_name = f"ternary_processor_{n}trit"
    elif choice == "7":
        print("\nPower-of-3 options:")
        print("  1: 3^1 =   3 trits (tryte)")
        print("  2: 3^2 =   9 trits (nonad)")
        print("  3: 3^3 =  27 trits (heptacosa)")
        print("  4: 3^4 =  81 trits (optimal) [RECOMMENDED]")
        print("  5: 3^5 = 243 trits (vector)")
        p = int(input("Enter power (1-5): ").strip())
        print(f"Generating 3^{p} = {3**p} trit processor...")
        chip = generate_power_of_3_processor(power=p)
        chip_name = f"ternary_3pow{p}_{3**p}trit"
    elif choice == "8":
        print("Generating 81-trit (3^4) optimal processor...")
        print("This is the recommended architecture for ternary computing.")
        print("128-bit equivalent | 4.4 × 10^38 values")
        chip = generate_81_trit_processor()
        chip_name = "ternary_81trit_optimal"
    elif choice == "10":
        print("Generating COMPLETE ALU with optical frontend...")
        print("  Laser → Kerr Clock → Y-Split → AWGs → Selectors → Mixer → 3-channel Output")
        print("\nSelector type:")
        print("  1. Ring resonator (default, compact)")
        print("  2. MZI switch (better extinction, fab-tolerant)")
        sel_choice = input("Select (1/2): ").strip()
        sel_type = 'mzi' if sel_choice == "2" else 'ring'
        chip = generate_complete_alu(selector_type=sel_type)
        chip_name = f"ternary_complete_alu_{sel_type}"
    elif choice == "11":
        print("Generating FULL 81-TRIT CHIP...")
        print("  Master clock + 9×9 grid of complete ALUs")
        print("\nSelector type:")
        print("  1. Ring resonator (default, compact)")
        print("  2. MZI switch (better extinction, fab-tolerant)")
        sel_choice = input("Select (1/2): ").strip()
        sel_type = 'mzi' if sel_choice == "2" else 'ring'
        print("  This may take a moment...")
        chip = generate_complete_81_trit(selector_type=sel_type)
        chip_name = f"ternary_81trit_full_{sel_type}"
    elif choice == "9":
        print("\nCustom components:")
        print("  a. Wavelength Selector (ring resonator)")
        print("  b. SFG Mixer (addition/multiply)")
        print("  c. DFG Divider (subtraction/divide)")
        print("  d. Wavelength Inverter (negation)")
        print("  e. Combiner")
        print("  f. Splitter")
        print("  g. Photodetector")
        print("  h. Kerr Resonator (optical clock)")
        print("  i. Y-Junction (beam splitter)")
        print("  j. AWG Demux (wavelength separator)")
        print("  k. Optical Frontend (complete input stage)")
        print("  l. MZI Switch (Mach-Zehnder interferometer)")
        print("  m. MZI Wavelength Selector (MZI-based gating)")
        sub = input("Select (a-m): ").strip().lower()

        if sub == "a":
            wvl = float(input("Wavelength (μm, e.g., 1.55): "))
            chip = wavelength_selector(wavelength_um=wvl)
            chip_name = f"selector_{wvl}um"
        elif sub == "b":
            chip = sfg_mixer()
            chip_name = "sfg_mixer"
        elif sub == "c":
            chip = dfg_divider()
            chip_name = "dfg_divider"
        elif sub == "d":
            chip = wavelength_inverter()
            chip_name = "wavelength_inverter"
        elif sub == "e":
            chip = wavelength_combiner()
            chip_name = "combiner"
        elif sub == "f":
            chip = wavelength_splitter()
            chip_name = "splitter"
        elif sub == "g":
            chip = photodetector()
            chip_name = "photodetector"
        elif sub == "h":
            chip = kerr_resonator()
            chip_name = "kerr_clock"
        elif sub == "i":
            chip = y_junction()
            chip_name = "y_junction"
        elif sub == "j":
            chip = awg_demux()
            chip_name = "awg_demux"
        elif sub == "k":
            print("Generating complete optical frontend...")
            print("  Kerr resonator (clock) -> Y-junction -> 2x AWG demux")
            chip = optical_frontend()
            chip_name = "optical_frontend"
        elif sub == "l":
            print("Generating MZI Switch...")
            print("  Two 3dB couplers + phase shifter arms")
            print("  Better extinction ratio than ring resonators")
            chip = mzi_switch()
            chip_name = "mzi_switch"
        elif sub == "m":
            wvl = float(input("Wavelength (μm, e.g., 1.55): "))
            print("Generating MZI Wavelength Selector...")
            print("  MZI switch with wavelength label")
            chip = wavelength_selector_mzi(wavelength_um=wvl)
            chip_name = f"mzi_selector_{wvl}um"
        else:
            print("Invalid selection")
            return
    else:
        print("Invalid selection")
        return

    # Save and show
    import os
    import subprocess
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data', 'gds')
    os.makedirs(data_dir, exist_ok=True)

    gds_path = os.path.join(data_dir, f"{chip_name}.gds")
    chip.write(gds_path)
    print(f"\nGDS file saved to: {gds_path}")

    # Show in KLayout
    show = input("Open in KLayout? (y/n): ").strip().lower()
    if show == "y":
        print("Opening KLayout...")
        subprocess.Popen(["klayout", gds_path])
        print("KLayout launched!")

    return chip


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    interactive_generator()
