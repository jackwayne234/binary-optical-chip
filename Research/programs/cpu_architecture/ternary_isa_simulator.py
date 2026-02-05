#!/usr/bin/env python3
"""
Ternary ISA Simulator for the 81-Trit Optical Computer

Simulates execution of ternary programs on the optical computer architecture.
Supports the full ternary instruction set including 3-way branching.

Features:
- 81-trit balanced ternary arithmetic (-1, 0, +1 per trit)
- 3-tier optical RAM simulation (Hot, Working, Parking)
- Full ISA implementation (27 instructions)
- 3-way branch prediction simulation
- Cycle-accurate timing model
- Execution tracing and profiling

Usage:
    simulator = TernarySimulator()
    simulator.load_program(program)
    simulator.run()
    simulator.print_stats()

Author: Wavelength-Division Ternary Optical Computer Project
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import time


# =============================================================================
# TERNARY VALUE REPRESENTATION
# =============================================================================

class Trit(Enum):
    """Single ternary digit (trit): -1, 0, or +1"""
    NEG = -1
    ZERO = 0
    POS = 1

    def __str__(self):
        return {-1: 'T', 0: '0', 1: '1'}[self.value]  # T for -1 (like some ternary notations)

    @classmethod
    def from_int(cls, val: int) -> 'Trit':
        """Convert integer to trit (with bounds)."""
        if val < 0:
            return cls.NEG
        elif val > 0:
            return cls.POS
        else:
            return cls.ZERO


class TernaryWord:
    """
    81-trit balanced ternary word.

    Represents values from -(3^81-1)/2 to +(3^81-1)/2
    This is approximately ±2.2 × 10^38 (similar to 128-bit integers)
    """

    def __init__(self, trits: Optional[List[int]] = None, value: Optional[int] = None):
        """
        Initialize from list of trits or integer value.

        Args:
            trits: List of 81 trit values (-1, 0, or 1)
            value: Integer value to convert to ternary
        """
        if trits is not None:
            # Pad or truncate to 81 trits
            self.trits = list(trits[:81]) + [0] * (81 - len(trits))
        elif value is not None:
            self.trits = self._int_to_ternary(value)
        else:
            self.trits = [0] * 81

    def _int_to_ternary(self, value: int) -> List[int]:
        """Convert integer to balanced ternary representation."""
        if value == 0:
            return [0] * 81

        trits = []
        n = abs(value)
        sign = 1 if value > 0 else -1

        while n > 0 and len(trits) < 81:
            remainder = n % 3
            if remainder == 2:
                trits.append(-1 * sign)
                n = (n + 1) // 3
            elif remainder == 1:
                trits.append(1 * sign)
                n = n // 3
            else:
                trits.append(0)
                n = n // 3

        # Pad to 81 trits
        trits.extend([0] * (81 - len(trits)))
        return trits

    def to_int(self) -> int:
        """Convert balanced ternary to integer."""
        result = 0
        for i, trit in enumerate(self.trits):
            result += trit * (3 ** i)
        return result

    def __add__(self, other: 'TernaryWord') -> Tuple['TernaryWord', int]:
        """Add two ternary words, return (result, carry)."""
        result_trits = []
        carry = 0

        for i in range(81):
            sum_val = self.trits[i] + other.trits[i] + carry

            if sum_val >= 2:
                result_trits.append(sum_val - 3)
                carry = 1
            elif sum_val <= -2:
                result_trits.append(sum_val + 3)
                carry = -1
            else:
                result_trits.append(sum_val)
                carry = 0

        return TernaryWord(trits=result_trits), carry

    def __sub__(self, other: 'TernaryWord') -> Tuple['TernaryWord', int]:
        """Subtract two ternary words."""
        negated = TernaryWord(trits=[-t for t in other.trits])
        return self + negated

    def __neg__(self) -> 'TernaryWord':
        """Negate (flip all trits)."""
        return TernaryWord(trits=[-t for t in self.trits])

    def __mul__(self, other: 'TernaryWord') -> 'TernaryWord':
        """Multiply two ternary words (simplified - uses int conversion)."""
        # For simulation, we use integer multiplication
        # Real hardware uses log-domain optical computation
        result = self.to_int() * other.to_int()
        return TernaryWord(value=result)

    def __floordiv__(self, other: 'TernaryWord') -> 'TernaryWord':
        """Integer division (simplified)."""
        if other.to_int() == 0:
            raise ZeroDivisionError("Division by zero")
        result = self.to_int() // other.to_int()
        return TernaryWord(value=result)

    def __eq__(self, other: 'TernaryWord') -> bool:
        return self.trits == other.trits

    def sign(self) -> int:
        """Return sign: -1, 0, or +1."""
        val = self.to_int()
        if val < 0:
            return -1
        elif val > 0:
            return 1
        else:
            return 0

    def is_zero(self) -> bool:
        return all(t == 0 for t in self.trits)

    def __str__(self) -> str:
        """String representation (show value and first few trits)."""
        val = self.to_int()
        trit_str = ''.join({-1: 'T', 0: '0', 1: '1'}[t] for t in self.trits[:12])
        return f"{val} [{trit_str}...]"

    def __repr__(self) -> str:
        return f"TernaryWord({self.to_int()})"


# =============================================================================
# MEMORY TIERS
# =============================================================================

@dataclass
class MemoryTier:
    """Represents one tier of optical RAM."""
    name: str
    size: int
    access_cycles: int
    registers: Dict[str, TernaryWord] = field(default_factory=dict)
    access_count: int = 0

    def read(self, reg: str) -> TernaryWord:
        self.access_count += 1
        return self.registers.get(reg, TernaryWord())

    def write(self, reg: str, value: TernaryWord):
        self.access_count += 1
        self.registers[reg] = value


# =============================================================================
# CPU STATE
# =============================================================================

@dataclass
class CPUState:
    """Complete CPU state."""
    # Program counter (81-trit)
    pc: int = 0

    # Status flags
    flag_negative: bool = False
    flag_zero: bool = True
    flag_positive: bool = False
    flag_carry: int = 0
    flag_overflow: bool = False

    # Halted?
    halted: bool = False

    # Cycle counter
    cycles: int = 0

    # Instruction counter
    instructions: int = 0

    # Branch stats
    branches_taken: int = 0
    branches_not_taken: int = 0
    branch_mispredictions: int = 0


# =============================================================================
# INSTRUCTION DEFINITIONS
# =============================================================================

@dataclass
class Instruction:
    """Represents a single instruction."""
    opcode: str
    operands: List[str] = field(default_factory=list)

    def __str__(self):
        if self.operands:
            return f"{self.opcode} {', '.join(str(o) for o in self.operands)}"
        return self.opcode


# =============================================================================
# 3-WAY BRANCH PREDICTOR
# =============================================================================

class TernaryBranchPredictor:
    """
    3-way branch predictor for ternary architecture.

    Unlike binary predictors (taken/not-taken), this predicts
    THREE possible outcomes: negative, zero, or positive path.

    Uses 3-state saturating counters per branch address.
    """

    def __init__(self, table_size: int = 64):
        self.table_size = table_size
        # State: -1 (predict neg), 0 (predict zero), +1 (predict pos)
        self.prediction_table: Dict[int, int] = {}
        self.predictions_made = 0
        self.correct_predictions = 0

    def predict(self, pc: int) -> int:
        """Predict branch outcome: -1, 0, or +1."""
        self.predictions_made += 1
        idx = pc % self.table_size
        return self.prediction_table.get(idx, 0)  # Default: predict zero

    def update(self, pc: int, actual: int, predicted: int):
        """Update predictor with actual outcome."""
        idx = pc % self.table_size

        if actual == predicted:
            self.correct_predictions += 1

        # Update prediction towards actual outcome
        current = self.prediction_table.get(idx, 0)
        if actual > current:
            self.prediction_table[idx] = min(1, current + 1)
        elif actual < current:
            self.prediction_table[idx] = max(-1, current - 1)

    def accuracy(self) -> float:
        if self.predictions_made == 0:
            return 0.0
        return self.correct_predictions / self.predictions_made


# =============================================================================
# TERNARY SIMULATOR
# =============================================================================

class TernarySimulator:
    """
    Full simulator for the 81-trit ternary optical computer.
    """

    # Instruction cycle counts (from ISA spec)
    CYCLE_COUNTS = {
        'ADD': 1, 'SUB': 1, 'MUL': 3, 'DIV': 5, 'NEG': 1, 'ABS': 1,
        'AND': 1, 'OR': 1, 'NOT': 1, 'XOR': 1, 'CMP': 1, 'TST': 1,
        'JMP': 2, 'BRN': 2, 'BRZ': 2, 'BRP': 2, 'BR3': 2, 'CALL': 3, 'RET': 2,
        'LD1': 2, 'ST1': 2, 'LD2': 4, 'ST2': 4, 'LD3': 8, 'ST3': 8, 'DMA': 1,
        'NOP': 1, 'HALT': 1, 'INT': 3,
        'MOV': 1, 'LDI': 1,  # Extra convenience instructions
    }

    def __init__(self, trace: bool = False):
        """
        Initialize the simulator.

        Args:
            trace: If True, print execution trace
        """
        self.trace = trace

        # Memory tiers
        self.tier1 = MemoryTier("Tier1_Hot", 4, 2)      # ACC, TMP, A, B
        self.tier2 = MemoryTier("Tier2_Working", 16, 4)  # R0-R15
        self.tier3 = MemoryTier("Tier3_Parking", 32, 8)  # P0-P31

        # Initialize Tier 1 registers
        for reg in ['ACC', 'TMP', 'A', 'B']:
            self.tier1.registers[reg] = TernaryWord()

        # Initialize Tier 2 registers
        for i in range(16):
            self.tier2.registers[f'R{i}'] = TernaryWord()

        # Initialize Tier 3 registers
        for i in range(32):
            self.tier3.registers[f'P{i}'] = TernaryWord()

        # CPU state
        self.state = CPUState()

        # Branch predictor
        self.branch_predictor = TernaryBranchPredictor()

        # Program memory
        self.program: List[Instruction] = []

        # Call stack (for CALL/RET)
        self.call_stack: List[int] = []

        # Execution history
        self.history: List[str] = []

    def reset(self):
        """Reset simulator to initial state."""
        self.state = CPUState()
        for tier in [self.tier1, self.tier2, self.tier3]:
            tier.access_count = 0
            for reg in tier.registers:
                tier.registers[reg] = TernaryWord()
        self.call_stack = []
        self.history = []
        self.branch_predictor = TernaryBranchPredictor()

    def load_program(self, program: List[Union[Instruction, Tuple, str]]):
        """
        Load a program into memory.

        Args:
            program: List of instructions (Instruction objects, tuples, or strings)
        """
        self.program = []
        for instr in program:
            if isinstance(instr, Instruction):
                self.program.append(instr)
            elif isinstance(instr, tuple):
                self.program.append(Instruction(instr[0], list(instr[1:])))
            elif isinstance(instr, str):
                parts = instr.replace(',', ' ').split()
                self.program.append(Instruction(parts[0], parts[1:] if len(parts) > 1 else []))

        if self.trace:
            print(f"Loaded {len(self.program)} instructions")

    def get_register(self, name: str) -> TernaryWord:
        """Get register value by name."""
        name = name.upper()
        if name in self.tier1.registers:
            return self.tier1.read(name)
        elif name in self.tier2.registers:
            return self.tier2.read(name)
        elif name in self.tier3.registers:
            return self.tier3.read(name)
        else:
            # Try to parse as immediate value
            try:
                return TernaryWord(value=int(name))
            except ValueError:
                raise ValueError(f"Unknown register or invalid immediate: {name}")

    def set_register(self, name: str, value: TernaryWord):
        """Set register value by name."""
        name = name.upper()
        if name in self.tier1.registers:
            self.tier1.write(name, value)
        elif name in self.tier2.registers:
            self.tier2.write(name, value)
        elif name in self.tier3.registers:
            self.tier3.write(name, value)
        else:
            raise ValueError(f"Unknown register: {name}")

    def update_flags(self, result: TernaryWord, carry: int = 0):
        """Update status flags based on result."""
        val = result.to_int()
        self.state.flag_negative = val < 0
        self.state.flag_zero = val == 0
        self.state.flag_positive = val > 0
        self.state.flag_carry = carry

    def execute_instruction(self, instr: Instruction) -> int:
        """
        Execute a single instruction.

        Returns:
            Number of cycles taken
        """
        op = instr.opcode.upper()
        operands = instr.operands
        cycles = self.CYCLE_COUNTS.get(op, 1)

        if self.trace:
            self.history.append(f"[{self.state.pc:4d}] {instr}")

        # Arithmetic operations
        if op == 'ADD':
            a = self.get_register(operands[0])
            b = self.get_register(operands[1])
            result, carry = a + b
            self.set_register(operands[0], result)
            self.update_flags(result, carry)

        elif op == 'SUB':
            a = self.get_register(operands[0])
            b = self.get_register(operands[1])
            result, carry = a - b
            self.set_register(operands[0], result)
            self.update_flags(result, carry)

        elif op == 'MUL':
            a = self.get_register(operands[0])
            b = self.get_register(operands[1])
            result = a * b
            self.set_register(operands[0], result)
            self.update_flags(result)

        elif op == 'DIV':
            a = self.get_register(operands[0])
            b = self.get_register(operands[1])
            if b.is_zero():
                self.state.flag_overflow = True
            else:
                result = a // b
                self.set_register(operands[0], result)
                self.update_flags(result)

        elif op == 'NEG':
            a = self.get_register(operands[0])
            result = -a
            self.set_register(operands[0], result)
            self.update_flags(result)

        elif op == 'ABS':
            a = self.get_register(operands[0])
            if a.to_int() < 0:
                result = -a
            else:
                result = a
            self.set_register(operands[0], result)
            self.update_flags(result)

        # Logic operations (ternary logic)
        elif op == 'AND':  # Ternary AND = min
            a = self.get_register(operands[0])
            b = self.get_register(operands[1])
            result_trits = [min(a.trits[i], b.trits[i]) for i in range(81)]
            result = TernaryWord(trits=result_trits)
            self.set_register(operands[0], result)
            self.update_flags(result)

        elif op == 'OR':  # Ternary OR = max
            a = self.get_register(operands[0])
            b = self.get_register(operands[1])
            result_trits = [max(a.trits[i], b.trits[i]) for i in range(81)]
            result = TernaryWord(trits=result_trits)
            self.set_register(operands[0], result)
            self.update_flags(result)

        elif op == 'NOT':  # Ternary NOT = negate each trit
            a = self.get_register(operands[0])
            result = -a
            self.set_register(operands[0], result)
            self.update_flags(result)

        elif op == 'CMP':
            a = self.get_register(operands[0])
            b = self.get_register(operands[1])
            result, carry = a - b
            self.update_flags(result, carry)
            # Don't store result, just update flags

        elif op == 'TST':
            a = self.get_register(operands[0])
            self.update_flags(a)

        # Control flow
        elif op == 'JMP':
            target = int(operands[0])
            self.state.pc = target - 1  # -1 because we increment after
            self.state.branches_taken += 1

        elif op == 'BRN':  # Branch if negative
            target = int(operands[0])
            if self.state.flag_negative:
                self.state.pc = target - 1
                self.state.branches_taken += 1
            else:
                self.state.branches_not_taken += 1

        elif op == 'BRZ':  # Branch if zero
            target = int(operands[0])
            if self.state.flag_zero:
                self.state.pc = target - 1
                self.state.branches_taken += 1
            else:
                self.state.branches_not_taken += 1

        elif op == 'BRP':  # Branch if positive
            target = int(operands[0])
            if self.state.flag_positive:
                self.state.pc = target - 1
                self.state.branches_taken += 1
            else:
                self.state.branches_not_taken += 1

        elif op == 'BR3':  # 3-way branch (THE TERNARY SPECIAL!)
            # BR3 neg_target, zero_target, pos_target
            neg_target = int(operands[0])
            zero_target = int(operands[1])
            pos_target = int(operands[2])

            # Get prediction
            predicted = self.branch_predictor.predict(self.state.pc)

            # Determine actual branch
            if self.state.flag_negative:
                actual = -1
                self.state.pc = neg_target - 1
            elif self.state.flag_zero:
                actual = 0
                self.state.pc = zero_target - 1
            else:  # positive
                actual = 1
                self.state.pc = pos_target - 1

            # Update predictor
            self.branch_predictor.update(self.state.pc, actual, predicted)

            if actual != predicted:
                self.state.branch_mispredictions += 1
                cycles += 2  # Misprediction penalty

            self.state.branches_taken += 1

        elif op == 'CALL':
            target = int(operands[0])
            self.call_stack.append(self.state.pc + 1)  # Save return address
            self.state.pc = target - 1

        elif op == 'RET':
            if self.call_stack:
                self.state.pc = self.call_stack.pop() - 1
            else:
                self.state.halted = True  # Return from main

        # Memory operations
        elif op == 'LD1':
            src = self.tier1.read(operands[1])
            self.set_register(operands[0], src)

        elif op == 'ST1':
            val = self.get_register(operands[0])
            self.tier1.write(operands[1], val)

        elif op == 'LD2':
            src = self.tier2.read(operands[1])
            self.set_register(operands[0], src)

        elif op == 'ST2':
            val = self.get_register(operands[0])
            self.tier2.write(operands[1], val)

        elif op == 'LD3':
            src = self.tier3.read(operands[1])
            self.set_register(operands[0], src)

        elif op == 'ST3':
            val = self.get_register(operands[0])
            self.tier3.write(operands[1], val)

        # Convenience instructions
        elif op == 'MOV':
            val = self.get_register(operands[1])
            self.set_register(operands[0], val)

        elif op == 'LDI':  # Load immediate
            val = TernaryWord(value=int(operands[1]))
            self.set_register(operands[0], val)
            self.update_flags(val)

        # System
        elif op == 'NOP':
            pass

        elif op == 'HALT':
            self.state.halted = True

        else:
            raise ValueError(f"Unknown opcode: {op}")

        return cycles

    def step(self) -> bool:
        """
        Execute one instruction.

        Returns:
            True if execution should continue, False if halted
        """
        if self.state.halted or self.state.pc >= len(self.program):
            return False

        instr = self.program[self.state.pc]
        cycles = self.execute_instruction(instr)

        self.state.cycles += cycles
        self.state.instructions += 1
        self.state.pc += 1

        return not self.state.halted

    def run(self, max_instructions: int = 100000) -> int:
        """
        Run program until halt or max instructions.

        Returns:
            Number of instructions executed
        """
        count = 0
        while self.step() and count < max_instructions:
            count += 1

        return count

    def print_state(self):
        """Print current CPU state."""
        print("\n" + "="*60)
        print("  CPU STATE")
        print("="*60)
        print(f"  PC: {self.state.pc}")
        print(f"  Flags: N={int(self.state.flag_negative)} Z={int(self.state.flag_zero)} P={int(self.state.flag_positive)} C={self.state.flag_carry}")
        print(f"  Halted: {self.state.halted}")
        print()

        print("  Tier 1 (Hot) Registers:")
        for name, val in self.tier1.registers.items():
            print(f"    {name}: {val}")

        print("\n  Tier 2 (Working) Registers (non-zero):")
        for name, val in self.tier2.registers.items():
            if not val.is_zero():
                print(f"    {name}: {val}")

        print("\n  Tier 3 (Parking) Registers (non-zero):")
        for name, val in self.tier3.registers.items():
            if not val.is_zero():
                print(f"    {name}: {val}")

    def print_stats(self):
        """Print execution statistics."""
        print("\n" + "="*60)
        print("  EXECUTION STATISTICS")
        print("="*60)
        print(f"  Instructions executed: {self.state.instructions}")
        print(f"  Total cycles: {self.state.cycles}")
        print(f"  Average CPI: {self.state.cycles / max(1, self.state.instructions):.2f}")
        print()

        print("  Branch Statistics:")
        total_branches = self.state.branches_taken + self.state.branches_not_taken
        print(f"    Branches taken: {self.state.branches_taken}")
        print(f"    Branches not taken: {self.state.branches_not_taken}")
        print(f"    Mispredictions: {self.state.branch_mispredictions}")
        print(f"    3-way predictor accuracy: {self.branch_predictor.accuracy()*100:.1f}%")
        print()

        print("  Memory Tier Access:")
        print(f"    Tier 1 (Hot): {self.tier1.access_count} accesses")
        print(f"    Tier 2 (Working): {self.tier2.access_count} accesses")
        print(f"    Tier 3 (Parking): {self.tier3.access_count} accesses")

    def print_trace(self, last_n: int = 20):
        """Print execution trace."""
        print("\n" + "="*60)
        print("  EXECUTION TRACE (last {})".format(min(last_n, len(self.history))))
        print("="*60)
        for line in self.history[-last_n:]:
            print(f"  {line}")


# =============================================================================
# EXAMPLE PROGRAMS
# =============================================================================

def demo_addition():
    """Demonstrate simple addition."""
    print("\n" + "="*60)
    print("  DEMO: Simple Addition (5 + 3)")
    print("="*60)

    program = [
        ('LDI', 'ACC', '5'),    # ACC = 5
        ('LDI', 'TMP', '3'),    # TMP = 3
        ('ADD', 'ACC', 'TMP'),  # ACC = ACC + TMP
        ('HALT',),
    ]

    sim = TernarySimulator(trace=True)
    sim.load_program(program)
    sim.run()

    sim.print_state()
    sim.print_stats()

    result = sim.tier1.registers['ACC'].to_int()
    print(f"\n  Result: 5 + 3 = {result}")
    assert result == 8, f"Expected 8, got {result}"
    print("  ✓ Test passed!")


def demo_3way_branch():
    """Demonstrate 3-way branching - THE TERNARY SPECIAL!"""
    print("\n" + "="*60)
    print("  DEMO: 3-Way Branch (classify number)")
    print("="*60)
    print("  This demonstrates ternary's unique 3-way branch!")
    print("  Input -7: should go to NEGATIVE path")
    print()

    # Program that classifies a number as negative, zero, or positive
    program = [
        # Load test value
        ('LDI', 'ACC', '-7'),      # 0: Load -7 into ACC
        ('TST', 'ACC'),            # 1: Test ACC (sets flags)

        # 3-way branch based on sign!
        ('BR3', '4', '7', '10'),   # 2: Branch to neg(4), zero(7), or pos(10)

        # Unreachable
        ('HALT',),                 # 3: Should never reach here

        # NEGATIVE path (address 4)
        ('LDI', 'R0', '-1'),       # 4: R0 = -1 (negative indicator)
        ('JMP', '13'),             # 5: Jump to end
        ('NOP',),                  # 6: Padding

        # ZERO path (address 7)
        ('LDI', 'R0', '0'),        # 7: R0 = 0 (zero indicator)
        ('JMP', '13'),             # 8: Jump to end
        ('NOP',),                  # 9: Padding

        # POSITIVE path (address 10)
        ('LDI', 'R0', '1'),        # 10: R0 = 1 (positive indicator)
        ('JMP', '13'),             # 11: Jump to end
        ('NOP',),                  # 12: Padding

        # End
        ('HALT',),                 # 13: Done
    ]

    sim = TernarySimulator(trace=True)
    sim.load_program(program)
    sim.run()

    sim.print_state()
    sim.print_stats()
    sim.print_trace()

    result = sim.tier2.registers['R0'].to_int()
    print(f"\n  Classification result: {result}")
    print(f"  (-1=negative, 0=zero, 1=positive)")
    assert result == -1, f"Expected -1 for negative, got {result}"
    print("  ✓ Test passed! Correctly identified -7 as negative.")


def demo_loop_multiply():
    """Demonstrate a loop with multiplication."""
    print("\n" + "="*60)
    print("  DEMO: Factorial (5!)")
    print("="*60)

    # Calculate 5! = 120
    program = [
        ('LDI', 'ACC', '1'),       # 0: result = 1
        ('LDI', 'R0', '5'),        # 1: counter = 5

        # Loop start (address 2)
        ('LDI', 'TMP', '0'),       # 2: Load 0 for comparison
        ('CMP', 'R0', 'TMP'),      # 3: Compare counter with 0
        ('BRZ', '9'),              # 4: If counter == 0, exit loop

        ('MUL', 'ACC', 'R0'),      # 5: result *= counter
        ('LDI', 'TMP', '1'),       # 6: Load 1
        ('SUB', 'R0', 'TMP'),      # 7: counter -= 1
        ('JMP', '2'),              # 8: Loop back

        # Loop end (address 9)
        ('HALT',),                 # 9: Done
    ]

    sim = TernarySimulator(trace=True)
    sim.load_program(program)
    sim.run()

    sim.print_state()
    sim.print_stats()

    result = sim.tier1.registers['ACC'].to_int()
    print(f"\n  Result: 5! = {result}")
    assert result == 120, f"Expected 120, got {result}"
    print("  ✓ Test passed!")


def demo_tier_migration():
    """Demonstrate data movement between memory tiers."""
    print("\n" + "="*60)
    print("  DEMO: Memory Tier Migration")
    print("="*60)
    print("  Shows data moving: Tier1 -> Tier2 -> Tier3 -> Tier1")
    print()

    program = [
        # Store in Tier 1
        ('LDI', 'ACC', '42'),      # 0: ACC = 42
        ('ST1', 'ACC', 'TMP'),     # 1: Tier1[TMP] = 42

        # Move to Tier 2
        ('LD1', 'A', 'TMP'),       # 2: A = Tier1[TMP]
        ('ST2', 'A', 'R5'),        # 3: Tier2[R5] = A

        # Move to Tier 3
        ('LD2', 'B', 'R5'),        # 4: B = Tier2[R5]
        ('ST3', 'B', 'P10'),       # 5: Tier3[P10] = B

        # Retrieve back to Tier 1
        ('LD3', 'ACC', 'P10'),     # 6: ACC = Tier3[P10]

        ('HALT',),                 # 7: Done
    ]

    sim = TernarySimulator(trace=True)
    sim.load_program(program)
    sim.run()

    sim.print_state()
    sim.print_stats()

    result = sim.tier1.registers['ACC'].to_int()
    print(f"\n  Final ACC: {result}")
    assert result == 42, f"Expected 42, got {result}"
    print("  ✓ Data successfully migrated through all 3 tiers!")


def demo_ternary_arithmetic():
    """Demonstrate ternary-specific arithmetic properties."""
    print("\n" + "="*60)
    print("  DEMO: Balanced Ternary Arithmetic")
    print("="*60)
    print("  In balanced ternary, -1 + 1 = 0 exactly (no borrow needed)")
    print()

    program = [
        # Test: -1 + 1 = 0
        ('LDI', 'ACC', '-1'),
        ('LDI', 'TMP', '1'),
        ('ADD', 'ACC', 'TMP'),     # Should be exactly 0
        ('ST2', 'ACC', 'R0'),      # Save result

        # Test: 13 in ternary is 1*9 + 1*3 + 1*1 = [1,1,1,0,0,...]
        ('LDI', 'ACC', '13'),
        ('ST2', 'ACC', 'R1'),

        # Test: -13 is [-1,-1,-1,0,0,...]  (just flip trits!)
        ('LDI', 'ACC', '-13'),
        ('ST2', 'ACC', 'R2'),

        # Test: 13 + (-13) = 0
        ('LD2', 'ACC', 'R1'),
        ('LD2', 'TMP', 'R2'),
        ('ADD', 'ACC', 'TMP'),
        ('ST2', 'ACC', 'R3'),      # Should be 0

        ('HALT',),
    ]

    sim = TernarySimulator(trace=True)
    sim.load_program(program)
    sim.run()

    sim.print_state()

    r0 = sim.tier2.registers['R0'].to_int()
    r1 = sim.tier2.registers['R1'].to_int()
    r2 = sim.tier2.registers['R2'].to_int()
    r3 = sim.tier2.registers['R3'].to_int()

    print(f"\n  R0 (-1 + 1): {r0}")
    print(f"  R1 (13): {r1}")
    print(f"  R2 (-13): {r2}")
    print(f"  R3 (13 + -13): {r3}")

    assert r0 == 0 and r3 == 0, "Arithmetic error"
    print("\n  ✓ Balanced ternary arithmetic verified!")


# =============================================================================
# INTERACTIVE MODE
# =============================================================================

def interactive_mode():
    """Run simulator in interactive mode."""
    print("\n" + "="*60)
    print("  TERNARY ISA SIMULATOR - Interactive Mode")
    print("="*60)
    print("\nCommands:")
    print("  LDI reg, value  - Load immediate")
    print("  ADD reg1, reg2  - Add reg2 to reg1")
    print("  SUB reg1, reg2  - Subtract reg2 from reg1")
    print("  MUL reg1, reg2  - Multiply")
    print("  BR3 n, z, p     - 3-way branch")
    print("  state           - Show CPU state")
    print("  stats           - Show statistics")
    print("  reset           - Reset simulator")
    print("  demo N          - Run demo (1-5)")
    print("  quit            - Exit")
    print()

    sim = TernarySimulator(trace=True)

    while True:
        try:
            line = input("ternary> ").strip()
            if not line:
                continue

            if line.lower() == 'quit':
                break
            elif line.lower() == 'state':
                sim.print_state()
            elif line.lower() == 'stats':
                sim.print_stats()
            elif line.lower() == 'reset':
                sim.reset()
                print("Simulator reset.")
            elif line.lower().startswith('demo'):
                parts = line.split()
                demo_num = int(parts[1]) if len(parts) > 1 else 1
                if demo_num == 1:
                    demo_addition()
                elif demo_num == 2:
                    demo_3way_branch()
                elif demo_num == 3:
                    demo_loop_multiply()
                elif demo_num == 4:
                    demo_tier_migration()
                elif demo_num == 5:
                    demo_ternary_arithmetic()
            else:
                # Parse and execute single instruction
                parts = line.replace(',', ' ').split()
                instr = Instruction(parts[0], parts[1:] if len(parts) > 1 else [])
                sim.program = [instr]
                sim.state.pc = 0
                sim.step()
                print(f"  Executed: {instr}")
                print(f"  Flags: N={int(sim.state.flag_negative)} Z={int(sim.state.flag_zero)} P={int(sim.state.flag_positive)}")

        except KeyboardInterrupt:
            print("\nInterrupted.")
            break
        except Exception as e:
            print(f"  Error: {e}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""
    import sys

    print("\n" + "="*70)
    print("  TERNARY ISA SIMULATOR")
    print("  81-Trit Optical Computer Instruction Set Simulator")
    print("="*70)

    if len(sys.argv) > 1 and sys.argv[1] == '-i':
        interactive_mode()
    else:
        print("\nRunning demonstration programs...\n")

        demo_addition()
        print()

        demo_3way_branch()
        print()

        demo_loop_multiply()
        print()

        demo_tier_migration()
        print()

        demo_ternary_arithmetic()

        print("\n" + "="*70)
        print("  ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\nRun with -i flag for interactive mode:")
        print("  python ternary_isa_simulator.py -i")


if __name__ == "__main__":
    main()
