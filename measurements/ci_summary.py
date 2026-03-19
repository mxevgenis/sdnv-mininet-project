#!/usr/bin/env python3
"""
Compute mean and 95% CI for each metric/scenario from summary.csv.
Outputs CSV and LaTeX table.
"""

import argparse
import csv
import math
import os
from collections import defaultdict


def mean(vals):
    return sum(vals) / len(vals) if vals else float('nan')


def std(vals):
    if len(vals) < 2:
        return 0.0
    m = mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def main():
    parser = argparse.ArgumentParser(description='Compute CI summary from results/summary.csv')
    parser.add_argument('--summary', default='results/summary.csv')
    parser.add_argument('--out-csv', default='results/summary_ci.csv')
    parser.add_argument('--out-tex', default='results/summary_ci.tex')
    args = parser.parse_args()

    if not os.path.exists(args.summary):
        print(f"summary file not found: {args.summary}")
        return

    data = defaultdict(list)
    units = {}

    with open(args.summary, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['scenario'], row['metric'])
            data[key].append(float(row['value']))
            units[row['metric']] = row['unit']

    rows = []
    for (scenario, metric), vals in sorted(data.items()):
        n = len(vals)
        m = mean(vals)
        s = std(vals)
        ci = 1.96 * s / math.sqrt(n) if n > 1 else 0.0
        rows.append({
            'scenario': scenario,
            'metric': metric,
            'unit': units.get(metric, ''),
            'n': n,
            'mean': m,
            'std': s,
            'ci95': ci,
        })

    with open(args.out_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['scenario', 'metric', 'unit', 'n', 'mean', 'std', 'ci95'])
        writer.writeheader()
        writer.writerows(rows)

    # LaTeX table
    with open(args.out_tex, 'w') as f:
        f.write("\\begin{tabular}{llrrrr}\n")
        f.write("Scenario & Metric & N & Mean & Std & 95\\% CI\\\\\n")
        f.write("\\hline\n")
        for r in rows:
            f.write(f"{r['scenario']} & {r['metric']} ({r['unit']}) & {r['n']} & {r['mean']:.4f} & {r['std']:.4f} & {r['ci95']:.4f}\\\\\n")
        f.write("\\end{tabular}\n")

    print(f"Wrote {args.out_csv} and {args.out_tex}")


if __name__ == '__main__':
    main()
