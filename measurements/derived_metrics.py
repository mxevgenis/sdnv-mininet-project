#!/usr/bin/env python3
"""Compute derived SDNV metrics from baseline and SDNV results tags."""

import argparse
import csv
import glob
import os
import re

PING_RE = re.compile(r"= ([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+)")
IPERF_BW_RE = re.compile(r"([0-9.]+)\s+([KMG]bits/sec)")
IPERF_JITTER_RE = re.compile(r"([0-9.]+)\s+ms")
IPERF_SERVER_UDP_RE = re.compile(
    r"\[\s*\d+\]\s+([0-9.]+)-([0-9.]+)\s+sec.*?([0-9.]+)\s+([KMG]bits/sec)\s+([0-9.]+)\s+ms"
)


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
    def ts(p):
        m = re.search(r'_(\d+)\.log$', os.path.basename(p))
        return int(m.group(1)) if m else 0
    return max(paths, key=ts) if paths else None


def _latest_with_jitter(paths):
    def ts(p):
        m = re.search(r'_(\d+)\.log$', os.path.basename(p))
        return int(m.group(1)) if m else 0
    for path in sorted(paths, key=ts, reverse=True):
        res = _parse_iperf_udp(path)
        if res:
            bw, jitter = res
            if jitter is not None:
                return path
    return _latest(paths)


def _parse_latency(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if 'min/avg/max' in line:
                m = PING_RE.search(line)
                if m:
                    return float(m.group(2)), float(m.group(4))
    return None


def _parse_iperf_tcp(path):
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


def _parse_iperf_udp(path):
    last_bw = None
    last_jitter = None
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if 'bits/sec' in line and 'sec' in line:
                m_bw = IPERF_BW_RE.search(line)
                if m_bw:
                    last_bw = _to_mbps(m_bw.group(1), m_bw.group(2))
                m_j = IPERF_JITTER_RE.search(line)
                if m_j:
                    last_jitter = float(m_j.group(1))
    if last_bw is None and last_jitter is None:
        return None
    return last_bw, last_jitter


def _parse_iperf_udp_server(path):
    best = None
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = IPERF_SERVER_UDP_RE.search(line)
            if not m:
                continue
            start = float(m.group(1))
            end = float(m.group(2))
            duration = end - start
            bw = _to_mbps(m.group(3), m.group(4))
            jitter = float(m.group(5))
            if best is None or duration > best[0]:
                best = (duration, bw, jitter)
    if best is None:
        return None
    _duration, bw, jitter = best
    return bw, jitter


def load_tag_metrics(results_dir, tag, logs_dir='logs'):
    base = os.path.join(results_dir, tag)
    if not os.path.isdir(base):
        raise FileNotFoundError(f"results directory not found: {base}")

    emergency_latency = _latest(glob.glob(os.path.join(base, 'emergency_latency_*.log')))
    if not emergency_latency:
        emergency_latency = _latest(glob.glob(os.path.join(base, 'latency_*.log')))
    background_latency = _latest(glob.glob(os.path.join(base, 'background_latency_*.log')))
    jitter = _latest_with_jitter(glob.glob(os.path.join(base, 'jitter_*.log')))
    throughput = _latest(glob.glob(os.path.join(base, 'throughput_*.log')))

    out = {}
    if emergency_latency:
        res = _parse_latency(emergency_latency)
        if res:
            avg_ms, mdev_ms = res
            out['latency_avg_ms'] = avg_ms
            out['latency_mdev_ms'] = mdev_ms
            out['emergency_latency_avg_ms'] = avg_ms
            out['emergency_latency_mdev_ms'] = mdev_ms
    if background_latency:
        res = _parse_latency(background_latency)
        if res:
            avg_ms, mdev_ms = res
            out['background_latency_avg_ms'] = avg_ms
            out['background_latency_mdev_ms'] = mdev_ms
    if jitter:
        res = _parse_iperf_udp(jitter)
        if res:
            out['udp_bw_mbps'], out['jitter_ms'] = res

    # Fall back to the UDP server log when the client-side iperf output does not
    # include the final server report (which is where jitter is reported).
    if logs_dir and ('jitter_ms' not in out or out.get('jitter_ms') is None):
        server_log = _latest(
            glob.glob(os.path.join(logs_dir, f'iperf_udp_server_{tag}_*.log'))
        )
        if server_log:
            res = _parse_iperf_udp_server(server_log)
            if res:
                bw, jitter_val = res
                out.setdefault('udp_bw_mbps', bw)
                out['jitter_ms'] = jitter_val
    if throughput:
        res = _parse_iperf_tcp(throughput)
        if res is not None:
            out['throughput_mbps'] = res

    return out


def load_policy_reaction(logs_dir, sdnv_tag):
    logs = glob.glob(os.path.join(logs_dir, f'policy_timing_{sdnv_tag}_*.log'))
    log_path = _latest(logs)
    if not log_path:
        return None
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('policy_reaction_s='):
                try:
                    return float(line.split('=', 1)[1].strip())
                except ValueError:
                    return None
    return None


def _fmt(value, unit):
    if value is None:
        return "n/a"
    if unit == 'ratio':
        return f"{value:.4f}"
    if unit == 'percent':
        return f"{value:.2f}%"
    return f"{value:.4f} {unit}"


def main():
    parser = argparse.ArgumentParser(
        description='Compute derived SDNV metrics from baseline/SDNV tags.'
    )
    parser.add_argument('--baseline-tag', required=True)
    parser.add_argument('--sdnv-tag', required=True)
    parser.add_argument('--results-dir', default='results')
    parser.add_argument('--logs-dir', default='logs')
    parser.add_argument('--write', action='store_true',
                        help='write derived_metrics_<baseline>_vs_<sdnv>.csv/txt')
    args = parser.parse_args()

    baseline = load_tag_metrics(args.results_dir, args.baseline_tag)
    sdnv = load_tag_metrics(args.results_dir, args.sdnv_tag)
    policy_reaction = load_policy_reaction(args.logs_dir, args.sdnv_tag)

    base_bg = baseline.get('throughput_mbps')
    sdnv_bg = sdnv.get('throughput_mbps')
    base_udp = baseline.get('udp_bw_mbps')
    sdnv_udp = sdnv.get('udp_bw_mbps')

    suppression = None
    if base_bg is not None and sdnv_bg is not None and base_bg > 0:
        suppression = (base_bg - sdnv_bg) / base_bg

    prio_ratio_baseline = None
    if base_udp is not None and base_bg:
        prio_ratio_baseline = base_udp / base_bg

    prio_ratio_sdnv = None
    if sdnv_udp is not None and sdnv_bg:
        prio_ratio_sdnv = sdnv_udp / sdnv_bg

    rows = [
        ('traffic_suppression_efficiency', suppression, 'ratio'),
        ('traffic_suppression_efficiency_percent',
         (suppression * 100.0) if suppression is not None else None, 'percent'),
        ('policy_reaction_time_s', policy_reaction, 's'),
        ('priority_enforcement_ratio_baseline', prio_ratio_baseline, 'ratio'),
        ('priority_enforcement_ratio_sdnv', prio_ratio_sdnv, 'ratio'),
    ]

    print(f"baseline_tag: {args.baseline_tag}")
    print(f"sdnv_tag: {args.sdnv_tag}")
    for name, value, unit in rows:
        if unit == 'percent':
            print(f"{name}: {_fmt(value, unit)}")
        else:
            print(f"{name}: {_fmt(value, unit)}")

    if args.write:
        out_base = f"derived_metrics_{args.baseline_tag}_vs_{args.sdnv_tag}"
        csv_path = os.path.join(args.results_dir, f"{out_base}.csv")
        txt_path = os.path.join(args.results_dir, f"{out_base}.txt")

        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['metric', 'value', 'unit'])
            for name, value, unit in rows:
                writer.writerow([name, value if value is not None else '', unit])

        with open(txt_path, 'w') as f:
            f.write(f"baseline_tag: {args.baseline_tag}\n")
            f.write(f"sdnv_tag: {args.sdnv_tag}\n")
            for name, value, unit in rows:
                if unit == 'percent':
                    f.write(f"{name}: {_fmt(value, unit)}\n")
                else:
                    f.write(f"{name}: {_fmt(value, unit)}\n")

        print(f"Wrote {csv_path} and {txt_path}")


if __name__ == '__main__':
    main()
