#!/usr/bin/env python3
"""Aggregate metrics across multiple baseline/SDNV runs."""

import argparse
import glob
import os
import re
import statistics
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from measurements.derived_metrics import load_policy_reaction, load_tag_metrics


def latest_emapt_csv(tag):
    pattern = os.path.join('results', f"emapt_{tag}_*.csv")
    matches = glob.glob(pattern)
    if not matches:
        return None

    def ts(p):
        m = re.search(r'_(\d+)\.csv$', os.path.basename(p))
        return int(m.group(1)) if m else 0

    return max(matches, key=ts)


def parse_emapt(path):
    out = {}
    if not path:
        return out
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line.startswith('coverage_curve_'):
                break
            if '=' not in line:
                continue
            key, val = line.split('=', 1)
            try:
                out[key.strip()] = float(val.strip())
            except ValueError:
                continue
    return out


def mean(vals):
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else None


def fmt(val, unit=''):
    if val is None:
        return 'n/a'
    if unit == 'percent':
        return f"{val:.2f}%"
    if unit == 'ms' or unit == 's' or unit == 'mbps':
        return f"{val:.3f}"
    return f"{val:.4f}"


def main():
    parser = argparse.ArgumentParser(description='Aggregate multiple run tags')
    parser.add_argument('--runs', type=int, default=5)
    parser.add_argument('--baseline-prefix', default='baseline_5g_be1540_r')
    parser.add_argument('--sdnv-prefix', default='sdnv_5g_be1540_r')
    parser.add_argument('--emapt-baseline-prefix', default='emapt_baseline_5g_be1540_r')
    parser.add_argument('--emapt-sdnv-prefix', default='emapt_sdnv_5g_be1540_r')
    parser.add_argument('--out', default='results/summary_5g_be1540_5x.txt')
    parser.add_argument('--out-csv', default='results/summary_5g_be1540_5x.csv')
    args = parser.parse_args()

    baseline_rows = []
    sdnv_rows = []
    derived_rows = []

    for i in range(1, args.runs + 1):
        b_tag = f"{args.baseline_prefix}{i}"
        s_tag = f"{args.sdnv_prefix}{i}"

        b = load_tag_metrics('results', b_tag)
        s = load_tag_metrics('results', s_tag)

        # EMAPT
        b_emapt = parse_emapt(latest_emapt_csv(f"{args.emapt_baseline_prefix}{i}"))
        s_emapt = parse_emapt(latest_emapt_csv(f"{args.emapt_sdnv_prefix}{i}"))

        # Derived metrics
        base_bg = b.get('throughput_mbps')
        sdnv_bg = s.get('throughput_mbps')
        base_udp = b.get('udp_bw_mbps')
        sdnv_udp = s.get('udp_bw_mbps')
        suppression = None
        if base_bg and sdnv_bg:
            suppression = (base_bg - sdnv_bg) / base_bg
        pr_base = None
        if base_udp and base_bg:
            pr_base = base_udp / base_bg
        pr_sdnv = None
        if sdnv_udp and sdnv_bg:
            pr_sdnv = sdnv_udp / sdnv_bg
        prt = load_policy_reaction('logs', s_tag)

        baseline_rows.append({
            **b,
            'emapt_50_ms': b_emapt.get('emapt_50_ms') or (b_emapt.get('emapt_50') * 1000 if b_emapt.get('emapt_50') else None),
            'emapt_90_ms': b_emapt.get('emapt_90_ms') or (b_emapt.get('emapt_90') * 1000 if b_emapt.get('emapt_90') else None),
            'emapt_100_ms': b_emapt.get('emapt_100_ms') or (b_emapt.get('emapt_100') * 1000 if b_emapt.get('emapt_100') else None),
        })
        sdnv_rows.append({
            **s,
            'emapt_50_ms': s_emapt.get('emapt_50_ms') or (s_emapt.get('emapt_50') * 1000 if s_emapt.get('emapt_50') else None),
            'emapt_90_ms': s_emapt.get('emapt_90_ms') or (s_emapt.get('emapt_90') * 1000 if s_emapt.get('emapt_90') else None),
            'emapt_100_ms': s_emapt.get('emapt_100_ms') or (s_emapt.get('emapt_100') * 1000 if s_emapt.get('emapt_100') else None),
        })
        derived_rows.append({
            'suppression': suppression,
            'priority_ratio_baseline': pr_base,
            'priority_ratio_sdnv': pr_sdnv,
            'policy_reaction_s': prt,
        })

    metrics = [
        ('latency_avg_ms', 'ms'),
        ('latency_mdev_ms', 'ms'),
        ('jitter_ms', 'ms'),
        ('udp_bw_mbps', 'mbps'),
        ('throughput_mbps', 'mbps'),
        ('emapt_50_ms', 'ms'),
        ('emapt_90_ms', 'ms'),
        ('emapt_100_ms', 'ms'),
    ]

    summary = {
        'baseline': {},
        'sdnv': {},
        'derived': {},
    }

    for key, unit in metrics:
        summary['baseline'][key] = mean([r.get(key) for r in baseline_rows])
        summary['sdnv'][key] = mean([r.get(key) for r in sdnv_rows])

    summary['derived']['traffic_suppression_eff'] = mean([r.get('suppression') for r in derived_rows])
    summary['derived']['priority_ratio_baseline'] = mean([r.get('priority_ratio_baseline') for r in derived_rows])
    summary['derived']['priority_ratio_sdnv'] = mean([r.get('priority_ratio_sdnv') for r in derived_rows])
    summary['derived']['policy_reaction_s'] = mean([r.get('policy_reaction_s') for r in derived_rows])

    # write text summary
    with open(args.out, 'w') as f:
        f.write('Baseline (mean over runs)\n')
        for key, unit in metrics:
            f.write(f"{key}: {fmt(summary['baseline'][key])} {unit}\n")
        f.write('\nSDNV (mean over runs)\n')
        for key, unit in metrics:
            f.write(f"{key}: {fmt(summary['sdnv'][key])} {unit}\n")
        f.write('\nDerived (mean over runs)\n')
        f.write(f"traffic_suppression_eff: {fmt(summary['derived']['traffic_suppression_eff'])}\n")
        f.write(f"priority_ratio_baseline: {fmt(summary['derived']['priority_ratio_baseline'])}\n")
        f.write(f"priority_ratio_sdnv: {fmt(summary['derived']['priority_ratio_sdnv'])}\n")
        prt_ms = summary['derived']['policy_reaction_s']
        if prt_ms is not None:
            prt_ms = prt_ms * 1000.0
        f.write(f"policy_reaction_ms: {fmt(prt_ms)} ms\n")

    # write csv summary
    with open(args.out_csv, 'w') as f:
        f.write('scenario,metric,mean,unit\n')
        for key, unit in metrics:
            f.write(f"baseline,{key},{summary['baseline'][key]},{unit}\n")
        for key, unit in metrics:
            f.write(f"sdnv,{key},{summary['sdnv'][key]},{unit}\n")
        f.write(f"derived,traffic_suppression_eff,{summary['derived']['traffic_suppression_eff']},ratio\n")
        f.write(f"derived,priority_ratio_baseline,{summary['derived']['priority_ratio_baseline']},ratio\n")
        f.write(f"derived,priority_ratio_sdnv,{summary['derived']['priority_ratio_sdnv']},ratio\n")
        f.write(f"derived,policy_reaction_s,{summary['derived']['policy_reaction_s']},s\n")

    print(f"Wrote {args.out} and {args.out_csv}")


if __name__ == '__main__':
    main()
