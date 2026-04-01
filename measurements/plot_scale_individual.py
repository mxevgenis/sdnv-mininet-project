#!/usr/bin/env python3
"""Create separate PNG plots for each metric vs vehicle count."""

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


def plot_metric(rows, key_base, label, out_path, y_label):
    vehicles = [int(r['vehicles']) for r in rows]
    b = [to_float(r.get(f"{key_base}_baseline")) for r in rows]
    s = [to_float(r.get(f"{key_base}_sdnv")) for r in rows]

    plt.figure(figsize=(5.5, 3.2))
    plt.plot(vehicles, b, marker='o', label='Baseline')
    plt.plot(vehicles, s, marker='o', label='SDNV')
    plt.title(label)
    plt.xlabel('Vehicles')
    plt.ylabel(y_label)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Plot per-metric scale PNGs')
    parser.add_argument('--summary', default='results/scale_summary.csv')
    parser.add_argument('--outdir', default='results/scale_metrics_individual')
    args = parser.parse_args()

    rows = load_rows(args.summary)
    if not rows:
        print(f"No data in {args.summary}")
        return

    os.makedirs(args.outdir, exist_ok=True)

    metrics = [
        ('latency_avg_ms', 'Latency avg', 'Time (ms)', 'latency_avg_ms.png'),
        ('jitter_ms', 'Jitter', 'Time (ms)', 'jitter_ms.png'),
        ('udp_bw_mbps', 'Emergency UDP throughput', 'Mbps', 'udp_bw_mbps.png'),
        ('bg_tcp_mbps', 'Background TCP throughput', 'Mbps', 'bg_tcp_mbps.png'),
        ('emapt_50_ms', 'EMAPT-50', 'Time (ms)', 'emapt_50_ms.png'),
        ('emapt_90_ms', 'EMAPT-90', 'Time (ms)', 'emapt_90_ms.png'),
        ('emapt_100_ms', 'EMAPT-100', 'Time (ms)', 'emapt_100_ms.png'),
        ('traffic_suppression_eff', 'Traffic suppression efficiency', 'Ratio', 'traffic_suppression_eff.png'),
        ('policy_reaction_s', 'Policy reaction time', 'Time (ms)', 'policy_reaction_ms.png'),
        ('priority_ratio', 'Priority enforcement ratio', 'Ratio', 'priority_ratio.png'),
    ]

    for key_base, label, y_label, filename in metrics:
        out_path = os.path.join(args.outdir, filename)
        if key_base == 'policy_reaction_s':
            vehicles = [int(r['vehicles']) for r in rows]
            b = [None for _ in rows]
            s = []
            for r in rows:
                val = to_float(r.get('policy_reaction_s'))
                s.append(val * 1000.0 if val is not None else None)
            plt.figure(figsize=(5.5, 3.2))
            plt.plot(vehicles, s, marker='o', label='SDNV')
            plt.title(label)
            plt.xlabel('Vehicles')
            plt.ylabel(y_label)
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.tight_layout()
            plt.savefig(out_path)
            plt.close()
            continue

        if key_base == 'priority_ratio':
            vehicles = [int(r['vehicles']) for r in rows]
            b = [to_float(r.get('priority_ratio_baseline')) for r in rows]
            s = [to_float(r.get('priority_ratio_sdnv')) for r in rows]
            plt.figure(figsize=(5.5, 3.2))
            plt.plot(vehicles, b, marker='o', label='Baseline')
            plt.plot(vehicles, s, marker='o', label='SDNV')
            plt.title(label)
            plt.xlabel('Vehicles')
            plt.ylabel(y_label)
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.tight_layout()
            plt.savefig(out_path)
            plt.close()
            continue

        if key_base in ('traffic_suppression_eff',):
            vehicles = [int(r['vehicles']) for r in rows]
            s = [to_float(r.get('traffic_suppression_eff')) for r in rows]
            plt.figure(figsize=(5.5, 3.2))
            plt.plot(vehicles, s, marker='o', label='SDNV')
            plt.title(label)
            plt.xlabel('Vehicles')
            plt.ylabel(y_label)
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.tight_layout()
            plt.savefig(out_path)
            plt.close()
            continue

        plot_metric(rows, key_base, label, out_path, y_label)

    print(f"Wrote per-metric plots to {args.outdir}")


if __name__ == '__main__':
    main()
