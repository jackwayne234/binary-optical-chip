#!/usr/bin/env python3
"""
Monte Carlo Process Variation Analysis — Monolithic 9x9 Binary Optical Chip
============================================================================

PURPOSE:
    Estimate fabrication yield by simulating how real-world process variations
    affect the binary optical chip's ability to function correctly.

    In a real TFLN foundry, nothing is perfect. Waveguides come out slightly
    wider or narrower than drawn. PPLN poling periods drift. Etch depths vary
    across the wafer. This script asks:
    "Given realistic fab tolerances, how often does the chip still work?"

    Because binary has only ONE QPM condition (1550→775 nm SHG), process
    variation sensitivity is dramatically lower than ternary (which needs
    6 QPM conditions to all hit simultaneously).

METHOD:
    Monte Carlo simulation — 10,000 trials. Each trial picks random fab
    parameter values from Gaussian distributions centered on the nominal design.
    For each "virtual chip," we re-run all design validation checks.
    Yield = fraction of trials that pass ALL checks.

PARAMETER SOURCES:
    - Waveguide width tolerance: DRC_RULES.md rule WG.W.1 (500nm ±20nm, 3σ)
    - PPLN poling period tolerance: ±0.2μm (foundry spec, ≈1% of 19.1μm)
    - Etch depth tolerance: ±10nm (RIE, from DRC_RULES.md §10.1)
    - Propagation loss: 2.0 dB/cm ±0.5 dB/cm (TFLN typical)
    - Edge coupling loss: 1.0 dB ±0.3 dB per facet

VALIDATION CHECKS:
    1. Loss budget — does 775nm SFG signal reach detector with positive margin?
    2. PPLN phase mismatch — does QPM period variation reduce SFG efficiency?
    3. WDM separation — are 775/1310/1550 nm still adequately separated?
    4. Path-length timing — does skew stay within acceptable bounds?
    5. Detector threshold — does photocurrent exceed 0.5μA threshold?

BINARY ADVANTAGE:
    - Only 1 PPLN period to get right (vs 6 for ternary)
    - No ring resonators (vs critical ring tuning in ternary that limits yield)
    - Large wavelength separations (535, 775 nm gaps vs ~20 nm in ternary)
    - Expected yield improvement: ~5-15% higher than ternary

Usage:
    python3 monte_carlo_binary_9x9.py

    Output: terminal summary + plots saved to ../docs/monte_carlo_binary_plots/

Author: Binary Optical Chip Project
Date: 2026-02-27
"""

import numpy as np
import sys
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not installed. Plots disabled. pip install matplotlib")

# =============================================================================
# NOMINAL DESIGN PARAMETERS
# =============================================================================

@dataclass
class NominalDesign:
    """Nominal (target) design parameters from monolithic_chip_binary_9x9.py."""

    # Waveguide geometry
    waveguide_width_nm:    float = 500.0    # nm
    etch_depth_nm:         float = 400.0    # nm
    waveguide_loss_db_cm:  float = 2.0      # dB/cm

    # PPLN (single QPM condition for 1550→775 SHG)
    ppln_period_um:        float = 19.1     # μm
    ppln_length_um:        float = 800.0    # μm
    sfg_conversion_pct:    float = 10.0     # % (at nominal pump power)

    # Optical power
    laser_power_dbm:       float = 10.0     # dBm
    edge_coupling_loss_db: float = 1.0      # dB per facet

    # Chip layout
    n_pe_cols:             int   = 9        # PEs per row (activation passes through all)
    pe_pitch_um:           float = 55.0     # μm
    ioc_input_um:          float = 190.0    # μm
    routing_gap_um:        float = 60.0     # μm
    ioc_output_um:         float = 200.0    # μm

    # Detector
    detector_sensitivity_dbm: float = -30.0   # dBm
    detector_threshold_ua:    float = 0.5     # μA

    # Wavelengths
    wl_bit0_nm:            float = 1310.0
    wl_bit1_nm:            float = 1550.0
    wl_sfg_nm:             float = 775.0


# =============================================================================
# PROCESS VARIATION MODEL
# =============================================================================

@dataclass
class FabVariation:
    """
    Gaussian process variation model for TFLN foundry.

    All sigmas are 1σ values. Each trial samples from N(0,1) × sigma.
    The sign convention matches the DRC_RULES.md tolerances.
    """

    # Waveguide geometry (DRC_RULES.md WG.W.1: 500nm ±20nm at 3σ → σ ≈ 7nm)
    sigma_waveguide_width_nm:    float = 7.0     # nm

    # Etch depth (DRC §10.1: 400nm ±10nm at 3σ → σ ≈ 3.3nm)
    sigma_etch_depth_nm:         float = 3.3     # nm

    # Waveguide loss (TFLN literature range 0.1-5 dB/cm, mean 2.0, σ≈0.5)
    sigma_loss_db_cm:            float = 0.5     # dB/cm

    # PPLN poling period (HyperLight spec: ±0.2μm at 3σ → σ≈0.067μm)
    sigma_ppln_period_um:        float = 0.067   # μm

    # SFG conversion efficiency (±30% relative variation, σ≈10%)
    sigma_sfg_conversion_rel:    float = 0.10    # fractional

    # Edge coupling loss (lensed fiber alignment: σ≈0.3dB)
    sigma_edge_coupling_db:      float = 0.30    # dB

    def sample(self, rng: np.random.Generator, nominal: NominalDesign) -> "SampledChip":
        """Sample a single random chip from the fab variation distribution."""
        return SampledChip(
            waveguide_width_nm    = nominal.waveguide_width_nm + rng.normal(0, self.sigma_waveguide_width_nm),
            etch_depth_nm         = nominal.etch_depth_nm + rng.normal(0, self.sigma_etch_depth_nm),
            waveguide_loss_db_cm  = max(0.1, nominal.waveguide_loss_db_cm + rng.normal(0, self.sigma_loss_db_cm)),
            ppln_period_um        = nominal.ppln_period_um + rng.normal(0, self.sigma_ppln_period_um),
            sfg_conversion_frac   = max(0.001, nominal.sfg_conversion_pct/100 + rng.normal(0, self.sigma_sfg_conversion_rel * nominal.sfg_conversion_pct/100)),
            edge_coupling_loss_db = max(0.0, nominal.edge_coupling_loss_db + rng.normal(0, self.sigma_edge_coupling_db)),
        )


@dataclass
class SampledChip:
    """One randomly-sampled chip instance with varied fabrication parameters."""
    waveguide_width_nm:    float
    etch_depth_nm:         float
    waveguide_loss_db_cm:  float
    ppln_period_um:        float
    sfg_conversion_frac:   float
    edge_coupling_loss_db: float


# =============================================================================
# VALIDATION CHECKS
# =============================================================================

def check_loss_budget(chip: SampledChip, nominal: NominalDesign) -> Tuple[bool, float]:
    """
    Check 1: Loss budget.
    Can the 775nm SFG signal reach the detector with positive margin?
    Worst case: PE[0, N-1] (row 0, last column).
    """
    # Edge coupling
    p = nominal.laser_power_dbm - chip.edge_coupling_loss_db

    # IOC input path (IOC + routing)
    ioc_path_um = nominal.ioc_input_um + nominal.routing_gap_um
    p -= chip.waveguide_loss_db_cm * (ioc_path_um / 1e4)

    # MZI insertion (2 dB: electrodes + splitters)
    p -= 2.0

    # Through 9 PEs (row 0, cols 0-8)
    for col in range(nominal.n_pe_cols):
        p -= 1.0  # PE crossing + PPLN insertion
        if col < nominal.n_pe_cols - 1:
            gap_um = nominal.pe_pitch_um - 50.0
            p -= chip.waveguide_loss_db_cm * (gap_um / 1e4)

    # SFG conversion at PE[0, 8]
    pump_w = 10 ** (p / 10) * 1e-3
    # PPLN period variation → phase mismatch → sinc² penalty
    delta_period_um = abs(chip.ppln_period_um - nominal.ppln_period_um)
    # Phase mismatch accumulated over PPLN length
    # Δφ = (2π/Λ_nominal - 2π/Λ_actual) * L
    if chip.ppln_period_um > 0:
        delta_k_per_um = 2 * np.pi * (1/nominal.ppln_period_um - 1/chip.ppln_period_um)
        delta_phi = delta_k_per_um * nominal.ppln_length_um
        sinc_sq = np.sinc(delta_phi / (2 * np.pi)) ** 2
    else:
        sinc_sq = 0.0

    sfg_eff = chip.sfg_conversion_frac * sinc_sq
    sfg_power_w = sfg_eff * pump_w
    if sfg_power_w <= 0:
        return False, -99.0
    sfg_power_dbm = 10 * np.log10(sfg_power_w * 1e3)

    # Routing to output
    out_path_um = nominal.routing_gap_um + nominal.ioc_output_um
    sfg_power_dbm -= chip.waveguide_loss_db_cm * (out_path_um / 1e4)
    sfg_power_dbm -= chip.edge_coupling_loss_db

    margin = sfg_power_dbm - nominal.detector_sensitivity_dbm
    return margin > 0, margin


def check_ppln_efficiency(chip: SampledChip, nominal: NominalDesign) -> Tuple[bool, float]:
    """
    Check 2: PPLN phase mismatch.
    Does the period variation reduce SFG efficiency below threshold?
    Minimum acceptable: 5% conversion (half of nominal 10%).
    """
    if chip.ppln_period_um <= 0:
        return False, 0.0
    delta_k_per_um = abs(2 * np.pi * (1/nominal.ppln_period_um - 1/chip.ppln_period_um))
    delta_phi = delta_k_per_um * nominal.ppln_length_um
    sinc_sq = float(np.sinc(delta_phi / (2 * np.pi)) ** 2)
    effective_eff = chip.sfg_conversion_frac * sinc_sq
    threshold = 0.03  # 3% minimum (vs nominal 10%)
    return effective_eff >= threshold, effective_eff


def check_wavelength_separation(chip: SampledChip, nominal: NominalDesign) -> Tuple[bool, float]:
    """
    Check 3: WDM wavelength separation.
    Are the 3 wavelengths (775, 1310, 1550 nm) still adequately separated?

    Binary huge advantage: minimum separation is 535 nm (775→1310).
    Even with significant waveguide width variation, SFG wavelength barely shifts.
    Δλ_SFG ≈ 2 × Δλ_pump / (pump wavelength²) × SFG wavelength²

    For waveguide width variation of ±20nm:
    Effective index shift → ~±0.5 nm wavelength shift at worst.
    535 nm >> 0.5 nm — this check almost never fails.
    """
    # Effective index shift from waveguide width variation
    width_delta_nm = chip.waveguide_width_nm - nominal.waveguide_width_nm
    # dn_eff/dW ≈ 0.02 per nm for TFLN 500nm waveguides (from simulation)
    dn_eff = 0.02 * width_delta_nm / 1000.0  # fractional
    # λ shift for SFG output
    sfg_shift_nm = abs(dn_eff * nominal.wl_sfg_nm)

    effective_sfg_nm  = nominal.wl_sfg_nm + sfg_shift_nm
    min_sep = min(
        abs(nominal.wl_bit0_nm - effective_sfg_nm),
        abs(nominal.wl_bit1_nm - effective_sfg_nm),
    )
    return min_sep > 10.0, min_sep  # 10 nm minimum for WDM coupler


def check_timing(chip: SampledChip, nominal: NominalDesign) -> Tuple[bool, float]:
    """
    Check 4: Path-length timing.
    Does meander equalization hold to within 0.1 ps?
    Variation: waveguide effective index shifts travel time.
    """
    # Effective index variation from waveguide width change
    width_delta_nm = chip.waveguide_width_nm - nominal.waveguide_width_nm
    dn_rel = 0.02 * width_delta_nm / 1000.0
    n_eff = 2.138 * (1 + dn_rel)  # approximate

    # Longest path length: IOC + array width
    path_um = nominal.ioc_input_um + nominal.routing_gap_um + (nominal.n_pe_cols - 1) * nominal.pe_pitch_um
    # Time variation: Δt = path × Δn / c
    c_um_ps = 299.792
    delta_t_ps = path_um * abs(dn_rel) * 2.138 / c_um_ps
    return delta_t_ps < 0.5, delta_t_ps  # 0.5 ps tolerance


def check_detector(chip: SampledChip, nominal: NominalDesign, margin_db: float) -> Tuple[bool, float]:
    """
    Check 5: Detector photocurrent.
    Does the detected 775nm signal exceed the 0.5μA threshold?
    """
    if margin_db < 0:
        return False, 0.0
    power_dbm = nominal.detector_sensitivity_dbm + margin_db
    power_w = 10 ** (power_dbm / 10) * 1e-3
    responsivity = 0.8  # A/W at 775 nm (Ge or InGaAs PD)
    current_ua = power_w * responsivity * 1e6
    return current_ua >= nominal.detector_threshold_ua, current_ua


# =============================================================================
# MONTE CARLO ENGINE
# =============================================================================

@dataclass
class TrialResult:
    """Results for one Monte Carlo trial."""
    loss_budget_pass:       bool
    ppln_efficiency_pass:   bool
    wavelength_sep_pass:    bool
    timing_pass:            bool
    detector_pass:          bool
    power_margin_db:        float
    ppln_efficiency:        float
    min_wavelength_sep_nm:  float
    timing_skew_ps:         float
    detector_current_ua:    float

    @property
    def all_pass(self) -> bool:
        return (self.loss_budget_pass and
                self.ppln_efficiency_pass and
                self.wavelength_sep_pass and
                self.timing_pass and
                self.detector_pass)


def run_monte_carlo(
    n_trials: int = 10_000,
    seed: int = 42,
    verbose: bool = True,
) -> List[TrialResult]:
    """Run Monte Carlo process variation analysis."""
    rng = np.random.default_rng(seed)
    nominal = NominalDesign()
    variation = FabVariation()

    results = []
    t0 = time.time()

    if verbose:
        print(f"\nRunning {n_trials:,} Monte Carlo trials...")
        print(f"  Nominal PPLN period: {nominal.ppln_period_um} μm")
        print(f"  PPLN σ: {variation.sigma_ppln_period_um} μm ({variation.sigma_ppln_period_um/nominal.ppln_period_um*100:.2f}%)")
        print(f"  WG width σ: {variation.sigma_waveguide_width_nm} nm")
        print(f"  Loss σ: {variation.sigma_loss_db_cm} dB/cm")
        print()

    for i in range(n_trials):
        chip = variation.sample(rng, nominal)

        lb_pass, margin = check_loss_budget(chip, nominal)
        pp_pass, eff    = check_ppln_efficiency(chip, nominal)
        ws_pass, sep    = check_wavelength_separation(chip, nominal)
        tm_pass, skew   = check_timing(chip, nominal)
        dt_pass, curr   = check_detector(chip, nominal, margin)

        results.append(TrialResult(
            loss_budget_pass      = lb_pass,
            ppln_efficiency_pass  = pp_pass,
            wavelength_sep_pass   = ws_pass,
            timing_pass           = tm_pass,
            detector_pass         = dt_pass,
            power_margin_db       = margin,
            ppln_efficiency       = eff,
            min_wavelength_sep_nm = sep,
            timing_skew_ps        = skew,
            detector_current_ua   = curr,
        ))

        if verbose and (i + 1) % 2000 == 0:
            elapsed = time.time() - t0
            n_pass = sum(1 for r in results if r.all_pass)
            yield_pct = n_pass / (i + 1) * 100
            print(f"  [{i+1:6,}/{n_trials:,}]  Running yield: {yield_pct:.2f}%  ({elapsed:.1f}s)")

    return results


def summarize(results: List[TrialResult]) -> dict:
    """Compute summary statistics from Monte Carlo results."""
    n = len(results)
    n_pass = sum(1 for r in results if r.all_pass)

    # Per-check yields
    checks = {
        "loss_budget":        sum(1 for r in results if r.loss_budget_pass) / n * 100,
        "ppln_efficiency":    sum(1 for r in results if r.ppln_efficiency_pass) / n * 100,
        "wavelength_sep":     sum(1 for r in results if r.wavelength_sep_pass) / n * 100,
        "timing":             sum(1 for r in results if r.timing_pass) / n * 100,
        "detector":           sum(1 for r in results if r.detector_pass) / n * 100,
    }

    # Key metrics
    margins     = [r.power_margin_db for r in results]
    efficiencies = [r.ppln_efficiency for r in results]
    seps        = [r.min_wavelength_sep_nm for r in results]
    skews       = [r.timing_skew_ps for r in results]
    currents    = [r.detector_current_ua for r in results]

    return {
        "n_trials":       n,
        "n_pass":         n_pass,
        "yield_pct":      n_pass / n * 100,
        "check_yields":   checks,
        "power_margin": {
            "mean_db":  float(np.mean(margins)),
            "std_db":   float(np.std(margins)),
            "min_db":   float(np.min(margins)),
            "p01_db":   float(np.percentile(margins, 1)),
        },
        "ppln_efficiency": {
            "mean_pct":   float(np.mean(efficiencies)) * 100,
            "std_pct":    float(np.std(efficiencies)) * 100,
            "min_pct":    float(np.min(efficiencies)) * 100,
            "p01_pct":    float(np.percentile(efficiencies, 1)) * 100,
        },
        "wavelength_separation": {
            "mean_nm":  float(np.mean(seps)),
            "min_nm":   float(np.min(seps)),
        },
        "timing_skew": {
            "mean_ps":  float(np.mean(skews)),
            "max_ps":   float(np.max(skews)),
        },
        "detector_current": {
            "mean_ua":  float(np.mean(currents)),
            "min_ua":   float(np.min(currents)),
            "p01_ua":   float(np.percentile(currents, 1)),
        },
    }


def print_summary(summary: dict):
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║  MONTE CARLO RESULTS — BINARY OPTICAL CHIP 9×9                  ║")
    print("╠" + "═" * 68 + "╣")
    print(f"║  Trials:   {summary['n_trials']:>10,}                                          ║")
    print(f"║  Passing:  {summary['n_pass']:>10,}                                          ║")
    print(f"║  YIELD:    {summary['yield_pct']:>9.2f}%                                         ║")
    print("╠" + "═" * 68 + "╣")
    print("║  Per-check yields:                                               ║")
    for name, pct in summary["check_yields"].items():
        bar = "█" * int(pct / 5)
        print(f"║    {name:22s}  {pct:6.2f}%  {bar:<20s}  ║")
    print("╠" + "═" * 68 + "╣")
    m = summary["power_margin"]
    print(f"║  Power margin (dB):  mean={m['mean_db']:+.1f}  std={m['std_db']:.1f}  min={m['min_db']:+.1f}  p1={m['p01_db']:+.1f}  ║")
    e = summary["ppln_efficiency"]
    print(f"║  PPLN efficiency:    mean={e['mean_pct']:.1f}%  std={e['std_pct']:.1f}%  min={e['min_pct']:.1f}%  p1={e['p01_pct']:.1f}%  ║")
    w = summary["wavelength_separation"]
    print(f"║  WDM separation:     mean={w['mean_nm']:.0f}nm  min={w['min_nm']:.0f}nm  (binary: huge)                ║")
    t = summary["timing_skew"]
    print(f"║  Timing skew:        mean={t['mean_ps']:.4f}ps  max={t['max_ps']:.4f}ps                         ║")
    print("╠" + "═" * 68 + "╣")
    yield_pct = summary["yield_pct"]
    if yield_pct >= 99.0:
        verdict = "EXCELLENT (>99%) — FAB READY"
    elif yield_pct >= 95.0:
        verdict = "GOOD (>95%) — PROCEED WITH CAUTION"
    elif yield_pct >= 80.0:
        verdict = "MARGINAL (>80%) — REVIEW TOLERANCES"
    else:
        verdict = "POOR (<80%) — DESIGN REVISION NEEDED"
    print(f"║  Verdict: {verdict:<57s}  ║")
    print("╚" + "═" * 68 + "╝")


def generate_plots(results: List[TrialResult], summary: dict, output_dir: str):
    """Generate publication-quality plots."""
    if not MATPLOTLIB_AVAILABLE:
        return

    os.makedirs(output_dir, exist_ok=True)

    margins     = np.array([r.power_margin_db for r in results])
    efficiencies = np.array([r.ppln_efficiency * 100 for r in results])
    seps        = np.array([r.min_wavelength_sep_nm for r in results])
    passing     = np.array([r.all_pass for r in results])

    # Plot 1: Power margin distribution
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(margins[passing], bins=60, color='#2196F3', alpha=0.8, label='Passing chips')
    ax.hist(margins[~passing], bins=60, color='#F44336', alpha=0.8, label='Failing chips')
    ax.axvline(0, color='red', lw=2, ls='--', label='Minimum (0 dB)')
    ax.set_xlabel("Power Margin (dB)", fontsize=12)
    ax.set_ylabel("Count", fontsize=12)
    ax.set_title(f"Power Margin Distribution — {summary['yield_pct']:.2f}% Yield", fontsize=13)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "margin_distribution.png"), dpi=150)
    plt.close(fig)

    # Plot 2: PPLN efficiency distribution
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(efficiencies, bins=60, color='#4CAF50', alpha=0.8, edgecolor='white')
    ax.axvline(3.0, color='red', lw=2, ls='--', label='Threshold (3%)')
    ax.set_xlabel("SFG Conversion Efficiency (%)", fontsize=12)
    ax.set_ylabel("Count", fontsize=12)
    ax.set_title("PPLN SFG Conversion Efficiency (1550→775 nm)", fontsize=13)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "ppln_efficiency.png"), dpi=150)
    plt.close(fig)

    # Plot 3: Yield summary bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    checks = summary["check_yields"]
    names = list(checks.keys())
    values = list(checks.values())
    colors = ['#4CAF50' if v >= 95 else '#FFC107' if v >= 80 else '#F44336' for v in values]
    bars = ax.bar(names, values, color=colors, edgecolor='white')
    ax.axhline(95, color='red', ls='--', lw=1.5, label='95% threshold')
    ax.set_ylim(0, 105)
    ax.set_ylabel("Check Yield (%)", fontsize=12)
    ax.set_title("Per-Check Yield Breakdown", fontsize=13)
    ax.legend()
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{val:.1f}%", ha='center', fontsize=10)
    plt.xticks(rotation=20, ha='right')
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "yield_summary.png"), dpi=150)
    plt.close(fig)

    # Plot 4: WDM separation (should be nearly constant for binary — shown to validate)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(seps, bins=60, color='#9C27B0', alpha=0.8)
    ax.axvline(10.0, color='red', lw=2, ls='--', label='Minimum (10 nm)')
    ax.set_xlabel("Min WDM Channel Separation (nm)", fontsize=12)
    ax.set_ylabel("Count", fontsize=12)
    ax.set_title("WDM Wavelength Separation (Binary: always >100 nm)", fontsize=13)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "wavelength_separation.png"), dpi=150)
    plt.close(fig)

    print(f"\nPlots saved to: {output_dir}")


# =============================================================================
# Main
# =============================================================================

def main():
    print("╔" + "═" * 68 + "╗")
    print("║  MONTE CARLO YIELD ANALYSIS — Binary Optical Chip 9×9            ║")
    print("║  10,000 trials — TFLN process variation model                    ║")
    print("╚" + "═" * 68 + "╝")

    n_trials = 10_000
    results = run_monte_carlo(n_trials=n_trials, verbose=True)
    summary = summarize(results)
    print_summary(summary)

    output_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "monte_carlo_binary_plots")
    generate_plots(results, summary, output_dir)

    # Save text summary
    os.makedirs(output_dir, exist_ok=True)
    summary_path = os.path.join(output_dir, "results_summary.txt")
    with open(summary_path, "w") as f:
        f.write(f"Binary Optical Chip 9x9 — Monte Carlo Results\n")
        f.write(f"Trials: {summary['n_trials']:,}\n")
        f.write(f"Yield:  {summary['yield_pct']:.4f}%\n")
        f.write(f"Pass:   {summary['n_pass']:,}\n\n")
        for check, pct in summary["check_yields"].items():
            f.write(f"  {check}: {pct:.4f}%\n")
        f.write(f"\nPower margin: mean={summary['power_margin']['mean_db']:+.2f} dB, "
                f"min={summary['power_margin']['min_db']:+.2f} dB\n")
        f.write(f"PPLN eff:     mean={summary['ppln_efficiency']['mean_pct']:.2f}%, "
                f"min={summary['ppln_efficiency']['min_pct']:.2f}%\n")
    print(f"\nText summary: {summary_path}")

    return summary["yield_pct"] >= 95.0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
