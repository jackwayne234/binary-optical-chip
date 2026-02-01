# Phase 4 Activation Decision Matrix

## Decision Framework

### Primary Path (Phase 3): Commercial Fabrication
**Goal:** Partner with foundry or MPW service for professional chip fabrication

**Success Criteria:**
- Secure $30k-50k funding for MPW run
- OR establish university partnership with lab access
- OR find commercial partner willing to fabricate prototypes

**Timeline:** 6 months from Phase 2 completion

### Contingency Path (Phase 4): DIY Fabrication
**Goal:** Build garage-scale fab for proof-of-concept chips

**Trigger Conditions:**
- No funding secured after 6 months of active pursuit
- MPW quotes exceed $50k for prototype run
- Foundry lead times exceed 12 months
- University partnerships fail to materialize
- **Strategic decision:** DIY provides faster iteration for research

## Evaluation Criteria

### Funding Status (Weight: 40%)
| Status | Score | Action |
|--------|-------|--------|
| $50k+ secured | 10 | Proceed Phase 3 |
| $20-50k secured | 7 | Negotiate reduced scope Phase 3 |
| $10-20k secured | 5 | Hybrid approach (DIY + limited MPW) |
| <$10k secured | 2 | Activate Phase 4 |
| $0 secured | 0 | Activate Phase 4 |

### Partnership Status (Weight: 30%)
| Status | Score | Action |
|--------|-------|--------|
| University lab committed | 10 | Proceed Phase 3 |
| Active negotiations | 6 | Continue Phase 3 pursuit |
| Initial contacts only | 3 | Parallel Phase 4 prep |
| No contacts | 0 | Activate Phase 4 |

### Timeline Pressure (Weight: 20%)
| Status | Score | Action |
|--------|-------|--------|
| No deadline | 10 | Flexible approach |
| 12+ months available | 7 | Standard Phase 3 timeline |
| 6-12 months | 4 | Accelerated Phase 3 or DIY |
| <6 months | 0 | Activate Phase 4 |

### Technical Requirements (Weight: 10%)
| Feature Size Needed | Score | Action |
|---------------------|-------|--------|
| <1μm | 0 | Must use Phase 3 (DIY insufficient) |
| 1-5μm | 5 | Phase 3 preferred, DIY possible |
| 5-10μm | 10 | DIY viable |
| >10μm | 10 | DIY ideal |

## Scoring

**Total Score = (Funding × 0.4) + (Partnership × 0.3) + (Timeline × 0.2) + (Technical × 0.1)**

### Decision Thresholds
- **Score 8-10:** Proceed with Phase 3 (Commercial)
- **Score 5-7:** Hybrid approach (DIY simple structures, MPW complex)
- **Score 0-4:** Activate Phase 4 (DIY Fab)

## Activation Protocol

### Step 1: Assessment (Month 6 of Phase 2)
- Review all funding applications
- Assess partnership negotiations
- Calculate total score

### Step 2: Decision Point
- **If Score ≥ 8:** Continue Phase 3 planning
- **If Score ≤ 4:** Initiate Phase 4 immediately
- **If Score 5-7:** Evaluate hybrid options

### Step 3: Phase 4 Startup (If Activated)
**Month 1-2: Planning & Sourcing**
- Finalize workspace design
- Order safety equipment (PRIORITY)
- Source DLP projector and optics
- Order initial chemical supply

**Month 3-4: Setup & Testing**
- Install ventilation/safety systems
- Assemble lithography tool
- Calibrate system with test patterns
- Practice process on dummy substrates

**Month 5-6: Process Development**
- Optimize resist process
- Calibrate etch rates
- Produce first test structures
- Iterate and improve

**Month 7+: Production**
- Fabricate ternary optical devices
- Test and characterize
- Document results

## Risk Mitigation

### Phase 4 Risks
| Risk | Mitigation |
|------|------------|
| Insufficient resolution | Accept larger feature sizes, redesign for 5-10μm |
| Safety incident | Rigorous training, never work alone, proper PPE |
| Chemical supply issues | Stockpile critical materials, multiple suppliers |
| Equipment failure | Build modular system, easy component replacement |
| Process not working | Extensive testing on dummy substrates first |

### Reversion to Phase 3
Even after activating Phase 4, continue pursuing:
- Grant applications
- University partnerships
- Commercial fab relationships

**If funding/partnerships materialize during Phase 4:**
- Pause DIY work
- Proceed with commercial fabrication
- Maintain DIY capability for rapid prototyping

## Budget Comparison

### Phase 3 (Commercial MPW)
- **Setup Cost:** $0 (external fab)
- **Per Run Cost:** $10k-50k
- **Resolution:** <1μm achievable
- **Timeline:** 6-12 months (including queue)
- **Risk:** High cost, long lead times, limited iterations

### Phase 4 (DIY Fab)
- **Setup Cost:** $2k-5k
- **Per Run Cost:** $50-200 (materials only)
- **Resolution:** 5-10μm (limited)
- **Timeline:** 2-3 months to operational
- **Risk:** Safety hazards, lower resolution, time intensive

## Recommendation

**Default Strategy:**
1. Pursue Phase 3 aggressively for 6 months
2. Prepare Phase 4 in parallel (low-cost prep)
3. Make go/no-go decision at Month 6
4. If Phase 3 fails, immediately activate Phase 4
5. Continue seeking Phase 3 opportunities even during DIY work

**The goal is chips, not pride.** Use whatever path gets working ternary optical devices into your hands fastest.

---
*Decision Date: [To be filled at Month 6 of Phase 2]*
*Decision Score: [Calculate based on criteria above]*
*Decision: [Phase 3 / Hybrid / Phase 4]*
*Rationale: [Document reasoning]*
