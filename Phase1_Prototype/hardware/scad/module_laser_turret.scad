// TERNARY OPTICAL COMPUTER - LASER TURRET MODULE
// Designed for "Plug and Play" Modular Breadboard
// Features: 3-Point Kinematic Tilt Adjustment (Tripod Style)

// --- PARAMETERS ---
laser_diameter = 12.2; // Standard 12mm Brass Module (use 6.2 for TO-18)
wall_thickness = 3;
base_width = 40;
base_length = 40;
screw_hole = 3.2; // M3 Clearance

// --- MODULES ---

module laser_holder() {
    difference() {
        // Main Body
        union() {
            cylinder(h=20, d=laser_diameter + (wall_thickness*2), $fn=60);
            // Flange for adjustment screws
            translate([0,0,0]) cylinder(h=4, r=20, $fn=3); // Triangular base
        }
        
        // Laser Hole
        translate([0,0,-1]) cylinder(h=22, d=laser_diameter, $fn=60);
        
        // Set Screw for Laser
        translate([0,0,10]) rotate([90,0,0]) cylinder(h=20, d=3, center=false, $fn=20);
        
        // Adjustment Screw Holes (Tripod Pattern)
        for(i=[0:120:240]) {
            rotate([0,0,i]) translate([15,0,-1]) cylinder(h=10, d=screw_hole, $fn=20);
        }
    }
}

module base_plate() {
    difference() {
        cube([base_width, base_length, 4], center=true);
        
        // Mounting Holes to Breadboard
        translate([15, 15, 0]) cylinder(h=10, d=4, center=true, $fn=20);
        translate([-15, -15, 0]) cylinder(h=10, d=4, center=true, $fn=20);
        translate([-15, 15, 0]) cylinder(h=10, d=4, center=true, $fn=20);
        translate([15, -15, 0]) cylinder(h=10, d=4, center=true, $fn=20);

        // Adjustment Screw Receivers (for M3 nuts or self-tap)
        for(i=[0:120:240]) {
            rotate([0,0,i]) translate([15,0,0]) cylinder(h=10, d=2.8, center=true, $fn=20); // Tight for tapping
        }
    }
}

// --- ASSEMBLY ---
// Translate to show exploded view
translate([0,0,15]) color("Cyan") laser_holder();
color("Gray") base_plate();

// --- INSTRUCTIONS ---
// 1. Print 1x Base and 1x Holder per laser.
// 2. Insert M3x20mm screws through Holder -> Spring -> Base.
// 3. Tightening screws independently aims the laser.
