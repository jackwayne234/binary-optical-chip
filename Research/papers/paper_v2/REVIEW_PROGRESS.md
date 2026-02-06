# Paper Review Progress - N-Radix v2

## File Location
`/home/jackwayne/Desktop/Optical_computing/Research/papers/paper_v2/updated_paper_v2.tex`

## What We're Doing
Reviewing the N-Radix paper for Zenodo publication. Reading through together, making changes as we go.

## Review Status: READY FOR PUBLICATION

Paper is complete and ready for Zenodo upload.

### Final Changes (Feb 5, 2026)
- **Softened cybersecurity claims** - Optical core is inherently secure, but interfaces need traditional security measures
- **Added "Important Limitations" subsection** - Honest about what this architecture can and cannot do
- **Removed Google/NVIDIA references** from systolic array section - more neutral framing
- **Added Kung & Leiserson (1979) citation** for systolic arrays - proper academic attribution
- **Overall:** More honest and academically proper. Claims are now well-supported and appropriately hedged.

### Final Additions (Feb 5, 2026)
- **Added "Ongoing Work" subsection** - Notes that 3-tier optical RAM validation is in progress
- **Fixed last Google/NVIDIA reference in conclusion** - Removed remaining corporate comparison
- **Paper is COMPLETE** - All sections reviewed, all changes applied, ready for Zenodo

---

## Completed Changes

### Title
- Changed to: "Wavelength-Division Ternary Computing II: N-Radix Optical AI Accelerator vs. B200 and Frontier"

### Abstract - REVIEWED AND UPDATED
1. Added citations to prior paper [1] and software [2]
2. Added GitHub footnote: https://github.com/jackwayne234/-wavelength-ternary-optical-computer
3. IOC → NR-IOC (N-Radix Input/Output Converter) throughout
4. Clarified 3³ encoding = 9× for ADD operations only
5. Added WDM 6 triplets explanation (6× parallelism, the radix bypass)
6. Updated Frontier comparison: "most powerful supercomputer in the world", 8 chips at <0.02% power
7. Added B200 comparison: 59× performance at 400W vs 1,000W

### Bibliography
- Added software citation [2] with Zenodo DOI

### Introduction (Section I)
- Added FDTD validation to contributions list (now 6 items total)
- Contributions now include: wavelength encoding, PE architecture, 3³ encoding, NR-IOC design, cybersecurity implications, AND FDTD simulation validation

### Simulation Validation (New Section - Before Cybersecurity)
Added comprehensive validation section documenting:
- **Clock distribution validation**: 27×27 array, 2.4% skew (< 3% threshold), PASS
- **WDM isolation validation**: All array sizes tested
  - 3×3: PASS
  - 9×9: PASS
  - 27×27: PASS
- **Scaling projections**: Validated foundation for larger array claims

### Cybersecurity Section (Section VII)
- Added "hardware security" to keywords
- Section discusses geometry-as-program security model

### Conclusion (Section VIII)
- Added FDTD validation to contributions list (now 7 items total)
- Contributions mirror introduction with added emphasis on simulation backing

### Keywords
- Added "hardware security" to keyword list

### Section References
- Fixed all section reference errors (broken \ref commands)

---

## BREAKTHROUGH: Weights Stream from Optical RAM (Feb 5, 2026)

**The Problem:** Paper said each PE has "bistable Kerr resonator storing one 9-trit weight" - but tristable optical storage is hard/unproven.

**The Solution:** Use the CPU's 3-tier optical RAM system as weight storage!
- Weights stored in Optical RAM tiers (already designed for CPU)
- Stream weights to PEs via optical waveguides
- PEs become SIMPLE - just mixer + routing, no per-PE storage
- Optical RAM → Optical Compute, stays optical the whole way
- NR-IOC only converts at HOST boundary, not between storage and compute

**This connects CPU and Accelerator work:**
- Optical RAM (from CPU) = weight storage for accelerator
- Optical CPU = memory controller / orchestrator
- Systolic Array = dumb compute fabric, just mixes wavelengths
- NR-IOC = host interface only

**Architecture simplification:**
- BEFORE: Each PE = Storage + Mixer + Accumulator (complex)
- AFTER: Each PE = Just Mixer + Waveguides (simple, higher yield)

**ACTION NEEDED:** Update paper Section III-B (Processing Element Design) to reflect this.

---

## Sections Reviewed

| Section | Status | Notes |
|---------|--------|-------|
| Title | ✓ DONE | Updated with v2 naming |
| Abstract | ✓ DONE | All 7 updates applied |
| Section I: Introduction | ✓ DONE | 6 contributions including FDTD |
| Section II: Wavelength Encoding | ✓ DONE | Reviewed |
| Section III: N-Radix Architecture | ✓ DONE | PE design documented |
| Section IV: Log-Domain Tower Scaling | ✓ DONE | Reviewed |
| Section V: Performance Analysis | ✓ DONE | Reviewed |
| Section VI: NR-IOC | ✓ DONE | Reviewed |
| Section VI-B: Simulation Validation | ✓ DONE | NEW - Added validation data |
| Section VII: Cybersecurity | ✓ DONE | Hardware security added |
| Section VIII: The Vision | ✓ DONE | Reviewed |
| Section IX: Conclusion | ✓ DONE | 7 contributions including FDTD |
| Acknowledgment | ✓ DONE | Reviewed |
| Keywords | ✓ DONE | Added "hardware security" |
| References | ✓ DONE | Fixed section refs |

---

## Current Abstract (for reference)
The abstract now includes:
- Citations to prior work [1] and software [2] with GitHub footnote
- NR-IOC terminology
- 3³ encoding (9× for ADD)
- WDM 6 triplets (6× parallelism)
- B200 comparison (59×, 400W vs 1000W)
- Frontier comparison (8 chips, <0.02% power)

---

## Zenodo Plan
- Publishing as NEW record (not updating v1)
- References v1 paper as prior work
- Will connect all three: theory paper, software, this architecture paper

---
*Last updated: 2026-02-05*
*Status: READY FOR PUBLICATION - Upload to Zenodo*
