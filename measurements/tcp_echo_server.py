#!/usr/bin/env python3
"""Simple threaded TCP echo server for best-effort latency probes."""

import argparse
import socket
import threading


def _handle_client(conn):
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            conn.sendall(data)
    finally:
        try:
            conn.close()
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser(description='TCP echo server')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=5004)
    args = parser.parse_args()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen()

    try:
        while True:
            conn, _addr = srv.accept()
            thread = threading.Thread(target=_handle_client, args=(conn,), daemon=True)
            thread.start()
    finally:
        srv.close()


if __name__ == '__main__':
    main()
