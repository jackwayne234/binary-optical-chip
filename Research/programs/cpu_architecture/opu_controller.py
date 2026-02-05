#!/usr/bin/env python3
"""
OPU Controller (Optical Processing Unit Controller)

The "brain" of the ternary optical computer that enables autonomous operation.
Takes high-level commands from the host CPU and orchestrates the optical ALU,
RAM tiers, and IOA adapters.

Architecture:
    ┌─────────────────────────────────────────────────────────────────────┐
    │                        OPU CONTROLLER                                │
    │                                                                      │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
    │  │   Command    │  │  Instruction │  │   Program    │               │
    │  │    Queue     │─▶│   Decoder    │─▶│   Counter    │               │
    │  │  (from CPU)  │  │  (ternary)   │  │  (81-trit)   │               │
    │  └──────────────┘  └──────┬───────┘  └──────────────┘               │
    │                           │                                          │
    │         ┌─────────────────┼─────────────────┐                        │
    │         │                 │                 │                        │
    │         ▼                 ▼                 ▼                        │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
    │  │   Branch     │  │  Sequencer   │  │  Register    │               │
    │  │  Predictor   │  │  (multi-op)  │  │  Allocator   │               │
    │  │  (3-way!)    │  │              │  │  (tiers)     │               │
    │  └──────────────┘  └──────────────┘  └──────────────┘               │
    │                           │                                          │
    │         ┌─────────────────┼─────────────────┐                        │
    │         │                 │                 │                        │
    │         ▼                 ▼                 ▼                        │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
    │  │  Interrupt   │  │    ALU       │  │    DMA       │               │
    │  │  Controller  │  │  Interface   │  │  Controller  │               │
    │  │  (IOA events)│  │              │  │              │               │
    │  └──────────────┘  └──────────────┘  └──────────────┘               │
    │                           │                                          │
    └───────────────────────────┼──────────────────────────────────────────┘
                                │
                                ▼
                    To IOC (Encode/Decode) and Optical ALU

Key Features:
- Ternary instruction set (3-way branching, balanced arithmetic)
- 81-trit program counter and registers
- Multi-cycle operation sequencing
- Autonomous DMA for bulk data movement
- Interrupt-driven IOA event handling

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

LAYER_METAL1: LayerSpec = (12, 0)        # Signal routing
LAYER_METAL2: LayerSpec = (20, 0)        # Power/ground
LAYER_LOGIC: LayerSpec = (40, 0)         # Logic blocks
LAYER_REG: LayerSpec = (41, 0)           # Register files
LAYER_CACHE: LayerSpec = (42, 0)         # Cache/queue memory
LAYER_CTRL: LayerSpec = (43, 0)          # Control logic
LAYER_PRED: LayerSpec = (44, 0)          # Predictor logic
LAYER_SEQ: LayerSpec = (45, 0)           # Sequencer
LAYER_INT: LayerSpec = (46, 0)           # Interrupt controller
LAYER_PAD: LayerSpec = (22, 0)           # Bond pads
LAYER_TEXT: LayerSpec = (100, 0)         # Labels

# =============================================================================
# Ternary Instruction Set Architecture
# =============================================================================

# Ternary opcodes (using balanced ternary: -1, 0, +1)
TERNARY_ISA = {
    # Arithmetic (opcode prefix: -1)
    'ADD':  {'opcode': (-1, -1, -1), 'cycles': 1, 'desc': 'Add two 81-trit values'},
    'SUB':  {'opcode': (-1, -1,  0), 'cycles': 1, 'desc': 'Subtract'},
    'MUL':  {'opcode': (-1, -1, +1), 'cycles': 3, 'desc': 'Multiply (log-domain)'},
    'DIV':  {'opcode': (-1,  0, -1), 'cycles': 5, 'desc': 'Divide (log-domain)'},
    'NEG':  {'opcode': (-1,  0,  0), 'cycles': 1, 'desc': 'Negate (flip wavelength)'},
    'ABS':  {'opcode': (-1,  0, +1), 'cycles': 1, 'desc': 'Absolute value'},

    # Logic (opcode prefix: 0)
    'AND':  {'opcode': (0, -1, -1), 'cycles': 1, 'desc': 'Ternary AND (min)'},
    'OR':   {'opcode': (0, -1,  0), 'cycles': 1, 'desc': 'Ternary OR (max)'},
    'NOT':  {'opcode': (0, -1, +1), 'cycles': 1, 'desc': 'Ternary NOT'},
    'XOR':  {'opcode': (0,  0, -1), 'cycles': 1, 'desc': 'Ternary XOR'},
    'CMP':  {'opcode': (0,  0,  0), 'cycles': 1, 'desc': 'Compare (sets flags)'},
    'TST':  {'opcode': (0,  0, +1), 'cycles': 1, 'desc': 'Test (check zero)'},

    # Control Flow (opcode prefix: +1)
    'JMP':  {'opcode': (+1, -1, -1), 'cycles': 2, 'desc': 'Unconditional jump'},
    'BRN':  {'opcode': (+1, -1,  0), 'cycles': 2, 'desc': 'Branch if negative'},
    'BRZ':  {'opcode': (+1, -1, +1), 'cycles': 2, 'desc': 'Branch if zero'},
    'BRP':  {'opcode': (+1,  0, -1), 'cycles': 2, 'desc': 'Branch if positive'},
    'BR3':  {'opcode': (+1,  0,  0), 'cycles': 2, 'desc': '3-way branch (ternary!)'},
    'CALL': {'opcode': (+1,  0, +1), 'cycles': 3, 'desc': 'Call subroutine'},
    'RET':  {'opcode': (+1, +1, -1), 'cycles': 2, 'desc': 'Return from subroutine'},

    # Memory (opcode prefix: +1, +1)
    'LD1':  {'opcode': (+1, +1,  0), 'cycles': 2, 'desc': 'Load from Tier 1 (hot)'},
    'ST1':  {'opcode': (+1, +1, +1), 'cycles': 2, 'desc': 'Store to Tier 1'},
    'LD2':  {'opcode': (-1, +1, -1), 'cycles': 4, 'desc': 'Load from Tier 2 (working)'},
    'ST2':  {'opcode': (-1, +1,  0), 'cycles': 4, 'desc': 'Store to Tier 2'},
    'LD3':  {'opcode': (-1, +1, +1), 'cycles': 8, 'desc': 'Load from Tier 3 (parking)'},
    'ST3':  {'opcode': (0, +1, -1), 'cycles': 8, 'desc': 'Store to Tier 3'},
    'DMA':  {'opcode': (0, +1,  0), 'cycles': 1, 'desc': 'Initiate DMA transfer'},

    # System
    'NOP':  {'opcode': (0, +1, +1), 'cycles': 1, 'desc': 'No operation'},
    'HALT': {'opcode': (-1, -1, -1, -1), 'cycles': 1, 'desc': 'Halt processor'},
    'INT':  {'opcode': (0,  0, -1, -1), 'cycles': 3, 'desc': 'Software interrupt'},
}


# =============================================================================
# COMMAND QUEUE
# =============================================================================

@gf.cell
def command_queue(
    depth: int = 64,
    width: int = 162  # 81 trits * 2 bits
) -> Component:
    """
    Command Queue - Buffers commands from host CPU.

    Allows CPU to queue up multiple operations while the
    optical processor works through them autonomously.

    Args:
        depth: Number of entries
        width: Bits per entry (162 for 81-trit instruction)
    """
    c = gf.Component()

    comp_width = 120.0
    comp_height = 80.0

    # Queue memory block
    queue_mem = c << gf.components.rectangle(
        size=(comp_width, comp_height),
        layer=LAYER_CACHE
    )

    # Write pointer
    wr_ptr = c << gf.components.rectangle(size=(30, 20), layer=LAYER_REG)
    wr_ptr.dmove((10, 50))
    c.add_label("WR", position=(25, 60), layer=LAYER_TEXT)

    # Read pointer
    rd_ptr = c << gf.components.rectangle(size=(30, 20), layer=LAYER_REG)
    rd_ptr.dmove((10, 10))
    c.add_label("RD", position=(25, 20), layer=LAYER_TEXT)

    # FIFO control
    fifo_ctrl = c << gf.components.rectangle(size=(50, 60), layer=LAYER_CTRL)
    fifo_ctrl.dmove((50, 10))
    c.add_label("FIFO", position=(75, 40), layer=LAYER_TEXT)

    # Status (empty/full flags)
    status = c << gf.components.rectangle(size=(30, 30), layer=LAYER_LOGIC)
    status.dmove((80, 40))
    c.add_label("E/F", position=(95, 55), layer=LAYER_TEXT)

    # Labels
    c.add_label(f"CMD QUEUE ({depth})", position=(comp_width/2, comp_height + 10), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="cpu_in", center=(0, comp_height/2), width=40, orientation=180, layer=LAYER_CACHE)
    c.add_port(name="instr_out", center=(comp_width, comp_height/2), width=40, orientation=0, layer=LAYER_CACHE)
    c.add_port(name="status", center=(comp_width/2, 0), width=20, orientation=-90, layer=LAYER_LOGIC)

    return c


# =============================================================================
# INSTRUCTION DECODER
# =============================================================================

@gf.cell
def ternary_instruction_decoder() -> Component:
    """
    Ternary Instruction Decoder.

    Decodes 81-trit instructions into control signals:
    - Opcode (3 trits) -> ALU operation
    - Operand A (27 trits) -> Source register/immediate
    - Operand B (27 trits) -> Source register/immediate
    - Destination (24 trits) -> Destination register/address

    Supports the full ternary ISA including 3-way branches.
    """
    c = gf.Component()

    width = 150.0
    height = 120.0

    # Decoder block
    decoder = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_LOGIC
    )

    # Opcode extract
    opcode_ext = c << gf.components.rectangle(size=(40, 30), layer=LAYER_CTRL)
    opcode_ext.dmove((10, 80))
    c.add_label("OPCODE", position=(30, 95), layer=LAYER_TEXT)
    c.add_label("[2:0]", position=(30, 85), layer=LAYER_TEXT)

    # Operand A extract
    op_a = c << gf.components.rectangle(size=(40, 30), layer=LAYER_CTRL)
    op_a.dmove((55, 80))
    c.add_label("OP_A", position=(75, 95), layer=LAYER_TEXT)
    c.add_label("[29:3]", position=(75, 85), layer=LAYER_TEXT)

    # Operand B extract
    op_b = c << gf.components.rectangle(size=(40, 30), layer=LAYER_CTRL)
    op_b.dmove((100, 80))
    c.add_label("OP_B", position=(120, 95), layer=LAYER_TEXT)
    c.add_label("[56:30]", position=(120, 85), layer=LAYER_TEXT)

    # Control signal generator
    ctrl_gen = c << gf.components.rectangle(size=(80, 40), layer=LAYER_LOGIC)
    ctrl_gen.dmove((10, 30))
    c.add_label("CONTROL", position=(50, 50), layer=LAYER_TEXT)
    c.add_label("SIGNALS", position=(50, 40), layer=LAYER_TEXT)

    # Immediate decoder
    imm_dec = c << gf.components.rectangle(size=(40, 40), layer=LAYER_CTRL)
    imm_dec.dmove((100, 30))
    c.add_label("IMM", position=(120, 50), layer=LAYER_TEXT)

    # Ternary-specific: 3-way branch decoder
    br3_dec = c << gf.components.rectangle(size=(60, 20), layer=LAYER_PRED)
    br3_dec.dmove((45, 5))
    c.add_label("BR3 DEC", position=(75, 15), layer=LAYER_TEXT)

    # Labels
    c.add_label("TERNARY INSTR DECODER", position=(width/2, height + 10), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="instr_in", center=(0, height/2), width=50, orientation=180, layer=LAYER_LOGIC)
    c.add_port(name="ctrl_out", center=(width, height/2), width=40, orientation=0, layer=LAYER_CTRL)
    c.add_port(name="alu_op", center=(width, height - 20), width=20, orientation=0, layer=LAYER_LOGIC)
    c.add_port(name="reg_addr", center=(width, 20), width=20, orientation=0, layer=LAYER_REG)

    return c


# =============================================================================
# PROGRAM COUNTER (81-trit)
# =============================================================================

@gf.cell
def program_counter_81trit() -> Component:
    """
    81-Trit Program Counter.

    Supports:
    - 3^81 addressable locations (astronomically large)
    - Increment, load, branch operations
    - Ternary arithmetic for address calculation
    """
    c = gf.Component()

    width = 100.0
    height = 80.0

    # PC register block
    pc_reg = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_REG
    )

    # Current PC value (81 trits = 162 bits storage)
    pc_val = c << gf.components.rectangle(size=(60, 40), layer=LAYER_LOGIC)
    pc_val.dmove((20, 30))
    c.add_label("PC", position=(50, 50), layer=LAYER_TEXT)
    c.add_label("[80:0]", position=(50, 40), layer=LAYER_TEXT)

    # Incrementer (+1 in ternary)
    inc = c << gf.components.rectangle(size=(25, 20), layer=LAYER_CTRL)
    inc.dmove((10, 5))
    c.add_label("+1", position=(22, 15), layer=LAYER_TEXT)

    # Load mux
    load_mux = c << gf.components.rectangle(size=(25, 20), layer=LAYER_CTRL)
    load_mux.dmove((40, 5))
    c.add_label("LD", position=(52, 15), layer=LAYER_TEXT)

    # Branch adder
    br_add = c << gf.components.rectangle(size=(25, 20), layer=LAYER_CTRL)
    br_add.dmove((70, 5))
    c.add_label("BR", position=(82, 15), layer=LAYER_TEXT)

    # Labels
    c.add_label("PROGRAM COUNTER", position=(width/2, height + 10), layer=LAYER_TEXT)
    c.add_label("81-trit", position=(width/2, height + 22), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="next_pc", center=(0, height/2), width=30, orientation=180, layer=LAYER_REG)
    c.add_port(name="pc_out", center=(width, height/2), width=30, orientation=0, layer=LAYER_REG)
    c.add_port(name="branch_target", center=(width/2, 0), width=30, orientation=-90, layer=LAYER_CTRL)

    return c


# =============================================================================
# BRANCH PREDICTOR (3-way Ternary!)
# =============================================================================

@gf.cell
def ternary_branch_predictor(
    entries: int = 64
) -> Component:
    """
    Ternary Branch Predictor - 3-way prediction!

    Unlike binary predictors (taken/not-taken), ternary branches
    have THREE outcomes:
    - Negative path (-1)
    - Zero path (0)
    - Positive path (+1)

    Uses a 3-state saturating counter per entry:
    State -1: Predict negative
    State  0: Predict zero (neutral)
    State +1: Predict positive

    Args:
        entries: Number of BTB entries
    """
    c = gf.Component()

    width = 140.0
    height = 100.0

    # Predictor block
    pred = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_PRED
    )

    # Branch Target Buffer (BTB)
    btb = c << gf.components.rectangle(size=(50, 60), layer=LAYER_CACHE)
    btb.dmove((10, 30))
    c.add_label("BTB", position=(35, 60), layer=LAYER_TEXT)
    c.add_label(f"{entries}", position=(35, 50), layer=LAYER_TEXT)

    # 3-state predictor array
    pred_arr = c << gf.components.rectangle(size=(50, 60), layer=LAYER_LOGIC)
    pred_arr.dmove((70, 30))
    c.add_label("3-STATE", position=(95, 60), layer=LAYER_TEXT)
    c.add_label("PRED", position=(95, 50), layer=LAYER_TEXT)

    # Prediction output (ternary: -1, 0, +1)
    pred_out = c << gf.components.rectangle(size=(30, 20), layer=LAYER_CTRL)
    pred_out.dmove((70, 5))
    c.add_label("-/0/+", position=(85, 15), layer=LAYER_TEXT)

    # Update logic
    update = c << gf.components.rectangle(size=(50, 20), layer=LAYER_LOGIC)
    update.dmove((10, 5))
    c.add_label("UPDATE", position=(35, 15), layer=LAYER_TEXT)

    # Labels
    c.add_label("TERNARY BRANCH PREDICTOR", position=(width/2, height + 10), layer=LAYER_TEXT)
    c.add_label("3-way prediction!", position=(width/2, height + 22), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="pc_in", center=(0, height/2), width=30, orientation=180, layer=LAYER_PRED)
    c.add_port(name="prediction", center=(width, height/2), width=20, orientation=0, layer=LAYER_CTRL)
    c.add_port(name="actual", center=(width/2, 0), width=20, orientation=-90, layer=LAYER_LOGIC)

    return c


# =============================================================================
# SEQUENCER
# =============================================================================

@gf.cell
def multi_cycle_sequencer() -> Component:
    """
    Multi-Cycle Operation Sequencer.

    Manages operations that take multiple cycles:
    - MUL: 3 cycles (log conversion + SFG + exp)
    - DIV: 5 cycles (log + DFG + exp + correction)
    - Memory ops: Variable based on tier

    Generates micro-operations for complex instructions.
    """
    c = gf.Component()

    width = 130.0
    height = 100.0

    # Sequencer block
    seq = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_SEQ
    )

    # Cycle counter
    cycle_cnt = c << gf.components.rectangle(size=(35, 30), layer=LAYER_REG)
    cycle_cnt.dmove((10, 60))
    c.add_label("CYC", position=(27, 75), layer=LAYER_TEXT)

    # Micro-op ROM
    uop_rom = c << gf.components.rectangle(size=(50, 40), layer=LAYER_CACHE)
    uop_rom.dmove((50, 50))
    c.add_label("uOP", position=(75, 70), layer=LAYER_TEXT)
    c.add_label("ROM", position=(75, 60), layer=LAYER_TEXT)

    # State machine
    fsm = c << gf.components.rectangle(size=(50, 40), layer=LAYER_LOGIC)
    fsm.dmove((10, 10))
    c.add_label("FSM", position=(35, 30), layer=LAYER_TEXT)

    # Micro-op output
    uop_out = c << gf.components.rectangle(size=(40, 40), layer=LAYER_CTRL)
    uop_out.dmove((70, 10))
    c.add_label("uOP", position=(90, 30), layer=LAYER_TEXT)
    c.add_label("OUT", position=(90, 20), layer=LAYER_TEXT)

    # Labels
    c.add_label("SEQUENCER", position=(width/2, height + 10), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="opcode", center=(0, height/2), width=25, orientation=180, layer=LAYER_SEQ)
    c.add_port(name="uop_out", center=(width, height/2), width=30, orientation=0, layer=LAYER_CTRL)
    c.add_port(name="done", center=(width/2, 0), width=15, orientation=-90, layer=LAYER_LOGIC)

    return c


# =============================================================================
# REGISTER ALLOCATOR
# =============================================================================

@gf.cell
def tier_register_allocator() -> Component:
    """
    Optical RAM Tier Register Allocator.

    Manages register allocation across the three optical RAM tiers:
    - Tier 1 (Hot): 4 registers, 1ns access
    - Tier 2 (Working): 16 registers, 10ns access
    - Tier 3 (Parking): 32 registers, 100ns access

    Implements register spilling/filling between tiers.
    """
    c = gf.Component()

    width = 160.0
    height = 120.0

    # Allocator block
    alloc = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_LOGIC
    )

    # Tier 1 tracker
    t1 = c << gf.components.rectangle(size=(40, 30), layer=LAYER_REG)
    t1.dmove((10, 80))
    c.add_label("T1:4", position=(30, 95), layer=LAYER_TEXT)
    c.add_label("HOT", position=(30, 85), layer=LAYER_TEXT)

    # Tier 2 tracker
    t2 = c << gf.components.rectangle(size=(40, 30), layer=LAYER_REG)
    t2.dmove((60, 80))
    c.add_label("T2:16", position=(80, 95), layer=LAYER_TEXT)
    c.add_label("WORK", position=(80, 85), layer=LAYER_TEXT)

    # Tier 3 tracker
    t3 = c << gf.components.rectangle(size=(40, 30), layer=LAYER_REG)
    t3.dmove((110, 80))
    c.add_label("T3:32", position=(130, 95), layer=LAYER_TEXT)
    c.add_label("PARK", position=(130, 85), layer=LAYER_TEXT)

    # Free list
    free_list = c << gf.components.rectangle(size=(60, 30), layer=LAYER_CACHE)
    free_list.dmove((10, 40))
    c.add_label("FREE LIST", position=(40, 55), layer=LAYER_TEXT)

    # Spill/fill controller
    spill = c << gf.components.rectangle(size=(70, 30), layer=LAYER_CTRL)
    spill.dmove((80, 40))
    c.add_label("SPILL/FILL", position=(115, 55), layer=LAYER_TEXT)

    # LRU tracker
    lru = c << gf.components.rectangle(size=(140, 25), layer=LAYER_LOGIC)
    lru.dmove((10, 8))
    c.add_label("LRU TRACKER", position=(80, 20), layer=LAYER_TEXT)

    # Labels
    c.add_label("REGISTER ALLOCATOR", position=(width/2, height + 10), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="reg_req", center=(0, height/2), width=30, orientation=180, layer=LAYER_LOGIC)
    c.add_port(name="tier1", center=(width, 90), width=20, orientation=0, layer=LAYER_REG)
    c.add_port(name="tier2", center=(width, 60), width=20, orientation=0, layer=LAYER_REG)
    c.add_port(name="tier3", center=(width, 30), width=20, orientation=0, layer=LAYER_REG)

    return c


# =============================================================================
# INTERRUPT CONTROLLER
# =============================================================================

@gf.cell
def interrupt_controller(
    n_sources: int = 16
) -> Component:
    """
    Interrupt Controller for IOA events.

    Handles asynchronous events from:
    - Electronic IOA (PCIe, USB events)
    - Network IOA (packet arrival, DMA complete)
    - Sensor IOA (sample ready, threshold crossed)
    - Storage IOA (transfer complete, error)

    Uses ternary priority encoding.

    Args:
        n_sources: Number of interrupt sources
    """
    c = gf.Component()

    width = 140.0
    height = 110.0

    # Controller block
    ctrl = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_INT
    )

    # Interrupt pending register
    pend = c << gf.components.rectangle(size=(50, 25), layer=LAYER_REG)
    pend.dmove((10, 75))
    c.add_label("PENDING", position=(35, 87), layer=LAYER_TEXT)

    # Interrupt enable register
    enable = c << gf.components.rectangle(size=(50, 25), layer=LAYER_REG)
    enable.dmove((70, 75))
    c.add_label("ENABLE", position=(95, 87), layer=LAYER_TEXT)

    # Priority encoder (ternary)
    pri_enc = c << gf.components.rectangle(size=(60, 30), layer=LAYER_LOGIC)
    pri_enc.dmove((10, 38))
    c.add_label("TERNARY", position=(40, 53), layer=LAYER_TEXT)
    c.add_label("PRIORITY", position=(40, 45), layer=LAYER_TEXT)

    # Vector generator
    vec_gen = c << gf.components.rectangle(size=(50, 30), layer=LAYER_CTRL)
    vec_gen.dmove((80, 38))
    c.add_label("VECTOR", position=(105, 53), layer=LAYER_TEXT)

    # Interrupt sources (left side)
    for i in range(4):
        src = c << gf.components.rectangle(size=(12, 15), layer=LAYER_METAL1)
        src.dmove((-15, 20 + i * 20))

    c.add_label("ELEC", position=(-25, 85), layer=LAYER_TEXT)
    c.add_label("NET", position=(-25, 65), layer=LAYER_TEXT)
    c.add_label("SENS", position=(-25, 45), layer=LAYER_TEXT)
    c.add_label("STOR", position=(-25, 25), layer=LAYER_TEXT)

    # Acknowledge
    ack = c << gf.components.rectangle(size=(30, 20), layer=LAYER_CTRL)
    ack.dmove((55, 8))
    c.add_label("ACK", position=(70, 18), layer=LAYER_TEXT)

    # Labels
    c.add_label("INTERRUPT CONTROLLER", position=(width/2, height + 10), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="irq_in", center=(0, height/2), width=80, orientation=180, layer=LAYER_INT)
    c.add_port(name="irq_out", center=(width, height/2), width=20, orientation=0, layer=LAYER_CTRL)
    c.add_port(name="vector", center=(width, 30), width=20, orientation=0, layer=LAYER_LOGIC)

    return c


# =============================================================================
# ALU INTERFACE
# =============================================================================

@gf.cell
def alu_interface() -> Component:
    """
    Interface to the Optical ALU.

    Translates control signals to:
    - Operation select (ADD/SUB/MUL/DIV)
    - Linear/Log domain select
    - SFG/DFG mixer select
    - Carry chain control
    """
    c = gf.Component()

    width = 120.0
    height = 90.0

    # Interface block
    intf = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_CTRL
    )

    # Operation decoder
    op_dec = c << gf.components.rectangle(size=(50, 35), layer=LAYER_LOGIC)
    op_dec.dmove((10, 45))
    c.add_label("OP DEC", position=(35, 62), layer=LAYER_TEXT)

    # Domain select (linear/log)
    dom_sel = c << gf.components.rectangle(size=(40, 35), layer=LAYER_LOGIC)
    dom_sel.dmove((70, 45))
    c.add_label("LIN/LOG", position=(90, 62), layer=LAYER_TEXT)

    # Timing generator
    timing = c << gf.components.rectangle(size=(50, 30), layer=LAYER_CTRL)
    timing.dmove((10, 8))
    c.add_label("TIMING", position=(35, 23), layer=LAYER_TEXT)

    # Status capture
    status = c << gf.components.rectangle(size=(40, 30), layer=LAYER_REG)
    status.dmove((70, 8))
    c.add_label("STATUS", position=(90, 23), layer=LAYER_TEXT)

    # Labels
    c.add_label("ALU INTERFACE", position=(width/2, height + 10), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="ctrl_in", center=(0, height/2), width=30, orientation=180, layer=LAYER_CTRL)
    c.add_port(name="to_ioc", center=(width, height/2), width=40, orientation=0, layer=LAYER_CTRL)
    c.add_port(name="status", center=(width/2, 0), width=20, orientation=-90, layer=LAYER_REG)

    return c


# =============================================================================
# DMA CONTROLLER
# =============================================================================

@gf.cell
def opu_dma_controller() -> Component:
    """
    DMA Controller for autonomous data movement.

    Handles bulk transfers between:
    - External storage (via Storage IOA)
    - Optical RAM tiers
    - Network (via Network IOA)

    Supports scatter-gather for non-contiguous data.
    """
    c = gf.Component()

    width = 130.0
    height = 90.0

    # Controller block
    ctrl = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_CTRL
    )

    # Descriptor fetch
    desc = c << gf.components.rectangle(size=(40, 35), layer=LAYER_CACHE)
    desc.dmove((10, 45))
    c.add_label("DESC", position=(30, 62), layer=LAYER_TEXT)

    # Address generator
    addr_gen = c << gf.components.rectangle(size=(40, 35), layer=LAYER_LOGIC)
    addr_gen.dmove((55, 45))
    c.add_label("ADDR", position=(75, 62), layer=LAYER_TEXT)

    # Transfer counter
    xfer_cnt = c << gf.components.rectangle(size=(30, 35), layer=LAYER_REG)
    xfer_cnt.dmove((100, 45))
    c.add_label("CNT", position=(115, 62), layer=LAYER_TEXT)

    # Channel arbiter
    arb = c << gf.components.rectangle(size=(110, 30), layer=LAYER_LOGIC)
    arb.dmove((10, 8))
    c.add_label("CHANNEL ARBITER", position=(65, 23), layer=LAYER_TEXT)

    # Labels
    c.add_label("DMA CONTROLLER", position=(width/2, height + 10), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="cmd_in", center=(0, height/2), width=25, orientation=180, layer=LAYER_CTRL)
    c.add_port(name="ioa_if", center=(width, height/2), width=30, orientation=0, layer=LAYER_CTRL)
    c.add_port(name="done", center=(width/2, 0), width=15, orientation=-90, layer=LAYER_LOGIC)

    return c


# =============================================================================
# STATUS REGISTER FILE
# =============================================================================

@gf.cell
def status_register_file() -> Component:
    """
    Status/Flag Register File.

    Ternary flags:
    - N (Negative): Result < 0
    - Z (Zero): Result = 0
    - P (Positive): Result > 0
    - C (Carry): Ternary carry out
    - O (Overflow): Result out of range

    Also includes:
    - Interrupt enable/disable
    - Processor mode
    - Exception status
    """
    c = gf.Component()

    width = 100.0
    height = 80.0

    # Register file block
    reg_file = c << gf.components.rectangle(
        size=(width, height),
        layer=LAYER_REG
    )

    # Flags
    flags = c << gf.components.rectangle(size=(40, 30), layer=LAYER_LOGIC)
    flags.dmove((10, 40))
    c.add_label("N Z P", position=(30, 55), layer=LAYER_TEXT)
    c.add_label("C O", position=(30, 45), layer=LAYER_TEXT)

    # Mode register
    mode = c << gf.components.rectangle(size=(30, 30), layer=LAYER_CTRL)
    mode.dmove((60, 40))
    c.add_label("MODE", position=(75, 55), layer=LAYER_TEXT)

    # Exception status
    exc = c << gf.components.rectangle(size=(80, 25), layer=LAYER_LOGIC)
    exc.dmove((10, 8))
    c.add_label("EXCEPTION STATUS", position=(50, 20), layer=LAYER_TEXT)

    # Labels
    c.add_label("STATUS REGS", position=(width/2, height + 10), layer=LAYER_TEXT)

    # Ports
    c.add_port(name="flags_in", center=(0, height/2), width=25, orientation=180, layer=LAYER_REG)
    c.add_port(name="flags_out", center=(width, height/2), width=25, orientation=0, layer=LAYER_REG)

    return c


# =============================================================================
# COMPLETE OPU CONTROLLER
# =============================================================================

@gf.cell
def opu_controller() -> Component:
    """
    Complete OPU (Optical Processing Unit) Controller.

    The "brain" of the ternary optical computer that enables
    autonomous operation. Integrates all control components:

    - Command Queue: Buffers commands from host CPU
    - Instruction Decoder: Parses ternary opcodes
    - Program Counter: 81-trit address tracking
    - Branch Predictor: 3-way ternary prediction
    - Sequencer: Multi-cycle operation management
    - Register Allocator: Optical RAM tier management
    - Interrupt Controller: IOA event handling
    - ALU Interface: Optical ALU control
    - DMA Controller: Autonomous data movement

    Size: ~600 x 500 um
    """
    c = gf.Component()

    # Title
    c.add_label("OPU CONTROLLER", position=(300, 480), layer=LAYER_TEXT)
    c.add_label("Ternary Optical Processor Control Unit", position=(300, 460), layer=LAYER_TEXT)

    # Row 1: Input stage
    cmd_queue = c << command_queue(depth=64)
    cmd_queue.dmove((20, 350))

    instr_dec = c << ternary_instruction_decoder()
    instr_dec.dmove((180, 340))

    pc = c << program_counter_81trit()
    pc.dmove((370, 360))

    # Row 2: Control stage
    branch_pred = c << ternary_branch_predictor(entries=64)
    branch_pred.dmove((20, 220))

    sequencer = c << multi_cycle_sequencer()
    sequencer.dmove((200, 220))

    reg_alloc = c << tier_register_allocator()
    reg_alloc.dmove((370, 200))

    # Row 3: Execution interface
    int_ctrl = c << interrupt_controller(n_sources=16)
    int_ctrl.dmove((20, 70))

    alu_if = c << alu_interface()
    alu_if.dmove((200, 80))

    dma_ctrl = c << opu_dma_controller()
    dma_ctrl.dmove((360, 80))

    # Row 4: Status
    status_regs = c << status_register_file()
    status_regs.dmove((510, 200))

    # Connection indicators
    c.add_label("FROM CPU", position=(20, 450), layer=LAYER_TEXT)
    c.add_label("↓", position=(80, 440), layer=LAYER_TEXT)

    c.add_label("TO IOC/ALU", position=(300, 50), layer=LAYER_TEXT)
    c.add_label("↓", position=(300, 40), layer=LAYER_TEXT)

    c.add_label("TO IOAs", position=(490, 120), layer=LAYER_TEXT)
    c.add_label("→", position=(500, 110), layer=LAYER_TEXT)

    # Feature summary
    c.add_label("Features:", position=(530, 380), layer=LAYER_TEXT)
    c.add_label("• 81-trit PC", position=(530, 360), layer=LAYER_TEXT)
    c.add_label("• 3-way branch", position=(530, 345), layer=LAYER_TEXT)
    c.add_label("• Auto DMA", position=(530, 330), layer=LAYER_TEXT)
    c.add_label("• Tier mgmt", position=(530, 315), layer=LAYER_TEXT)

    # Main ports
    c.add_port(name="cpu_cmd", port=cmd_queue.ports["cpu_in"])
    c.add_port(name="to_ioc", port=alu_if.ports["to_ioc"])
    c.add_port(name="irq_in", port=int_ctrl.ports["irq_in"])
    c.add_port(name="dma_if", port=dma_ctrl.ports["ioa_if"])
    c.add_port(name="tier1", port=reg_alloc.ports["tier1"])
    c.add_port(name="tier2", port=reg_alloc.ports["tier2"])
    c.add_port(name="tier3", port=reg_alloc.ports["tier3"])

    return c


# =============================================================================
# CONVENIENCE GENERATORS
# =============================================================================

def generate_opu_controller(output_path: Optional[str] = None) -> Component:
    """Generate complete OPU Controller."""
    chip = opu_controller()
    if output_path:
        chip.write(output_path)
        print(f"OPU Controller saved to: {output_path}")
    return chip


# =============================================================================
# INTERACTIVE CLI
# =============================================================================

def interactive_opu_generator():
    """Interactive CLI for generating OPU Controller components."""
    print("\n" + "="*60)
    print("  OPU CONTROLLER GENERATOR")
    print("  The Brain of the Ternary Optical Computer")
    print("="*60)

    print("\nAvailable components:")
    print("  1. Complete OPU Controller")
    print("  2. Command Queue")
    print("  3. Instruction Decoder")
    print("  4. Program Counter (81-trit)")
    print("  5. Branch Predictor (3-way)")
    print("  6. Sequencer")
    print("  7. Register Allocator")
    print("  8. Interrupt Controller")
    print("  9. ALU Interface")
    print(" 10. DMA Controller")

    choice = input("\nSelect component (1-10): ").strip()

    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data', 'gds')
    os.makedirs(data_dir, exist_ok=True)

    if choice == "1":
        chip = opu_controller()
        chip_name = "opu_controller"
    elif choice == "2":
        depth = int(input("Queue depth [64]: ").strip() or "64")
        chip = command_queue(depth=depth)
        chip_name = f"command_queue_{depth}"
    elif choice == "3":
        chip = ternary_instruction_decoder()
        chip_name = "ternary_instruction_decoder"
    elif choice == "4":
        chip = program_counter_81trit()
        chip_name = "program_counter_81trit"
    elif choice == "5":
        entries = int(input("BTB entries [64]: ").strip() or "64")
        chip = ternary_branch_predictor(entries=entries)
        chip_name = f"branch_predictor_{entries}"
    elif choice == "6":
        chip = multi_cycle_sequencer()
        chip_name = "sequencer"
    elif choice == "7":
        chip = tier_register_allocator()
        chip_name = "register_allocator"
    elif choice == "8":
        sources = int(input("Interrupt sources [16]: ").strip() or "16")
        chip = interrupt_controller(n_sources=sources)
        chip_name = f"interrupt_controller_{sources}"
    elif choice == "9":
        chip = alu_interface()
        chip_name = "alu_interface"
    elif choice == "10":
        chip = opu_dma_controller()
        chip_name = "dma_controller"
    else:
        print("Invalid selection")
        return None

    # Save GDS
    gds_path = os.path.join(data_dir, f"{chip_name}.gds")
    chip.write(gds_path)
    print(f"\nGDS file saved to: {gds_path}")

    # Print ISA summary for instruction decoder
    if choice in ["1", "3"]:
        print("\n" + "="*50)
        print("  TERNARY INSTRUCTION SET SUMMARY")
        print("="*50)
        for name, info in list(TERNARY_ISA.items())[:12]:
            print(f"  {name:5} : {info['desc'][:35]:35} ({info['cycles']} cyc)")
        print("  ... and more")

    # Offer to open in KLayout
    import subprocess
    show = input("\nOpen in KLayout? (y/n): ").strip().lower()
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
    interactive_opu_generator()
