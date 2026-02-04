#!/usr/bin/env python3
"""
Parallel Wavelength Triplet Search - Uses all available cores
"""

import itertools
from typing import List, Tuple, Set
from multiprocessing import Pool, cpu_count
import time


def sfg_wavelength(l1: float, l2: float) -> float:
    return (l1 * l2) / (l1 + l2)


def get_all_sfg_products(wavelengths: List[float]) -> Set[float]:
    products = set()
    for i, l1 in enumerate(wavelengths):
        for l2 in wavelengths[i:]:
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


def can_stack_triplets(triplets: List[Tuple[float, float, float]], tolerance: float = 10.0) -> bool:
    all_wavelengths = []
    for t in triplets:
        all_wavelengths.extend(list(t))

    for i, w1 in enumerate(all_wavelengths):
        for w2 in all_wavelengths[i+1:]:
            if abs(w1 - w2) <= tolerance:
                return False

    sfg_products = get_all_sfg_products(all_wavelengths)
    for product in sfg_products:
        if check_collision(product, all_wavelengths, tolerance):
            return False
    return True


def check_triplet_valid(args):
    triplet, tolerance = args
    if is_valid_triplet(triplet, tolerance):
        return triplet
    return None


def try_start_triplet(args):
    """Try building a stack starting from one triplet."""
    start_triplet, all_triplets, tolerance, max_depth = args
    current_stack = [start_triplet]

    for t in all_triplets:
        if t == start_triplet:
            continue
        if len(current_stack) >= max_depth:
            break
        test = current_stack + [t]
        if can_stack_triplets(test, tolerance):
            current_stack.append(t)

    return current_stack


def find_all_valid_triplets_parallel(min_wl=1000, max_wl=1700, step=10, tolerance=10.0):
    wavelengths = list(range(int(min_wl), int(max_wl) + 1, int(step)))
    all_combos = list(itertools.combinations(wavelengths, 3))
    args = [(tuple(sorted(c, reverse=True)), tolerance) for c in all_combos]

    print(f"Checking {len(args)} combinations with {cpu_count()} cores...")

    with Pool(cpu_count()) as pool:
        results = pool.map(check_triplet_valid, args, chunksize=100)

    return [r for r in results if r is not None]


def find_max_stack_parallel(valid_triplets, tolerance=10.0, max_depth=6):
    if not valid_triplets:
        return []

    print(f"Trying {len(valid_triplets)} starting points with {cpu_count()} cores...")

    args = [(t, valid_triplets, tolerance, max_depth) for t in valid_triplets]

    with Pool(cpu_count()) as pool:
        all_stacks = pool.map(try_start_triplet, args, chunksize=50)

    best = max(all_stacks, key=len)
    return best


def analyze_triplet(triplet):
    a, b, c = triplet
    return {
        'SFG_AB': sfg_wavelength(a, b),
        'SFG_AC': sfg_wavelength(a, c),
        'SFG_BC': sfg_wavelength(b, c),
    }


def main():
    start_time = time.time()

    print("=" * 70)
    print("PARALLEL WAVELENGTH TRIPLET SEARCH")
    print(f"Using {cpu_count()} CPU cores")
    print("=" * 70)

    known = (1550, 1310, 1064)
    print(f"\nKnown triplet: {known}")
    a = analyze_triplet(known)
    print(f"  SFG: {a['SFG_AB']:.1f}, {a['SFG_AC']:.1f}, {a['SFG_BC']:.1f} nm")
    print(f"  Valid: {is_valid_triplet(known)}")

    print("\nPhase 1: Finding valid triplets...")
    valid_triplets = find_all_valid_triplets_parallel(1000, 1700, 10, 10.0)
    print(f"Found {len(valid_triplets)} valid triplets")

    print("\nPhase 2: Finding maximum stackable...")
    best_stack = find_max_stack_parallel(valid_triplets, 10.0, 6)

    elapsed = time.time() - start_time

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {len(best_stack)} STACKABLE TRIPLETS")
    print(f"Time: {elapsed:.1f} seconds")
    print(f"{'=' * 70}")

    all_wl = []
    for i, t in enumerate(best_stack):
        all_wl.extend(t)
        a = analyze_triplet(t)
        print(f"\nTriplet {i+1}: {t[0]}nm / {t[1]}nm / {t[2]}nm")
        print(f"  SFG: {a['SFG_AB']:.0f}, {a['SFG_AC']:.0f}, {a['SFG_BC']:.0f} nm")

    print(f"\n{'=' * 70}")
    print(f"TOTAL CHANNELS: {len(all_wl)}")
    print(f"Wavelengths: {sorted(all_wl)}")

    if len(best_stack) > 0:
        print(f"\n{'=' * 70}")
        print("PERFORMANCE PROJECTIONS (with 8 dense WDM per band)")
        print(f"{'=' * 70}")

        n = len(best_stack)
        total = n * 3 * 8

        for name, pes in [("27×27", 729), ("81×81", 6561), ("243×243", 59049)]:
            tflops = pes * total * 617e6 / 1e12
            print(f"  {name}: {tflops:.1f} TFLOPS")


if __name__ == "__main__":
    main()
