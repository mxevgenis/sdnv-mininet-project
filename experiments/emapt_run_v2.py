#!/usr/bin/env python3
"""Fair v2 EMAPT measurement under the same fixed background load."""

import argparse
import math
import os
import signal
import subprocess
import time

from mininet.log import info, setLogLevel

import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import topology.sdnv_topology as sdnv_topology


def _start_controller(log_path, ryu_ip, ryu_port):
    log_file = open(log_path, 'w')
    proc = subprocess.Popen(
        [
            'ryu-manager',
            '--ofp-listen-host', ryu_ip,
            '--ofp-tcp-listen-port', str(ryu_port),
            'controller/sdnv_controller.py',
        ],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid,
    )
    return proc, log_file


def _stop_controller(proc, log_file):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except Exception:
        pass
    try:
        log_file.close()
    except Exception:
        pass


def _float_env(key, default):
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def _popen_in_node(node, cmd, log_path=None):
    if log_path:
        log_file = open(log_path, 'w')
        proc = node.popen(cmd, shell=True, stdout=log_file, stderr=subprocess.STDOUT)
        return proc, log_file
    proc = node.popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc, None


def main():
    parser = argparse.ArgumentParser(description='Fair v2 EMAPT runner')
    parser.add_argument('--scenario', choices=['baseline', 'sdnv'], default='sdnv')
    parser.add_argument('--results-tag', default='emapt_v2')
    parser.add_argument('--num-vehicles', type=int, default=None)
    parser.add_argument('--area-size', type=float, default=None)
    parser.add_argument('--speed-kmh', type=float, default=None)
    parser.add_argument('--warmup', type=float, default=None)
    parser.add_argument('--ryu-ip', default='127.0.0.1')
    parser.add_argument('--ryu-port', type=int, default=6653)
    args = parser.parse_args()

    os.makedirs('logs', exist_ok=True)
    timestamp = int(time.time())
    warmup = args.warmup
    if warmup is None:
        warmup = _float_env('SDNV_WARMUP', 5.0)

    background_total_mbit = _float_env('SDNV_BG_TOTAL_MBIT', 30.0)
    emapt_port = int(os.environ.get('SDNV_EMAPT_PORT', '6000'))
    best_effort_port = int(os.environ.get('SDNV_BEST_EFFORT_PORT', '5002'))

    info('*** starting controller\n')
    ctrl_log = f'logs/controller_{args.results_tag}_{timestamp}.log'
    ctrl_proc, ctrl_log_file = _start_controller(ctrl_log, args.ryu_ip, args.ryu_port)
    time.sleep(2)

    info('*** building topology\n')
    os.environ['RYU_IP'] = args.ryu_ip
    os.environ['RYU_PORT'] = str(args.ryu_port)
    if args.num_vehicles is not None:
        os.environ['SDNV_NUM_VEHICLES'] = str(args.num_vehicles)
    if args.area_size is not None:
        os.environ['SDNV_AREA_SIZE'] = str(args.area_size)
    if args.speed_kmh is not None:
        os.environ['SDNV_SPEED_KMH'] = str(args.speed_kmh)
    net = sdnv_topology.build_network()

    sta1 = net.get('sta1')
    h1 = net.get('h1')
    stations = sorted(net.stations, key=lambda s: s.name)
    recv_stations = [s for s in stations if s.name != 'sta1']

    try:
        info('*** waiting for stations to associate\n')
        try:
            net.waitConnected()
        except Exception:
            pass

        if args.scenario == 'sdnv':
            info('*** applying SDNV policy on sta1\n')
            proc, _ = _popen_in_node(sta1, 'bash vehicle/sdnv_policy.sh')
            proc.wait()
        else:
            info('*** applying flat baseline policy on sta1\n')
            proc, _ = _popen_in_node(sta1, 'bash vehicle/baseline_policy.sh')
            proc.wait()

        info('*** starting TCP server for background load on h1\n')
        tcp_proc, tcp_log = _popen_in_node(
            h1,
            f'iperf -s -p {best_effort_port}',
            f'logs/iperf_tcp_server_{args.results_tag}_{timestamp}.log',
        )

        per_sender_mbit = background_total_mbit / max(1, len(recv_stations))
        per_sender_rate = f'{per_sender_mbit:.3f}mbit'
        background_duration = int(math.ceil(warmup + 10))

        info(f'*** applying background sender caps ({per_sender_rate} per sender)\n')
        for sta in recv_stations:
            proc, _ = _popen_in_node(sta, f'bash vehicle/background_policy.sh {per_sender_rate}')
            proc.wait()

        info('*** starting background flows during dissemination run\n')
        bg_processes = []
        for sta in recv_stations:
            proc, logf = _popen_in_node(
                sta,
                f'iperf -c 10.0.0.100 -p {best_effort_port} -t {background_duration} -i 5',
                f'logs/{sta.name}_background_{args.results_tag}_{timestamp}.log',
            )
            bg_processes.append((proc, logf))

        base = f'logs/emapt_{args.results_tag}_{timestamp}'
        rx_logs = []
        for sta in recv_stations:
            log_path = f'{base}_rx_{sta.name}.log'
            cmd = f'python3 measurements/emapt_receiver.py --port {emapt_port} --log {log_path}'
            proc, logf = _popen_in_node(sta, cmd)
            rx_logs.append((proc, logf))

        if warmup > 0:
            info(f'*** warm-up for {warmup:.1f}s before EMAPT send\n')
            time.sleep(warmup)

        info('*** sending emergency dissemination flow from sta1\n')
        tx_log = f'{base}_tx.log'
        dests = ','.join([sta.IP() for sta in recv_stations])
        proc, logf = _popen_in_node(
            sta1,
            f'python3 measurements/emapt_sender.py --dests {dests} --port {emapt_port} --log {tx_log}',
        )
        proc.wait()
        if logf:
            logf.close()

        time.sleep(2)

        for proc, logf in bg_processes:
            proc.wait()
            if logf:
                logf.close()
        for _proc, logf in rx_logs:
            if logf:
                logf.close()
        if tcp_log:
            tcp_log.close()

        out_path = f'results/emapt_{args.results_tag}_{timestamp}.csv'
        subprocess.check_call(
            f'python3 measurements/emapt_analyze.py --logs {base} --out {out_path}',
            shell=True,
        )

    finally:
        info('*** stopping network\n')
        try:
            net.stop()
        except Exception:
            pass
        info('*** stopping controller\n')
        _stop_controller(ctrl_proc, ctrl_log_file)


if __name__ == '__main__':
    setLogLevel('info')
    main()
