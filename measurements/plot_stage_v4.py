#!/usr/bin/env python3
"""Plot staged v4 metrics with scatter and mean/std error bars."""

import argparse
import csv
import os
import random

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


def collect_runs(rows, key):
    data = {}
    for row in rows:
        stage = int(float(row['stage_pct']))
        data.setdefault(stage, {'baseline': [], 'sdnv': []})
        b = to_float(row.get(f'{key}_baseline'))
        s = to_float(row.get(f'{key}_sdnv'))
        if b is not None:
            data[stage]['baseline'].append(b)
        if s is not None:
            data[stage]['sdnv'].append(s)
    return data


def collect_summary(rows, key):
    data = {}
    for row in rows:
        stage = int(float(row['stage_pct']))
        data[stage] = {
            'baseline_mean': to_float(row.get(f'{key}_baseline_mean')),
            'baseline_std': to_float(row.get(f'{key}_baseline_std')),
            'sdnv_mean': to_float(row.get(f'{key}_sdnv_mean')),
            'sdnv_std': to_float(row.get(f'{key}_sdnv_std')),
        }
    return data


def collect_sdnv_only(rows, key):
    data = {}
    for row in rows:
        stage = int(float(row['stage_pct']))
        data.setdefault(stage, [])
        value = to_float(row.get(f'{key}_sdnv'))
        if value is not None:
            data[stage].append(value)
    return data


def collect_sdnv_only_summary(rows, key):
    data = {}
    for row in rows:
        stage = int(float(row['stage_pct']))
        data[stage] = {
            'mean': to_float(row.get(f'{key}_sdnv_mean')),
            'std': to_float(row.get(f'{key}_sdnv_std')),
        }
    return data


def _plot_dual_metric(run_rows, summary_rows, key, title, xlabel, ylabel, out_path):
    runs = collect_runs(run_rows, key)
    summary = collect_summary(summary_rows, key)
    stages = sorted(runs.keys())
    if not stages:
        return

    random.seed(7)
    plt.figure(figsize=(6.6, 3.9))
    for stage in stages:
        base_x = [stage + random.uniform(-1.0, -0.2) for _ in runs[stage]['baseline']]
        sdnv_x = [stage + random.uniform(0.2, 1.0) for _ in runs[stage]['sdnv']]
        plt.scatter(base_x, runs[stage]['baseline'], color='#2563eb', alpha=0.7, s=18)
        plt.scatter(sdnv_x, runs[stage]['sdnv'], color='#dc2626', alpha=0.7, s=18)

    b_means = [summary[stage]['baseline_mean'] for stage in stages]
    b_stds = [summary[stage]['baseline_std'] for stage in stages]
    s_means = [summary[stage]['sdnv_mean'] for stage in stages]
    s_stds = [summary[stage]['sdnv_std'] for stage in stages]
    plt.errorbar(stages, b_means, yerr=b_stds, color='#2563eb', marker='o',
                 linestyle='-', linewidth=1.2, capsize=3, label='BASELINE')
    plt.errorbar(stages, s_means, yerr=s_stds, color='#dc2626', marker='o',
                 linestyle='-', linewidth=1.2, capsize=3, label='SDNV')
    plt.title(title.upper())
    plt.xlabel(xlabel.upper())
    plt.ylabel(ylabel.upper())
    plt.grid(True, alpha=0.25)
    plt.legend(loc='upper left', frameon=False)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def _plot_sdnv_only(run_rows, summary_rows, key, title, xlabel, ylabel, out_path):
    runs = collect_sdnv_only(run_rows, key)
    summary = collect_sdnv_only_summary(summary_rows, key)
    stages = sorted(runs.keys())
    if not stages:
        return

    random.seed(7)
    plt.figure(figsize=(6.6, 3.9))
    for stage in stages:
        xvals = [stage + random.uniform(-0.8, 0.8) for _ in runs[stage]]
        plt.scatter(xvals, runs[stage], color='#dc2626', alpha=0.7, s=18)

    means = [summary[stage]['mean'] for stage in stages]
    stds = [summary[stage]['std'] for stage in stages]
    plt.errorbar(stages, means, yerr=stds, color='#dc2626', marker='o',
                 linestyle='-', linewidth=1.2, capsize=3, label='SDNV')
    plt.title(title.upper())
    plt.xlabel(xlabel.upper())
    plt.ylabel(ylabel.upper())
    plt.grid(True, alpha=0.25)
    plt.legend(loc='upper left', frameon=False)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Plot staged v4 metrics')
    parser.add_argument('--runs', default='results/stage_runs_v4.csv')
    parser.add_argument('--summary', default='results/stage_summary_v4.csv')
    parser.add_argument('--outdir', default='results/stage_metrics_v4')
    args = parser.parse_args()

    run_rows = load_rows(args.runs)
    summary_rows = load_rows(args.summary)
    if not run_rows or not summary_rows:
        print('Missing input CSVs. Run stage_analysis_v4.py first.')
        return

    os.makedirs(args.outdir, exist_ok=True)

    _plot_dual_metric(run_rows, summary_rows, 'udp_bw_mbps',
                      'Total UDP Throughput', 'Target UDP Share (%)', 'Throughput (Mbps)',
                      os.path.join(args.outdir, 'udp_throughput_vs_stage.png'))
    _plot_dual_metric(run_rows, summary_rows, 'throughput_mbps',
                      'Total TCP Throughput', 'Target UDP Share (%)', 'Throughput (Mbps)',
                      os.path.join(args.outdir, 'tcp_throughput_vs_stage.png'))
    _plot_dual_metric(run_rows, summary_rows, 'emergency_latency_avg_ms',
                      'Emergency UDP Latency', 'Target UDP Share (%)', 'Time (ms)',
                      os.path.join(args.outdir, 'udp_latency_vs_stage.png'))
    _plot_dual_metric(run_rows, summary_rows, 'udp_share_pct',
                      'Achieved UDP Share', 'Target UDP Share (%)', 'UDP Share (%)',
                      os.path.join(args.outdir, 'udp_share_vs_stage.png'))
    _plot_dual_metric(run_rows, summary_rows, 'emapt_50_ms',
                      'EMAPT-50', 'Target UDP Share (%)', 'Time (ms)',
                      os.path.join(args.outdir, 'emapt50_vs_stage.png'))
    _plot_dual_metric(run_rows, summary_rows, 'emapt_90_ms',
                      'EMAPT-90', 'Target UDP Share (%)', 'Time (ms)',
                      os.path.join(args.outdir, 'emapt90_vs_stage.png'))
    _plot_dual_metric(run_rows, summary_rows, 'emapt_100_ms',
                      'EMAPT-100', 'Target UDP Share (%)', 'Time (ms)',
                      os.path.join(args.outdir, 'emapt100_vs_stage.png'))
    _plot_sdnv_only(run_rows, summary_rows, 'policy_reaction_ms',
                    'Policy Reaction Time', 'Target UDP Share (%)', 'Time (ms)',
                    os.path.join(args.outdir, 'policy_reaction_time_sdnv_vs_stage.png'))

    print(f'Wrote plots to {args.outdir}')


if __name__ == '__main__':
    main()
