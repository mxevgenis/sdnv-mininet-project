#!/usr/bin/env python3
"""Plot EMAPT coverage curves per vehicle count (baseline vs SDNV)."""

import argparse
import glob
import os
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def latest_emapt_csv(prefix):
    pattern = os.path.join('results', f"emapt_{prefix}_*.csv")
    matches = glob.glob(pattern)
    if not matches:
        return None

    def ts(p):
        m = re.search(r'_(\d+)\.csv$', os.path.basename(p))
        return int(m.group(1)) if m else 0

    return max(matches, key=ts)


def parse_coverage(path):
    times = []
    covs = []
    if not path:
        return times, covs, 'ms'
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        header = None
        for line in f:
            line = line.strip()
            if line.startswith('coverage_curve_'):
                header = line
                break
        if header is None:
            return times, covs, 'ms'
        unit = 'ms'
        if header.startswith('coverage_curve_seconds'):
            unit = 's'
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) < 2:
                continue
            try:
                t = float(parts[0])
                c = float(parts[1])
            except ValueError:
                continue
            if unit == 's':
                t *= 1000.0
            times.append(t)
            covs.append(c)
    return times, covs, 'ms'


def main():
    parser = argparse.ArgumentParser(description='Plot EMAPT coverage curves per vehicle count')
    parser.add_argument('--counts', default='5,9,13,17,20')
    parser.add_argument('--baseline-prefix', default='emapt_baseline_scale_v')
    parser.add_argument('--sdnv-prefix', default='emapt_sdnv_scale_v')
    parser.add_argument('--outdir', default='results/scale_emapt_curves')
    args = parser.parse_args()

    counts = [int(c.strip()) for c in args.counts.split(',') if c.strip()]
    os.makedirs(args.outdir, exist_ok=True)

    for n in counts:
        b_path = latest_emapt_csv(f"{args.baseline_prefix}{n}")
        s_path = latest_emapt_csv(f"{args.sdnv_prefix}{n}")
        b_times, b_cov, _ = parse_coverage(b_path)
        s_times, s_cov, _ = parse_coverage(s_path)

        plt.figure(figsize=(5.5, 3.2))
        if b_times:
            plt.plot(b_times, b_cov, marker='o', label='Baseline')
        if s_times:
            plt.plot(s_times, s_cov, marker='o', label='SDNV')
        plt.title(f'EMAPT Coverage Curve (Vehicles={n})')
        plt.xlabel('Time (ms)')
        plt.ylabel('Coverage fraction')
        plt.ylim(0, 1.05)
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        out_path = os.path.join(args.outdir, f'emapt_curve_v{n}.png')
        plt.savefig(out_path)
        plt.close()

    print(f"Wrote EMAPT curves to {args.outdir}")


if __name__ == '__main__':
    main()
