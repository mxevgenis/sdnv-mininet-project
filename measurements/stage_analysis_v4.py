#!/usr/bin/env python3
"""Aggregate staged v4 experiment results with mean/stddev."""

import argparse
import csv
import glob
import os
import re
import statistics
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from measurements.derived_metrics import load_policy_reaction

LAT_RE = re.compile(r"= ([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+)")
BW_RE = re.compile(r"([0-9.]+)\s+([KMG]bits/sec)")

METRICS = [
    ('emergency_latency_avg_ms', 'ms'),
    ('primary_udp_bw_mbps', 'mbps'),
    ('helper_udp_bw_mbps', 'mbps'),
    ('udp_bw_mbps', 'mbps'),
    ('throughput_mbps', 'mbps'),
    ('udp_share_pct', 'percent'),
]

EMAPT_KEYS = ['emapt_50_ms', 'emapt_90_ms', 'emapt_100_ms']


def _to_mbps(value, unit):
    value = float(value)
    if unit == 'Kbits/sec':
        return value / 1000.0
    if unit == 'Mbits/sec':
        return value
    if unit == 'Gbits/sec':
        return value * 1000.0
    return value


def _latest(paths):
    def ts(path):
        m = re.search(r'_(\d+)\.(?:log|csv)$', os.path.basename(path))
        return int(m.group(1)) if m else 0
    return max(paths, key=ts) if paths else None


def _parse_latency(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if 'min/avg/max' not in line:
                continue
            m = LAT_RE.search(line)
            if m:
                return float(m.group(2))
    return None


def _parse_iperf_bw(path):
    last = None
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if 'bits/sec' in line and 'sec' in line:
                last = line
    if not last:
        return None
    m = BW_RE.search(last)
    if not m:
        return None
    return _to_mbps(m.group(1), m.group(2))


def _parse_stage_meta(path):
    out = {}
    if not path:
        return out
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '=' not in line:
                continue
            key, value = line.strip().split('=', 1)
            out[key] = value
    return out


def latest_emapt_csv(tag_prefix):
    pattern = os.path.join('results', f'emapt_{tag_prefix}_*.csv')
    matches = glob.glob(pattern)
    return _latest(matches)


def parse_emapt(path):
    values = {}
    if not path:
        return values
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('coverage_curve_'):
                if line.startswith('coverage_curve_'):
                    break
                continue
            if '=' not in line:
                continue
            key, val = line.split('=', 1)
            try:
                values[key.strip()] = float(val.strip())
            except ValueError:
                continue
    out = {}
    if 'emapt_50_ms' in values:
        for key in EMAPT_KEYS:
            out[key] = values.get(key)
    return out


def load_tag_metrics(results_dir, tag):
    base = os.path.join(results_dir, tag)
    if not os.path.isdir(base):
        raise FileNotFoundError(f'results directory not found: {base}')

    emergency_latency = _latest(glob.glob(os.path.join(base, 'emergency_latency_*.log')))
    emergency_udp = _latest(glob.glob(os.path.join(base, 'emergency_udp_*.log')))
    helper_udp_logs = sorted(glob.glob(os.path.join(base, 'helper_udp_*.log')))
    helper_tcp_logs = sorted(glob.glob(os.path.join(base, 'helper_tcp_*.log')))
    stage_meta = _latest(glob.glob(os.path.join(base, 'stage_meta_*.log')))

    out = {}
    if emergency_latency:
        value = _parse_latency(emergency_latency)
        if value is not None:
            out['emergency_latency_avg_ms'] = value
    if emergency_udp:
        value = _parse_iperf_bw(emergency_udp)
        if value is not None:
            out['primary_udp_bw_mbps'] = value
    helper_udp_total = 0.0
    helper_udp_found = False
    for path in helper_udp_logs:
        value = _parse_iperf_bw(path)
        if value is not None:
            helper_udp_total += value
            helper_udp_found = True
    if helper_udp_found:
        out['helper_udp_bw_mbps'] = helper_udp_total
    helper_tcp_total = 0.0
    helper_tcp_found = False
    for path in helper_tcp_logs:
        value = _parse_iperf_bw(path)
        if value is not None:
            helper_tcp_total += value
            helper_tcp_found = True
    if helper_tcp_found:
        out['throughput_mbps'] = helper_tcp_total

    primary = out.get('primary_udp_bw_mbps', 0.0)
    helper = out.get('helper_udp_bw_mbps', 0.0)
    total_udp = primary + helper
    if out.get('primary_udp_bw_mbps') is not None or out.get('helper_udp_bw_mbps') is not None:
        out['udp_bw_mbps'] = total_udp
    total_tcp = out.get('throughput_mbps')
    if total_tcp not in (None, 0):
        out['udp_share_pct'] = total_udp / (total_udp + total_tcp) * 100.0
    elif total_udp > 0:
        out['udp_share_pct'] = 100.0

    meta = _parse_stage_meta(stage_meta)
    if meta.get('configured_udp_pct'):
        try:
            out['configured_udp_pct'] = float(meta['configured_udp_pct'])
        except ValueError:
            pass
    return out


def mean_std(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None, None
    if len(vals) == 1:
        return vals[0], 0.0
    return statistics.mean(vals), statistics.stdev(vals)


def main():
    parser = argparse.ArgumentParser(description='Summarize staged v4 experiment results')
    parser.add_argument('--stages', default='20,40,60,80')
    parser.add_argument('--runs', type=int, default=5)
    parser.add_argument('--baseline-prefix', default='baseline_v4_v5_p')
    parser.add_argument('--sdnv-prefix', default='sdnv_v4_v5_p')
    parser.add_argument('--emapt-baseline-prefix', default='emapt_baseline_v4_v5_p')
    parser.add_argument('--emapt-sdnv-prefix', default='emapt_sdnv_v4_v5_p')
    parser.add_argument('--out-runs', default='results/stage_runs_v4.csv')
    parser.add_argument('--out-summary', default='results/stage_summary_v4.csv')
    args = parser.parse_args()

    stages = [int(s.strip()) for s in args.stages.split(',') if s.strip()]
    run_rows = []
    summary_rows = []

    for stage in stages:
        baseline_runs = {k: [] for k, _ in METRICS}
        sdnv_runs = {k: [] for k, _ in METRICS}
        baseline_emapt = {k: [] for k in EMAPT_KEYS}
        sdnv_emapt = {k: [] for k in EMAPT_KEYS}
        prt_runs = []
        per_baseline_runs = []
        per_sdnv_runs = []
        tse_runs = []

        for r in range(1, args.runs + 1):
            b_tag = f'{args.baseline_prefix}{stage}_r{r}'
            s_tag = f'{args.sdnv_prefix}{stage}_r{r}'

            b = load_tag_metrics('results', b_tag)
            s = load_tag_metrics('results', s_tag)
            row = {'stage_pct': stage, 'run': r}

            for key, _unit in METRICS:
                b_val = b.get(key)
                s_val = s.get(key)
                row[f'{key}_baseline'] = b_val
                row[f'{key}_sdnv'] = s_val
                baseline_runs[key].append(b_val)
                sdnv_runs[key].append(s_val)

            b_udp = b.get('udp_bw_mbps')
            b_tcp = b.get('throughput_mbps')
            s_udp = s.get('udp_bw_mbps')
            s_tcp = s.get('throughput_mbps')

            b_per = (b_udp / b_tcp) if b_udp is not None and b_tcp not in (None, 0) else None
            s_per = (s_udp / s_tcp) if s_udp is not None and s_tcp not in (None, 0) else None
            row['priority_enforcement_ratio_baseline'] = b_per
            row['priority_enforcement_ratio_sdnv'] = s_per
            per_baseline_runs.append(b_per)
            per_sdnv_runs.append(s_per)

            tse = None
            if b_tcp is not None and s_tcp is not None and b_tcp > 0:
                tse = (b_tcp - s_tcp) / b_tcp * 100.0
            row['traffic_suppression_efficiency_pct_sdnv'] = tse
            tse_runs.append(tse)

            prt = load_policy_reaction('logs', s_tag)
            prt_ms = (prt * 1000.0) if prt is not None else None
            row['policy_reaction_ms_sdnv'] = prt_ms
            prt_runs.append(prt_ms)

            b_emapt = parse_emapt(latest_emapt_csv(f'{args.emapt_baseline_prefix}{stage}_r{r}'))
            s_emapt = parse_emapt(latest_emapt_csv(f'{args.emapt_sdnv_prefix}{stage}_r{r}'))
            for key in EMAPT_KEYS:
                b_val = b_emapt.get(key)
                s_val = s_emapt.get(key)
                row[f'{key}_baseline'] = b_val
                row[f'{key}_sdnv'] = s_val
                baseline_emapt[key].append(b_val)
                sdnv_emapt[key].append(s_val)

            run_rows.append(row)

        summary = {'stage_pct': stage}
        for key, unit in METRICS:
            b_mean, b_std = mean_std(baseline_runs[key])
            s_mean, s_std = mean_std(sdnv_runs[key])
            summary[f'{key}_baseline_mean'] = b_mean
            summary[f'{key}_baseline_std'] = b_std
            summary[f'{key}_sdnv_mean'] = s_mean
            summary[f'{key}_sdnv_std'] = s_std
            summary[f'{key}_unit'] = unit
        for key in EMAPT_KEYS:
            b_mean, b_std = mean_std(baseline_emapt[key])
            s_mean, s_std = mean_std(sdnv_emapt[key])
            summary[f'{key}_baseline_mean'] = b_mean
            summary[f'{key}_baseline_std'] = b_std
            summary[f'{key}_sdnv_mean'] = s_mean
            summary[f'{key}_sdnv_std'] = s_std
        b_per_mean, b_per_std = mean_std(per_baseline_runs)
        s_per_mean, s_per_std = mean_std(per_sdnv_runs)
        tse_mean, tse_std = mean_std(tse_runs)
        prt_mean, prt_std = mean_std(prt_runs)
        summary['priority_enforcement_ratio_baseline_mean'] = b_per_mean
        summary['priority_enforcement_ratio_baseline_std'] = b_per_std
        summary['priority_enforcement_ratio_sdnv_mean'] = s_per_mean
        summary['priority_enforcement_ratio_sdnv_std'] = s_per_std
        summary['traffic_suppression_efficiency_pct_sdnv_mean'] = tse_mean
        summary['traffic_suppression_efficiency_pct_sdnv_std'] = tse_std
        summary['policy_reaction_ms_sdnv_mean'] = prt_mean
        summary['policy_reaction_ms_sdnv_std'] = prt_std
        summary_rows.append(summary)

    os.makedirs(os.path.dirname(args.out_runs) or '.', exist_ok=True)
    os.makedirs(os.path.dirname(args.out_summary) or '.', exist_ok=True)

    if run_rows:
        with open(args.out_runs, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(run_rows[0].keys()))
            writer.writeheader()
            writer.writerows(run_rows)
    if summary_rows:
        with open(args.out_summary, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)

    print(f'Wrote {args.out_runs} and {args.out_summary}')


if __name__ == '__main__':
    main()
