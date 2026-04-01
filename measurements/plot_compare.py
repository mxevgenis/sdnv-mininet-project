#!/usr/bin/env python3
"""Create comparison plots for baseline vs SDNV tags."""

import argparse
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from measurements.derived_metrics import load_tag_metrics


def main():
    parser = argparse.ArgumentParser(description='Plot baseline vs SDNV metrics')
    parser.add_argument('--baseline-tag', required=True)
    parser.add_argument('--sdnv-tag', required=True)
    parser.add_argument('--results-dir', default='results')
    parser.add_argument('--out', default='results/metrics_comparison.png')
    args = parser.parse_args()

    baseline = load_tag_metrics(args.results_dir, args.baseline_tag)
    sdnv = load_tag_metrics(args.results_dir, args.sdnv_tag)

    metrics = [
        ('latency_avg_ms', 'Latency avg (ms)'),
        ('jitter_ms', 'Jitter (ms)'),
        ('udp_bw_mbps', 'Emergency UDP (Mbps)'),
        ('throughput_mbps', 'Background TCP (Mbps)'),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(8, 6))
    axes = axes.ravel()

    for ax, (key, label) in zip(axes, metrics):
        b_val = baseline.get(key)
        s_val = sdnv.get(key)
        ax.bar(['Baseline', 'SDNV'], [b_val, s_val], color=['#4c78a8', '#f28e2b'])
        ax.set_title(label)
        ax.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    plt.savefig(args.out)
    plt.close()

    print(f"Wrote {args.out}")


if __name__ == '__main__':
    main()
