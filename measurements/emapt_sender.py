#!/usr/bin/env python3
"""
Send UDP emergency packets and log send time.
"""

import argparse
import socket
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dest', default='10.0.0.255')
    parser.add_argument('--dests', default='')
    parser.add_argument('--port', type=int, default=6000)
    parser.add_argument('--count', type=int, default=50)
    parser.add_argument('--interval', type=float, default=0.02)
    parser.add_argument('--log', required=True)
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    t0 = time.time()
    with open(args.log, 'w') as f:
        f.write(f"tx_start_epoch={t0:.6f}\n")

    payload = b'EMERGENCY'
    if args.dests:
        dests = [d.strip() for d in args.dests.split(',') if d.strip()]
    else:
        dests = [args.dest]

    for _ in range(args.count):
        for d in dests:
            sock.sendto(payload, (d, args.port))
        time.sleep(args.interval)


if __name__ == '__main__':
    main()
