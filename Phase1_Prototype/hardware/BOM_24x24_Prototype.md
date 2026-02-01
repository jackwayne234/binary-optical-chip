# BILL OF MATERIALS: MODULAR TERNARY OPTICAL BREADBOARD (24" x 24")

## 1. 3D PRINTED PARTS (From generated .scad files)
*   **6x Laser Turret - Holder** (Print in PLA/PETG)
*   **6x Laser Turret - Base** (Print in PLA/PETG)
*   **1x Mixing Core** (Print in **WHITE PLA** - Critical for reflectivity)
*   **1x Sensor Housing** (Print in BLACK PLA - Critical for light blocking)

## 2. ELECTRONICS
### Controller & Drivers
*   **1x ESP32 Development Board** (ESP32-DevKitC V4 or generic NodeMCU-32S).
    *   *Verified Option:* **HiLetgo ESP-WROOM-32 ESP-32S**.
    *   *Why:* Fast, WiFi enabled for telemetry, 3.3V logic.
    *   *Note:* Most ESP32 boards work. Ensure it has the "EN" and "BOOT" buttons.
*   **1x ULN2803A Darlington Transistor Array**.
    *   *Why:* The ESP32 cannot power lasers directly. This chip acts as a switch.
    *   *Package:* DIP-18 (Breadboard friendly).
*   **1x Breadboard** (830 Point / Full Size).
*   **1x Jumper Wire Kit** (Male-Male, Male-Female).

### Sensors
*   **1x Adafruit AS7341 10-Channel Light/Color Sensor Breakout**.
    *   *Part ID:* Adafruit 4698.
    *   *Interface:* I2C (STEMMA QT / Qwiic compatible).

### Light Sources
*   **2x Red Laser Module** (650nm).
    *   *Amazon Search:* "650nm 5mW Laser Dot Module 12mm"
    *   *Typical Price:* ~$12 for a pack of 10.
    *   *Look for:* Brass cylindrical housing (approx 12mm diameter), red/black wires.
*   **2x Green Laser Module** (520nm or 532nm).
    *   *Amazon Search:* "520nm Laser Diode Module 12mm" OR "532nm Laser Module 5V"
    *   *Typical Price:* ~$8 - $12 each.
    *   *Note:* Green is more expensive. 520nm (Direct Diode) is more stable than 532nm (DPSS) but either works.
*   **2x Blue/Violet Laser Module** (405nm).
    *   *Amazon Search:* "405nm Laser Dot Module 12mm"
    *   *Dimensions:* **0.47" (12mm) Diameter** is the critical part. Length is usually 1.2" - 1.8" (30-45mm), which is fine.
    *   *Typical Price:* ~$6 - $10 each.
    *   *Warning:* 405nm is dim to the eye but reacts strongly with fluorescent materials.
*   **Important:** Ensure all lasers have a **12mm diameter brass housing** to fit the 3D printed turrets. Avoid the "KY-008" PCB-mounted versions unless you want to desolder them.

### Power
*   **1x 5V 2A USB Power Supply** (Phone charger works).
*   **1x USB Cable** (Micro-USB or USB-C depending on ESP32).

## 3. HARDWARE & STRUCTURE
### Base Board
*   **1x MDF or Plywood Sheet** (24" x 24" x 0.5").
    *   *Alt:* Aluminum sheet if budget allows.

### Alignment Hardware (For Laser Turrets)
*   **18x M3 x 20mm Screws** (Socket Head Cap Screws preferred).
*   **18x M3 Nuts**.
*   **18x Small Compression Springs** (Fits over M3 screw, approx 5mm diameter).
    *   *Function:* These provide the tension for the "Tripod" tilt adjustment.

### Conduits (Light Tunnels)
*   **Aluminum Tubing (Recommended)**
    *   **Quantity:** 2x 36-inch rods (Cut them to 9 inches each to get 6 pieces).
    *   **Dimensions:** **1/2 inch (12.7mm) Outer Diameter**.
    *   *Why:* Matches the 3D print perfectly, light-proof, looks professional.
    *   *Where to buy:* Home Depot / Lowes (in the "Metal Shapes" aisle) or Amazon ("1/2 inch aluminum round tube").
    *   *Note:* You will need a simple hacksaw to cut them.
*   **Alternate (PVC):**
    *   If you use 1/2" PVC, the OD is larger (~21mm). You must modify the SCAD file `port_id` parameter to `22` before printing the Mixing Core.

## 4. TOOLS
*   **3D Printer** (Bambu Lab A1).
*   **Soldering Kit:**
    *   **Iron:** Any adjustable temperature 60W soldering iron (e.g., "Plusivo" or generic kits on Amazon ~$20).
    *   **Solder:** **60/40 Rosin Core Solder** (0.8mm diameter). Leaded solder is much easier for beginners than lead-free.
    *   **Flux:** **Rosin Paste Flux** or a **Flux Pen**. (Makes the solder stick instantly).
    *   **Tip Cleaner:** Brass wire sponge (better than a wet sponge).
*   **Screwdriver** (M3 Hex/Phillips).
*   **Drill** (for mounting modules to base board).
