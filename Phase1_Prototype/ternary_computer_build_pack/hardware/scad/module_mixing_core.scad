// TERNARY OPTICAL COMPUTER - MIXING CORE MODULE
// Function: Integration Sphere for Chromatic Mixing

// --- PARAMETERS ---
sphere_id = 30; // Internal Diameter
wall = 4;
port_id = 14; // OD of the PVC/Tube conduit (approx 1/2 inch is 12.7mm, giving room)
port_len = 15;

// --- MAIN GEOMETRY ---

difference() {
    // 1. Outer Shell
    sphere(d = sphere_id + (wall*2), $fn=100);
    
    // 2. Internal Cavity (The Integration Chamber)
    sphere(d = sphere_id, $fn=100);
    
    // 3. Input Ports (6 Radial Inputs)
    // Arranged to bounce light, not hit center directly
    for(i=[0:60:300]) {
        rotate([0, 0, i]) 
        rotate([45, 0, 0]) // Enter from top hemisphere to hit bottom
        translate([0,0,10]) 
        cylinder(h=30, d=port_id, $fn=50);
    }
    
    // 4. Output Port (To Sensor)
    rotate([0,90,0]) translate([0,0,10]) cylinder(h=30, d=15, $fn=50);

    // 5. Lid Cut (So you can print it and paint inside white)
    translate([0,0,50]) cube([100,100,60], center=true);
}

// --- BAFFLE (Forces Mixing) ---
// Central pillar to block direct line of sight
intersection() {
    sphere(d = sphere_id + (wall*2), $fn=100); // Keep it inside bounds
    translate([0,0,-sphere_id/2]) cylinder(h=sphere_id, d=8, $fn=30);
}

// --- MOUNTING FEET ---
difference() {
    translate([0,0,-((sphere_id/2)+wall)]) cube([60, 60, 5], center=true);
    // Mounting Holes
    translate([25, 25, -25]) cylinder(h=20, d=4, center=true, $fn=20);
    translate([-25, -25, -25]) cylinder(h=20, d=4, center=true, $fn=20);
    translate([-25, 25, -25]) cylinder(h=20, d=4, center=true, $fn=20);
    translate([25, -25, -25]) cylinder(h=20, d=4, center=true, $fn=20);
    // Remove center from block
    sphere(d = sphere_id + (wall*2) + 2, $fn=100);
}

// --- NOTE ---
// Print in 2 halves if needed, or print with supports.
// PAINT INTERIOR WHITE before assembly!
