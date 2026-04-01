#!/usr/bin/env python3
"""Plot EMAPT coverage as a heatmap (vehicles vs time, color=coverage)."""

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


def collect_points(counts, prefix):
    xs, ys, cs = [], [], []
    for n in counts:
        path = latest_emapt_csv(f"{prefix}{n}")
        times, covs, _unit = parse_coverage(path)
        for t, c in zip(times, covs):
            xs.append(n)
            ys.append(t)
            cs.append(c)
    return xs, ys, cs


def main():
    parser = argparse.ArgumentParser(description='Plot EMAPT coverage heatmaps')
    parser.add_argument('--counts', default='5,9,13,17,20')
    parser.add_argument('--baseline-prefix', default='emapt_baseline_scale_v')
    parser.add_argument('--sdnv-prefix', default='emapt_sdnv_scale_v')
    parser.add_argument('--out', default='results/scale_emapt_heatmap.png')
    args = parser.parse_args()

    counts = [int(c.strip()) for c in args.counts.split(',') if c.strip()]

    b_x, b_y, b_c = collect_points(counts, args.baseline_prefix)
    s_x, s_y, s_c = collect_points(counts, args.sdnv_prefix)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4), sharey=True)

    sc0 = axes[0].scatter(b_x, b_y, c=b_c, cmap='viridis', vmin=0, vmax=1, s=60)
    axes[0].set_title('Baseline Coverage Heatmap')
    axes[0].set_xlabel('Vehicles')
    axes[0].set_ylabel('Time (ms)')
    axes[0].grid(True, alpha=0.2)

    sc1 = axes[1].scatter(s_x, s_y, c=s_c, cmap='viridis', vmin=0, vmax=1, s=60)
    axes[1].set_title('SDNV Coverage Heatmap')
    axes[1].set_xlabel('Vehicles')
    axes[1].grid(True, alpha=0.2)

    cbar = fig.colorbar(sc1, ax=axes, orientation='vertical', fraction=0.03, pad=0.02)
    cbar.set_label('Coverage ratio')

    plt.tight_layout()
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    plt.savefig(args.out)
    plt.close()

    print(f"Wrote {args.out}")


if __name__ == '__main__':
    main()
