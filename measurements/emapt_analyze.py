#!/usr/bin/env python3
"""
Compute EMAPT and coverage curve from receiver logs.
"""

import argparse
import glob
import os
import re


def parse_time(path, key):
    with open(path, 'r') as f:
        for line in f:
            if line.startswith(key):
                return float(line.strip().split('=')[1])
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--logs', required=True, help='log prefix, e.g. logs/emapt')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    tx_log = args.logs + '_tx.log'
    t0 = parse_time(tx_log, 'tx_start_epoch')
    if t0 is None:
        print('tx_start not found')
        return

    rx_logs = sorted(glob.glob(args.logs + '_rx_*.log'))
    times = []
    for path in rx_logs:
        t = parse_time(path, 'first_rx_epoch')
        if t is not None:
            times.append(t - t0)

    times.sort()
    n = len(times)
    if n == 0:
        print('no receivers')
        return

    def emapt(p):
        idx = max(0, int((p/100.0)*n) - 1)
        return times[idx]

    emapt_50 = emapt(50)
    emapt_90 = emapt(90)
    emapt_100 = times[-1]

    with open(args.out, 'w') as f:
        f.write(f"emapt_50={emapt_50:.6f}\n")
        f.write(f"emapt_90={emapt_90:.6f}\n")
        f.write(f"emapt_100={emapt_100:.6f}\n")
        f.write("coverage_curve_seconds,coverage_fraction\n")
        for i, t in enumerate(times, start=1):
            f.write(f"{t:.6f},{i/n:.3f}\n")

    print(f"Wrote {args.out}")


if __name__ == '__main__':
    main()
