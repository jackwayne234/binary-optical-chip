# OPERATIONAL RISK MANAGEMENT (ORM) ASSESSMENT
## Phase 4: DIY Semiconductor Fabrication
**Operation:** GARAGE-FAB-001 (Photolithography with Hazardous Chemicals)
**Date:** [TO BE COMPLETED BEFORE FIRST OPERATION]
**Operator:** [NAME]
**Review Authority:** [SELF/SAFETY OFFICER]

---

## 1. MISSION ANALYSIS

### Primary Mission
Fabricate photonic waveguide structures using wet chemical etching on lithium niobate substrates in a non-commercial, residential setting.

### Critical Tasks
1. Handle concentrated hydrofluoric acid (HF) for substrate etching
2. Operate UV exposure equipment
3. Manage chemical waste streams
4. Maintain contamination control

### Constraints
- Residential setting (not industrial lab)
- Limited ventilation capacity
- No on-site emergency medical support
- Potential HOA/lease restrictions

---

## 2. HAZARD IDENTIFICATION

### CHEMICAL HAZARDS

#### H1: Hydrofluoric Acid (HF) - CRITICAL
**Properties:**
- Concentration: 48% (anhydrous)
- pH: <1 (highly acidic)
- Special Hazard: Penetrates skin, attacks bone (calcium sequestration)
- LD50: Lethal at small exposures without immediate treatment

**Exposure Routes:**
- Dermal (skin contact)
- Inhalation (vapors)
- Ocular (eye contact)
- Ingestion (accidental)

**Symptoms:**
- Delayed pain (may not feel immediate burning)
- White/gray skin discoloration
- Systemic fluoride toxicity (cardiac arrest)

#### H2: Nitric Acid (HNO3) - HIGH
**Properties:**
- Concentration: Concentrated (68-70%)
- Strong oxidizer
- Generates toxic NOx fumes when mixed with organics

**Exposure Routes:**
- Inhalation (fumes)
- Dermal
- Ocular

#### H3: Photoresist Solvents (PGMEA, Acetone) - MODERATE
**Properties:**
- Volatile organic compounds
- Flammable
- Central nervous system depressants at high exposure

#### H4: Developer Solutions (TMAH) - MODERATE
**Properties:**
- Strong base
- Skin/eye irritant
- Toxic if ingested

### PHYSICAL HAZARDS

#### P1: UV Radiation Exposure
**Source:** UV LED array (365nm-405nm)
**Risk:** Retinal damage, skin burns
**Distance:** Hazard zone within 1 meter

#### P2: Sharp Objects
**Sources:** Broken glassware, wafer edges, cleaved substrates
**Risk:** Lacerations, blood exposure

#### P3: Electrical Hazards
**Sources:** 120V equipment, UV power supplies
**Risk:** Electrocution, especially near water/chemicals

#### P4: Ergonomic Hazards
**Sources:** Extended microscope use, awkward postures
**Risk:** Eye strain, repetitive stress injuries

### ENVIRONMENTAL HAZARDS

#### E1: Inadequate Ventilation
**Risk:** Chemical vapor accumulation, respiratory exposure
**Threshold:** Fume hood must maintain 100+ CFM at face

#### E2: Temperature Extremes
**Risk:** Heat stress (hot plate use), cold (winter garage work)

#### E3: Clutter/Obstacles
**Risk:** Tripping, knocking over chemicals, delayed egress

---

## 3. RISK ASSESSMENT MATRIX

### Risk Severity Levels
| Code | Level | Definition | Medical Treatment |
|------|-------|------------|-------------------|
| C | Catastrophic | Death or permanent disability | Emergency response, hospitalization |
| H | High | Severe injury, hospitalization | Immediate medical care |
| M | Moderate | Significant injury, lost work time | Medical treatment required |
| L | Low | Minor injury, first aid only | Self-treatment |
| N | Negligible | No injury, near miss | None |

### Probability Levels
| Code | Level | Definition |
|------|-------|------------|
| A | Almost Certain | Will occur without controls |
| B | Likely | Probably will occur |
| C | Possible | May occur |
| D | Unlikely | Not expected, but possible |
| E | Rare | Very unlikely |

### Risk Matrix
| Severity \ Probability | A (Almost Certain) | B (Likely) | C (Possible) | D (Unlikely) | E (Rare) |
|------------------------|-------------------|------------|--------------|--------------|----------|
| **C (Catastrophic)** | CRITICAL | CRITICAL | HIGH | HIGH | MEDIUM |
| **H (High)** | CRITICAL | HIGH | HIGH | MEDIUM | MEDIUM |
| **M (Moderate)** | HIGH | MEDIUM | MEDIUM | LOW | LOW |
| **L (Low)** | MEDIUM | LOW | LOW | LOW | NEGLIGIBLE |
| **N (Negligible)** | LOW | NEGLIGIBLE | NEGLIGIBLE | NEGLIGIBLE | NEGLIGIBLE |

---

## 4. HAZARD RISK ASSESSMENT

### H1: Hydrofluoric Acid (HF)
**Initial Risk:** Catastrophic (C) x Likely (B) = **CRITICAL**

**Risk Narrative:**
Without proper controls, HF exposure is almost certain over multiple operations. Any significant exposure is catastrophic (bone destruction, systemic toxicity, potential death).

**Controls:**
1. **Engineering Controls:**
   - Fume hood with 100+ CFM (verified with anemometer)
   - Secondary containment trays (polypropylene)
   - Emergency shower within 10 seconds
   - Calcium gluconate gel at workstation

2. **Administrative Controls:**
   - Two-person rule (never work alone with HF)
   - Buddy system with visual contact
   - Pre-operation safety brief
   - HF-specific training completion
   - Signed risk acknowledgment

3. **PPE (Personal Protective Equipment):**
   - Full-face respirator with acid gas cartridges (fit-tested)
   - Butyl rubber gloves (HF-resistant, not nitrile)
   - Chemical-resistant apron
   - Long sleeves, long pants, closed shoes
   - Emergency change of clothes nearby

**Residual Risk:** High (H) x Unlikely (D) = **MEDIUM**

**Risk Acceptance Authority:** Self (with documented training)

---

### H2: Nitric Acid (HNO3)
**Initial Risk:** High (H) x Possible (C) = **HIGH**

**Controls:**
- Same ventilation/PPE as HF
- Never mix with organics (explosion risk)
- Secondary containment
- Neutralizing agents available

**Residual Risk:** Medium (M) x Unlikely (D) = **LOW**

---

### H3: Solvent Exposure
**Initial Risk:** Moderate (M) x Likely (B) = **HIGH**

**Controls:**
- Fume hood use mandatory
- Nitrile gloves (adequate for solvents)
- Quantity limits (no bulk storage)
- Fire extinguisher (Class B) accessible

**Residual Risk:** Low (L) x Unlikely (D) = **LOW**

---

### H4: UV Radiation
**Initial Risk:** High (H) x Possible (C) = **HIGH**

**Controls:**
- Interlocked enclosure (UV off when door open)
- UV-blocking safety glasses
- Warning signs posted
- Never look directly at UV source

**Residual Risk:** Low (L) x Unlikely (D) = **LOW**

---

## 5. GO/NO-GO CRITERIA

### PRE-OPERATION CHECKLIST

#### CRITICAL ITEMS (Any NO = NO-GO)
- [ ] Calcium gluconate gel present and accessible
- [ ] Emergency shower functional and within 10 seconds
- [ ] Fume hood operational (verified airflow)
- [ ] Full-face respirator available and fit-tested
- [ ] Butyl rubber gloves available
- [ ] Buddy present and briefed
- [ ] Emergency contact numbers posted
- [ ] Fire extinguisher accessible
- [ ] First aid kit stocked
- [ ] Chemical spill kit ready

#### REQUIRED ITEMS (Any NO = DELAY OPERATION)
- [ ] All chemicals properly labeled
- [ ] Secondary containment in place
- [ ] Waste containers available and labeled
- [ ] Workspace clear of clutter
- [ ] Proper lighting functional
- [ ] Phone charged and accessible
- [ ] Weather conditions acceptable (no extreme heat/cold)
- [ ] No distractions expected (phone on silent, no visitors)

#### RECOMMENDED ITEMS (NO = PROCEED WITH CAUTION)
- [ ] Emergency change of clothes nearby
- [ ] Eye wash station available
- [ ] Neutralizing agents prepared
- [ ] Process documentation printed
- [ ] Timer/stopwatch available

### DECISION MATRIX

| Condition | Action |
|-----------|--------|
| All Critical + All Required = YES | **GO** - Proceed with operation |
| Any Critical = NO | **NO-GO** - Do not operate. Correct deficiency. |
| All Critical = YES, Any Required = NO | **DELAY** - Address required items before proceeding. |
| Fatigue/Illness/Medication | **NO-GO** - Operator unfit for hazardous work. |
| Weather emergency | **NO-GO** - Delay until conditions improve. |
| Alone (no buddy) | **NO-GO** - Never work alone with HF. |

---

## 6. EMERGENCY PROCEDURES

### HF EXPOSURE - IMMEDIATE ACTION

#### Skin Contact
1. **SECONDS MATTER** - Begin immediately
2. Remove contaminated clothing
3. Flood area with water (15+ minutes)
4. **Apply calcium gluconate gel** - massage into skin
5. Call 911 immediately - even for small exposures
6. Continue gel application until medical help arrives
7. Do NOT use neutralizing agents on skin

#### Eye Contact
1. Flush eyes with water (eyewash or gentle stream)
2. 15+ minutes continuous flushing
3. Hold eyelids open
4. Call 911 immediately
5. Do NOT apply calcium gluconate to eyes

#### Inhalation
1. Remove to fresh air immediately
2. Call 911
3. Monitor for breathing difficulties
4. Begin CPR if necessary
5. Medical evaluation mandatory even if asymptomatic

#### Ingestion
1. Do NOT induce vomiting
2. Drink large quantities of water or milk
3. Call 911 immediately
4. Call Poison Control: 1-800-222-1222

### CHEMICAL SPILL

#### Small Spill (<100ml)
1. Alert buddy
2. Don appropriate PPE
3. Contain spill (dike with absorbent)
4. Neutralize if appropriate (soda ash for acids)
5. Absorb with spill pads
6. Dispose as hazardous waste
7. Decontaminate area

#### Large Spill (>100ml) or HF Spill
1. **EVACUATE** - Leave area immediately
2. Alert others
3. Call 911 (for HF)
4. Do NOT attempt cleanup
5. Secure area
6. Contact hazardous materials response

### FIRE

#### Small Fire (extinguisher capable)
1. Alert buddy
2. Activate fire extinguisher (PASS method)
3. Evacuate if fire grows
4. Call 911

#### Large Fire
1. **EVACUATE** immediately
2. Alert others
3. Call 911
4. Do NOT re-enter
5. Account for all personnel

### MEDICAL EMERGENCY (Non-HF)

1. Call 911 if serious
2. Provide first aid within training limits
3. Do NOT move injured person unless immediate danger
4. Stay with victim until help arrives
5. Document incident

---

## 7. RISK MITIGATION SUMMARY

### Engineering Controls (Most Effective)
| Control | Status | Verification |
|---------|--------|--------------|
| Fume hood (100+ CFM) | ☐ | Anemometer reading: ___ CFM |
| Secondary containment | ☐ | Visual inspection |
| Emergency shower | ☐ | Flow test: ___ GPM |
| UV interlock | ☐ | Functional test |
| Eyewash station | ☐ | Flow test |

### Administrative Controls
| Control | Status | Notes |
|---------|--------|-------|
| Two-person rule | ☐ | Buddy: _________ |
| Pre-op briefing | ☐ | Time: _________ |
| Training current | ☐ | HF training date: _________ |
| MSDS accessible | ☐ | Location: _________ |
| Emergency numbers posted | ☐ | Verified: _________ |

### PPE
| Item | Status | Inspection |
|------|--------|------------|
| Full-face respirator | ☐ | Fit test current: _________ |
| Butyl rubber gloves | ☐ | No defects: _________ |
| Chemical apron | ☐ | Clean/undamaged: _________ |
| UV safety glasses | ☐ | Available: _________ |
| Emergency clothes | ☐ | Nearby: _________ |

---

## 8. SUPERVISION AND REVIEW

### Pre-Operation Brief
**Conducted By:** _______________ **Date/Time:** _______________
**Attendees:** _______________

**Topics Covered:**
- [ ] Mission overview
- [ ] Hazard review (emphasis on HF)
- [ ] PPE requirements
- [ ] Emergency procedures
- [ ] Go/No-Go criteria
- [ ] Questions/concerns addressed

### Post-Operation Review
**Conducted By:** _______________ **Date/Time:** _______________

**Operational Summary:**
- Tasks completed: _______________
- Deviations from plan: _______________
- Issues encountered: _______________
- Near misses: _______________

**Lessons Learned:**
1. _______________
2. _______________
3. _______________

**Recommendations:**
1. _______________
2. _______________
3. _______________

---

## 9. DOCUMENTATION REQUIREMENTS

### Required Records
- [ ] ORM Assessment completed (this document)
- [ ] Pre-operation checklist completed
- [ ] Chemical inventory log
- [ ] Waste disposal records
- [ ] Incident/near-miss reports (if any)
- [ ] Post-operation review completed

### Retention
- ORM Assessments: 3 years
- Training records: Duration + 3 years
- Incident reports: 5 years
- Medical surveillance: 30 years (if applicable)

---

## 10. SIGNATURES

**Operator:**
I have read, understand, and will comply with this ORM assessment. I am medically fit, properly trained, and have all required PPE.

Signature: _________________ Date: _________ Time: _______

**Buddy/Safety Observer:**
I have been briefed on my responsibilities. I understand the emergency procedures and will maintain visual contact with the operator.

Signature: _________________ Date: _________ Time: _______

**Review Authority:**
This ORM assessment has been reviewed and is approved for execution under the specified controls.

Signature: _________________ Date: _________ Time: _______

---

**END OF ORM ASSESSMENT**

*Remember: Complacency kills. Every operation, every time, full ORM.*
