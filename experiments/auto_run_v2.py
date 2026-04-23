#!/usr/bin/env python3
"""
Fair v2 SDNV experiment runner.
Measures emergency UDP throughput, emergency UDP latency, background TCP
latency, and local best-effort TCP throughput concurrently under the same
fixed background load.
"""

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
    parser = argparse.ArgumentParser(description='Fair v2 SDNV experiment runner')
    parser.add_argument('--scenario', choices=['baseline', 'sdnv'], default='baseline')
    parser.add_argument('--results-tag', default=None)
    parser.add_argument('--duration', type=int, default=60)
    parser.add_argument('--warmup', type=float, default=None)
    parser.add_argument('--num-vehicles', type=int, default=None)
    parser.add_argument('--area-size', type=float, default=None)
    parser.add_argument('--speed-kmh', type=float, default=None)
    parser.add_argument('--ryu-ip', default='127.0.0.1')
    parser.add_argument('--ryu-port', type=int, default=6653)
    args = parser.parse_args()

    results_tag = args.results_tag or args.scenario
    os.makedirs('logs', exist_ok=True)
    os.makedirs(f'results/{results_tag}', exist_ok=True)

    timestamp = int(time.time())
    warmup = args.warmup
    if warmup is None:
        warmup = _float_env('SDNV_WARMUP', 5.0)

    background_total_mbit = _float_env('SDNV_BG_TOTAL_MBIT', 30.0)
    latency_interval = _float_env('SDNV_LATENCY_INTERVAL', 0.2)
    emergency_port = int(os.environ.get('SDNV_EMERGENCY_PORT', '5001'))
    best_effort_port = int(os.environ.get('SDNV_BEST_EFFORT_PORT', '5002'))
    latency_port = int(os.environ.get('SDNV_LATENCY_PORT', '5003'))
    background_latency_port = int(os.environ.get('SDNV_BACKGROUND_LATENCY_PORT', '5004'))

    info('*** starting controller\n')
    ctrl_log = f'logs/controller_{results_tag}_{timestamp}.log'
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
    other_stations = [s for s in stations if s.name != 'sta1']

    try:
        info('*** waiting for stations to associate\n')
        try:
            net.waitConnected()
        except Exception:
            pass

        info('*** starting servers on h1\n')
        server_processes = []
        for cmd, name in (
            (f'iperf -s -u -p {emergency_port}', 'iperf_udp_server'),
            (f'iperf -s -p {best_effort_port}', 'iperf_tcp_server'),
            (f'python3 measurements/udp_echo_server.py --port {latency_port}', 'udp_echo_server'),
            (f'python3 measurements/tcp_echo_server.py --port {background_latency_port}', 'tcp_echo_server'),
        ):
            proc, logf = _popen_in_node(h1, cmd, f'logs/{name}_{results_tag}_{timestamp}.log')
            server_processes.append((proc, logf))
        time.sleep(1)

        info('*** quick connectivity check (sta1 -> h1)\n')
        ping_proc, ping_log = _popen_in_node(
            sta1,
            'ping -c 3 10.0.0.100',
            f'logs/ping_{results_tag}_{timestamp}.log',
        )
        ping_proc.wait()
        if ping_log:
            ping_log.close()

        if args.scenario == 'sdnv':
            info('*** applying SDNV policy on sta1\n')
            policy_log = f'logs/policy_timing_{results_tag}_{timestamp}.log'
            policy_start = time.time()
            proc, _ = _popen_in_node(sta1, 'bash vehicle/sdnv_policy.sh')
            proc.wait()
            policy_end = time.time()
            with open(policy_log, 'w') as f:
                f.write(f'policy_start_epoch={policy_start:.6f}\n')
                f.write(f'policy_end_epoch={policy_end:.6f}\n')
                f.write(f'policy_reaction_s={policy_end - policy_start:.6f}\n')
        else:
            info('*** applying flat baseline policy on sta1\n')
            proc, _ = _popen_in_node(sta1, 'bash vehicle/baseline_policy.sh')
            proc.wait()

        per_sender_mbit = background_total_mbit / max(1, len(other_stations))
        per_sender_rate = f'{per_sender_mbit:.3f}mbit'
        background_duration = int(math.ceil(args.duration + warmup + 5))

        info(f'*** applying background sender caps ({per_sender_rate} per sender)\n')
        for sta in other_stations:
            proc, _ = _popen_in_node(sta, f'bash vehicle/background_policy.sh {per_sender_rate}')
            proc.wait()

        info('*** starting fixed-load background flows\n')
        background_processes = []
        for sta in other_stations:
            proc, logf = _popen_in_node(
                sta,
                f'iperf -c 10.0.0.100 -p {best_effort_port} -t {background_duration} -i 5',
                f'logs/{sta.name}_background_{results_tag}_{timestamp}.log',
            )
            background_processes.append((proc, logf))

        if warmup > 0:
            info(f'*** warm-up for {warmup:.1f}s before concurrent measurements\n')
            time.sleep(warmup)

        info('*** starting concurrent emergency/background latency and throughput measurements from sta1\n')
        result_dir = f'results/{results_tag}'
        run_processes = []
        commands = (
            (
                f'python3 measurements/udp_latency_client.py '
                f'--dest 10.0.0.100 --port {latency_port} '
                f'--duration {args.duration} --interval {latency_interval} '
                f'--log {result_dir}/emergency_latency_{timestamp}.log',
                f'logs/emergency_latency_run_{results_tag}_{timestamp}.log',
            ),
            (
                f'python3 measurements/tcp_latency_client.py '
                f'--dest 10.0.0.100 --port {background_latency_port} '
                f'--duration {args.duration} --interval {latency_interval} '
                f'--log {result_dir}/background_latency_{timestamp}.log',
                f'logs/background_latency_run_{results_tag}_{timestamp}.log',
            ),
            (
                f'iperf -u -c 10.0.0.100 -p {emergency_port} -b {os.environ.get("EMERGENCY_RATE", "10m")} '
                f'-t {args.duration} -i 1 | tee {result_dir}/jitter_{timestamp}.log',
                f'logs/jitter_run_{results_tag}_{timestamp}.log',
            ),
            (
                f'iperf -c 10.0.0.100 -p {best_effort_port} -t {args.duration} -i 5 '
                f'| tee {result_dir}/throughput_{timestamp}.log',
                f'logs/throughput_run_{results_tag}_{timestamp}.log',
            ),
        )
        for cmd, log_name in commands:
            proc, logf = _popen_in_node(sta1, cmd, log_name)
            run_processes.append((proc, logf))

        for proc, logf in run_processes:
            proc.wait()
            if logf:
                logf.close()

        for proc, logf in background_processes:
            proc.wait()
            if logf:
                logf.close()

        for _proc, logf in server_processes:
            if logf:
                logf.close()

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
