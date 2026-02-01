# DIY Photolithography Equipment List

## Core Lithography System

### 1. Projection System
**Option A: DLP Projector Modification**
- **Item:** 1080p DLP projector (used, $50-100)
  - Models: Optoma HD142X, BenQ W1070, ViewSonic PJD7828HDL
  - Requirement: Must have accessible color wheel (for UV conversion)
- **UV LED Array:** 365nm or 405nm high-power LEDs ($30-60)
  - 10W minimum output
  - Collimating lenses
- **Modification:** Remove color wheel, replace white LED with UV
- **Expected Resolution:** 7-15μm (depends on projection distance)

**Option B: Mask Aligner (Professional)**
- **Item:** Used mask aligner from university surplus ($500-2000)
  - Models: Karl Suss MA6, Quintel Q4000
  - Resolution: 1-2μm
  - *Note:* Rare availability, requires networking to find

### 2. XY Positioning Stage
**Manual Stage (Budget)**
- **Item:** Compound microscope XY stage ($100-200)
  - Travel: 50mm x 50mm minimum
  - Resolution: 10μm per division
  
**Motorized Stage (Preferred)**
- **Item:** CNC router with precision lead screws ($300-600)
  - OpenBuilds ACRO System or similar
  - Stepper motors with microstepping
  - Repeatability: ±5μm

### 3. Wafer Handling
- **Vacuum Chuck:** DIY from aluminum block + aquarium pump ($30)
- **Wafer Tweezers:** Anti-static, flat tip ($15)
- **Wafer Storage:** Gel-Pak or waffle pack ($20)

## Photoresist & Chemistry

### Photoresist
- **Positive Resist:** Shipley S1813 or AZ1512 ($50/250ml)
  - Resolution: 1-2μm
  - Sensitivity: 365nm (i-line)
- **Negative Resist:** SU-8 2000 series ($80/100ml)
  - For thick structures (waveguides)
  - Resolution: 5-10μm

### Developers & Solvents
- **Developer:** AZ300MIF or Shipley 351 ($30)
- **Acetone:** Semiconductor grade ($20/gallon)
- **Isopropyl Alcohol:** 99% purity ($15/gallon)
- **Deionized Water:** Distilled water acceptable ($5/gallon)

### Etchants (Lithium Niobate)
- **Hydrofluoric Acid (HF):** 48% concentration ($50)
  - **WARNING:** Extreme hazard, requires calcium gluconate gel
- **Nitric Acid:** Concentrated ($30)
- **Ethylene Glycol:** Buffer component ($10)

## Safety Equipment (Non-Negotiable)

### Personal Protection
- **Respirator:** 3M 6800 full-face with acid gas cartridges ($150)
- **Gloves:** Butyl rubber (for HF), Nitrile (general) ($30/box)
- **Apron:** Chemical-resistant PVC ($20)
- **Emergency Shower:** Portable camping shower + bucket ($30)
- **Eyewash Station:** Bottled eyewash + mirror ($15)

### Ventilation
- **Fume Hood:** Converted range hood or DIY ($200-500)
  - Minimum 100 CFM
  - Activated carbon + HEPA filtration
  - Negative pressure workspace

### Chemical Storage
- **Acid Cabinet:** Polypropylene or wooden with acid-resistant coating ($150)
- **Spill Kit:** Neutralizing agents, absorbent pads ($50)
- **HF Antidote:** Calcium gluconate gel 2.5% ($40/tube)
  - **CRITICAL:** Keep within arm's reach when using HF

## Metrology & Inspection

### Microscopy
- **Inspection Microscope:** 10x-40x magnification ($100-300)
  - Reflected light capability
  - Digital camera attachment ($50)
- **USB Microscope:** 200x-1000x for quick checks ($30)

### Measurement
- **Digital Calipers:** 0.01mm resolution ($20)
- **Stage Micrometer:** Calibration standard ($25)
- **Optical Power Meter:** For testing waveguides ($100-300)

## Substrates

### Lithium Niobate (LiNbO3)
- **X-cut, Z-propagating:** Standard for electro-optic devices
- **Thickness:** 500μm or 1mm
- **Size:** 10mm x 10mm chips ($50-100 each)
- **Sources:**
  - University surplus
  - Alibaba (verify quality)
  - Del Mar Photonics
  - HC Photonics

### Silicon-on-Insulator (SOI)
- **Layer Stack:** 220nm Si / 2μm SiO2 / Si substrate
- **Size:** 10mm x 10mm chips ($30-60 each)
- **Source:** SOITEC samples, university partnerships

## Estimated Total Cost

**Budget Build:** $800-1200
- DLP projector method
- Manual XY stage
- Basic chemistry
- Essential safety

**Mid-Range Build:** $2000-3000
- Better optics
- Motorized stage
- Full safety setup
- Multiple resist types

**Note:** This does not include facility modifications (ventilation, plumbing, electrical). Budget additional $500-1000 for workspace preparation.

## Sourcing Strategy

1. **eBay/University Surplus:** Microscopes, stages, lab equipment
2. **Amazon/McMaster:** Hardware, safety equipment
3. **Chemical Suppliers:**
   - MicroChemicals (resists)
   - Sigma-Aldrich (solvents)
   - Local industrial suppliers (acids)
4. **Substrates:** Direct from manufacturers or academic collaborators

## Legal Considerations

- **Chemical Storage:** Check local regulations for HF possession
- **Waste Disposal:** Hazardous waste pickup services required
- **Zoning:** Home-based chemical work may violate HOA/lease agreements
- **Insurance:** Standard homeowner's may not cover chemical accidents

---
*Safety is not optional. If you cannot afford proper safety equipment, you cannot afford to do this project.*
