#!/usr/bin/env python3
"""
Create simple plots from results/summary.csv.
"""

import argparse
import csv
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description='Plot SDNV summary results')
    parser.add_argument('--summary', default='results/summary.csv')
    parser.add_argument('--outdir', default='results/plots')
    args = parser.parse_args()

    if not os.path.exists(args.summary):
        print(f"summary file not found: {args.summary}")
        return

    os.makedirs(args.outdir, exist_ok=True)

    data = {}
    with open(args.summary, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['metric'], row['unit'])
            data.setdefault(key, {})
            data[key].setdefault(row['scenario'], []).append(float(row['value']))

    for (metric, unit), scenarios in data.items():
        labels = []
        values = []
        for scenario, vals in scenarios.items():
            labels.append(scenario)
            values.append(sum(vals) / len(vals))

        plt.figure(figsize=(5, 3))
        plt.bar(labels, values, color=['#4c78a8', '#f28e2b'][:len(labels)])
        plt.title(metric)
        plt.ylabel(unit)
        plt.tight_layout()
        out_path = os.path.join(args.outdir, f"{metric}.png")
        plt.savefig(out_path)
        plt.close()

    print(f"Wrote plots to {args.outdir}")


if __name__ == '__main__':
    main()
