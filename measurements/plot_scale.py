#!/usr/bin/env python3
"""Plot scale results with vehicle count on the x-axis."""

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


def plot_metrics(rows, out_path):
    vehicles = [int(r['vehicles']) for r in rows]

    def vals(key):
        return [to_float(r.get(key)) for r in rows]

    fig, axes = plt.subplots(2, 2, figsize=(9, 6))
    axes = axes.ravel()

    series = [
        ('latency_avg_ms', 'Latency avg (ms)'),
        ('jitter_ms', 'Jitter (ms)'),
        ('udp_bw_mbps', 'Emergency UDP (Mbps)'),
        ('bg_tcp_mbps', 'Background TCP (Mbps)'),
    ]

    for ax, (base_key, label) in zip(axes, series):
        b = vals(f"{base_key}_baseline")
        s = vals(f"{base_key}_sdnv")
        ax.plot(vehicles, b, marker='o', label='Baseline')
        ax.plot(vehicles, s, marker='o', label='SDNV')
        ax.set_title(label)
        ax.set_xlabel('Vehicles')
        ax.grid(True, alpha=0.3)
        ax.legend()

    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def plot_emapt(rows, out_path):
    vehicles = [int(r['vehicles']) for r in rows]

    def vals(key):
        return [to_float(r.get(key)) for r in rows]

    plt.figure(figsize=(8, 4))
    for p in ('50', '90', '100'):
        plt.plot(vehicles, vals(f"emapt_{p}_ms_baseline"), marker='o',
                 label=f'Baseline EMAPT-{p}')
        plt.plot(vehicles, vals(f"emapt_{p}_ms_sdnv"), marker='o',
                 label=f'SDNV EMAPT-{p}')

    plt.xlabel('Vehicles')
    plt.ylabel('Time (ms)')
    plt.title('EMAPT vs Vehicles')
    plt.grid(True, alpha=0.3)
    plt.legend(ncol=2, fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def plot_derived(rows, out_path):
    vehicles = [int(r['vehicles']) for r in rows]

    def vals(key):
        return [to_float(r.get(key)) for r in rows]

    policy_ms = []
    for v in vals('policy_reaction_s'):
        policy_ms.append(v * 1000.0 if v is not None else None)

    fig, axes = plt.subplots(1, 3, figsize=(11, 3.5))

    axes[0].plot(vehicles, vals('traffic_suppression_eff'), marker='o', color='#f28e2b')
    axes[0].set_title('Traffic Suppression')
    axes[0].set_xlabel('Vehicles')
    axes[0].set_ylabel('Ratio')
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(vehicles, policy_ms, marker='o', color='#59a14f')
    axes[1].set_title('Policy Reaction Time')
    axes[1].set_xlabel('Vehicles')
    axes[1].set_ylabel('Time (ms)')
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(vehicles, vals('priority_ratio_baseline'), marker='o', label='Baseline')
    axes[2].plot(vehicles, vals('priority_ratio_sdnv'), marker='o', label='SDNV')
    axes[2].set_title('Priority Enforcement Ratio')
    axes[2].set_xlabel('Vehicles')
    axes[2].set_ylabel('Ratio')
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Plot scale study results')
    parser.add_argument('--summary', default='results/scale_summary.csv')
    parser.add_argument('--outdir', default='results')
    args = parser.parse_args()

    rows = load_rows(args.summary)
    if not rows:
        print(f"No data in {args.summary}")
        return

    os.makedirs(args.outdir, exist_ok=True)
    plot_metrics(rows, os.path.join(args.outdir, 'scale_metrics.png'))
    plot_emapt(rows, os.path.join(args.outdir, 'scale_emapt.png'))
    plot_derived(rows, os.path.join(args.outdir, 'scale_derived.png'))

    print(f"Wrote plots to {args.outdir}")


if __name__ == '__main__':
    main()
