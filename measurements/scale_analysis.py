#!/usr/bin/env python3
"""Aggregate baseline vs SDNV metrics across vehicle counts."""

import argparse
import csv
import glob
import os
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from measurements.derived_metrics import load_policy_reaction, load_tag_metrics


def parse_emapt_latest(tag_prefix):
    """Return dict of EMAPT metrics (ms) from latest matching CSV."""
    pattern = os.path.join('results', f"emapt_{tag_prefix}_*.csv")
    matches = glob.glob(pattern)
    if not matches:
        return {}

    def ts(p):
        m = re.search(r'_(\d+)\.csv$', os.path.basename(p))
        return int(m.group(1)) if m else 0

    latest_path = max(matches, key=ts)
    values = {}
    with open(latest_path, 'r', encoding='utf-8', errors='ignore') as f:
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
        out['emapt_50_ms'] = values.get('emapt_50_ms')
        out['emapt_90_ms'] = values.get('emapt_90_ms')
        out['emapt_100_ms'] = values.get('emapt_100_ms')
        return out

    if 'emapt_50' in values:
        out['emapt_50_ms'] = values.get('emapt_50') * 1000.0
        out['emapt_90_ms'] = values.get('emapt_90') * 1000.0
        out['emapt_100_ms'] = values.get('emapt_100') * 1000.0
    return out


def main():
    parser = argparse.ArgumentParser(description='Summarize scale results')
    parser.add_argument('--counts', default='5,9,13,17,20',
                        help='Comma-separated vehicle counts')
    parser.add_argument('--baseline-prefix', default='baseline_scale_v')
    parser.add_argument('--sdnv-prefix', default='sdnv_scale_v')
    parser.add_argument('--emapt-baseline-prefix', default='emapt_baseline_scale_v')
    parser.add_argument('--emapt-sdnv-prefix', default='emapt_sdnv_scale_v')
    parser.add_argument('--out', default='results/scale_summary.csv')
    args = parser.parse_args()

    counts = [int(c.strip()) for c in args.counts.split(',') if c.strip()]
    rows = []

    for n in counts:
        base_tag = f"{args.baseline_prefix}{n}"
        sdnv_tag = f"{args.sdnv_prefix}{n}"

        base = load_tag_metrics('results', base_tag)
        sdnv = load_tag_metrics('results', sdnv_tag)

        base_bg = base.get('throughput_mbps')
        sdnv_bg = sdnv.get('throughput_mbps')
        base_udp = base.get('udp_bw_mbps')
        sdnv_udp = sdnv.get('udp_bw_mbps')

        suppression = None
        if base_bg and sdnv_bg:
            suppression = (base_bg - sdnv_bg) / base_bg

        ratio_base = None
        if base_udp and base_bg:
            ratio_base = base_udp / base_bg

        ratio_sdnv = None
        if sdnv_udp and sdnv_bg:
            ratio_sdnv = sdnv_udp / sdnv_bg

        policy_reaction = load_policy_reaction('logs', sdnv_tag)

        emapt_base = parse_emapt_latest(f"{args.emapt_baseline_prefix}{n}")
        emapt_sdnv = parse_emapt_latest(f"{args.emapt_sdnv_prefix}{n}")

        rows.append({
            'vehicles': n,
            'latency_avg_ms_baseline': base.get('latency_avg_ms'),
            'latency_avg_ms_sdnv': sdnv.get('latency_avg_ms'),
            'jitter_ms_baseline': base.get('jitter_ms'),
            'jitter_ms_sdnv': sdnv.get('jitter_ms'),
            'udp_bw_mbps_baseline': base_udp,
            'udp_bw_mbps_sdnv': sdnv_udp,
            'bg_tcp_mbps_baseline': base_bg,
            'bg_tcp_mbps_sdnv': sdnv_bg,
            'emapt_50_ms_baseline': emapt_base.get('emapt_50_ms'),
            'emapt_50_ms_sdnv': emapt_sdnv.get('emapt_50_ms'),
            'emapt_90_ms_baseline': emapt_base.get('emapt_90_ms'),
            'emapt_90_ms_sdnv': emapt_sdnv.get('emapt_90_ms'),
            'emapt_100_ms_baseline': emapt_base.get('emapt_100_ms'),
            'emapt_100_ms_sdnv': emapt_sdnv.get('emapt_100_ms'),
            'traffic_suppression_eff': suppression,
            'policy_reaction_s': policy_reaction,
            'priority_ratio_baseline': ratio_base,
            'priority_ratio_sdnv': ratio_sdnv,
        })

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {args.out}")


if __name__ == '__main__':
    main()
