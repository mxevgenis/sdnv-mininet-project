#!/usr/bin/env python3
"""Aggregate multi-run scale results with mean and stddev."""

import argparse
import csv
import glob
import os
import re
import statistics
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from measurements.derived_metrics import load_tag_metrics


METRICS = [
    ('latency_avg_ms', 'ms'),
    ('jitter_ms', 'ms'),
    ('udp_bw_mbps', 'mbps'),
    ('throughput_mbps', 'mbps'),
]

EMAPT_KEYS = ['emapt_50_ms', 'emapt_90_ms', 'emapt_100_ms']


def latest_emapt_csv(tag_prefix):
    pattern = os.path.join('results', f"emapt_{tag_prefix}_*.csv")
    matches = glob.glob(pattern)
    if not matches:
        return None

    def ts(p):
        m = re.search(r'_(\\d+)\\.csv$', os.path.basename(p))
        return int(m.group(1)) if m else 0

    return max(matches, key=ts)


def parse_emapt(path):
    values = {}
    if not path:
        return values
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('coverage_curve_'):
                break
            if '=' not in line:
                continue
            key, val = line.split('=', 1)
            try:
                values[key.strip()] = float(val.strip())
            except ValueError:
                continue

    out = {}
    if 'emapt_50_ms' in values:
        for k in EMAPT_KEYS:
            out[k] = values.get(k)
        return out

    if 'emapt_50' in values:
        out['emapt_50_ms'] = values.get('emapt_50') * 1000.0
        out['emapt_90_ms'] = values.get('emapt_90') * 1000.0
        out['emapt_100_ms'] = values.get('emapt_100') * 1000.0
    return out


def mean_std(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None, None
    if len(vals) == 1:
        return vals[0], 0.0
    return statistics.mean(vals), statistics.stdev(vals)


def main():
    parser = argparse.ArgumentParser(description='Summarize multi-run scale results')
    parser.add_argument('--counts', default='5,10,15,20',
                        help='Comma-separated vehicle counts')
    parser.add_argument('--runs', type=int, default=5,
                        help='Number of runs per count')
    parser.add_argument('--baseline-prefix', default='baseline_scale_v',
                        help='Baseline tag prefix (expects suffix: <count>_r<run>)')
    parser.add_argument('--sdnv-prefix', default='sdnv_scale_v',
                        help='SDNV tag prefix (expects suffix: <count>_r<run>)')
    parser.add_argument('--emapt-baseline-prefix', default='emapt_baseline_scale_v',
                        help='EMAPT baseline tag prefix (expects suffix: <count>_r<run>)')
    parser.add_argument('--emapt-sdnv-prefix', default='emapt_sdnv_scale_v',
                        help='EMAPT SDNV tag prefix (expects suffix: <count>_r<run>)')
    parser.add_argument('--out-runs', default='results/scale_runs_multi.csv',
                        help='Per-run metrics output CSV')
    parser.add_argument('--out-summary', default='results/scale_summary_multi.csv',
                        help='Mean/std summary output CSV')
    args = parser.parse_args()

    counts = [int(c.strip()) for c in args.counts.split(',') if c.strip()]
    run_rows = []
    summary_rows = []

    for n in counts:
        baseline_runs = {k: [] for k, _ in METRICS}
        sdnv_runs = {k: [] for k, _ in METRICS}
        baseline_emapt = {k: [] for k in EMAPT_KEYS}
        sdnv_emapt = {k: [] for k in EMAPT_KEYS}

        for r in range(1, args.runs + 1):
            b_tag = f"{args.baseline_prefix}{n}_r{r}"
            s_tag = f"{args.sdnv_prefix}{n}_r{r}"

            b = load_tag_metrics('results', b_tag)
            s = load_tag_metrics('results', s_tag)

            row = {
                'vehicles': n,
                'run': r,
            }

            for key, _unit in METRICS:
                b_val = b.get(key)
                s_val = s.get(key)
                row[f"{key}_baseline"] = b_val
                row[f"{key}_sdnv"] = s_val
                baseline_runs[key].append(b_val)
                sdnv_runs[key].append(s_val)

            # EMAPT per-run (optional)
            b_emapt = parse_emapt(
                latest_emapt_csv(f"{args.emapt_baseline_prefix}{n}_r{r}")
            )
            s_emapt = parse_emapt(
                latest_emapt_csv(f"{args.emapt_sdnv_prefix}{n}_r{r}")
            )
            for k in EMAPT_KEYS:
                b_val = b_emapt.get(k)
                s_val = s_emapt.get(k)
                row[f"{k}_baseline"] = b_val
                row[f"{k}_sdnv"] = s_val
                baseline_emapt[k].append(b_val)
                sdnv_emapt[k].append(s_val)

            run_rows.append(row)

        summary = {'vehicles': n}
        for key, unit in METRICS:
            b_mean, b_std = mean_std(baseline_runs[key])
            s_mean, s_std = mean_std(sdnv_runs[key])
            summary[f"{key}_baseline_mean"] = b_mean
            summary[f"{key}_baseline_std"] = b_std
            summary[f"{key}_sdnv_mean"] = s_mean
            summary[f"{key}_sdnv_std"] = s_std
            summary[f"{key}_unit"] = unit

        for k in EMAPT_KEYS:
            b_mean, b_std = mean_std(baseline_emapt[k])
            s_mean, s_std = mean_std(sdnv_emapt[k])
            summary[f"{k}_baseline_mean"] = b_mean
            summary[f"{k}_baseline_std"] = b_std
            summary[f"{k}_sdnv_mean"] = s_mean
            summary[f"{k}_sdnv_std"] = s_std
        summary_rows.append(summary)

    os.makedirs(os.path.dirname(args.out_runs) or '.', exist_ok=True)
    os.makedirs(os.path.dirname(args.out_summary) or '.', exist_ok=True)

    if run_rows:
        with open(args.out_runs, 'w', newline='') as f:
            fieldnames = list(run_rows[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(run_rows)

    if summary_rows:
        with open(args.out_summary, 'w', newline='') as f:
            fieldnames = list(summary_rows[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_rows)

    print(f"Wrote {args.out_runs} and {args.out_summary}")


if __name__ == '__main__':
    main()
