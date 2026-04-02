#!/usr/bin/env python3
"""Plot EMAPT-50/90/100 vs vehicle count (separate PNGs)."""

import argparse
import csv
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_rows(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def to_float(val):
    try:
        return float(val)
    except Exception:
        return None


def plot_metric(rows, key_base, title, out_path):
    vehicles = [int(r['vehicles']) for r in rows]
    b = [to_float(r.get(f"{key_base}_baseline")) for r in rows]
    s = [to_float(r.get(f"{key_base}_sdnv")) for r in rows]

    plt.figure(figsize=(5.5, 3.2))
    plt.plot(vehicles, b, marker='o', label='Baseline')
    plt.plot(vehicles, s, marker='o', label='SDNV')
    plt.title(title)
    plt.xlabel('Vehicles')
    plt.ylabel('Time (ms)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Plot EMAPT metrics vs vehicles')
    parser.add_argument('--summary', default='results/scale_summary.csv')
    parser.add_argument('--outdir', default='results/scale_emapt_metrics')
    args = parser.parse_args()

    rows = load_rows(args.summary)
    if not rows:
        print(f"No data in {args.summary}")
        return

    os.makedirs(args.outdir, exist_ok=True)
    plot_metric(rows, 'emapt_50_ms', 'EMAPT-50 vs Vehicles',
                os.path.join(args.outdir, 'emapt_50_ms.png'))
    plot_metric(rows, 'emapt_90_ms', 'EMAPT-90 vs Vehicles',
                os.path.join(args.outdir, 'emapt_90_ms.png'))
    plot_metric(rows, 'emapt_100_ms', 'EMAPT-100 vs Vehicles',
                os.path.join(args.outdir, 'emapt_100_ms.png'))

    print(f"Wrote EMAPT metric plots to {args.outdir}")


if __name__ == '__main__':
    main()
