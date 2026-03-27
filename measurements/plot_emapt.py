#!/usr/bin/env python3
"""Plot EMAPT coverage curve from baseline/SDNV CSV files."""

import argparse
import csv
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_curve(path):
    with open(path, newline='') as f:
        reader = csv.reader(f)
        header = next(reader, [])
        if not header:
            return [], [], 'ms'
        time_label = header[0]
        times = []
        coverage = []
        for row in reader:
            if len(row) < 2:
                continue
            try:
                times.append(float(row[0]))
                coverage.append(float(row[1]))
            except ValueError:
                continue

    unit = 'ms'
    if 'time_s' in time_label or 'seconds' in time_label:
        unit = 's'
    return times, coverage, unit


def main():
    parser = argparse.ArgumentParser(description='Plot EMAPT coverage curves')
    parser.add_argument('--baseline', default='results/coverage_curve_baseline.csv')
    parser.add_argument('--sdnv', default='results/coverage_curve_sdnv.csv')
    parser.add_argument('--out', default='results/coverage_curve.png')
    args = parser.parse_args()

    b_times, b_cov, b_unit = load_curve(args.baseline)
    s_times, s_cov, s_unit = load_curve(args.sdnv)

    # Convert seconds to milliseconds if needed.
    if b_unit == 's':
        b_times = [t * 1000.0 for t in b_times]
    if s_unit == 's':
        s_times = [t * 1000.0 for t in s_times]

    plt.figure(figsize=(5.2, 3.2))
    if b_times:
        plt.plot(b_times, b_cov, marker='o', label='Baseline')
    if s_times:
        plt.plot(s_times, s_cov, marker='o', label='SDNV')

    plt.title('EMAPT Coverage Curve')
    plt.xlabel('Time (ms)')
    plt.ylabel('Coverage fraction')
    plt.ylim(0, 1.05)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    plt.savefig(args.out)
    plt.close()

    print(f"Wrote {args.out}")


if __name__ == '__main__':
    main()
