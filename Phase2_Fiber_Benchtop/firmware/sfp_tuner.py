#!/usr/bin/env python3
"""
Finisar FTLX6872MCC Tuning Calculator
-------------------------------------
Calculates the I2C Register values needed to tune a specific frequency.
Based on SFF-8690 Standard.

Usage:
    python3 sfp_tuner.py --channel 30
    python3 sfp_tuner.py --freq 193.00
"""

import argparse

def calculate_tuning_bytes(frequency_thz):
    """
    Converts THz frequency to SFF-8690 Register Bytes.
    Formula: Frequency / 0.05 GHz = Integer Value
    """
    freq_ghz = frequency_thz * 1000
    grid_spacing = 0.05 # GHz
    
    tuning_int = int(freq_ghz / grid_spacing)
    
    # Convert to 4-byte Hex (Big Endian)
    byte_str = tuning_int.to_bytes(4, byteorder='big')
    
    return byte_str

def main():
    parser = argparse.ArgumentParser(description="Calculate SFP+ Tuning Registers")
    parser.add_argument("--channel", type=int, help="ITU Channel Number (e.g., 30)")
    parser.add_argument("--freq", type=float, help="Frequency in THz (e.g., 193.00)")
    
    args = parser.parse_args()
    
    # ITU Grid Base (Standard C-Band)
    # Ch 1 = 190.1 THz, Spacing = 100GHz (0.1 THz)
    # Formula: Freq = 190.1 + (Channel - 1) * 0.1
    
    target_freq = 0.0
    
    if args.channel:
        # Calculate freq from channel
        # Note: Standard ITU grid definition varies, using common C-Band ref
        # 193.10 THz is traditionally Ch 31 (Reference)
        target_freq = 193.10 + (args.channel - 31) * 0.1
        print(f"Target: ITU Channel {args.channel} -> {target_freq:.2f} THz")
    elif args.freq:
        target_freq = args.freq
        print(f"Target: {target_freq:.2f} THz")
    else:
        # Default to Phase 2 Specs (CommScope NG4-VDML2MDA440C1K Logic)
        print("No input. Showing Phase 2 Defaults (CommScope NG4 Map):")
        defaults = {
            "Trit -1 (Ch 44)": 44,
            "Trit  0 (Ch 46)": 46,
            "Trit +1 (Ch 48)": 48
        }
        for label, ch in defaults.items():
            freq = 193.10 + (ch - 31) * 0.1
            bytes_val = calculate_tuning_bytes(freq)
            print(f"  {label}: Ch{ch} ({freq:.2f} THz) -> Write: 0x{bytes_val.hex().upper()}")
        return

    # Calculate Bytes
    bytes_val = calculate_tuning_bytes(target_freq)
    
    print("\n[I2C Configuration]")
    print(f"Address: 0xA2 (0x51)")
    print(f"Page:    0x02 (Write 0x02 to Reg 127)")
    print(f"Bytes:   0x{bytes_val.hex().upper()}")
    print("-" * 30)
    print(f"Reg 128 (MSB): 0x{bytes_val[0]:02X}")
    print(f"Reg 129:       0x{bytes_val[1]:02X}")
    print(f"Reg 130:       0x{bytes_val[2]:02X}")
    print(f"Reg 131 (LSB): 0x{bytes_val[3]:02X}")

if __name__ == "__main__":
    main()
