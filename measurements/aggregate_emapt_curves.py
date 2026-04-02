#!/usr/bin/env python3
"""Aggregate EMAPT coverage curves across multiple runs."""

import argparse
import glob
import os
import re
import statistics


def latest_emapt_csv(tag):
    pattern = os.path.join('results', f"emapt_{tag}_*.csv")
    matches = glob.glob(pattern)
    if not matches:
        return None

    def ts(p):
        m = re.search(r'_(\d+)\.csv$', os.path.basename(p))
        return int(m.group(1)) if m else 0

    return max(matches, key=ts)


def parse_curve(path):
    curve = {}
    if not path:
        return curve
    in_curve = False
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('coverage_curve_'):
                in_curve = True
                continue
            if not in_curve:
                continue
            parts = line.split(',')
            if len(parts) < 2:
                continue
            try:
                t = float(parts[0])
                cov = float(parts[1])
            except ValueError:
                continue
            cov_key = round(cov, 3)
            curve.setdefault(cov_key, []).append(t)
    return curve


def aggregate(prefix, runs):
    combined = {}
    for i in range(1, runs + 1):
        tag = f"{prefix}{i}"
        path = latest_emapt_csv(tag)
        curve = parse_curve(path)
        for cov, times in curve.items():
            combined.setdefault(cov, []).extend(times)
    averaged = []
    for cov, times in combined.items():
        if not times:
            continue
        averaged.append((statistics.mean(times), cov))
    averaged.sort(key=lambda x: x[1])
    return averaged


def write_curve(path, averaged):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w') as f:
        f.write('time_ms,coverage\n')
        for t, cov in averaged:
            f.write(f"{t:.3f},{cov:.3f}\n")


def main():
    parser = argparse.ArgumentParser(description='Aggregate EMAPT curves')
    parser.add_argument('--runs', type=int, default=5)
    parser.add_argument('--baseline-prefix', default='emapt_baseline_5g_be1540_r')
    parser.add_argument('--sdnv-prefix', default='emapt_sdnv_5g_be1540_r')
    parser.add_argument('--out-baseline', default='results/coverage_curve_baseline.csv')
    parser.add_argument('--out-sdnv', default='results/coverage_curve_sdnv.csv')
    args = parser.parse_args()

    b_avg = aggregate(args.baseline_prefix, args.runs)
    s_avg = aggregate(args.sdnv_prefix, args.runs)
    write_curve(args.out_baseline, b_avg)
    write_curve(args.out_sdnv, s_avg)

    print(f"Wrote {args.out_baseline} and {args.out_sdnv}")


if __name__ == '__main__':
    main()
