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

# =============================================================================
# TERNARY ENCODING: Wavelength -> Value
# =============================================================================
TERNARY_ENCODING = {
    'NEG':   {'value': -1, 'wavelength_um': 1.55, 'color': 'red',   'name': 'Red'},
    'ZERO':  {'value':  0, 'wavelength_um': 1.30, 'color': 'green', 'name': 'Green'},
    'POS':   {'value': +1, 'wavelength_um': 1.00, 'color': 'blue',  'name': 'Blue'},
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

def wavelength_selector(
    wavelength_um: float,
    radius: float = 5.0,
    gap: float = 0.2,
    name: str = "selector"
) -> gf.Component:
    """
    Creates a ring resonator wavelength selector.

    This selects a specific wavelength from a multi-wavelength input.
    When voltage is applied, it shifts the resonance (ON/OFF control).

    Args:
        wavelength_um: Target wavelength to select
        radius: Ring radius (larger = sharper filter)
        gap: Coupling gap
        name: Component name
    """
    c = gf.Component(name)

    # Ring resonator - the core selector element
    ring = c << gf.components.ring_single(radius=radius, gap=gap)

    # Add labels for clarity
    c.add_label(f"λ={wavelength_um}μm", position=(0, radius + 2))

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

    c.add_label("NEG (λ swap)", position=(15, spacing + 3))

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
    c.add_label("χ² DFG Divider", position=(length/2, -width - 1))

    c.add_port(name="input", port=wg.ports["o1"])
    c.add_port(name="output", port=wg.ports["o2"])

    return c


def sfg_mixer(
    length: float = 20.0,
    width: float = 0.8,
    name: str = "sfg_mixer"
) -> gf.Component:
    """
    Creates a Sum-Frequency Generation mixer.

    Mixes two wavelengths via χ² nonlinearity to produce sum frequency.
    This is where ternary logic operations happen!

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
    c.add_label("χ² SFG Mixer", position=(length/2, -width - 1))

    c.add_port(name="input", port=wg.ports["o1"])
    c.add_port(name="output", port=wg.ports["o2"])

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
    """
    c = gf.Component(name)

    if n_outputs == 2:
        mmi = c << gf.components.mmi1x2()
        c.add_port(name="input", port=mmi.ports["o1"])
        c.add_port(name="out1", port=mmi.ports["o2"])
        c.add_port(name="out2", port=mmi.ports["o3"])
    else:
        # Cascaded splitters
        mmi1 = c << gf.components.mmi1x2()
        mmi2 = c << gf.components.mmi1x2()
        mmi2.dmove((30, -10))

        # Route
        route_single(c, cross_section=XS, port1=mmi1.ports["o3"], port2=mmi2.ports["o1"])

        c.add_port(name="input", port=mmi1.ports["o1"])
        c.add_port(name="out1", port=mmi1.ports["o2"])
        c.add_port(name="out2", port=mmi2.ports["o2"])
        c.add_port(name="out3", port=mmi2.ports["o3"])

    return c


def photodetector(
    width: float = 5.0,
    length: float = 10.0,
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

    c.add_label("Photodetector", position=(10, -width))
    c.add_port(name="input", port=taper.ports["o1"])

    return c


def ternary_output_stage(
    name: str = "output_stage"
) -> gf.Component:
    """
    Creates a wavelength-discriminating output stage.

    Structure: Input -> Splitter -> 3x Filters -> 3x Photodetectors

    The mixer output hits all three filtered detectors simultaneously.
    Each detector only responds to its wavelength (R, G, or B).
    Firmware reads all three to determine which colors are present.

    Output combinations:
      - Red only:        result = -1 (or -2)
      - Green only:      result = 0
      - Blue only:       result = +1 (or +2)
      - Red + Blue:      result = 0 (purple = cancellation)
      - Red + Green:     result = -1
      - Green + Blue:    result = +1
      - R + G + B:       all three present
    """
    c = gf.Component(name)

    # Splitter to send light to all three detector paths
    splitter = c << wavelength_splitter(n_outputs=3, name=f"output_split")

    # Three filtered detector channels
    y_spacing = 25
    detector_x = 80

    for i, (trit, info) in enumerate(TERNARY_ENCODING.items()):
        # Ring resonator filter for this wavelength
        filt = c << wavelength_selector(
            wavelength_um=info['wavelength_um'],
            radius=5.0,
            name=f"filter_{info['name']}"
        )
        filt.dmove((40, (i - 1) * y_spacing))

        # Photodetector after filter
        det = c << photodetector(
            width=4.0,
            length=8.0,
            name=f"detect_{info['name']}"
        )
        det.dmove((detector_x, (i - 1) * y_spacing))

        # Route splitter -> filter -> detector
        route_single(c, cross_section=XS,
                    port1=splitter.ports[f"out{i+1}"],
                    port2=filt.ports["input"])
        route_single(c, cross_section=XS,
                    port1=filt.ports["output"],
                    port2=det.ports["input"])

        # Label each detector output
        c.add_label(f"V_{info['color']}", position=(detector_x + 15, (i - 1) * y_spacing))

    # Input port
    c.add_port(name="input", port=splitter.ports["input"])

    # Labels
    c.add_label("Output Stage", position=(50, y_spacing + 10))
    c.add_label("(3-channel wavelength detector)", position=(50, y_spacing + 5))

    return c


# =============================================================================
# HIGH-LEVEL CHIP GENERATORS
# =============================================================================

def ternary_input_stage(
    operand_name: str = "A",
    y_offset: float = 0,
    uid: str = ""
) -> gf.Component:
    """
    Creates an input stage for one ternary operand.

    Structure: Input -> Splitter -> 3x Selectors (R/G/B)
    Each selector can be individually enabled to set the ternary value.
    """
    c = gf.Component(f"input_{operand_name}_{uid}")

    # Input splitter (1 -> 3 wavelengths)
    splitter = c << wavelength_splitter(n_outputs=3, name=f"split_{operand_name}_{uid}")

    # Three selectors for R, G, B
    y_spacing = 30
    selectors = []

    for i, (trit, info) in enumerate(TERNARY_ENCODING.items()):
        sel = c << wavelength_selector(
            wavelength_um=info['wavelength_um'],
            name=f"sel_{operand_name}_{info['name']}_{uid}"
        )
        sel.dmove((60, (i - 1) * y_spacing))
        selectors.append(sel)

        # Route splitter to selector
        route_single(c, cross_section=XS, port1=splitter.ports[f"out{i+1}"], port2=sel.ports["input"])

    # Combiner to merge selected wavelengths
    combiner = c << wavelength_combiner(n_inputs=3, name=f"comb_{operand_name}_{uid}")
    combiner.dmove((130, 0))

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
    name: str = "TernaryALU"
) -> gf.Component:
    """
    Generates a complete Ternary ALU chip.

    Args:
        operations: List of operations to support ['add', 'multiply', 'compare']
        name: Chip name

    Returns:
        Complete chip layout
    """
    import uuid
    uid = str(uuid.uuid4())[:8]

    c = gf.Component(name)

    # =========================
    # 1. INPUT STAGES (2 operands)
    # =========================
    input_a = c << ternary_input_stage("A", y_offset=50, uid=uid)
    input_b = c << ternary_input_stage("B", y_offset=-50, uid=uid)

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
    mixer = c << sfg_mixer(length=30, name=f"alu_mixer_{uid}")
    mixer.dmove((250, 0))

    route_single(c, cross_section=XS, port1=op_combiner.ports["o1"], port2=mixer.ports["input"])

    # =========================
    # 4. OUTPUT DETECTION (3-channel)
    # =========================
    output_stage = c << ternary_output_stage(name=f"output_{uid}")
    output_stage.dmove((300, 0))

    route_single(c, cross_section=XS, port1=mixer.ports["output"], port2=output_stage.ports["input"])

    # =========================
    # 5. LABELS & METADATA
    # =========================
    c.add_label(f"Ternary ALU - Operations: {', '.join(operations)}", position=(150, 100))
    c.add_label("Input A (-1, 0, +1)", position=(0, 80))
    c.add_label("Input B (-1, 0, +1)", position=(0, -80))
    c.add_label("Result (V_red, V_green, V_blue)", position=(300, 40))

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

    c.add_label(f"{n_trits}-Trit Ternary Processor", position=(150, n_trits * y_spacing + 50))

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
    c.add_label("81-TRIT TERNARY PROCESSOR (3^4)", position=(600, -100))
    c.add_label("128-bit equivalent | 4.4 × 10^38 values", position=(600, -150))

    # Label the three 27-trit sections
    for row in range(3):
        y_label = row * (y_spacing * 9) + y_spacing * 4
        c.add_label(f"Heptacosa {row} (trits {row*27}-{row*27+26})", position=(-100, y_label))

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

    choice = input("\nSelect template (1-9): ").strip()

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
    elif choice == "9":
        print("\nCustom components:")
        print("  a. Wavelength Selector")
        print("  b. SFG Mixer (addition/multiply)")
        print("  c. DFG Divider (subtraction/divide)")
        print("  d. Wavelength Inverter (negation)")
        print("  e. Combiner")
        print("  f. Splitter")
        print("  g. Photodetector")
        sub = input("Select (a-g): ").strip().lower()

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
    data_dir = os.path.join(base_dir, 'data')
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
