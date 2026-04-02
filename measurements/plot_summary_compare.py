#!/usr/bin/env python3
"""Plot baseline vs SDNV comparisons from a summary CSV."""

import argparse
import csv
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_summary(path):
    data = {'baseline': {}, 'sdnv': {}, 'derived': {}}
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            scenario = row.get('scenario', '').strip()
            metric = row.get('metric', '').strip()
            mean = row.get('mean', '').strip()
            try:
                mean_val = float(mean)
            except ValueError:
                continue
            if scenario in data:
                data[scenario][metric] = mean_val
    return data


def plot_metrics(summary, out_path):
    metrics = [
        ('latency_avg_ms', 'Latency avg (ms)'),
        ('jitter_ms', 'Jitter (ms)'),
        ('udp_bw_mbps', 'Emergency UDP (Mbps)'),
        ('throughput_mbps', 'Background TCP (Mbps)'),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(8, 6))
    axes = axes.ravel()

    for ax, (key, label) in zip(axes, metrics):
        b_val = summary['baseline'].get(key)
        s_val = summary['sdnv'].get(key)
        ax.bar(['Baseline', 'SDNV'], [b_val, s_val], color=['#4c78a8', '#f28e2b'])
        ax.set_title(label)
        ax.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    plt.savefig(out_path)
    plt.close()


def plot_emapt(summary, out_path):
    labels = ['EMAPT-50', 'EMAPT-90', 'EMAPT-100']
    b_vals = [
        summary['baseline'].get('emapt_50_ms'),
        summary['baseline'].get('emapt_90_ms'),
        summary['baseline'].get('emapt_100_ms'),
    ]
    s_vals = [
        summary['sdnv'].get('emapt_50_ms'),
        summary['sdnv'].get('emapt_90_ms'),
        summary['sdnv'].get('emapt_100_ms'),
    ]

    x = range(len(labels))
    width = 0.35

    plt.figure(figsize=(6.5, 3.5))
    plt.bar([i - width / 2 for i in x], b_vals, width, label='Baseline', color='#4c78a8')
    plt.bar([i + width / 2 for i in x], s_vals, width, label='SDNV', color='#f28e2b')
    plt.xticks(list(x), labels)
    plt.ylabel('Time (ms)')
    plt.title('EMAPT Comparison (5-run average)')
    plt.grid(True, axis='y', alpha=0.3)
    plt.legend()
    plt.tight_layout()

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    plt.savefig(out_path)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Plot summary comparisons')
    parser.add_argument('--summary', default='results/summary_5g_be1540_5x.csv')
    parser.add_argument('--out-metrics', default='results/metrics_comparison.png')
    parser.add_argument('--out-emapt', default='results/emapt_comparison.png')
    args = parser.parse_args()

    summary = load_summary(args.summary)
    plot_metrics(summary, args.out_metrics)
    plot_emapt(summary, args.out_emapt)

    print(f"Wrote {args.out_metrics} and {args.out_emapt}")


if __name__ == '__main__':
    main()
