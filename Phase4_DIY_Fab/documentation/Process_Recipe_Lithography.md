# DIY Lithography Process Recipe

## Overview
This document describes the complete process flow for fabricating optical waveguides using DIY photolithography. Target: 5-10μm features on LiNbO3 substrate.

## Pre-Fabrication Checklist

### Workspace Preparation
- [ ] Fume hood operational (100+ CFM)
- [ ] Emergency shower within 10 seconds reach
- [ ] Calcium gluconate gel available (for HF work)
- [ ] Fire extinguisher (Class ABC) accessible
- [ ] First aid kit stocked
- [ ] Chemical spill kit ready
- [ ] Waste containers labeled and sealed

### Personal Protection
- [ ] Full-face respirator fit-tested
- [ ] Butyl rubber gloves (HF) or nitrile (other)
- [ ] Chemical-resistant apron
- [ ] Long sleeves, long pants, closed shoes
- [ ] Hair tied back, no loose jewelry

## Process Flow

### Step 1: Substrate Preparation
**Goal:** Clean, dry substrate with proper surface energy for resist adhesion.

**Procedure:**
1. **Degrease:** Acetone soak (5 min) + ultrasonic if available
2. **Rinse:** DI water (30 seconds)
3. **Acid Clean:** HCl:H2O (1:10) dip (2 min) - removes metal ions
4. **Rinse:** DI water (30 seconds)
5. **Dehydration:** Hot plate at 150°C (10 min)
6. **Cool:** Allow to reach room temperature on hot plate

**Verification:** Water break test - DI water should sheet off uniformly, not bead up.

### Step 2: Photoresist Application
**Goal:** Uniform resist coating 1-5μm thick.

**Materials:**
- Shipley S1813 (1.3μm at 4000 RPM) or SU-8 2005 (5μm)

**Spin Coating (if spinner available):**
1. Center substrate on chuck
2. Apply resist (1-2ml for 10mm x 10mm chip)
3. Spin: 500 RPM (5 sec spread), then 4000 RPM (30 sec)
4. Edge bead removal with acetone swab

**Alternative - Dip Coating (no spinner):**
1. Immerse substrate vertically in resist (slow, steady motion)
2. Withdraw at 1-2 mm/sec
3. Drain excess (10 sec)
4. Level and allow solvent evaporation (5 min)

**Soft Bake:**
- S1813: 115°C hot plate (60 sec)
- SU-8: 65°C (1 min) → 95°C (2 min) (ramp slowly!)

**Verification:** Visual inspection - uniform color, no striations or bubbles.

### Step 3: Exposure
**Goal:** Pattern transfer from digital design to resist.

**DLP Projection Method:**
1. **Prepare Mask:** Convert GDSII/OASIS to PNG/BMP (black = expose, white = protect)
   - Resolution: Match DLP pixel size to desired feature
   - Invert: Negative resist requires inverted image
2. **Focus:** Adjust projection distance for sharpest image
   - Test pattern: Lines and spaces of various widths
   - Use microscope to verify focus
3. **Align:** Position substrate under projection area
   - Use microscope crosshairs or alignment marks
4. **Expose:**
   - S1813: 10-30 seconds (depends on UV intensity)
   - SU-8: 20-60 seconds
   - **Critical:** Do not move during exposure

**Contact Printing (if using photomask):**
1. Place chrome mask directly on resist (gentle contact)
2. Expose with UV source above
3. Exposure time: 5-15 seconds

**Verification:** Develop test strip (see Step 4) to check exposure dose.

### Step 4: Development
**Goal:** Remove exposed (positive) or unexposed (negative) resist.

**S1813 (Positive):**
1. Immerse in AZ300MIF developer
2. Agitate gently (10-30 seconds)
3. Rinse in DI water (30 seconds)
4. Blow dry with nitrogen

**SU-8 (Negative):**
1. Immerse in SU-8 developer (PGMEA)
2. Agitate (2-5 minutes)
3. Rinse in isopropyl alcohol
4. Blow dry with nitrogen

**Inspection:**
- Microscope check at 10x-40x
- Verify pattern fidelity
- Check for undercut (overdeveloped) or scumming (underdeveloped)

**Troubleshooting:**
- **Resist not clearing:** Increase development time or exposure dose
- **Resist washing away:** Decrease development time or exposure dose
- **Poor adhesion:** Improve dehydration bake, use HMDS primer

### Step 5: Etching (Lithium Niobate)
**Goal:** Transfer resist pattern into substrate.

**WARNING:** Hydrofluoric acid is extremely hazardous. Read MSDS completely.

**Wet Etch Recipe (LiNbO3):**
- **Etchant:** HF:HNO3 (1:2) with ethylene glycol buffer
- **Temperature:** Room temperature (or 40°C for faster etch)
- **Rate:** ~100 nm/min (varies with crystal orientation)
- **Target Depth:** 200-500 nm for waveguides

**Procedure:**
1. **Prepare etchant:** Add acids to water (never reverse!)
   - In fume hood, wearing full PPE
   - Use PTFE or polypropylene container
2. **Immerse sample:** Use Teflon wafer holder
3. **Agitate:** Gentle stirring for uniform etch
4. **Time:** Calculate based on etch rate (e.g., 3 min for 300nm)
5. **Quench:** Transfer immediately to DI water bath
6. **Rinse:** Multiple DI water baths (3x, 1 min each)
7. **Neutralize:** Soak in baking soda solution (5 min)
8. **Final rinse:** DI water, blow dry

**Alternative - Reactive Ion Etching (if equipment available):**
- **Gas:** CHF3 or SF6
- **Power:** 100-200W
- **Rate:** 50-100 nm/min
- **Better anisotropy than wet etch**

**Verification:**
- Profilometer measurement (if available)
- Microscope inspection of cross-section (cleave sample)
- Optical test: Light coupling into waveguide

### Step 6: Resist Stripping
**Goal:** Remove remaining resist without damaging substrate.

**Procedure:**
1. **Solvent Strip:** Acetone soak (5 min) + gentle agitation
2. **Rinse:** Isopropyl alcohol (30 sec)
3. **Rinse:** DI water (30 sec)
4. **Dry:** Nitrogen blow dry

**For stubborn resist (SU-8):**
- Piranha clean (H2SO4:H2O2, 3:1) - **EXTREME HAZARD**
- Or plasma ash (O2 plasma, 100W, 10 min)

**Verification:** Uniform surface, no resist residue visible under microscope.

### Step 7: Post-Fabrication Testing
**Goal:** Verify waveguide functionality.

**Visual Inspection:**
- Microscope: 10x-100x inspection
- Look for: Surface roughness, cracks, undercut, residue

**Optical Testing:**
1. **End-Fire Coupling:** Focus laser into waveguide facet
2. **Output Imaging:** Image exit facet with camera
3. **Loss Measurement:** Compare input/output power

**Acceptance Criteria:**
- Waveguides continuous, no breaks
- Sidewalls relatively smooth (<100 nm roughness)
- Light propagation observed

## Process Parameters Summary

| Parameter | S1813 Recipe | SU-8 Recipe |
|-----------|--------------|-------------|
| Resist Thickness | 1.3 μm | 5 μm |
| Soft Bake | 115°C, 60s | 65°C/95°C, 3min |
| Exposure Time | 10-30s | 20-60s |
| Development | 10-30s AZ300MIF | 2-5min PGMEA |
| Etch Depth | 200-500 nm | 200-500 nm |
| Etch Time | 2-5 min | 2-5 min |

## Common Defects & Solutions

| Defect | Cause | Solution |
|--------|-------|----------|
| Lifting resist | Poor adhesion | Better dehydration, HMDS primer |
| Scumming | Underexposure/underdevelopment | Increase dose/time |
| Undercut | Overdevelopment | Decrease development time |
| T-topping | Reflective substrate | Anti-reflective coating |
| Rough sidewalls | Etch rate too fast | Reduce temperature, agitation |
| Incomplete etch | Etch time too short | Increase time, verify etch rate |

## Safety Notes

### Hydrofluoric Acid (HF) - CRITICAL
- **Hazard:** Penetrates skin, destroys bone tissue, systemic toxicity
- **Antidote:** Calcium gluconate gel 2.5% (apply immediately if contact)
- **Emergency:** Call 911 for any HF exposure, even small amounts
- **Storage:** Polyethylene container, secondary containment
- **Disposal:** Neutralize with calcium hydroxide, hazardous waste pickup

### General Chemical Safety
- Never work alone with hazardous chemicals
- Know location of all safety equipment
- Have emergency contact numbers posted
- Maintain chemical inventory log
- Dispose of waste properly (never down drain)

## Documentation

**Required Records:**
- Date, operator, substrate ID
- All process parameters (times, temps, concentrations)
- Photographs of each step
- Test results and observations
- Any deviations from recipe

**Digital Log:**
- Store photos with metadata
- Backup process data
- Track yield statistics

---
*This recipe is a starting point. You will need to calibrate for your specific equipment and materials. Start with test patterns and iterate.*
