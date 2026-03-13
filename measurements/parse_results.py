#!/usr/bin/env python3
"""
Parse results logs and produce a summary CSV and text report.
"""

import argparse
import csv
import glob
import os
import re

PING_RE = re.compile(r"= ([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+)")
IPERF_BW_RE = re.compile(r"([0-9.]+)\s+([KMG]bits/sec)")
IPERF_JITTER_RE = re.compile(r"([0-9.]+)\s+ms")


def _to_mbps(value, unit):
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
    return _to_mbps(m.group(1), m.group(2))


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
        bw = _to_mbps(m_bw.group(1), m_bw.group(2))
    if m_j:
        jitter = float(m_j.group(1))
    return bw, jitter


def collect_scenario(scenario_dir):
    rows = []

    for path in glob.glob(os.path.join(scenario_dir, 'latency_*.log')):
        res = parse_latency(path)
        if res:
            avg_ms, mdev_ms = res
            rows.append(['latency_avg_ms', avg_ms, 'ms', path])
            rows.append(['latency_mdev_ms', mdev_ms, 'ms', path])

    for path in glob.glob(os.path.join(scenario_dir, 'throughput_*.log')):
        res = parse_iperf_tcp(path)
        if res is not None:
            rows.append(['throughput_mbps', res, 'Mbps', path])

    for path in glob.glob(os.path.join(scenario_dir, 'jitter_*.log')):
        res = parse_iperf_udp(path)
        if res:
            bw, jitter = res
            if bw is not None:
                rows.append(['udp_bw_mbps', bw, 'Mbps', path])
            if jitter is not None:
                rows.append(['jitter_ms', jitter, 'ms', path])

    return rows


def summarize(rows):
    summary = {}
    for metric, value, unit, _path in rows:
        key = (metric, unit)
        summary.setdefault(key, []).append(float(value))
    return {k: sum(v) / len(v) for k, v in summary.items() if v}


def main():
    parser = argparse.ArgumentParser(description='Parse SDNV results')
    parser.add_argument('--results', default='results', help='Results directory')
    args = parser.parse_args()

    scenarios = []
    for name in ('baseline', 'sdnv'):
        scenario_dir = os.path.join(args.results, name)
        if os.path.isdir(scenario_dir):
            scenarios.append((name, scenario_dir))

    all_rows = []
    for name, scenario_dir in scenarios:
        rows = collect_scenario(scenario_dir)
        for row in rows:
            all_rows.append([name] + row)

    if not all_rows:
        print('No results found.')
        return

    csv_path = os.path.join(args.results, 'summary.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['scenario', 'metric', 'value', 'unit', 'source'])
        writer.writerows(all_rows)

    txt_path = os.path.join(args.results, 'summary.txt')
    with open(txt_path, 'w') as f:
        for name, _scenario_dir in scenarios:
            rows = [r[1:] for r in all_rows if r[0] == name]
            f.write(f"[{name}]\n")
            summary = summarize(rows)
            for (metric, unit), value in sorted(summary.items()):
                f.write(f"{metric}: {value:.4f} {unit}\n")
            f.write("\n")

    print(f"Wrote {csv_path} and {txt_path}")


if __name__ == '__main__':
    main()
