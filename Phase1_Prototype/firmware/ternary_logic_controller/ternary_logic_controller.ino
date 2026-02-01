/*
 * Wavelength-Division Ternary Logic Controller (Prototype v1)
 * -----------------------------------------------------------
 * Target: ESP32 DevKit V1
 * Sensors: Adafruit AS7341 (Spectral Sensor)
 * Actuators: 6x Laser Diodes via ULN2803 Driver
 * 
 * Logic Mapping (Balanced Ternary):
 * -1 (Red)   | 0 (Green)   | +1 (Blue)
 * 
 * Hardware Pinout (ESP32):
 * Input A: Red=12, Grn=13, Blu=14
 * Input B: Red=25, Grn=26, Blu=27
 * I2C: SDA=21, SCL=22
 */

#include <Wire.h>
#include <Adafruit_AS7341.h>

Adafruit_AS7341 as7341;

// --- Pin Definitions ---
// Input A (Left Bank)
const int PIN_A_RED = 12; // -1
const int PIN_A_GRN = 13; //  0
const int PIN_A_BLU = 14; // +1

// Input B (Right Bank)
const int PIN_B_RED = 25; // -1
const int PIN_B_GRN = 26; //  0
const int PIN_B_BLU = 27; // +1

// --- Calibration Thresholds (Default) ---
// These will need tuning based on your specific 3D printed chamber
uint16_t THRESHOLD_LOW = 100;   // Noise floor
uint16_t THRESHOLD_HIGH = 2000; // Strong signal (Pure Color)

// --- State Variables ---
int inputA = 0; // -1, 0, +1
int inputB = 0; // -1, 0, +1

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(1); }

  Serial.println("\n--- Opto-Ternary Prototype v1.0 ---");
  Serial.println("Initializing Hardware...");

  // Setup Laser Pins
  pinMode(PIN_A_RED, OUTPUT); pinMode(PIN_A_GRN, OUTPUT); pinMode(PIN_A_BLU, OUTPUT);
  pinMode(PIN_B_RED, OUTPUT); pinMode(PIN_B_GRN, OUTPUT); pinMode(PIN_B_BLU, OUTPUT);
  
  // Turn off all lasers
  allLasersOff();

  // Initialize Sensor
  if (!as7341.begin()){
    Serial.println("ERROR: AS7341 Sensor not found! Check wiring.");
    while(1) { delay(100); } // Halt
  }
  
  // Configure Sensor for Indoor/Lab use
  as7341.setATIME(100); // Integration time (100 = ~278ms)
  as7341.setASTEP(999);
  as7341.setGain(AS7341_GAIN_16X); // Adjust if saturating

  Serial.println("System Ready. Type 'HELP' for commands.");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    cmd.toUpperCase();
    processCommand(cmd);
  }
}

// --- Laser Control ---

void setInputA(int val) {
  // Clear A
  digitalWrite(PIN_A_RED, LOW);
  digitalWrite(PIN_A_GRN, LOW);
  digitalWrite(PIN_A_BLU, LOW);
  
  if (val == -1) digitalWrite(PIN_A_RED, HIGH);
  else if (val == 0) digitalWrite(PIN_A_GRN, HIGH);
  else if (val == 1) digitalWrite(PIN_A_BLU, HIGH);
  
  inputA = val;
  Serial.print("Input A set to: "); Serial.println(val);
}

void setInputB(int val) {
  // Clear B
  digitalWrite(PIN_B_RED, LOW);
  digitalWrite(PIN_B_GRN, LOW);
  digitalWrite(PIN_B_BLU, LOW);
  
  if (val == -1) digitalWrite(PIN_B_RED, HIGH);
  else if (val == 0) digitalWrite(PIN_B_GRN, HIGH);
  else if (val == 1) digitalWrite(PIN_B_BLU, HIGH);
  
  inputB = val;
  Serial.print("Input B set to: "); Serial.println(val);
}

void allLasersOff() {
  digitalWrite(PIN_A_RED, LOW); digitalWrite(PIN_A_GRN, LOW); digitalWrite(PIN_A_BLU, LOW);
  digitalWrite(PIN_B_RED, LOW); digitalWrite(PIN_B_GRN, LOW); digitalWrite(PIN_B_BLU, LOW);
}

// --- Logic & Measurement ---

void runLogic() {
  Serial.println("Reading Sensor...");
  delay(100); // Wait for lasers to stabilize/sensor to integrate

  if (!as7341.readAllChannels()){
    Serial.println("Error reading sensor data");
    return;
  }

  // Get raw spectral data
  uint16_t red = as7341.getChannel(AS7341_CHANNEL_630nm_F7);
  uint16_t grn = as7341.getChannel(AS7341_CHANNEL_515nm_F4);
  uint16_t blu = as7341.getChannel(AS7341_CHANNEL_445nm_F2);

  Serial.print("Spectrum [R,G,B]: ");
  Serial.print(red); Serial.print(", ");
  Serial.print(grn); Serial.print(", ");
  Serial.println(blu);

  // --- Chromatic Decoding Logic ---
  // Determine presence of wavelengths
  bool hasRed = red > THRESHOLD_LOW;
  bool hasGrn = grn > THRESHOLD_LOW;
  bool hasBlu = blu > THRESHOLD_LOW;

  // Determine "Double Intensity" (Carry detection)
  bool strongRed = red > THRESHOLD_HIGH;
  bool strongBlu = blu > THRESHOLD_HIGH;

  String result = "UNKNOWN";
  int sum = -99;
  int carry = 0;

  // Logic Table (Additive Mixing)
  // Note: Green (0) is effectively "neutral" in mixing
  
  if (strongBlu && !hasRed && !hasGrn) {
    result = "PURE BLUE (Double)";
    sum = -1; carry = 1; // 1 + 1 = 2 -> (1, -1) in balanced
  }
  else if (strongRed && !hasBlu && !hasGrn) {
    result = "PURE RED (Double)";
    sum = 1; carry = -1; // -1 + -1 = -2 -> (-1, 1) in balanced
  }
  else if (hasBlu && hasRed) {
    result = "PURPLE (Blue + Red)";
    sum = 0; carry = 0; // 1 + -1 = 0
  }
  else if (hasBlu && hasGrn) {
    result = "CYAN (Blue + Green)";
    sum = 1; carry = 0; // 1 + 0 = 1
  }
  else if (hasRed && hasGrn) {
    result = "YELLOW (Red + Green)";
    sum = -1; carry = 0; // -1 + 0 = -1
  }
  else if (hasGrn && !hasBlu && !hasRed) {
    result = "PURE GREEN";
    sum = 0; carry = 0; // 0 + 0 = 0
  }
  // Single inputs (should not happen if using 2 inputs, but for debug)
  else if (hasBlu) { result = "Single Blue (+1)"; sum = 1; }
  else if (hasRed) { result = "Single Red (-1)"; sum = -1; }
  else { result = "DARK / NO SIGNAL"; }

  Serial.print("Logic Result: "); Serial.println(result);
  Serial.print("Decoded: Sum="); Serial.print(sum);
  Serial.print(", Carry="); Serial.println(carry);
}

// --- Calibration ---

void calibrate() {
  Serial.println("Starting Calibration...");
  Serial.println("Ensure chamber is sealed/dark.");
  allLasersOff();
  delay(500);
  
  as7341.readAllChannels();
  uint16_t noise = as7341.getChannel(AS7341_CHANNEL_515nm_F4); // Use Green as reference
  
  THRESHOLD_LOW = noise * 2 + 50; // Safety margin
  Serial.print("New Noise Floor: "); Serial.println(noise);
  Serial.print("Set THRESHOLD_LOW to: "); Serial.println(THRESHOLD_LOW);
  
  Serial.println("Now testing Laser Intensity...");
  // Quick flash of Blue to test High
  digitalWrite(PIN_A_BLU, HIGH);
  delay(200);
  as7341.readAllChannels();
  uint16_t highVal = as7341.getChannel(AS7341_CHANNEL_445nm_F2);
  digitalWrite(PIN_A_BLU, LOW);
  
  THRESHOLD_HIGH = highVal * 0.8; // 80% of single max
  Serial.print("Measured Single Blue: "); Serial.println(highVal);
  Serial.print("Set THRESHOLD_HIGH to: "); Serial.println(THRESHOLD_HIGH);
}

// --- Command Parser ---

void processCommand(String cmd) {
  if (cmd == "HELP") {
    Serial.println("Commands:");
    Serial.println("  SET A [val]  -> Set Input A (-1, 0, 1)");
    Serial.println("  SET B [val]  -> Set Input B (-1, 0, 1)");
    Serial.println("  RUN          -> Read Sensor & Compute");
    Serial.println("  CAL          -> Auto-calibrate thresholds");
    Serial.println("  OFF          -> Turn all lasers off");
  }
  else if (cmd.startsWith("SET A")) {
    int val = cmd.substring(6).toInt();
    setInputA(val);
  }
  else if (cmd.startsWith("SET B")) {
    int val = cmd.substring(6).toInt();
    setInputB(val);
  }
  else if (cmd == "RUN") {
    runLogic();
  }
  else if (cmd == "CAL") {
    calibrate();
  }
  else if (cmd == "OFF") {
    allLasersOff();
    Serial.println("Lasers OFF");
  }
  else {
    Serial.println("Unknown command. Type HELP.");
  }
}
