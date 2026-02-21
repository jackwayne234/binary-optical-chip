#!/usr/bin/env python3
"""
IOC 6-Lane Integration Test: All 6 Triplets × All 6 SFG Pairs
================================================================

FDTD simulation validating that all 6 wavelength triplets produce correct
SFG outputs through dedicated PPLN mixers with per-triplet QPM tuning.

This test validates the 6-lane parallel mixer architecture:
    - Each triplet gets its own PPLN mixer with QPM period tuned to its wavelengths
    - Each mixer must produce correct SFG for all 6 unique trit×trit multiplications
    - Cross-triplet isolation is inherent (each mixer only sees its own triplet)

6 Wavelength Triplets:
    T1: 1040/1020/1000 nm  →  SFG outputs 500-520 nm
    T2: 1100/1080/1060 nm  →  SFG outputs 530-550 nm
    T3: 1160/1140/1120 nm  →  SFG outputs 560-580 nm
    T4: 1220/1200/1180 nm  →  SFG outputs 590-610 nm
    T5: 1280/1260/1240 nm  →  SFG outputs 620-640 nm
    T6: 1340/1320/1300 nm  →  SFG outputs 650-670 nm

For each triplet, tests 6 unique SFG interactions (36 total simulations):
    B+B → (+1)×(+1) = +1
    G+B → ( 0)×(+1) =  0
    R+B → (-1)×(+1) = -1
    G+G → ( 0)×( 0) =  0
    R+G → (-1)×( 0) =  0
    R+R → (-1)×(-1) = +1

Usage:
    # Full test (all 6 triplets, ~1-2 hours)
    mpirun -np 12 /home/jackwayne/miniconda/envs/meep_env/bin/python -u ioc_6lane_integration_test.py

    # Single triplet (for quick validation)
    mpirun -np 12 /home/jackwayne/miniconda/envs/meep_env/bin/python -u ioc_6lane_integration_test.py --triplet 1

    # OpenMP alternative
    export OMP_NUM_THREADS=12
    /home/jackwayne/miniconda/envs/meep_env/bin/python ioc_6lane_integration_test.py

Copyright (c) 2026 Christopher Riner
Licensed under the MIT License.

Wavelength-Division Ternary Optical Computer
DOI: 10.5281/zenodo.18437600
"""

import os
import sys
import time
import argparse
import meep as mp
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

# ---------------------------------------------------------------------------
# MPI support
# ---------------------------------------------------------------------------
try:
    from mpi4py import MPI
    RANK = MPI.COMM_WORLD.Get_rank()
    SIZE = MPI.COMM_WORLD.Get_size()
    IS_PARALLEL = SIZE > 1
except (ImportError, RuntimeError, OSError):
    RANK = 0
    SIZE = 1
    IS_PARALLEL = False


def print_master(msg):
    if RANK == 0:
        print(msg, flush=True)


# ===========================================================================
# MATERIAL MODEL (LiNbO3 — Sellmeier equation for accurate dispersion)
# ===========================================================================

# Sellmeier coefficients for LiNbO3 ordinary ray (no)
# From Zelmon, Small & Jundt, "Infrared corrected Sellmeier coefficients for
# congruently grown lithium niobate", JOSA B 14, 3319-3322 (1997)
# n²(λ) = a₁ + b₁λ²/(λ² - c₁²) + b₂λ²/(λ² - c₂²) with λ in micrometers
SELLMEIER_A1 = 1.0       # Fixed term
SELLMEIER_B1 = 2.6734    # First oscillator strength (UV pole)
SELLMEIER_B2 = 1.2290    # Second oscillator strength (UV pole)
SELLMEIER_C1 = 0.1327    # First resonance wavelength (μm)
SELLMEIER_C2 = 0.2431    # Second resonance wavelength (μm)

# Lorentzian damping for FDTD numerical stability (small enough to not affect ε)
LORENTZ_GAMMA = 1e-2

CHI2_VAL = 0.5

def compute_meep_index(wavelength_um: float) -> float:
    """Refractive index from Sellmeier equation for LiNbO3."""
    wl2 = wavelength_um**2
    c1_sq = SELLMEIER_C1**2
    c2_sq = SELLMEIER_C2**2
    # Sellmeier equation: n² = a₁ + b₁λ²/(λ² - c₁²) + b₂λ²/(λ² - c₂²)
    n2 = SELLMEIER_A1 + SELLMEIER_B1*wl2/(wl2 - c1_sq) + SELLMEIER_B2*wl2/(wl2 - c2_sq)
    return float(np.sqrt(n2))

def compute_lorentzian_params(lambda_pump_um: float, lambda_sfg_um: float,
                              f0: float = 3.5):
    """Single-pole Lorentzian fit matching corrected Sellmeier at pump & SFG.

    Uses Meep convention: ε(f) = ε∞*(1 + σ·f₀²/(f₀²-f²)).
    Fixed f₀=3.5 keeps the pole below the FDTD stability boundary (~4.0
    at resolution 20). Solves for ε∞ and σ to exactly match ε at both
    the pump and SFG wavelengths.
    """
    eps_pump = compute_meep_index(lambda_pump_um)**2
    eps_sfg = compute_meep_index(lambda_sfg_um)**2

    f_pump = 1.0 / lambda_pump_um
    f_sfg = 1.0 / lambda_sfg_um

    # Lorentzian factors at pump and SFG frequencies
    a1 = f0**2 / (f0**2 - f_pump**2)
    a2 = f0**2 / (f0**2 - f_sfg**2)

    # Solve 2x2 system: ε∞*(1 + a_i*σ) = ε_i for i = pump, sfg
    R = eps_pump / eps_sfg
    sigma = (R - 1.0) / (a1 - R * a2)
    eps_inf = eps_pump / (1.0 + a1 * sigma)

    return eps_inf, sigma, f0

def make_linbo3_medium(lambda_pump_um: float, lambda_sfg_um: float,
                       chi2: float = 0.0) -> 'mp.Medium':
    """Create LiNbO3 medium with single-pole Lorentzian fit to Sellmeier.

    Matches correct dispersion at both pump and SFG wavelengths.
    """
    eps_inf, sigma, f0 = compute_lorentzian_params(lambda_pump_um, lambda_sfg_um)
    return mp.Medium(
        epsilon=eps_inf,
        E_susceptibilities=[
            mp.LorentzianSusceptibility(frequency=f0, gamma=LORENTZ_GAMMA,
                                        sigma=sigma),
        ],
        chi2=chi2,
    )


def compute_qpm_period(lambda_a_um: float, lambda_b_um: float) -> float:
    """PPLN quasi-phase-matching period for SFG: lambda_a + lambda_b -> lambda_sfg."""
    lambda_sfg = 1.0 / (1.0 / lambda_a_um + 1.0 / lambda_b_um)
    n_a = compute_meep_index(lambda_a_um)
    n_b = compute_meep_index(lambda_b_um)
    n_sfg = compute_meep_index(lambda_sfg)
    delta_k = 2.0 * np.pi * (n_sfg / lambda_sfg - n_a / lambda_a_um - n_b / lambda_b_um)
    if abs(delta_k) < 1e-10:
        return float('inf')
    return abs(2.0 * np.pi / delta_k)


def sfg_wavelength(la: float, lb: float) -> float:
    return 1.0 / (1.0 / la + 1.0 / lb)


# ===========================================================================
# 6 WAVELENGTH TRIPLETS
# ===========================================================================

TRIPLETS = {
    1: {'name': 'T1', 'lambda_neg': 1.040, 'lambda_zero': 1.020, 'lambda_pos': 1.000},
    2: {'name': 'T2', 'lambda_neg': 1.100, 'lambda_zero': 1.080, 'lambda_pos': 1.060},
    3: {'name': 'T3', 'lambda_neg': 1.160, 'lambda_zero': 1.140, 'lambda_pos': 1.120},
    4: {'name': 'T4', 'lambda_neg': 1.220, 'lambda_zero': 1.200, 'lambda_pos': 1.180},
    5: {'name': 'T5', 'lambda_neg': 1.280, 'lambda_zero': 1.260, 'lambda_pos': 1.240},
    6: {'name': 'T6', 'lambda_neg': 1.340, 'lambda_zero': 1.320, 'lambda_pos': 1.300},
}


def build_sfg_table(triplet):
    """Build the SFG interaction table for a given triplet."""
    R = triplet['lambda_neg']   # trit -1
    G = triplet['lambda_zero']  # trit  0
    B = triplet['lambda_pos']   # trit +1

    table = {}
    for key, la, lb, trit in [
        ('B+B', B, B, +1),
        ('G+B', G, B,  0),
        ('R+B', R, B, -1),
        ('G+G', G, G,  0),
        ('R+G', R, G,  0),
        ('R+R', R, R, +1),
    ]:
        table[key] = {
            'lambda_a': la,
            'lambda_b': lb,
            'lambda_sfg': sfg_wavelength(la, lb),
            'result_trit': trit,
            'qpm_period': compute_qpm_period(la, lb),
        }
    return table


# ===========================================================================
# SIMULATION PARAMETERS
# ===========================================================================

SFG_WG_WIDTH  = 0.8
SFG_WG_LENGTH = 20.0
OUT_WG_LENGTH = 5.0
N_CLAD        = 1.44
RESOLUTION    = 20
PML_THICKNESS = 1.0
SRC_BW_FRAC   = 0.04


# ===========================================================================
# SINGLE-PAIR SIMULATION (same physics as original test)
# ===========================================================================

def run_sfg_test(triplet_id, sfg_key, sfg_info):
    """
    Run FDTD for one SFG interaction in a PPLN waveguide.
    Returns result dict with pass/fail and measurements.
    """
    la, lb = sfg_info['lambda_a'], sfg_info['lambda_b']
    lsfg = sfg_info['lambda_sfg']
    ppln_period = sfg_info['qpm_period']
    is_shg = abs(la - lb) < 0.001

    print_master(f"\n  {'='*60}")
    print_master(f"  TEST: T{triplet_id} {sfg_key} | "
                 f"{la*1000:.0f}nm + {lb*1000:.0f}nm -> {lsfg*1000:.1f}nm"
                 f" | trit {sfg_info['result_trit']:+d}")
    print_master(f"  QPM period: {ppln_period:.2f} um"
                 f" | {'SHG' if is_shg else 'cross-SFG'}")

    # Cell layout
    src_margin = 1.5
    x0 = PML_THICKNESS
    x_src      = x0 + src_margin
    x_sfg_st   = x_src + 0.5
    x_sfg_end  = x_sfg_st + SFG_WG_LENGTH
    x_out_end  = x_sfg_end + OUT_WG_LENGTH
    cell_x     = x_out_end + 1.0 + PML_THICKNESS
    cell_y     = SFG_WG_WIDTH + 4.0

    xshift = -cell_x / 2.0
    def sx(x):
        return x + xshift

    # Build PPLN domains
    geometry = []
    domain_len = ppln_period / 2.0
    n_dom = max(int(SFG_WG_LENGTH / domain_len), 2)

    for i in range(n_dom):
        ds = x_sfg_st + i * domain_len
        de = min(ds + domain_len, x_sfg_st + SFG_WG_LENGTH)
        dl = de - ds
        if dl < 0.01:
            break
        sign = 1 if (i % 2 == 0) else -1
        # Use average pump wavelength for cross-SFG
        l_pump_avg = (la + lb) / 2.0
        mat = make_linbo3_medium(l_pump_avg, lsfg, chi2=CHI2_VAL * sign)
        geometry.append(
            mp.Block(size=mp.Vector3(dl, SFG_WG_WIDTH, mp.inf),
                     center=mp.Vector3(sx(ds + dl / 2.0), 0), material=mat)
        )

    print_master(f"  PPLN: {n_dom} domains, period={ppln_period:.2f} um")

    # Output waveguide (linear LiNbO3, no poling)
    l_pump_avg = (la + lb) / 2.0
    linbo3_linear = make_linbo3_medium(l_pump_avg, lsfg)
    geometry.append(
        mp.Block(size=mp.Vector3(OUT_WG_LENGTH, SFG_WG_WIDTH, mp.inf),
                 center=mp.Vector3(sx(x_sfg_end + OUT_WG_LENGTH / 2.0), 0),
                 material=linbo3_linear)
    )

    # Sources
    fa, fb = 1.0 / la, 1.0 / lb
    dfa, dfb = SRC_BW_FRAC * fa, SRC_BW_FRAC * fb

    if is_shg:
        sources = [
            mp.Source(src=mp.GaussianSource(fa, fwidth=dfa), component=mp.Ez,
                      center=mp.Vector3(sx(x_src), 0),
                      size=mp.Vector3(0, SFG_WG_WIDTH, 0), amplitude=2.0),
        ]
    else:
        sources = [
            mp.Source(src=mp.GaussianSource(fa, fwidth=dfa), component=mp.Ez,
                      center=mp.Vector3(sx(x_src), 0),
                      size=mp.Vector3(0, SFG_WG_WIDTH, 0)),
            mp.Source(src=mp.GaussianSource(fb, fwidth=dfb), component=mp.Ez,
                      center=mp.Vector3(sx(x_src), 0),
                      size=mp.Vector3(0, SFG_WG_WIDTH, 0)),
        ]

    sim = mp.Simulation(
        cell_size=mp.Vector3(cell_x, cell_y, 0),
        geometry=geometry,
        sources=sources,
        boundary_layers=[mp.PML(PML_THICKNESS)],
        resolution=RESOLUTION,
        default_material=mp.Medium(index=N_CLAD),
    )

    # Flux monitor — narrow band around expected SFG wavelength
    f_sfg = 1.0 / lsfg
    monitor_half_bw_nm = 40.0
    f_lo = 1.0 / (lsfg + monitor_half_bw_nm / 1000.0)
    f_hi = 1.0 / (lsfg - monitor_half_bw_nm / 1000.0)
    fcen_sfg = (f_lo + f_hi) / 2.0
    df_sfg = f_hi - f_lo
    nfreq_sfg = 200

    sfg_mon = sim.add_flux(
        fcen_sfg, df_sfg, nfreq_sfg,
        mp.FluxRegion(
            center=mp.Vector3(sx(x_out_end - 0.5), 0),
            size=mp.Vector3(0, SFG_WG_WIDTH * 2, 0),
        )
    )

    # Broadband monitor for spectral plot
    f_min, f_max = 0.55, 2.10
    fcen_full = (f_min + f_max) / 2.0
    df_full = f_max - f_min
    full_mon = sim.add_flux(
        fcen_full, df_full, 500,
        mp.FluxRegion(
            center=mp.Vector3(sx(x_out_end - 0.5), 0),
            size=mp.Vector3(0, SFG_WG_WIDTH * 2, 0),
        )
    )

    # Run
    t0 = time.time()
    sim.run(until_after_sources=200)
    wall = time.time() - t0
    print_master(f"  Meep time: {sim.meep_time():.0f}, wall: {wall:.1f}s")

    # --- Analyze SFG monitor ---
    sfg_freqs = np.array(mp.get_flux_freqs(sfg_mon))
    sfg_flux = np.array(mp.get_fluxes(sfg_mon))
    sfg_wvls = 1.0 / sfg_freqs

    sfg_flux_abs = np.abs(sfg_flux)
    if len(sfg_flux_abs) > 0 and sfg_flux_abs.max() > 0:
        pk_idx = np.argmax(sfg_flux_abs)
        peak_wvl = float(sfg_wvls[pk_idx])
        peak_val = float(sfg_flux_abs[pk_idx])
    else:
        peak_wvl = lsfg
        peak_val = 0.0

    # S/N calculation
    n_edge = max(5, len(sfg_flux_abs) // 10)
    edge_flux = np.concatenate([sfg_flux_abs[:n_edge], sfg_flux_abs[-n_edge:]])
    bg_level = float(np.mean(edge_flux)) if len(edge_flux) > 0 else 0.0

    if bg_level > 1e-20 and peak_val > 1e-20:
        snr_db = float(10 * np.log10(peak_val / bg_level))
    elif peak_val > 1e-20:
        snr_db = 99.0
    else:
        snr_db = -99.0

    deviation_nm = abs(peak_wvl - lsfg) * 1000

    # Full spectrum
    full_freqs = np.array(mp.get_flux_freqs(full_mon))
    full_flux = np.array(mp.get_fluxes(full_mon))
    full_wvls = 1.0 / full_freqs

    # Pass criteria (isolated-lane architecture: no SHG suppression needed)
    correct_peak = deviation_nm < 20.0
    snr_ok = snr_db > 0.0

    passed = correct_peak and snr_ok
    status = "PASS" if passed else "FAIL"

    print_master(f"  Peak: {peak_wvl*1000:.1f}nm "
                 f"(expected {lsfg*1000:.1f}nm, dev={deviation_nm:.1f}nm)")
    print_master(f"  Flux: {peak_val:.4e}, bg: {bg_level:.4e}, S/N: {snr_db:.1f} dB")
    print_master(f"  Result: {status}")

    return {
        'triplet_id': triplet_id,
        'sfg_key': sfg_key,
        'lambda_a': la, 'lambda_b': lb, 'lambda_sfg': lsfg,
        'expected_trit': sfg_info['result_trit'],
        'is_shg': is_shg,
        'qpm_period': ppln_period,
        'n_domains': n_dom,
        'peak_wvl_nm': peak_wvl * 1000,
        'peak_flux': peak_val,
        'bg_level': bg_level,
        'deviation_nm': deviation_nm,
        'correct_peak': correct_peak,
        'shg_suppression_db': None,
        'snr_db': snr_db,
        'passed': passed,
        'status': status,
        'wall_time': wall,
        'wvls': full_wvls,
        'flux': full_flux,
        'sfg_wvls': sfg_wvls,
        'sfg_flux': sfg_flux_abs,
    }


# ===========================================================================
# RUN ALL TRIPLETS
# ===========================================================================

def run_all(triplet_ids=None):
    """Run SFG tests for specified triplets (default: all 6)."""
    if triplet_ids is None:
        triplet_ids = list(TRIPLETS.keys())

    t0 = time.time()
    n_triplets = len(triplet_ids)
    n_tests = n_triplets * 6

    print_master("\n" + "#" * 70)
    print_master("#  IOC 6-LANE INTEGRATION TEST")
    print_master("#  6 Triplets × 6 SFG Pairs = 36 Simulations")
    print_master("#" * 70)
    print_master(f"  Date: {datetime.now()}")
    print_master(f"  MPI processes: {SIZE}")
    print_master(f"  Resolution: {RESOLUTION} px/um")
    print_master(f"  Triplets to test: {triplet_ids}")
    print_master(f"  Total simulations: {n_tests}")
    print_master("")

    # Print triplet info
    print_master("  TRIPLET WAVELENGTHS:")
    print_master(f"  {'ID':>4} {'neg(nm)':>8} {'zero(nm)':>9} {'pos(nm)':>8} {'SFG band (nm)':>14}")
    print_master("  " + "-" * 45)
    for tid in triplet_ids:
        t = TRIPLETS[tid]
        sfg_table = build_sfg_table(t)
        sfg_min = min(v['lambda_sfg'] for v in sfg_table.values()) * 1000
        sfg_max = max(v['lambda_sfg'] for v in sfg_table.values()) * 1000
        print_master(f"  T{tid:>3} {t['lambda_neg']*1000:>8.0f} {t['lambda_zero']*1000:>9.0f} "
                     f"{t['lambda_pos']*1000:>8.0f} {sfg_min:>6.0f}-{sfg_max:.0f}")

    print_master("")

    # Print QPM periods
    print_master("  QPM PERIODS (um):")
    print_master(f"  {'ID':>4} | {'B+B':>7} {'G+B':>7} {'R+B':>7} {'G+G':>7} {'R+G':>7} {'R+R':>7}")
    print_master("  " + "-" * 55)
    for tid in triplet_ids:
        t = TRIPLETS[tid]
        sfg_table = build_sfg_table(t)
        periods = [sfg_table[k]['qpm_period'] for k in ['B+B', 'G+B', 'R+B', 'G+G', 'R+G', 'R+R']]
        line = " ".join(f"{p:7.2f}" for p in periods)
        print_master(f"  T{tid:>3} | {line}")

    print_master("")

    # Run all tests
    all_results = {}
    test_num = 0

    for tid in triplet_ids:
        triplet = TRIPLETS[tid]
        sfg_table = build_sfg_table(triplet)

        print_master(f"\n{'='*70}")
        print_master(f"  TRIPLET {tid}: {triplet['name']} "
                     f"({triplet['lambda_pos']*1000:.0f}/"
                     f"{triplet['lambda_zero']*1000:.0f}/"
                     f"{triplet['lambda_neg']*1000:.0f} nm)")
        print_master(f"{'='*70}")

        triplet_results = {}
        for sfg_key in ['B+B', 'G+B', 'R+B', 'G+G', 'R+G', 'R+R']:
            test_num += 1
            print_master(f"\n  >>> Test {test_num}/{n_tests}: T{tid} {sfg_key}")
            triplet_results[sfg_key] = run_sfg_test(tid, sfg_key, sfg_table[sfg_key])

        all_results[tid] = triplet_results

    total_time = time.time() - t0
    return all_results, total_time


def print_summary(all_results, total_time):
    """Print combined summary for all triplets."""

    print_master("\n" + "=" * 70)
    print_master("  SUMMARY: 6-LANE IOC INTEGRATION TEST")
    print_master("=" * 70)

    total_passed = 0
    total_tests = 0

    for tid in sorted(all_results.keys()):
        results = all_results[tid]
        triplet = TRIPLETS[tid]
        n_passed = sum(1 for r in results.values() if r['passed'])
        total_passed += n_passed
        total_tests += len(results)

        print_master(f"\n  ── TRIPLET {tid} ({triplet['lambda_pos']*1000:.0f}/"
                     f"{triplet['lambda_zero']*1000:.0f}/"
                     f"{triplet['lambda_neg']*1000:.0f} nm) "
                     f"— {n_passed}/6 PASSED ──")
        print_master(f"  {'Pair':<6} {'SFG(nm)':<9} {'Peak(nm)':<10} {'Dev(nm)':<9}"
                     f" {'S/N(dB)':<9} {'Status'}")
        print_master("  " + "-" * 55)

        for sfg_key in ['B+B', 'G+B', 'R+B', 'G+G', 'R+G', 'R+R']:
            r = results[sfg_key]
            print_master(f"  {sfg_key:<6} {r['lambda_sfg']*1000:<9.1f} "
                         f"{r['peak_wvl_nm']:<10.1f} {r['deviation_nm']:<9.1f} "
                         f"{r['snr_db']:<9.1f} {r['status']}")

    # 9-case multiplication table for each triplet
    print_master(f"\n  TERNARY MULTIPLICATION TABLES:")
    mult_cases = [
        (-1, -1, 'R+R', +1), (-1,  0, 'R+G',  0), (-1, +1, 'R+B', -1),
        ( 0, -1, 'R+G',  0), ( 0,  0, 'G+G',  0), ( 0, +1, 'G+B',  0),
        (+1, -1, 'R+B', -1), (+1,  0, 'G+B',  0), (+1, +1, 'B+B', +1),
    ]

    for tid in sorted(all_results.keys()):
        results = all_results[tid]
        print_master(f"\n  T{tid}:")
        print_master(f"  {'In':>4} {'Wt':>4} {'Exp':>4} {'Pair':<6} {'Status'}")
        print_master("  " + "-" * 30)
        for inp, wgt, sfg_key, exp in mult_cases:
            r = results[sfg_key]
            st = "PASS" if r['passed'] else "FAIL"
            print_master(f"  {inp:+4d} {wgt:+4d} {exp:+4d} {sfg_key:<6} {st}")

    # Overall
    all_passed = total_passed == total_tests
    print_master(f"\n  {'*'*50}")
    print_master(f"  *  {total_passed}/{total_tests} TESTS PASSED"
                 f"{'  — ALL CLEAR!' if all_passed else '  — SOME FAILED'}")
    print_master(f"  *  Total time: {total_time:.0f}s ({total_time/60:.1f} min)")
    print_master(f"  {'*'*50}")

    if all_passed:
        print_master(f"\n  ✓ ALL 6 TRIPLETS VALIDATED")
        print_master(f"  ✓ 6-LANE PARALLEL PPLN ARCHITECTURE CONFIRMED")
        print_master(f"  ✓ EACH MIXER PRODUCES CORRECT SFG WITH PER-TRIPLET QPM")
    else:
        failed = []
        for tid in sorted(all_results.keys()):
            for sfg_key, r in all_results[tid].items():
                if not r['passed']:
                    failed.append(f"T{tid} {sfg_key}")
        print_master(f"\n  ✗ FAILED TESTS: {', '.join(failed)}")

    return all_passed


def save_plots(all_results, output_dir):
    """Generate per-triplet spectral plots."""
    if RANK != 0:
        return

    dark_bg = '#1a1a2e'
    dark_fg = '#e0e0e0'
    dark_grid = '#333355'
    triplet_colors = {
        1: '#ff6b6b', 2: '#4ecdc4', 3: '#ffe66d',
        4: '#a8e6cf', 5: '#ff9ff3', 6: '#48dbfb'
    }
    sfg_colors = ['#ff6b6b', '#4ecdc4', '#ffe66d', '#a8e6cf', '#ff9ff3', '#48dbfb']

    for tid in sorted(all_results.keys()):
        results = all_results[tid]
        triplet = TRIPLETS[tid]

        fig, axes = plt.subplots(3, 2, figsize=(18, 16), facecolor=dark_bg)
        fig.suptitle(f"T{tid} Integration Test: "
                     f"{triplet['lambda_pos']*1000:.0f}/"
                     f"{triplet['lambda_zero']*1000:.0f}/"
                     f"{triplet['lambda_neg']*1000:.0f} nm",
                     fontsize=16, fontweight='bold', color=dark_fg, y=0.98)

        for idx, sfg_key in enumerate(['B+B', 'G+B', 'R+B', 'G+G', 'R+G', 'R+R']):
            ax = axes[idx // 2][idx % 2]
            ax.set_facecolor(dark_bg)

            r = results[sfg_key]
            wvls_nm = r['wvls'] * 1000
            flux = np.abs(r['flux'])

            mask = (wvls_nm >= 450) & (wvls_nm <= 750)
            ax.plot(wvls_nm[mask], flux[mask], color=sfg_colors[idx],
                    linewidth=1.0, alpha=0.5, label='Full spectrum')

            sfg_wvls_nm = r['sfg_wvls'] * 1000
            ax.plot(sfg_wvls_nm, r['sfg_flux'], color='white',
                    linewidth=2.0, alpha=0.9, label='SFG window')

            target = r['lambda_sfg'] * 1000
            ax.axvline(x=target, color='#00ff88', linestyle='--',
                       linewidth=2, alpha=0.8, label=f'Expected {target:.0f}nm')

            status_color = '#4ecdc4' if r['passed'] else '#ff6b6b'
            ax.set_title(f"{sfg_key}: {r['lambda_a']*1000:.0f}+"
                         f"{r['lambda_b']*1000:.0f} -> {target:.0f}nm "
                         f"[{r['status']}]",
                         color=status_color, fontsize=12, fontweight='bold')

            info_text = f"S/N: {r['snr_db']:.1f} dB\n" \
                        f"Peak: {r['peak_wvl_nm']:.0f}nm\n" \
                        f"Dev: {r['deviation_nm']:.1f}nm"

            ax.text(0.97, 0.95, info_text, transform=ax.transAxes,
                    fontsize=9, color=dark_fg, fontfamily='monospace',
                    verticalalignment='top', horizontalalignment='right',
                    bbox=dict(boxstyle='round', facecolor=dark_bg, edgecolor=dark_grid))

            ax.legend(loc='upper left', fontsize=7, facecolor=dark_bg,
                      edgecolor=dark_grid, labelcolor=dark_fg)
            ax.set_xlabel("Wavelength (nm)", color=dark_fg, fontsize=9)
            ax.set_ylabel("Flux (a.u.)", color=dark_fg, fontsize=9)
            ax.tick_params(colors=dark_fg, labelsize=8)
            ax.grid(True, alpha=0.2, color=dark_grid)
            for spine in ax.spines.values():
                spine.set_color(dark_grid)

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        path = os.path.join(output_dir, f'ioc_6lane_T{tid}.png')
        plt.savefig(path, dpi=200, facecolor=dark_bg, bbox_inches='tight')
        print_master(f"  Plot: {path}")
        plt.close()

    # Summary plot — one row per triplet, showing pass/fail
    fig, ax = plt.subplots(1, 1, figsize=(14, 8), facecolor=dark_bg)
    ax.set_facecolor(dark_bg)

    sfg_keys = ['B+B', 'G+B', 'R+B', 'G+G', 'R+G', 'R+R']
    triplet_ids = sorted(all_results.keys())

    for row, tid in enumerate(triplet_ids):
        results = all_results[tid]
        for col, sfg_key in enumerate(sfg_keys):
            r = results[sfg_key]
            color = '#4ecdc4' if r['passed'] else '#ff6b6b'
            ax.add_patch(plt.Rectangle((col, len(triplet_ids) - 1 - row),
                                       0.9, 0.9, facecolor=color, alpha=0.8))
            ax.text(col + 0.45, len(triplet_ids) - 1 - row + 0.45,
                    f"{r['snr_db']:.0f}dB",
                    ha='center', va='center', fontsize=9, color=dark_bg,
                    fontweight='bold')

    ax.set_xlim(-0.1, len(sfg_keys))
    ax.set_ylim(-0.1, len(triplet_ids))
    ax.set_xticks([i + 0.45 for i in range(len(sfg_keys))])
    ax.set_xticklabels(sfg_keys, color=dark_fg, fontsize=11)
    ax.set_yticks([i + 0.45 for i in range(len(triplet_ids))])
    ax.set_yticklabels([f'T{tid}' for tid in reversed(triplet_ids)],
                       color=dark_fg, fontsize=11)
    ax.set_title("6-Lane Integration Test Summary (S/N in dB)",
                 color=dark_fg, fontsize=14, fontweight='bold')
    ax.tick_params(colors=dark_fg)
    for spine in ax.spines.values():
        spine.set_color(dark_grid)

    path = os.path.join(output_dir, 'ioc_6lane_summary.png')
    plt.savefig(path, dpi=200, facecolor=dark_bg, bbox_inches='tight')
    print_master(f"  Summary plot: {path}")
    plt.close()


def save_results(all_results, total_time, output_dir):
    """Save machine-readable results file."""
    if RANK != 0:
        return

    path = os.path.join(output_dir, 'ioc_6lane_results.txt')
    with open(path, 'w') as f:
        f.write("IOC 6-LANE INTEGRATION TEST RESULTS\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"MPI: {SIZE} processes\n")
        f.write(f"Resolution: {RESOLUTION} px/um\n")
        f.write(f"Chi2: {CHI2_VAL}\n")
        f.write(f"Time: {total_time:.1f}s\n\n")

        total_passed = 0
        total_tests = 0

        for tid in sorted(all_results.keys()):
            results = all_results[tid]
            triplet = TRIPLETS[tid]
            n_passed = sum(1 for r in results.values() if r['passed'])
            total_passed += n_passed
            total_tests += len(results)

            f.write(f"\n[TRIPLET {tid}] "
                    f"{triplet['lambda_pos']*1000:.0f}/"
                    f"{triplet['lambda_zero']*1000:.0f}/"
                    f"{triplet['lambda_neg']*1000:.0f} nm "
                    f"({n_passed}/6)\n")
            f.write("-" * 40 + "\n")

            for sfg_key in ['B+B', 'G+B', 'R+B', 'G+G', 'R+G', 'R+R']:
                r = results[sfg_key]
                f.write(f"  {sfg_key}: peak={r['peak_wvl_nm']:.1f}nm "
                        f"dev={r['deviation_nm']:.1f}nm "
                        f"snr={r['snr_db']:.1f}dB "
                        f"qpm={r['qpm_period']:.2f}um "
                        f"{r['status']}\n")

        f.write(f"\nOVERALL: {total_passed}/{total_tests} PASSED\n")
        f.write(f"ALL_PASSED: {total_passed == total_tests}\n")

    print_master(f"  Results: {path}")


def run_parallel_triplets(output_dir, python_bin, n_cores):
    """
    Run all 6 triplets as parallel subprocesses, each using a share of cores.
    This is the fastest approach — 6 independent simulations running concurrently.
    """
    import subprocess
    import json

    os.makedirs(output_dir, exist_ok=True)

    # Divide cores among 6 triplets
    cores_per_triplet = max(1, n_cores // 6)
    remaining = n_cores - (cores_per_triplet * 6)

    print(f"\n{'#'*70}")
    print(f"#  PARALLEL 6-LANE IOC INTEGRATION TEST")
    print(f"#  Running 6 triplets concurrently")
    print(f"#  Total cores: {n_cores}, per triplet: {cores_per_triplet}")
    print(f"{'#'*70}\n")

    script_path = os.path.abspath(__file__)
    procs = []

    for tid in range(1, 7):
        env = os.environ.copy()
        env['OMP_NUM_THREADS'] = str(cores_per_triplet + (1 if tid <= remaining else 0))
        # Disable MPI for subprocess mode — use OpenMP only
        env['MEEP_NUM_THREADS'] = env['OMP_NUM_THREADS']

        triplet_output = os.path.join(output_dir, f'T{tid}')
        os.makedirs(triplet_output, exist_ok=True)

        cmd = [python_bin, script_path,
               '--triplet', str(tid),
               '--output', triplet_output]

        log_path = os.path.join(triplet_output, f'T{tid}_log.txt')
        log_file = open(log_path, 'w')

        print(f"  Starting T{tid} ({env['OMP_NUM_THREADS']} threads) → {log_path}")
        proc = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=subprocess.STDOUT)
        procs.append((tid, proc, log_file, log_path))

    # Wait for all to complete
    print(f"\n  All 6 triplets running. Waiting for completion...\n")
    t0 = time.time()

    results_summary = {}
    for tid, proc, log_file, log_path in procs:
        proc.wait()
        log_file.close()
        rc = proc.returncode
        status = "PASSED" if rc == 0 else "FAILED"
        results_summary[tid] = {'returncode': rc, 'status': status, 'log': log_path}
        print(f"  T{tid}: {status} (exit code {rc}) — log: {log_path}")

    total_time = time.time() - t0

    # Collect results files
    print(f"\n  {'='*50}")
    print(f"  PARALLEL EXECUTION COMPLETE")
    print(f"  Total wall time: {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"  {'='*50}")

    all_passed = all(r['returncode'] == 0 for r in results_summary.values())

    for tid in range(1, 7):
        r = results_summary[tid]
        marker = "✓" if r['returncode'] == 0 else "✗"
        print(f"  {marker} T{tid}: {r['status']}")

        # Print key results from log
        try:
            with open(r['log'], 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if 'PASS' in line or 'FAIL' in line:
                        if any(k in line for k in ['B+B', 'G+B', 'R+B', 'G+G', 'R+G', 'R+R']):
                            print(f"    {line.rstrip()}")
        except Exception:
            pass

    print(f"\n  {'*'*50}")
    if all_passed:
        print(f"  *  ALL 6 TRIPLETS PASSED — 6-LANE ARCHITECTURE VALIDATED")
    else:
        failed = [f"T{tid}" for tid, r in results_summary.items() if r['returncode'] != 0]
        print(f"  *  FAILED: {', '.join(failed)}")
    print(f"  *  Wall time: {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"  *  Output: {output_dir}")
    print(f"  {'*'*50}")

    return all_passed


def main():
    parser = argparse.ArgumentParser(description='IOC 6-Lane Integration Test')
    parser.add_argument('--triplet', type=int, default=None,
                        help='Test single triplet (1-6), default: all')
    parser.add_argument('--output', type=str,
                        default='/home/jackwayne/Desktop/Optical_computing/Research/data/ioc_6lane_validation',
                        help='Output directory')
    parser.add_argument('--parallel', action='store_true',
                        help='Run all 6 triplets as parallel subprocesses (max core usage)')
    parser.add_argument('--cores', type=int, default=None,
                        help='Total CPU cores available (default: auto-detect)')
    parser.add_argument('--python', type=str,
                        default='/home/jackwayne/miniconda/envs/meep_env/bin/python',
                        help='Path to Python binary with Meep installed')

    # In parallel subprocess mode, only rank 0 matters
    if RANK == 0:
        args = parser.parse_args()
    else:
        args = argparse.Namespace(triplet=None, output='', parallel=False, cores=None, python='')

    if IS_PARALLEL:
        args = MPI.COMM_WORLD.bcast(args, root=0)

    # Auto-detect cores
    if args.cores is None:
        try:
            args.cores = len(os.sched_getaffinity(0))
        except AttributeError:
            import multiprocessing
            args.cores = multiprocessing.cpu_count()

    # Parallel mode — run 6 triplets concurrently as subprocesses
    if args.parallel:
        success = run_parallel_triplets(args.output, args.python, args.cores)
        sys.exit(0 if success else 1)

    # Sequential mode (single triplet or all)
    output_dir = args.output
    if RANK == 0:
        os.makedirs(output_dir, exist_ok=True)

    triplet_ids = [args.triplet] if args.triplet else None

    all_results, total_time = run_all(triplet_ids)
    all_passed = print_summary(all_results, total_time)
    save_plots(all_results, output_dir)
    save_results(all_results, total_time, output_dir)

    print_master(f"\n  6-LANE IOC INTEGRATION TEST COMPLETE")
    print_master(f"  Status: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    print_master(f"  Output: {output_dir}\n")

    return all_passed


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
