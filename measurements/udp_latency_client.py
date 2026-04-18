#!/usr/bin/env python3
"""Measure RTT over an emergency-class UDP echo flow."""

import argparse
import math
import socket
import statistics
import time


def main():
    parser = argparse.ArgumentParser(description='UDP latency probe client')
    parser.add_argument('--dest', required=True)
    parser.add_argument('--port', type=int, default=5003)
    parser.add_argument('--duration', type=float, default=60.0)
    parser.add_argument('--interval', type=float, default=0.2)
    parser.add_argument('--timeout', type=float, default=1.0)
    parser.add_argument('--log', required=True)
    args = parser.parse_args()

    count = max(1, int(math.floor(args.duration / args.interval)))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', args.port))
    sock.settimeout(args.timeout)

    rtts = []
    received = 0

    for seq in range(count):
        payload = f'{seq}:{time.time():.6f}'.encode('ascii')
        t0 = time.time()
        try:
            sock.sendto(payload, (args.dest, args.port))
            data, _addr = sock.recvfrom(2048)
            if data == payload:
                received += 1
                rtts.append((time.time() - t0) * 1000.0)
        except socket.timeout:
            pass

        elapsed = time.time() - t0
        remaining = args.interval - elapsed
        if remaining > 0:
            time.sleep(remaining)

    with open(args.log, 'w') as f:
        f.write(f"{count} packets transmitted, {received} received\n")
        if rtts:
            avg = statistics.mean(rtts)
            mdev = statistics.pstdev(rtts) if len(rtts) > 1 else 0.0
            f.write(
                "rtt min/avg/max/mdev = "
                f"{min(rtts):.3f}/{avg:.3f}/{max(rtts):.3f}/{mdev:.3f} ms\n"
            )


if __name__ == '__main__':
    main()
