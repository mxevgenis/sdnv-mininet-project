#!/usr/bin/env python3
"""Summarize the latest logs in a single results/<tag> directory."""

import argparse
import glob
import os
import re

PING_RE = re.compile(r"= ([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+)")
IPERF_BW_RE = re.compile(r"([0-9.]+)\s+([KMG]bits/sec)")
IPERF_JITTER_RE = re.compile(r"([0-9.]+)\s+ms")


def to_mbps(value, unit):
    value = float(value)
    if unit == 'Kbits/sec':
        return value / 1000.0
    if unit == 'Mbits/sec':
        return value
    if unit == 'Gbits/sec':
        return value * 1000.0
    return value


def latest(paths):
    def ts(p):
        m = re.search(r'_(\d+)\.log$', os.path.basename(p))
        return int(m.group(1)) if m else 0
    return max(paths, key=ts) if paths else None


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
    last_bw = None
    last_jitter = None
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if 'bits/sec' in line and 'sec' in line:
                last = line
                m_bw = IPERF_BW_RE.search(line)
                if m_bw:
                    last_bw = to_mbps(m_bw.group(1), m_bw.group(2))
                m_j = IPERF_JITTER_RE.search(line)
                if m_j:
                    last_jitter = float(m_j.group(1))
    if not last:
        return None
    return last_bw, last_jitter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('tag', help='results subdirectory tag')
    args = parser.parse_args()

    base = os.path.join('results', args.tag)
    if not os.path.isdir(base):
        print(f"results directory not found: {base}")
        return

    latency = latest(glob.glob(os.path.join(base, 'latency_*.log')))
    jitter = latest(glob.glob(os.path.join(base, 'jitter_*.log')))
    throughput = latest(glob.glob(os.path.join(base, 'throughput_*.log')))

    out = {}
    if latency:
        res = parse_latency(latency)
        if res:
            out['latency_avg_ms'], out['latency_mdev_ms'] = res
    if jitter:
        res = parse_iperf_udp(jitter)
        if res:
            out['udp_bw_mbps'], out['jitter_ms'] = res
    if throughput:
        res = parse_iperf_tcp(throughput)
        if res is not None:
            out['throughput_mbps'] = res

    print(args.tag)
    for k in ('latency_avg_ms', 'latency_mdev_ms', 'jitter_ms', 'udp_bw_mbps', 'throughput_mbps'):
        if k in out:
            print(f"{k}: {out[k]}")


if __name__ == '__main__':
    main()
