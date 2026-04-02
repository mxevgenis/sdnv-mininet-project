#!/usr/bin/env python3
"""Generate IEEE-style LaTeX table with EMAPT coverage points."""

import argparse
import glob
import os
import re


def latest_emapt_csv(prefix):
    pattern = os.path.join('results', f"emapt_{prefix}_*.csv")
    matches = glob.glob(pattern)
    if not matches:
        return None

    def ts(p):
        m = re.search(r'_(\d+)\.csv$', os.path.basename(p))
        return int(m.group(1)) if m else 0

    return max(matches, key=ts)


def parse_coverage(path):
    times = []
    covs = []
    if not path:
        return times, covs
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        header = None
        for line in f:
            line = line.strip()
            if line.startswith('coverage_curve_'):
                header = line
                break
        if header is None:
            return times, covs
        unit = 'ms'
        if header.startswith('coverage_curve_seconds'):
            unit = 's'
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) < 2:
                continue
            try:
                t = float(parts[0])
                c = float(parts[1])
            except ValueError:
                continue
            if unit == 's':
                t *= 1000.0
            times.append(t)
            covs.append(c)
    return times, covs


def main():
    parser = argparse.ArgumentParser(description='Generate EMAPT coverage point table')
    parser.add_argument('--counts', default='5,9,13,17,20')
    parser.add_argument('--baseline-prefix', default='emapt_baseline_scale_v')
    parser.add_argument('--sdnv-prefix', default='emapt_sdnv_scale_v')
    parser.add_argument('--out', default='results/ieee_table_emapt_scale_points.tex')
    args = parser.parse_args()

    counts = [int(c.strip()) for c in args.counts.split(',') if c.strip()]

    rows = []
    for n in counts:
        b_path = latest_emapt_csv(f"{args.baseline_prefix}{n}")
        s_path = latest_emapt_csv(f"{args.sdnv_prefix}{n}")
        b_times, b_covs = parse_coverage(b_path)
        s_times, s_covs = parse_coverage(s_path)

        for t, c in zip(b_times, b_covs):
            rows.append(('Baseline', n, t, c))
        for t, c in zip(s_times, s_covs):
            rows.append(('SDNV', n, t, c))

    with open(args.out, 'w') as f:
        f.write('\\begin{table*}[t]\n')
        f.write('\\caption{EMAPT coverage curve points (ms) for scalability sweep}\n')
        f.write('\\label{tab:emapt-scale-points}\n')
        f.write('\\centering\n')
        f.write('\\begin{tabular}{lrrr}\n')
        f.write('\\hline\n')
        f.write('Scenario & Vehicles & Time (ms) & Coverage\\\\\n')
        f.write('\\hline\n')
        for scenario, vehicles, t, c in rows:
            f.write(f"{scenario} & {vehicles} & {t:.3f} & {c:.3f}\\\\\n")
        f.write('\\hline\n')
        f.write('\\end{tabular}\n')
        f.write('\\end{table*}\n')

    print(f"Wrote {args.out}")


if __name__ == '__main__':
    main()
