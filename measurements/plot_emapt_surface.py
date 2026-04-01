#!/usr/bin/env python3
"""Plot EMAPT coverage as 3D surfaces (vehicles vs time vs coverage)."""

import argparse
import glob
import os
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


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
        return times, covs
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        header = None
        for line in f:
            line = line.strip()
            if line.startswith('coverage_curve_'):
                header = line
                break
        if header is None:
            return times, covs
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
    return times, covs


def collect_points(counts, prefix):
    xs, ys, zs = [], [], []
    for n in counts:
        path = latest_emapt_csv(f"{prefix}{n}")
        times, covs = parse_coverage(path)
        for t, c in zip(times, covs):
            xs.append(n)
            ys.append(t)
            zs.append(c)
    return xs, ys, zs


def plot_surface(ax, xs, ys, zs, title):
    ax.plot_trisurf(xs, ys, zs, cmap='viridis', linewidth=0.2, antialiased=True)
    ax.set_title(title)
    ax.set_xlabel('Vehicles')
    ax.set_ylabel('Time (ms)')
    ax.set_zlabel('Coverage ratio')


def main():
    parser = argparse.ArgumentParser(description='Plot EMAPT 3D surfaces')
    parser.add_argument('--counts', default='5,9,13,17,20')
    parser.add_argument('--baseline-prefix', default='emapt_baseline_scale_v')
    parser.add_argument('--sdnv-prefix', default='emapt_sdnv_scale_v')
    parser.add_argument('--out', default='results/scale_emapt_surface.png')
    args = parser.parse_args()

    counts = [int(c.strip()) for c in args.counts.split(',') if c.strip()]

    b_x, b_y, b_z = collect_points(counts, args.baseline_prefix)
    s_x, s_y, s_z = collect_points(counts, args.sdnv_prefix)

    fig = plt.figure(figsize=(11, 4.5))
    ax1 = fig.add_subplot(1, 2, 1, projection='3d')
    ax2 = fig.add_subplot(1, 2, 2, projection='3d')

    plot_surface(ax1, b_x, b_y, b_z, 'Baseline EMAPT Surface')
    plot_surface(ax2, s_x, s_y, s_z, 'SDNV EMAPT Surface')

    plt.tight_layout()
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    plt.savefig(args.out)
    plt.close()

    print(f"Wrote {args.out}")


if __name__ == '__main__':
    main()
