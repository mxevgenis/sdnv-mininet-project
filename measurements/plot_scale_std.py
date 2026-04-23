#!/usr/bin/env python3
"""Plot scale metrics with per-run scatter and mean/std error bars."""

import argparse
import csv
import os
import random

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load_runs(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def load_summary(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def to_float(val):
    try:
        return float(val)
    except Exception:
        return None


def collect_runs(rows, key):
    data = {}
    for r in rows:
        v = int(float(r['vehicles']))
        data.setdefault(v, {'baseline': [], 'sdnv': []})
        b = to_float(r.get(f"{key}_baseline"))
        s = to_float(r.get(f"{key}_sdnv"))
        if b is not None:
            data[v]['baseline'].append(b)
        if s is not None:
            data[v]['sdnv'].append(s)
    return data


def collect_summary(rows, key):
    data = {}
    for r in rows:
        v = int(float(r['vehicles']))
        data[v] = {
            'baseline_mean': to_float(r.get(f"{key}_baseline_mean")),
            'baseline_std': to_float(r.get(f"{key}_baseline_std")),
            'sdnv_mean': to_float(r.get(f"{key}_sdnv_mean")),
            'sdnv_std': to_float(r.get(f"{key}_sdnv_std")),
        }
    return data


def collect_sdnv_only_runs(rows, key):
    data = {}
    for r in rows:
        v = int(float(r['vehicles']))
        data.setdefault(v, [])
        val = to_float(r.get(f"{key}_sdnv"))
        if val is not None:
            data[v].append(val)
    return data


def collect_sdnv_only_summary(rows, key):
    data = {}
    for r in rows:
        v = int(float(r['vehicles']))
        data[v] = {
            'sdnv_mean': to_float(r.get(f"{key}_sdnv_mean")),
            'sdnv_std': to_float(r.get(f"{key}_sdnv_std")),
        }
    return data


def _fit_line(xs, ys):
    xs = [x for x, y in zip(xs, ys) if y is not None]
    ys = [y for y in ys if y is not None]
    if len(xs) < 2:
        return None
    n = len(xs)
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    den = sum((x - x_mean) ** 2 for x in xs)
    if den == 0:
        return None
    slope = num / den
    intercept = y_mean - slope * x_mean
    return slope, intercept


def plot_metric(runs_rows, summary_rows, key, title, y_label, out_path):
    runs = collect_runs(runs_rows, key)
    summary = collect_summary(summary_rows, key)

    vehicles = sorted(runs.keys())
    if not vehicles:
        return

    # Scatter points with slight x jitter for visibility
    random.seed(7)
    plt.figure(figsize=(6.4, 3.8))

    for v in vehicles:
        jitter = [(v + random.uniform(-0.08, 0.08)) for _ in runs[v]['baseline']]
        plt.scatter(jitter, runs[v]['baseline'], color='#2563eb', alpha=0.7, s=18)
        jitter = [(v + random.uniform(-0.08, 0.08)) for _ in runs[v]['sdnv']]
        plt.scatter(jitter, runs[v]['sdnv'], color='#dc2626', alpha=0.7, s=18)

    # Mean + std error bars
    b_means = [summary[v]['baseline_mean'] for v in vehicles]
    b_stds = [summary[v]['baseline_std'] for v in vehicles]
    s_means = [summary[v]['sdnv_mean'] for v in vehicles]
    s_stds = [summary[v]['sdnv_std'] for v in vehicles]

    plt.errorbar(vehicles, b_means, yerr=b_stds, color='#2563eb', marker='o',
                 linestyle='None', capsize=3, label='BASE')
    plt.errorbar(vehicles, s_means, yerr=s_stds, color='#dc2626', marker='o',
                 linestyle='None', capsize=3, label='SDN')

    # Trendlines based on mean values
    fit_b = _fit_line(vehicles, b_means)
    fit_s = _fit_line(vehicles, s_means)
    if fit_b:
        m, c = fit_b
        xs = [min(vehicles), max(vehicles)]
        ys = [m * x + c for x in xs]
        plt.plot(xs, ys, color='#93c5fd', linewidth=1.2)
    if fit_s:
        m, c = fit_s
        xs = [min(vehicles), max(vehicles)]
        ys = [m * x + c for x in xs]
        plt.plot(xs, ys, color='#fca5a5', linewidth=1.2)

    plt.title(title.upper())
    plt.xlabel('VEHICLES')
    plt.ylabel(y_label.upper())
    plt.grid(True, alpha=0.25)
    plt.legend(loc='upper center', ncol=2, frameon=False)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def plot_sdnv_only_metric(runs_rows, summary_rows, key, title, y_label, out_path):
    runs = collect_sdnv_only_runs(runs_rows, key)
    summary = collect_sdnv_only_summary(summary_rows, key)

    vehicles = sorted(runs.keys())
    if not vehicles:
        return

    random.seed(7)
    plt.figure(figsize=(6.4, 3.8))

    for v in vehicles:
        jitter = [(v + random.uniform(-0.08, 0.08)) for _ in runs[v]]
        plt.scatter(jitter, runs[v], color='#dc2626', alpha=0.7, s=18)

    means = [summary[v]['sdnv_mean'] for v in vehicles]
    stds = [summary[v]['sdnv_std'] for v in vehicles]

    plt.errorbar(vehicles, means, yerr=stds, color='#dc2626', marker='o',
                 linestyle='None', capsize=3, label='SDNV')

    fit = _fit_line(vehicles, means)
    if fit:
        m, c = fit
        xs = [min(vehicles), max(vehicles)]
        ys = [m * x + c for x in xs]
        plt.plot(xs, ys, color='#fca5a5', linewidth=1.2)

    plt.title(title.upper())
    plt.xlabel('VEHICLES')
    plt.ylabel(y_label.upper())
    plt.grid(True, alpha=0.25)
    plt.legend(loc='upper center', ncol=1, frameon=False)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Plot scale metrics with stddev')
    parser.add_argument('--runs', default='results/scale_runs_multi.csv')
    parser.add_argument('--summary', default='results/scale_summary_multi.csv')
    parser.add_argument('--outdir', default='results/scale_metrics_std')
    args = parser.parse_args()

    runs_rows = load_runs(args.runs)
    summary_rows = load_summary(args.summary)
    if not runs_rows or not summary_rows:
        print("Missing input CSVs. Run scale_analysis_multi.py first.")
        return

    os.makedirs(args.outdir, exist_ok=True)

    plot_metric(runs_rows, summary_rows, 'emergency_latency_avg_ms',
                'Emergency Latency', 'Time (ms)',
                os.path.join(args.outdir, 'emergency_latency_vs_vehicles.png'))

    plot_metric(runs_rows, summary_rows, 'background_latency_avg_ms',
                'Background Latency', 'Time (ms)',
                os.path.join(args.outdir, 'background_latency_vs_vehicles.png'))

    plot_metric(runs_rows, summary_rows, 'udp_bw_mbps',
                'Emergency UDP Throughput', 'Throughput (Mbps)',
                os.path.join(args.outdir, 'emergency_throughput_vs_vehicles.png'))

    plot_metric(runs_rows, summary_rows, 'throughput_mbps',
                'Background TCP Throughput', 'Throughput (Mbps)',
                os.path.join(args.outdir, 'background_throughput_vs_vehicles.png'))

    # Optional EMAPT plots if present in summary
    if any('emapt_50_ms_baseline_mean' in r for r in summary_rows):
        plot_metric(runs_rows, summary_rows, 'emapt_50_ms',
                    'EMAPT-50', 'Time (ms)',
                    os.path.join(args.outdir, 'emapt50_vs_vehicles.png'))
        plot_metric(runs_rows, summary_rows, 'emapt_90_ms',
                    'EMAPT-90', 'Time (ms)',
                    os.path.join(args.outdir, 'emapt90_vs_vehicles.png'))
        plot_metric(runs_rows, summary_rows, 'emapt_100_ms',
                    'EMAPT-100', 'Time (ms)',
                    os.path.join(args.outdir, 'emapt100_vs_vehicles.png'))

    if any('policy_reaction_ms_sdnv_mean' in r for r in summary_rows):
        plot_sdnv_only_metric(
            runs_rows,
            summary_rows,
            'policy_reaction_ms',
            'Policy Reaction Time',
            'Time (ms)',
            os.path.join(args.outdir, 'policy_reaction_time_sdnv_vs_vehicles.png'),
        )

    if any('priority_enforcement_ratio_sdnv_mean' in r for r in summary_rows):
        plot_sdnv_only_metric(
            runs_rows,
            summary_rows,
            'priority_enforcement_ratio',
            'Priority Enforcement Ratio',
            'Ratio',
            os.path.join(args.outdir, 'priority_enforcement_ratio_sdnv_vs_vehicles.png'),
        )

    print(f"Wrote plots to {args.outdir}")


if __name__ == '__main__':
    main()
