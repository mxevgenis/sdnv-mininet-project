#!/usr/bin/env python3
"""
Compute mean and 95% CI for each metric/scenario using latest N logs.
Outputs CSV and IEEE-style LaTeX table.
"""

import argparse
import csv
import glob
import math
import os
import re
from collections import defaultdict

PING_RE = re.compile(r"= ([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+)")
IPERF_BW_RE = re.compile(r"([0-9.]+)\s+([KMG]bits/sec)")
IPERF_JITTER_RE = re.compile(r"([0-9.]+)\s+ms")


def mean(vals):
    return sum(vals) / len(vals) if vals else float('nan')


def std(vals):
    if len(vals) < 2:
        return 0.0
    m = mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def to_mbps(value, unit):
    value = float(value)
    if unit == 'Kbits/sec':
        return value / 1000.0
    if unit == 'Mbits/sec':
        return value
    if unit == 'Gbits/sec':
        return value * 1000.0
    return value


def parse_latency(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if 'min/avg/max' in line:
                m = PING_RE.search(line)
                if m:
                    return float(m.group(2)), float(m.group(4))
    return None


def parse_iperf_tcp(path):
    last = None
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if 'bits/sec' in line and 'sec' in line:
                last = line
    if not last:
        return None
    m = IPERF_BW_RE.search(last)
    if not m:
        return None
    return to_mbps(m.group(1), m.group(2))


def parse_iperf_udp(path):
    last = None
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if 'bits/sec' in line and 'sec' in line:
                last = line
    if not last:
        return None
    bw = None
    jitter = None
    m_bw = IPERF_BW_RE.search(last)
    m_j = IPERF_JITTER_RE.search(last)
    if m_bw:
        bw = to_mbps(m_bw.group(1), m_bw.group(2))
    if m_j:
        jitter = float(m_j.group(1))
    return bw, jitter


def latest_n(paths, n):
    def ts(p):
        m = re.search(r'_(\d+)\.log$', os.path.basename(p))
        return int(m.group(1)) if m else 0
    return sorted(paths, key=ts, reverse=True)[:n]


def collect_latest_metrics(results_dir, scenario, n):
    scenario_dir = os.path.join(results_dir, scenario)
    rows = []

    latency_paths = latest_n(glob.glob(os.path.join(scenario_dir, 'latency_*.log')), n)
    for path in latency_paths:
        res = parse_latency(path)
        if res:
            avg_ms, mdev_ms = res
            rows.append(['latency_avg_ms', avg_ms, 'ms', path])
            rows.append(['latency_mdev_ms', mdev_ms, 'ms', path])

    throughput_paths = latest_n(glob.glob(os.path.join(scenario_dir, 'throughput_*.log')), n)
    for path in throughput_paths:
        res = parse_iperf_tcp(path)
        if res is not None:
            rows.append(['throughput_mbps', res, 'Mbps', path])

    jitter_paths = latest_n(glob.glob(os.path.join(scenario_dir, 'jitter_*.log')), n)
    for path in jitter_paths:
        res = parse_iperf_udp(path)
        if res:
            bw, jitter = res
            if bw is not None:
                rows.append(['udp_bw_mbps', bw, 'Mbps', path])
            if jitter is not None:
                rows.append(['jitter_ms', jitter, 'ms', path])

    return rows


def main():
    parser = argparse.ArgumentParser(description='Compute CI summary from latest N logs')
    parser.add_argument('--results', default='results')
    parser.add_argument('--n', type=int, default=5)
    parser.add_argument('--out-csv', default='results/summary_ci_latest5.csv')
    parser.add_argument('--out-tex', default='results/summary_ci_latest5.tex')
    args = parser.parse_args()

    all_rows = []
    for scenario in ('baseline', 'sdnv'):
        rows = collect_latest_metrics(args.results, scenario, args.n)
        for row in rows:
            all_rows.append([scenario] + row)

    if not all_rows:
        print('No results found.')
        return

    # aggregate
    data = defaultdict(list)
    units = {}
    for scenario, metric, value, unit, _path in all_rows:
        data[(scenario, metric)].append(float(value))
        units[metric] = unit

    out_rows = []
    for (scenario, metric), vals in sorted(data.items()):
        n = len(vals)
        m = mean(vals)
        s = std(vals)
        ci = 1.96 * s / math.sqrt(n) if n > 1 else 0.0
        out_rows.append({
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
        writer.writerows(out_rows)

    # IEEE-style LaTeX table
    with open(args.out_tex, 'w') as f:
        f.write('\\begin{table}[t]\n')
        f.write(f'\\\\caption{{Emergency use case: mean and 95\\\\% CI over latest {args.n} runs}}\\n')
        f.write('\\label{tab:emergency-ci}\n')
        f.write('\\centering\n')
        f.write('\\begin{tabular}{llrrrr}\n')
        f.write('\\hline\n')
        f.write('Scenario & Metric (unit) & N & Mean & Std & 95\\% CI\\\\\n')
        f.write('\\hline\n')
        for r in out_rows:
            f.write(f"{r['scenario']} & {r['metric']} ({r['unit']}) & {r['n']} & {r['mean']:.4f} & {r['std']:.4f} & {r['ci95']:.4f}\\\\\n")
        f.write('\\hline\n')
        f.write('\\end{tabular}\n')
        f.write('\\end{table}\n')

    print(f"Wrote {args.out_csv} and {args.out_tex}")


if __name__ == '__main__':
    main()
