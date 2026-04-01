#!/usr/bin/env python3
"""Plot EMAPT-50/90/100 comparison for baseline vs SDNV."""

import argparse
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def _parse_emapt(path):
    values = {}
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('coverage_curve_'):
                break
            if '=' not in line:
                continue
            key, val = line.split('=', 1)
            try:
                values[key.strip()] = float(val.strip())
            except ValueError:
                continue

    # Normalize to ms
    out = {}
    if 'emapt_50_ms' in values:
        out['emapt_50_ms'] = values.get('emapt_50_ms')
        out['emapt_90_ms'] = values.get('emapt_90_ms')
        out['emapt_100_ms'] = values.get('emapt_100_ms')
        return out

    # fall back to seconds keys if present
    if 'emapt_50' in values:
        out['emapt_50_ms'] = values.get('emapt_50') * 1000.0
        out['emapt_90_ms'] = values.get('emapt_90') * 1000.0
        out['emapt_100_ms'] = values.get('emapt_100') * 1000.0
    return out


def main():
    parser = argparse.ArgumentParser(description='Plot EMAPT comparison bars')
    parser.add_argument('--baseline', required=True, help='baseline emapt csv')
    parser.add_argument('--sdnv', required=True, help='sdnv emapt csv')
    parser.add_argument('--out', default='results/emapt_comparison.png')
    args = parser.parse_args()

    b = _parse_emapt(args.baseline)
    s = _parse_emapt(args.sdnv)

    labels = ['EMAPT-50', 'EMAPT-90', 'EMAPT-100']
    b_vals = [b.get('emapt_50_ms'), b.get('emapt_90_ms'), b.get('emapt_100_ms')]
    s_vals = [s.get('emapt_50_ms'), s.get('emapt_90_ms'), s.get('emapt_100_ms')]

    x = range(len(labels))
    width = 0.35

    plt.figure(figsize=(6.5, 3.5))
    plt.bar([i - width / 2 for i in x], b_vals, width, label='Baseline', color='#4c78a8')
    plt.bar([i + width / 2 for i in x], s_vals, width, label='SDNV', color='#f28e2b')
    plt.xticks(list(x), labels)
    plt.ylabel('Time (ms)')
    plt.title('EMAPT Comparison')
    plt.grid(True, axis='y', alpha=0.3)
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
