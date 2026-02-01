/*
 * TERNARY OPTICAL COMPUTER - CONTROLLER FIRMWARE
 * Platform: ESP32 DevKit V1
 * Sensor: Adafruit AS7341 (I2C)
 * Driver: ULN2803A (6 Channels used)
 * 
 * Logic: Balanced Ternary (-1, 0, +1)
 * Physical Mapping: 
 *   -1 (Red, ~650nm)
 *    0 (Green, ~520nm)
 *   +1 (Blue, ~405nm)
 */

#include <Wire.h>
#include <Adafruit_AS7341.h>

Adafruit_AS7341 as7341;

// --- PIN DEFINITIONS (ESP32 GPIO) ---
// Connect these to ULN2803 Inputs
// A = First Operand, B = Second Operand
const int PIN_A_RED = 13; // Input A: -1
const int PIN_A_GRN = 12; // Input A:  0
const int PIN_A_BLU = 14; // Input A: +1

const int PIN_B_RED = 27; // Input B: -1
const int PIN_B_GRN = 26; // Input B:  0
const int PIN_B_BLU = 25; // Input B: +1

// --- CALIBRATION THRESHOLDS (Auto-Calibrate on Startup recommended) ---
// These are "Safe Defaults" but will be overwritten by calibrate()
uint16_t THRESH_RED = 1000;
uint16_t THRESH_GRN = 1000;
uint16_t THRESH_BLU = 1000;

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(1); }

  Serial.println("\n--- TERNARY OPTICAL COMPUTER BOOT ---");

  // 1. Init Pins
  pinMode(PIN_A_RED, OUTPUT); pinMode(PIN_A_GRN, OUTPUT); pinMode(PIN_A_BLU, OUTPUT);
  pinMode(PIN_B_RED, OUTPUT); pinMode(PIN_B_GRN, OUTPUT); pinMode(PIN_B_BLU, OUTPUT);
  
  allLasersOff();

  // 2. Init Sensor
  if (!as7341.begin()){
    Serial.println("ERROR: AS7341 Sensor not found! Check Wiring.");
    while (1) { delay(100); } // Halt
  }
  
  // Configure Sensor (High Sensitivity for Low Light Reflection)
  as7341.setATIME(100);
  as7341.setASTEP(999);
  as7341.setGain(AS7341_GAIN_256X);

  Serial.println("Sensor Online. Running Calibration...");
  calibrate_system();
  Serial.println("System Ready. Send commands (e.g., 'ADD 1 -1')");
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.length() > 0) {
      parse_command(input);
    }
  }
}

// --- CORE LOGIC ---

void parse_command(String cmd) {
  // Expected format: "ADD <val1> <val2>"
  // val can be -1, 0, 1
  
  if (cmd.startsWith("ADD")) {
    int space1 = cmd.indexOf(' ');
    int space2 = cmd.indexOf(' ', space1 + 1);
    
    if (space1 == -1 || space2 == -1) {
      Serial.println("Error: Invalid Format. Use 'ADD A B' (e.g. ADD 1 -1)");
      return;
    }
    
    String s1 = cmd.substring(space1 + 1, space2);
    String s2 = cmd.substring(space2 + 1);
    
    int v1 = s1.toInt();
    int v2 = s2.toInt();
    
    perform_addition(v1, v2);
  } else if (cmd == "CAL") {
    calibrate_system();
  } else {
    Serial.println("Unknown command.");
  }
}

void perform_addition(int v1, int v2) {
  Serial.print("Computing: "); Serial.print(v1); Serial.print(" + "); Serial.println(v2);
  
  allLasersOff();
  
  // Activate Input A
  if (v1 == -1) digitalWrite(PIN_A_RED, HIGH);
  else if (v1 == 0) digitalWrite(PIN_A_GRN, HIGH);
  else if (v1 == 1) digitalWrite(PIN_A_BLU, HIGH);
  
  // Activate Input B
  if (v2 == -1) digitalWrite(PIN_B_RED, HIGH);
  else if (v2 == 0) digitalWrite(PIN_B_GRN, HIGH);
  else if (v2 == 1) digitalWrite(PIN_B_BLU, HIGH);
  
  delay(200); // Wait for light to stabilize in mixer
  
  // Read Sensor
  if (!as7341.readAllChannels()){
    Serial.println("Error reading sensor");
    return;
  }
  
  // Decode Spectrum
  // F7 = Red/NIR, F4 = Green, F2 = Blue/Violet
  uint16_t r = as7341.getChannel(AS7341_CHANNEL_630nm_F7);
  uint16_t g = as7341.getChannel(AS7341_CHANNEL_515nm_F4);
  uint16_t b = as7341.getChannel(AS7341_CHANNEL_445nm_F2);
  
  Serial.print("Spectrum [R,G,B]: "); 
  Serial.print(r); Serial.print(","); Serial.print(g); Serial.print(","); Serial.println(b);
  
  decode_result(r, g, b);
  
  allLasersOff();
}

void decode_result(uint16_t r, uint16_t g, uint16_t b) {
  // Logic Table for Balanced Ternary Addition
  // Cyan (B+G) = +1
  // Magenta (R+B) = 0
  // Yellow (R+G) = -1
  // Pure Blue (B+B) = Carry +1 (+2)
  // Pure Red (R+R) = Carry -1 (-2)
  // Pure Green (G+G) = 0
  
  bool is_red = r > THRESH_RED;
  bool is_grn = g > THRESH_GRN;
  bool is_blu = b > THRESH_BLU;
  
  Serial.print("LOGIC OUT: ");
  
  if (is_blu && is_grn && !is_red) {
    Serial.println("CYAN -> Result: +1");
  } else if (is_blu && is_red && !is_grn) {
    Serial.println("MAGENTA -> Result: 0");
  } else if (is_red && is_grn && !is_blu) {
    Serial.println("YELLOW -> Result: -1");
  } else if (is_blu && !is_grn && !is_red) {
    Serial.println("PURE BLUE -> Result: +1 (Carry generated)"); // +1 + +1 = +2 (-1, Carry +1)
  } else if (is_red && !is_grn && !is_blu) {
    Serial.println("PURE RED -> Result: -1 (Carry generated)");  // -1 + -1 = -2 (+1, Carry -1)
  } else if (is_grn && !is_red && !is_blu) {
    Serial.println("PURE GREEN -> Result: 0");
  } else {
    Serial.println("UNDEFINED STATE (Noise or Invalid Mix)");
  }
}

void allLasersOff() {
  digitalWrite(PIN_A_RED, LOW); digitalWrite(PIN_A_GRN, LOW); digitalWrite(PIN_A_BLU, LOW);
  digitalWrite(PIN_B_RED, LOW); digitalWrite(PIN_B_GRN, LOW); digitalWrite(PIN_B_BLU, LOW);
}

void calibrate_system() {
  Serial.println(">>> CALIBRATING BASELINES...");
  allLasersOff();
  delay(100);
  
  // Measure Dark Noise
  as7341.readAllChannels();
  uint16_t noise_r = as7341.getChannel(AS7341_CHANNEL_630nm_F7);
  uint16_t noise_g = as7341.getChannel(AS7341_CHANNEL_515nm_F4);
  uint16_t noise_b = as7341.getChannel(AS7341_CHANNEL_445nm_F2);
  
  // Set Thresholds just above noise + margin
  // Ideally, fire lasers to find MAX brightness, then set threshold at 50%
  // For prototype, we will just use a safe margin above dark.
  
  THRESH_RED = noise_r + 200;
  THRESH_GRN = noise_g + 200;
  THRESH_BLU = noise_b + 200;
  
  Serial.print("New Thresholds: R="); Serial.print(THRESH_RED);
  Serial.print(" G="); Serial.print(THRESH_GRN);
  Serial.print(" B="); Serial.println(THRESH_BLU);
}
