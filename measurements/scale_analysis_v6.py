#!/usr/bin/env python3
"""Aggregate cooperative v6 experiment results with mean/stddev."""

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
    ('background_latency_avg_ms', 'ms'),
    ('primary_udp_bw_mbps', 'mbps'),
    ('helper_udp_bw_mbps', 'mbps'),
    ('local_tcp_bw_mbps', 'mbps'),
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


def _latest_by_helper(paths):
    grouped = {}
    for path in paths:
        name = os.path.basename(path)
        m = re.match(r'(helper_(?:udp|tcp)_[^_]+)_(\d+)\.log$', name)
        if not m:
            grouped.setdefault(name, []).append(path)
            continue
        grouped.setdefault(m.group(1), []).append(path)
    latest = []
    for matches in grouped.values():
        latest.append(_latest(matches))
    return [path for path in latest if path]


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


def _latest_emapt_csv(results_dir, tag_prefix):
    matches = glob.glob(os.path.join(results_dir, f'emapt_{tag_prefix}_*.csv'))
    return _latest(matches)


def _parse_emapt(path):
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
    return {key: values.get(key) for key in EMAPT_KEYS if key in values}


def load_tag_metrics(results_dir, tag):
    base = os.path.join(results_dir, tag)
    if not os.path.isdir(base):
        raise FileNotFoundError(f'results directory not found: {base}')

    emergency_latency = _latest(glob.glob(os.path.join(base, 'emergency_latency_*.log')))
    background_latency = _latest(glob.glob(os.path.join(base, 'background_latency_*.log')))
    emergency_udp = _latest(glob.glob(os.path.join(base, 'emergency_udp_*.log')))
    helper_udp_logs = _latest_by_helper(glob.glob(os.path.join(base, 'helper_udp_*.log')))
    helper_tcp_logs = _latest_by_helper(glob.glob(os.path.join(base, 'helper_tcp_*.log')))
    local_tcp = _latest(glob.glob(os.path.join(base, 'local_tcp_*.log')))

    out = {}
    if emergency_latency:
        value = _parse_latency(emergency_latency)
        if value is not None:
            out['emergency_latency_avg_ms'] = value
    if background_latency:
        value = _parse_latency(background_latency)
        if value is not None:
            out['background_latency_avg_ms'] = value
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
    local_tcp_bw = None
    if local_tcp:
        local_tcp_bw = _parse_iperf_bw(local_tcp)
        if local_tcp_bw is not None:
            out['local_tcp_bw_mbps'] = local_tcp_bw
    if helper_tcp_found or local_tcp_bw is not None:
        out['throughput_mbps'] = helper_tcp_total + (local_tcp_bw or 0.0)

    primary_udp = out.get('primary_udp_bw_mbps', 0.0)
    helper_udp = out.get('helper_udp_bw_mbps', 0.0)
    total_udp = primary_udp + helper_udp
    if out.get('primary_udp_bw_mbps') is not None or out.get('helper_udp_bw_mbps') is not None:
        out['udp_bw_mbps'] = total_udp
    total_tcp = out.get('throughput_mbps')
    if total_tcp not in (None, 0):
        out['udp_share_pct'] = total_udp / (total_udp + total_tcp) * 100.0
    elif total_udp > 0:
        out['udp_share_pct'] = 100.0
    return out


def mean_std(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None, None
    if len(vals) == 1:
        return vals[0], 0.0
    return statistics.mean(vals), statistics.stdev(vals)


def main():
    parser = argparse.ArgumentParser(description='Summarize cooperative v6 experiment results')
    parser.add_argument('--counts', default='5,10,15,20')
    parser.add_argument('--runs', type=int, default=5)
    parser.add_argument('--baseline-prefix', default='baseline_v6_scale_v')
    parser.add_argument('--sdnv-prefix', default='sdnv_v6_scale_v')
    parser.add_argument('--emapt-baseline-prefix', default='emapt_baseline_v6_scale_v')
    parser.add_argument('--emapt-sdnv-prefix', default='emapt_sdnv_v6_scale_v')
    parser.add_argument('--results-dir', default='results')
    parser.add_argument('--logs-dir', default='logs')
    parser.add_argument('--out-runs', default='results/scale_runs_v6.csv')
    parser.add_argument('--out-summary', default='results/scale_summary_v6.csv')
    parser.add_argument('--out-table', default='results/scale_table_v6.csv')
    args = parser.parse_args()

    counts = [int(s.strip()) for s in args.counts.split(',') if s.strip()]
    run_rows = []
    summary_rows = []
    table_rows = []

    for vehicles in counts:
        baseline_runs = {k: [] for k, _ in METRICS}
        sdnv_runs = {k: [] for k, _ in METRICS}
        baseline_emapt = {k: [] for k in EMAPT_KEYS}
        sdnv_emapt = {k: [] for k in EMAPT_KEYS}
        prt_runs = []
        per_baseline_runs = []
        per_sdnv_runs = []
        tse_runs = []

        for run in range(1, args.runs + 1):
            tag_suffix = f'{vehicles}_r{run}'
            b_tag = f'{args.baseline_prefix}{tag_suffix}'
            s_tag = f'{args.sdnv_prefix}{tag_suffix}'

            b = load_tag_metrics(args.results_dir, b_tag)
            s = load_tag_metrics(args.results_dir, s_tag)
            row = {'vehicle_count': vehicles, 'run': run}

            for key, _unit in METRICS:
                b_val = b.get(key)
                s_val = s.get(key)
                row[f'{key}_baseline'] = b_val
                row[f'{key}_sdnv'] = s_val
                baseline_runs[key].append(b_val)
                sdnv_runs[key].append(s_val)

            b_primary = b.get('primary_udp_bw_mbps')
            s_primary = s.get('primary_udp_bw_mbps')
            b_tcp = b.get('throughput_mbps')
            s_tcp = s.get('throughput_mbps')
            b_per = (b_primary / b_tcp) if b_primary is not None and b_tcp not in (None, 0) else None
            s_per = (s_primary / s_tcp) if s_primary is not None and s_tcp not in (None, 0) else None
            row['priority_enforcement_ratio_baseline'] = b_per
            row['priority_enforcement_ratio_sdnv'] = s_per
            per_baseline_runs.append(b_per)
            per_sdnv_runs.append(s_per)

            tse = None
            if b_tcp is not None and s_tcp is not None and b_tcp > 0:
                tse = (b_tcp - s_tcp) / b_tcp * 100.0
            row['traffic_suppression_efficiency_pct_sdnv'] = tse
            tse_runs.append(tse)

            prt = load_policy_reaction(args.logs_dir, s_tag)
            prt_ms = (prt * 1000.0) if prt is not None else None
            row['policy_reaction_ms_sdnv'] = prt_ms
            prt_runs.append(prt_ms)

            b_emapt = _parse_emapt(
                _latest_emapt_csv(args.results_dir, f'{args.emapt_baseline_prefix}{tag_suffix}')
            )
            s_emapt = _parse_emapt(
                _latest_emapt_csv(args.results_dir, f'{args.emapt_sdnv_prefix}{tag_suffix}')
            )
            for key in EMAPT_KEYS:
                b_val = b_emapt.get(key)
                s_val = s_emapt.get(key)
                row[f'{key}_baseline'] = b_val
                row[f'{key}_sdnv'] = s_val
                baseline_emapt[key].append(b_val)
                sdnv_emapt[key].append(s_val)

            run_rows.append(row)

        summary = {'vehicle_count': vehicles}
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

        table_rows.append({
            'vehicle_count': vehicles,
            'udp_share_pct_baseline_mean': summary.get('udp_share_pct_baseline_mean'),
            'udp_share_pct_sdnv_mean': summary.get('udp_share_pct_sdnv_mean'),
            'traffic_suppression_efficiency_pct_sdnv_mean': tse_mean,
            'traffic_suppression_efficiency_pct_sdnv_std': tse_std,
            'policy_reaction_ms_sdnv_mean': prt_mean,
            'policy_reaction_ms_sdnv_std': prt_std,
            'priority_enforcement_ratio_baseline_mean': b_per_mean,
            'priority_enforcement_ratio_sdnv_mean': s_per_mean,
            'emapt_50_baseline_mean': summary.get('emapt_50_ms_baseline_mean'),
            'emapt_50_sdnv_mean': summary.get('emapt_50_ms_sdnv_mean'),
            'emapt_90_baseline_mean': summary.get('emapt_90_ms_baseline_mean'),
            'emapt_90_sdnv_mean': summary.get('emapt_90_ms_sdnv_mean'),
            'emapt_100_baseline_mean': summary.get('emapt_100_ms_baseline_mean'),
            'emapt_100_sdnv_mean': summary.get('emapt_100_ms_sdnv_mean'),
        })

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
    if table_rows:
        with open(args.out_table, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(table_rows[0].keys()))
            writer.writeheader()
            writer.writerows(table_rows)

    print(f'Wrote {args.out_runs}, {args.out_summary}, and {args.out_table}')


if __name__ == '__main__':
    main()
