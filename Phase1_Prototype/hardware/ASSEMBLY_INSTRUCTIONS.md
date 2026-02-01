# ASSEMBLY INSTRUCTIONS: MODULAR TERNARY OPTICAL BREADBOARD

## PHASE 1: PREPARATION
1.  **3D Printing:**
    *   Print 6x `module_laser_turret.scad` (Base + Holder). Material: PLA/PETG. Color: Any.
    *   Print 1x `module_mixing_core.scad`. **Material: WHITE PLA (Mandatory).**
    *   Print 1x `module_sensor_housing.scad`. Material: BLACK PLA (Recommended).
2.  **Base Board:**
    *   Cut a 24" x 24" sheet of MDF or Plywood.
    *   Mark the **Center Point (0,0)**.
    *   Draw a **10-inch Radius Circle** around the center. This is your "Laser Perimeter".

## PHASE 2: MECHANICAL ASSEMBLY

### 1. Mounting the Core
*   Place the **Mixing Core** at the exact center (0,0).
*   Rotate it so the Output Port faces "South" (towards you).
*   Screw it down using the 4 mounting holes.

### 2. Mounting the Lasers (The Arc)
*   You have 6 Lasers: Input A (R,G,B) and Input B (R,G,B).
*   Mark 6 points on your 10-inch circle.
    *   Spacing: Approx 15 degrees apart.
    *   Aim: Draw a line from each point to the Center. This is your "Beam Path".
*   Screw down the **Laser Turret Bases** at these 6 points.
*   **Install the Turrets:**
    *   Insert the M3 screws + Springs through the Turret Holder into the Base.
    *   Insert the Laser Diodes into the Holders. Secure with the side set-screw.

### 3. Installing the Conduits (Light Tunnels)
*   Cut your PVC/Aluminum tubes to length (measure distance from Laser Turret face to Mixing Core port).
*   **Paint the inside Black** if you haven't already.
*   Slide the tubes into the Mixing Core ports. Ideally, they should hover just in front of the Laser Turrets.

### 4. Sensor Installation
*   Solder header pins to your **AS7341 Sensor**.
*   Connect 4 wires (VCC, GND, SDA, SCL).
*   Slide the sensor into the `module_sensor_housing` slot.
*   Snap the housing onto the Output Port of the Mixing Core.

## PHASE 3: ELECTRONICS & WIRING

### 1. The Controller
*   Mount the breadboard to the corner of your base plate.
*   Insert the **ESP32** and **ULN2803** chip.

### 2. Wiring Logic
*   **Power:** Connect USB 5V to the Breadboard Power Rails.
*   **Ground:** Connect ESP32 GND to Breadboard GND.
*   **ULN2803:**
    *   Pin 9 (GND) -> Breadboard GND.
    *   Pin 10 (COM) -> 5V Rail (This is for the flyback diodes, important for inductive loads, good practice here too).
    *   Inputs 1-6 -> ESP32 Pins (13, 12, 14, 27, 26, 25).
    *   Outputs 1-6 -> **Negative Wire** of Lasers.
*   **Lasers:**
    *   **Positive Wire** of ALL Lasers -> 5V Rail.
    *   **Negative Wire** -> Corresponding ULN2803 Output Pin.

### 3. Sensor Wiring
*   VCC -> 3.3V (ESP32 3V3 pin). **Do not use 5V for STEMMA QT unless it has a regulator.**
*   GND -> GND.
*   SDA -> ESP32 Pin 21.
*   SCL -> ESP32 Pin 22.

## PHASE 4: CALIBRATION & FIRST LIGHT

1.  **Flash the Firmware:** Upload `ternary_logic_controller.ino` using Arduino IDE.
2.  **Mechanical Alignment:**
    *   Send Command: `ADD -1 0` (Fires Red A + Green B).
    *   Look at the Mixing Core. **Is the light hitting the center?**
    *   **Adjust:** Tighten/Loosen the 3 screws on the Laser Turret to steer the beam until it shoots straight down the tube into the mixer.
    *   Repeat for all 6 lasers.
3.  **System Check:**
    *   Open Serial Monitor (115200 baud).
    *   Type `CAL`. The system will measure the "Dark" baseline.
    *   Type `ADD 1 -1`. You should see the result "MAGENTA -> Result: 0".

**Congratulations! You have built a Ternary Photonic Computer.**
