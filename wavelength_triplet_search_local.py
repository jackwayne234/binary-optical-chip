#!/usr/bin/env python3
"""
Wavelength Triplet Search for Ternary Optical Computing
"""
import itertools
from typing import List, Tuple, Set

def sfg_wavelength(l1: float, l2: float) -> float:
    return (l1 * l2) / (l1 + l2)

def get_all_sfg_products(wavelengths: List[float]) -> Set[float]:
    products = set()
    for i, l1 in enumerate(wavelengths):
        for j, l2 in enumerate(wavelengths):
            if i <= j:
                products.add(sfg_wavelength(l1, l2))
    return products

def check_collision(value: float, targets: List[float], tolerance: float = 10.0) -> bool:
    for target in targets:
        if abs(value - target) <= tolerance:
            return True
    return False

def is_valid_triplet(triplet: Tuple[float, float, float], tolerance: float = 10.0) -> bool:
    wavelengths = list(triplet)
    sfg_products = get_all_sfg_products(wavelengths)
    for product in sfg_products:
        if check_collision(product, wavelengths, tolerance):
            return False
    return True

def can_add_triplet(existing_wavelengths: List[float], new_triplet: Tuple[float, float, float],
                    tolerance: float = 10.0) -> bool:
    new_wavelengths = list(new_triplet)
    all_wavelengths = existing_wavelengths + new_wavelengths
    for nw in new_wavelengths:
        if check_collision(nw, existing_wavelengths, tolerance):
            return False
    sfg_products = get_all_sfg_products(all_wavelengths)
    for product in sfg_products:
        if check_collision(product, all_wavelengths, tolerance):
            return False
    return True

def find_all_valid_triplets(min_wl: float = 1000, max_wl: float = 1700,
                            step: float = 10, tolerance: float = 10.0) -> List[Tuple[float, float, float]]:
    wavelengths = list(range(int(min_wl), int(max_wl) + 1, int(step)))
    valid_triplets = []
    for combo in itertools.combinations(wavelengths, 3):
        triplet = tuple(sorted(combo, reverse=True))
        if is_valid_triplet(triplet, tolerance):
            valid_triplets.append(triplet)
    return valid_triplets

def find_max_stackable_exhaustive(valid_triplets: List[Tuple[float, float, float]],
                                   tolerance: float = 10.0,
                                   max_depth: int = 8) -> Tuple[int, List[Tuple[float, float, float]]]:
    if not valid_triplets:
        return 0, []
    best_stack = []
    def backtrack(current_stack, current_wavelengths, remaining):
        nonlocal best_stack
        if len(current_stack) > len(best_stack):
            best_stack = current_stack.copy()
        if len(current_stack) >= max_depth:
            return
        for i, triplet in enumerate(remaining):
            if can_add_triplet(current_wavelengths, triplet, tolerance):
                current_stack.append(triplet)
                backtrack(current_stack, current_wavelengths + list(triplet), remaining[i+1:])
                current_stack.pop()
    backtrack([], [], valid_triplets)
    return len(best_stack), best_stack

def analyze_triplet(triplet):
    a, b, c = triplet
    return {
        'SFG_AB': sfg_wavelength(a, b),
        'SFG_AC': sfg_wavelength(a, c),
        'SFG_BC': sfg_wavelength(b, c),
    }

if __name__ == "__main__":
    print("=" * 70)
    print("WAVELENGTH TRIPLET SEARCH FOR TERNARY OPTICAL COMPUTING")
    print("=" * 70)

    known = (1550, 1310, 1064)
    print(f"\nKnown triplet: {known}")
    a = analyze_triplet(known)
    print(f"  SFG products: {a['SFG_AB']:.1f}, {a['SFG_AC']:.1f}, {a['SFG_BC']:.1f} nm")
    print(f"  Valid: {is_valid_triplet(known)}")

    print("\nSearching for valid triplets (1000-1700nm, 10nm step)...")
    valid_triplets = find_all_valid_triplets(1000, 1700, 10, 10.0)
    print(f"Found {len(valid_triplets)} valid single triplets")

    print("\nSample valid triplets:")
    for t in valid_triplets[:5]:
        a = analyze_triplet(t)
        print(f"  {t} -> SFG: {a['SFG_AB']:.0f}, {a['SFG_AC']:.0f}, {a['SFG_BC']:.0f} nm")

    print("\nSearching for maximum stackable triplets...")
    max_count, best_stack = find_max_stackable_exhaustive(valid_triplets, 10.0, 8)

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {max_count} STACKABLE TRIPLETS FOUND")
    print(f"{'=' * 70}")

    all_wavelengths = []
    for i, t in enumerate(best_stack):
        all_wavelengths.extend(t)
        a = analyze_triplet(t)
        print(f"\nTriplet {i+1}: {t[0]}nm / {t[1]}nm / {t[2]}nm")
        print(f"  SFG products: {a['SFG_AB']:.0f}nm, {a['SFG_AC']:.0f}nm, {a['SFG_BC']:.0f}nm")

    print(f"\n{'=' * 70}")
    print(f"TOTAL WAVELENGTH CHANNELS: {len(all_wavelengths)}")
    print(f"All wavelengths (nm): {sorted(all_wavelengths)}")

    if max_count > 0:
        print(f"\n{'=' * 70}")
        print("PERFORMANCE PROJECTIONS")
        print(f"{'=' * 70}")
        dense_wdm = 8
        total_channels = max_count * 3 * dense_wdm
        print(f"\nWith {dense_wdm} dense WDM channels per band:")
        print(f"  Total parallel wavelength lanes: {max_count} triplets x 3 bands x {dense_wdm} = {total_channels}")
        for array_name, pes in [("27x27", 729), ("81x81", 6561), ("243x243", 59049)]:
            ops = pes * total_channels
            tflops = ops * 617e6 / 1e12
            print(f"\n  {array_name} array ({pes} PEs):")
            print(f"    Parallel ops: {ops:,}")
            print(f"    @ 617 MHz: {tflops:.1f} TFLOPS")
