#!/usr/bin/env python3
"""
UDP receiver that logs the first packet arrival time.
"""

import argparse
import socket
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=6000)
    parser.add_argument('--log', required=True)
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', args.port))

    first = True
    while True:
        data, _addr = sock.recvfrom(2048)
        if first:
            t = time.time()
            with open(args.log, 'w') as f:
                f.write(f"first_rx_epoch={t:.6f}\n")
            first = False
            break


if __name__ == '__main__':
    main()
