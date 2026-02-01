#!/usr/bin/env python3
"""
Ternary Optical Computer - Serial Controller
--------------------------------------------
Interacts with the ESP32/Arduino Firmware to run logic tests.
"""

import serial
import time
import argparse
import sys

# Standard Ternary Logic Table (Balanced)
# A + B -> Sum, Carry
TRUTH_TABLE = {
    (1, 1):   (-1, 1), # +1 + +1 = +2 -> (-1, Carry +1)
    (1, 0):   (1, 0),
    (1, -1):  (0, 0),
    (0, 1):   (1, 0),
    (0, 0):   (0, 0),
    (0, -1):  (-1, 0),
    (-1, 1):  (0, 0),
    (-1, 0):  (-1, 0),
    (-1, -1): (1, -1)  # -1 + -1 = -2 -> (+1, Carry -1)
}

class TernaryController:
    def __init__(self, port, baud=115200):
        try:
            self.ser = serial.Serial(port, baud, timeout=2)
            time.sleep(2) # Wait for Arduino reset
            print(f"Connected to {port}")
            self.clear_buffer()
        except serial.SerialException as e:
            print(f"Error connecting to {port}: {e}")
            sys.exit(1)

    def clear_buffer(self):
        while self.ser.in_waiting:
            self.ser.read()

    def send_command(self, cmd):
        print(f"> {cmd}")
        self.ser.write(f"{cmd}\n".encode())
        time.sleep(0.1)
        
        # Read response
        response = []
        start_time = time.time()
        while (time.time() - start_time) < 3.0: # 3 sec timeout
            if self.ser.in_waiting:
                line = self.ser.readline().decode().strip()
                if line:
                    response.append(line)
                    print(f"< {line}")
                    # Stop reading if we see result or error
                    if "Logic Result:" in line or "Unknown" in line:
                        break
        return response

    def run_test(self, a, b):
        print(f"\n--- Testing {a} + {b} ---")
        self.send_command(f"SET A {a}")
        self.send_command(f"SET B {b}")
        response = self.send_command("RUN")
        
        # Parse result
        decoded_sum = None
        decoded_carry = None
        
        for line in response:
            if "Decoded: Sum=" in line:
                # Format: "Decoded: Sum=1, Carry=0"
                parts = line.split(',')
                s_part = parts[0].split('=')[1]
                c_part = parts[1].split('=')[1]
                decoded_sum = int(s_part)
                decoded_carry = int(c_part)
        
        expected_sum, expected_carry = TRUTH_TABLE[(a, b)]
        
        if decoded_sum == expected_sum and decoded_carry == expected_carry:
            print(f"✅ PASS: {a}+{b} = {decoded_sum} (Carry {decoded_carry})")
            return True
        else:
            print(f"❌ FAIL: Expected {expected_sum} (C{expected_carry}), Got {decoded_sum} (C{decoded_carry})")
            return False

    def close(self):
        self.send_command("OFF")
        self.ser.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="Serial Port (e.g., /dev/ttyUSB0 or COM3)", required=True)
    parser.add_argument("--test", help="Run full truth table test", action="store_true")
    args = parser.parse_args()

    controller = TernaryController(args.port)

    if args.test:
        print("\n=== STARTING TRUTH TABLE VERIFICATION ===")
        score = 0
        total = len(TRUTH_TABLE)
        
        # Run calibration first
        controller.send_command("CAL")
        time.sleep(2)
        
        for (a, b) in TRUTH_TABLE:
            if controller.run_test(a, b):
                score += 1
            time.sleep(0.5)
        
        print(f"\n=== TEST COMPLETE: {score}/{total} PASSED ===")
    
    else:
        # Interactive Mode
        print("Interactive Mode. Type 'exit' to quit.")
        while True:
            cmd = input("Command (e.g., SET A 1): ")
            if cmd.lower() == 'exit':
                break
            controller.send_command(cmd)

    controller.close()

if __name__ == "__main__":
    main()
