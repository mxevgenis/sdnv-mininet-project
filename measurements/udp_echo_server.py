#!/usr/bin/env python3
"""Simple UDP echo server for emergency-class RTT measurements."""

import argparse
import socket


def main():
    parser = argparse.ArgumentParser(description='UDP echo server')
    parser.add_argument('--port', type=int, default=5003)
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', args.port))

    while True:
        data, addr = sock.recvfrom(2048)
        sock.sendto(data, addr)


if __name__ == '__main__':
    main()
