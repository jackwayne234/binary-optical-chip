// TERNARY OPTICAL COMPUTER - SENSOR HOUSING
// Fits: Adafruit AS7341 Breakout Board
// Mates to: Mixing Core Output

// --- PARAMETERS ---
sensor_w = 18; // PCB Width approx
sensor_h = 18; // PCB Height approx
sensor_d = 5;  // PCB Thickness clearance
wall = 2;
mount_d = 15; // Mates to Mixing Core Output Port

module sensor_box() {
    difference() {
        // Body
        cube([sensor_w + wall*2, sensor_h + wall*2, sensor_d + 10 + wall], center=true);
        
        // PCB Slot
        translate([0,0,2]) cube([sensor_w, sensor_h, sensor_d + 20], center=true);
        
        // Light Path Hole (Front)
        rotate([90,0,0]) cylinder(h=50, d=8, center=true, $fn=30);
        
        // Wire Exit (Side)
        translate([0, 10, 0]) cube([10, 10, 5], center=true);
    }
}

module connector_tube() {
    difference() {
        cylinder(h=15, d=mount_d + wall, $fn=50);
        cylinder(h=16, d=mount_d, $fn=50); // Slips OVER the mixer port
    }
}

// --- ASSEMBLY ---
union() {
    translate([0,0,-10]) sensor_box();
    rotate([90,0,0]) translate([0, -10, -5]) connector_tube();
}
