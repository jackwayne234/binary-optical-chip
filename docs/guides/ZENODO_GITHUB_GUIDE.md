# Connecting GitHub to Zenodo - Complete Guide

This guide walks you through connecting your GitHub repository to Zenodo for automatic archiving and DOI generation.

## What This Does

- ✅ Automatically archives every GitHub release
- ✅ Assigns a unique DOI to each release
- ✅ Preserves your code forever at CERN
- ✅ Makes your software citable in academic papers
- ✅ Links your code to your published paper

## Prerequisites

- [ ] GitHub account with your repository
- [ ] Zenodo account (can use same GitHub login)
- [ ] Your paper already published on Zenodo (✅ Done!)

## Step-by-Step Instructions

### Step 1: Enable GitHub Integration in Zenodo

1. Go to https://zenodo.org
2. Click **"Log in"** (top right)
3. Choose **"Log in with GitHub"**
4. Authorize Zenodo to access your GitHub account
5. Once logged in, click your **username** (top right)
6. Select **"GitHub"** from the dropdown menu
7. You'll see a list of your repositories
8. Find `-wavelength-ternary-optical-computer`
9. Toggle the switch to **"ON"**
10. Click **"Sync"** if needed

**Status:** Repository is now linked! 🎉

### Step 2: Create Your First GitHub Release

1. Go to your GitHub repo: https://github.com/jackwayne234/-wavelength-ternary-optical-computer
2. On the right side, click **"Create a new release"**
3. Click **"Choose a tag"**
4. Type: `v1.0.0`
5. Click **"Create new tag: v1.0.0"**
6. **Release title:** `v1.0.0 - Initial Open Source Release`
7. **Release notes:** (copy and paste below)

```markdown
## v1.0.0 - Initial Open Source Release

This is the first official release of the Wavelength-Division Ternary Optical Computer project.

### What's Included

**Hardware Designs (Phase 1):**
- Complete 24"×24" visible light prototype BOM
- 3D printable optical components (SCAD/STL files)
- Assembly instructions
- Safety documentation with ORM assessment

**Software:**
- ESP32 firmware for ternary logic controller
- Python simulation scripts (Meep FDTD)
- Research literature search tool
- Test and validation scripts

**Documentation:**
- Complete open source licensing (MIT/CC BY 4.0/CERN OHL)
- Build logs and engineering documentation
- Community contribution guidelines
- Safety protocols

**Research:**
- Links to published paper (DOI: 10.5281/zenodo.18437600)
- Simulation results and data
- Architecture diagrams

### Features

- ✅ Full open source hardware and software
- ✅ Complete safety documentation
- ✅ Ready for replication by community
- ✅ All licenses properly applied
- ✅ GitHub-Zenodo integration enabled

### Paper Reference

This software implements the architecture described in:
**"Wavelength-Division Ternary Logic: Bypassing the Radix Economy Penalty in Optical Computing"**
- DOI: 10.5281/zenodo.18437600
- Author: Christopher Riner
- License: CC BY 4.0

### Licenses

- **Software:** MIT License
- **Documentation:** CC BY 4.0
- **Hardware:** CERN Open Hardware License

### Getting Started

See [README.md](README.md) for:
- Quick start guide
- Build instructions
- Safety requirements
- Contributing guidelines

### Acknowledgments

Part of the open science movement. Made possible by:
- Open source community
- CERN Zenodo for archival
- Render.com for free hosting
- Replit for development environment

---

**Note:** This is a research project. Safety protocols must be followed when building hardware (see SAFETY.md).
```

8. Scroll down and click **"Publish release"**

**Status:** Release created! 🚀

### Step 3: Wait for Zenodo Archiving

Zenodo automatically detects the release (usually within 5-10 minutes).

**What happens:**
1. Zenodo sees the new release via GitHub webhook
2. Creates a new record
3. Archives the entire repository
4. Assigns a DOI
5. Sends you an email notification

**You don't need to do anything!** It's automatic.

### Step 4: Verify the Zenodo Record

1. Wait for the email from Zenodo (subject: "New release for...")
2. Click the link in the email, OR
3. Go to https://zenodo.org
4. Click your username → "My uploads"
5. You should see a new record: "Wavelength-Division Ternary Optical Computer"
6. Click it to view details

**What you'll see:**
- New DOI (different from your paper!)
- All your code files archived
- Metadata from `.zenodo.json`
- Link to your paper (in "Related identifiers")

### Step 5: Get Your DOI Badge

1. In the Zenodo record, find the DOI section
2. Copy the **Markdown** code (looks like):
   ```markdown
   [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
   ```
3. Add this to your README.md (I can do this for you!)

## Post-Release Steps

### Update README with Software DOI

Add this section to your README.md:

```markdown
## Citation

### Paper (Theory)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18437600.svg)](https://doi.org/10.5281/zenodo.18437600)

Riner, C. (2026). Wavelength-Division Ternary Logic: Bypassing the Radix Economy Penalty in Optical Computing. Zenodo. https://doi.org/10.5281/zenodo.18437600

### Software (Implementation)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)

Riner, C. (2026). Wavelength-Division Ternary Optical Computer (Version v1.0.0) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.XXXXXXX
```

*(Replace XXXXXXX with your actual software DOI)*

### Link Paper and Code

**In the Zenodo software record:**
1. Click "Edit" (if available)
2. Add related identifier:
   - Relation: "Is supplement to"
   - Identifier: 10.5281/zenodo.18437600
   - Resource type: Publication
3. Save

**In the Zenodo paper record:**
1. Go to your paper: https://doi.org/10.5281/zenodo.18437600
2. Click "Edit" (if available)
3. Add related identifier:
   - Relation: "Has supplement"
   - Identifier: 10.5281/zenodo.XXXXXXX (your new DOI)
   - Resource type: Software
4. Save

## Future Releases

For each new version:

1. Make changes to your code
2. Commit and push to GitHub
3. Create new release with version number:
   - Bug fixes: `v1.0.1`, `v1.0.2`
   - New features: `v1.1.0`, `v1.2.0`
   - Major changes: `v2.0.0`
4. Zenodo automatically archives each release with its own DOI

## Troubleshooting

### Release not showing in Zenodo
- Wait 10-15 minutes
- Check that Zenodo GitHub integration is ON
- Ensure the release is published (not draft)

### Wrong metadata
- Edit `.zenodo.json` file
- Create new release to update

### Can't edit Zenodo record
- Records are immutable after publication
- Create new release with corrections

## Benefits Summary

✅ **Paper** (10.5281/zenodo.18437600) - Your research publication
✅ **Code** (10.5281/zenodo.XXXXXXX) - Your software implementation
✅ **Both citable** - Different DOIs for different purposes
✅ **Both preserved** - CERN guarantees 20+ years storage
✅ **Linked together** - Show the complete research workflow

## Questions?

- Zenodo docs: https://help.zenodo.org/
- GitHub releases: https://docs.github.com/en/repositories/releasing-projects-on-github
- Contact: chrisriner45@gmail.com

---

**Ready? Follow Step 1 above to get started!**
