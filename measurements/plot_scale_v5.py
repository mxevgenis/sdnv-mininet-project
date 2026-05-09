#!/usr/bin/env python3
"""Plot cooperative v5 scalability metrics."""

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


def _series(summary_rows, key, scenario):
    xs = []
    means = []
    stds = []
    for row in summary_rows:
        xs.append(int(float(row['vehicle_count'])))
        means.append(to_float(row.get(f'{key}_{scenario}_mean')))
        stds.append(to_float(row.get(f'{key}_{scenario}_std')))
    return xs, means, stds


def _plot_four_lines(summary_rows, specs, title, ylabel, out_path):
    plt.figure(figsize=(7.2, 4.2))
    for key, scenario, label, color, linestyle in specs:
        xs, means, stds = _series(summary_rows, key, scenario)
        plt.errorbar(
            xs,
            means,
            yerr=stds,
            color=color,
            linestyle=linestyle,
            marker='o',
            linewidth=1.5,
            capsize=3,
            label=label,
        )
    plt.title(title)
    plt.xlabel('Vehicles')
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.25)
    plt.legend(frameon=False, ncol=2)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def _plot_emapt(summary_rows, out_path):
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 9.2), sharex=True)
    metrics = [
        ('emapt_50_ms', 'EMAPT-50'),
        ('emapt_90_ms', 'EMAPT-90'),
        ('emapt_100_ms', 'EMAPT-100'),
    ]
    for ax, (key, label) in zip(axes, metrics):
        for scenario, color in (('baseline', '#2563eb'), ('sdnv', '#dc2626')):
            xs, means, stds = _series(summary_rows, key, scenario)
            ax.errorbar(
                xs,
                means,
                yerr=stds,
                color=color,
                linestyle='-',
                marker='o',
                linewidth=1.5,
                capsize=3,
                label=scenario.upper(),
            )
        ax.set_title(label)
        ax.set_ylabel('Time (ms)')
        ax.grid(True, alpha=0.25)
        ax.legend(frameon=False)
    axes[-1].set_xlabel('Vehicles')
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description='Plot cooperative v5 scalability metrics')
    parser.add_argument('--summary', default='results/scale_summary_v5.csv')
    parser.add_argument('--outdir', default='results/scale_metrics_v5')
    args = parser.parse_args()

    summary_rows = load_rows(args.summary)
    if not summary_rows:
        print('Missing input CSV. Run scale_analysis_v5.py first.')
        return

    os.makedirs(args.outdir, exist_ok=True)

    _plot_four_lines(
        summary_rows,
        [
            ('background_latency_avg_ms', 'baseline', 'Baseline TCP', '#2563eb', '--'),
            ('emergency_latency_avg_ms', 'baseline', 'Baseline UDP', '#2563eb', '-'),
            ('background_latency_avg_ms', 'sdnv', 'SDNV TCP', '#dc2626', '--'),
            ('emergency_latency_avg_ms', 'sdnv', 'SDNV UDP', '#dc2626', '-'),
        ],
        'Latency vs Vehicles',
        'Time (ms)',
        os.path.join(args.outdir, 'latency_vs_vehicles.png'),
    )

    _plot_four_lines(
        summary_rows,
        [
            ('throughput_mbps', 'baseline', 'Baseline TCP', '#2563eb', '--'),
            ('udp_bw_mbps', 'baseline', 'Baseline UDP', '#2563eb', '-'),
            ('throughput_mbps', 'sdnv', 'SDNV TCP', '#dc2626', '--'),
            ('udp_bw_mbps', 'sdnv', 'SDNV UDP', '#dc2626', '-'),
        ],
        'Throughput vs Vehicles',
        'Throughput (Mbps)',
        os.path.join(args.outdir, 'throughput_vs_vehicles.png'),
    )

    _plot_emapt(summary_rows, os.path.join(args.outdir, 'emapt_vs_vehicles.png'))
    print(f'Wrote plots to {args.outdir}')


if __name__ == '__main__':
    main()
