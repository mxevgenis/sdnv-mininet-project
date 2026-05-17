#!/usr/bin/env python3
"""Plot cooperative v6 scalability metrics."""

import argparse
import csv
import os
from collections import defaultdict

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


def _run_points(run_rows, key, scenario):
    grouped = defaultdict(list)
    column = f'{key}_{scenario}'
    for row in run_rows:
        x = int(float(row['vehicle_count']))
        value = to_float(row.get(column))
        if value is not None:
            grouped[x].append(value)
    return grouped


def _summary_points(summary_rows, key):
    xs = []
    means = []
    stds = []
    for row in summary_rows:
        xs.append(int(float(row['vehicle_count'])))
        means.append(to_float(row.get(f'{key}_mean')))
        stds.append(to_float(row.get(f'{key}_std')))
    return xs, means, stds


def _run_points_single(run_rows, key):
    grouped = defaultdict(list)
    for row in run_rows:
        x = int(float(row['vehicle_count']))
        value = to_float(row.get(key))
        if value is not None:
            grouped[x].append(value)
    return grouped


def _plot_four_lines(summary_rows, run_rows, specs, title, ylabel, out_path):
    plt.figure(figsize=(7.2, 4.2))
    for key, scenario, label, color, linestyle in specs:
        xs, means, stds = _series(summary_rows, key, scenario)
        grouped = _run_points(run_rows, key, scenario)
        scatter_x = []
        scatter_y = []
        for x in xs:
            values = grouped.get(x, [])
            scatter_x.extend([x] * len(values))
            scatter_y.extend(values)
        plt.scatter(
            scatter_x,
            scatter_y,
            color=color,
            s=22,
            alpha=0.85,
            edgecolors='none',
        )
        plt.plot(
            xs,
            means,
            color=color,
            linestyle=linestyle,
            marker='o',
            linewidth=1.5,
            markersize=5,
            label=f'{label} mean',
        )
    plt.title(title)
    plt.xlabel('Vehicles')
    plt.ylabel(ylabel)
    plt.ylim(bottom=0)
    plt.grid(True, alpha=0.25)
    plt.legend(frameon=False, ncol=2)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def _plot_two_lines(summary_rows, run_rows, key, title, ylabel, out_path):
    plt.figure(figsize=(7.2, 4.2))
    for scenario, color in (('baseline', '#2563eb'), ('sdnv', '#dc2626')):
        xs, means, _stds = _series(summary_rows, key, scenario)
        grouped = _run_points(run_rows, key, scenario)
        scatter_x = []
        scatter_y = []
        for x in xs:
            values = grouped.get(x, [])
            scatter_x.extend([x] * len(values))
            scatter_y.extend(values)
        plt.scatter(
            scatter_x,
            scatter_y,
            color=color,
            s=22,
            alpha=0.85,
            edgecolors='none',
        )
        plt.plot(
            xs,
            means,
            color=color,
            linestyle='-',
            marker='o',
            linewidth=1.5,
            markersize=5,
            label=f'{scenario.upper()} mean',
        )
    plt.title(title)
    plt.xlabel('Vehicles')
    plt.ylabel(ylabel)
    plt.ylim(bottom=0)
    plt.grid(True, alpha=0.25)
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def _plot_single_series(summary_rows, run_rows, key, title, ylabel, out_path, color='#dc2626', label='SDNV mean'):
    plt.figure(figsize=(7.2, 4.2))
    xs, means, _stds = _summary_points(summary_rows, key)
    grouped = _run_points_single(run_rows, key)
    scatter_x = []
    scatter_y = []
    for x in xs:
        values = grouped.get(x, [])
        scatter_x.extend([x] * len(values))
        scatter_y.extend(values)
    plt.scatter(
        scatter_x,
        scatter_y,
        color=color,
        s=22,
        alpha=0.85,
        edgecolors='none',
    )
    plt.plot(
        xs,
        means,
        color=color,
        linestyle='-',
        marker='o',
        linewidth=1.5,
        markersize=5,
        label=label,
    )
    plt.title(title)
    plt.xlabel('Vehicles')
    plt.ylabel(ylabel)
    plt.ylim(bottom=0)
    plt.grid(True, alpha=0.25)
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def _plot_emapt(summary_rows, run_rows, out_path):
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 9.2), sharex=True)
    metrics = [
        ('emapt_50_ms', 'EMAPT-50'),
        ('emapt_90_ms', 'EMAPT-90'),
        ('emapt_100_ms', 'EMAPT-100'),
    ]
    for ax, (key, label) in zip(axes, metrics):
        for scenario, color in (('baseline', '#2563eb'), ('sdnv', '#dc2626')):
            xs, means, stds = _series(summary_rows, key, scenario)
            grouped = _run_points(run_rows, key, scenario)
            scatter_x = []
            scatter_y = []
            for x in xs:
                values = grouped.get(x, [])
                scatter_x.extend([x] * len(values))
                scatter_y.extend(values)
            ax.scatter(
                scatter_x,
                scatter_y,
                color=color,
                s=22,
                alpha=0.85,
                edgecolors='none',
            )
            ax.plot(
                xs,
                means,
                color=color,
                linestyle='-',
                marker='o',
                linewidth=1.5,
                markersize=5,
                label=f'{scenario.upper()} mean',
            )
        ax.set_title(label)
        ax.set_ylabel('Time (ms)')
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.25)
        ax.legend(frameon=False)
    axes[-1].set_xlabel('Vehicles')
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description='Plot cooperative v6 scalability metrics')
    parser.add_argument('--summary', default='results/scale_summary_v6.csv')
    parser.add_argument('--runs', default='results/scale_runs_v6.csv')
    parser.add_argument('--outdir', default='results/scale_metrics_v6')
    args = parser.parse_args()

    summary_rows = load_rows(args.summary)
    if not summary_rows:
        print('Missing input CSV. Run scale_analysis_v5.py first.')
        return
    run_rows = load_rows(args.runs)
    if not run_rows:
        print('Missing run CSV. Run scale_analysis_v6.py first.')
        return

    os.makedirs(args.outdir, exist_ok=True)

    _plot_four_lines(
        summary_rows,
        run_rows,
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
        run_rows,
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

    _plot_emapt(summary_rows, run_rows, os.path.join(args.outdir, 'emapt_vs_vehicles.png'))
    _plot_two_lines(
        summary_rows,
        run_rows,
        'emapt_100_ms',
        'EMAPT-100 vs Vehicles',
        'Time (ms)',
        os.path.join(args.outdir, 'emapt100_vs_vehicles.png'),
    )
    _plot_two_lines(
        summary_rows,
        run_rows,
        'udp_share_pct',
        'UDP Share vs Vehicles',
        'UDP Share (%)',
        os.path.join(args.outdir, 'udp_share_vs_vehicles.png'),
    )
    _plot_two_lines(
        summary_rows,
        run_rows,
        'priority_enforcement_ratio',
        'PER vs Vehicles',
        'Priority Enforcement Ratio',
        os.path.join(args.outdir, 'per_vs_vehicles.png'),
    )
    _plot_single_series(
        summary_rows,
        run_rows,
        'traffic_suppression_efficiency_pct_sdnv',
        'TSE vs Vehicles',
        'Traffic Suppression Efficiency (%)',
        os.path.join(args.outdir, 'tse_vs_vehicles.png'),
    )
    _plot_single_series(
        summary_rows,
        run_rows,
        'policy_reaction_ms_sdnv',
        'PRT vs Vehicles',
        'Policy Reaction Time (ms)',
        os.path.join(args.outdir, 'prt_vs_vehicles.png'),
    )
    print(f'Wrote plots to {args.outdir}')


if __name__ == '__main__':
    main()
