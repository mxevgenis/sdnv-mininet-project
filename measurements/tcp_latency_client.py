#!/usr/bin/env python3
"""Measure RTT over a best-effort TCP echo flow."""

import argparse
import math
import socket
import statistics
import time


def _recv_exact(sock, length):
    chunks = []
    remaining = length
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError('connection closed during recv')
        chunks.append(chunk)
        remaining -= len(chunk)
    return b''.join(chunks)


def main():
    parser = argparse.ArgumentParser(description='TCP latency probe client')
    parser.add_argument('--dest', required=True)
    parser.add_argument('--port', type=int, default=5004)
    parser.add_argument('--duration', type=float, default=60.0)
    parser.add_argument('--interval', type=float, default=0.2)
    parser.add_argument('--timeout', type=float, default=1.0)
    parser.add_argument('--log', required=True)
    args = parser.parse_args()

    count = max(1, int(math.floor(args.duration / args.interval)))
    rtts = []
    received = 0

    sock = socket.create_connection((args.dest, args.port), timeout=args.timeout)
    sock.settimeout(args.timeout)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    try:
        for seq in range(count):
            payload = f'{seq}:{time.time():.6f}'.encode('ascii').ljust(64, b' ')
            t0 = time.time()
            try:
                sock.sendall(payload)
                data = _recv_exact(sock, len(payload))
                if data == payload:
                    received += 1
                    rtts.append((time.time() - t0) * 1000.0)
            except (socket.timeout, ConnectionError, BrokenPipeError):
                break

            elapsed = time.time() - t0
            remaining = args.interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
    finally:
        sock.close()

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
