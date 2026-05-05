#!/usr/bin/env python3
"""Cooperative staged ECM v4 EMAPT runner."""

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
from experiments.auto_run_v4 import (
    _apply_emergency_policy,
    _apply_helper_policy,
    _float_env,
    _int_env,
    _popen_in_node,
    _rate_str,
    _stage_profile,
    _start_controller,
    _stop_controller,
    _write_stage_meta,
)


def _apply_stage_policies(sta1, helpers, helper_ports, scenario, profile):
    if scenario != 'sdnv':
        info('*** emergency trigger: baseline keeps flat helper policies for EMAPT\n')
        return
    info('*** emergency trigger: applying SDNV ECM policy for dissemination\n')
    _apply_emergency_policy(sta1)
    for helper, port in zip(helpers, helper_ports):
        _apply_helper_policy(helper, port, profile)


def main():
    parser = argparse.ArgumentParser(description='Cooperative staged ECM v4 EMAPT runner')
    parser.add_argument('--scenario', choices=['baseline', 'sdnv'], default='sdnv')
    parser.add_argument('--results-tag', default='emapt_v4')
    parser.add_argument('--stage', type=int, required=True,
                        help='Target ECM stage as overall UDP percentage (e.g. 20,40,60,80)')
    parser.add_argument('--num-vehicles', type=int, default=None)
    parser.add_argument('--area-size', type=float, default=None)
    parser.add_argument('--speed-kmh', type=float, default=None)
    parser.add_argument('--warmup', type=float, default=None)
    parser.add_argument('--ryu-ip', default='127.0.0.1')
    parser.add_argument('--ryu-port', type=int, default=6653)
    args = parser.parse_args()

    os.makedirs('logs', exist_ok=True)
    timestamp = int(time.time())
    warmup = args.warmup if args.warmup is not None else _float_env('SDNV_WARMUP', 10.0)
    num_vehicles = args.num_vehicles if args.num_vehicles is not None else _int_env('SDNV_NUM_VEHICLES', 5)
    helper_count = max(0, num_vehicles - 1)
    helper_udp_base = _int_env('SDNV_HELPER_UDP_PORT_BASE', 5100)
    helper_udp_ports = [helper_udp_base + idx for idx in range(helper_count)]
    helper_priority_ports = helper_udp_ports + [
        int(os.environ.get('SDNV_EMERGENCY_PORT', '5001')),
        int(os.environ.get('SDNV_LATENCY_PORT', '5003')),
        int(os.environ.get('SDNV_EMAPT_PORT', '6000')),
    ]
    os.environ['SDNV_PRIORITY_PORTS'] = ','.join(str(p) for p in helper_priority_ports)

    profile = _stage_profile(args.stage, helper_count)
    stage_meta = f'results/emapt_{args.results_tag}_{timestamp}_stage_meta.log'
    _write_stage_meta(stage_meta, profile, helper_count, helper_udp_ports)

    best_effort_port = int(os.environ.get('SDNV_BEST_EFFORT_PORT', '5002'))
    emapt_port = int(os.environ.get('SDNV_EMAPT_PORT', '6000'))
    emapt_duration = max(4, int(math.ceil(_float_env('SDNV_EMAPT_BG_DURATION', 10.0))))

    info('*** starting controller\n')
    ctrl_log = f'logs/controller_{args.results_tag}_{timestamp}.log'
    ctrl_proc, ctrl_log_file = _start_controller(ctrl_log, args.ryu_ip, args.ryu_port)
    time.sleep(2)

    info('*** building topology\n')
    os.environ['RYU_IP'] = args.ryu_ip
    os.environ['RYU_PORT'] = str(args.ryu_port)
    os.environ['SDNV_NUM_VEHICLES'] = str(num_vehicles)
    if args.area_size is not None:
        os.environ['SDNV_AREA_SIZE'] = str(args.area_size)
    if args.speed_kmh is not None:
        os.environ['SDNV_SPEED_KMH'] = str(args.speed_kmh)
    net = sdnv_topology.build_network()

    sta1 = net.get('sta1')
    h1 = net.get('h1')
    stations = sorted(net.stations, key=lambda s: s.name)
    helpers = [s for s in stations if s.name != 'sta1']

    try:
        info('*** waiting for stations to associate\n')
        try:
            net.waitConnected()
        except Exception:
            pass

        info('*** applying common pre-trigger policies\n')
        proc, _ = _popen_in_node(sta1, 'bash vehicle/baseline_policy.sh')
        proc.wait()
        helper_total_rate = _rate_str(profile['helper_total_mbit'])
        for helper in helpers:
            proc, _ = _popen_in_node(helper, f'bash vehicle/background_policy.sh {helper_total_rate}')
            proc.wait()

        info('*** starting servers on h1 for helper traffic\n')
        server_processes = []
        proc, logf = _popen_in_node(
            h1,
            f'iperf -s -p {best_effort_port}',
            f'logs/iperf_tcp_server_{args.results_tag}_{timestamp}.log',
        )
        server_processes.append((proc, logf))
        for idx, port in enumerate(helper_udp_ports, start=1):
            proc, logf = _popen_in_node(
                h1,
                f'iperf -s -u -p {port}',
                f'logs/iperf_udp_server_helper{idx}_{args.results_tag}_{timestamp}.log',
            )
            server_processes.append((proc, logf))

        background_duration = int(math.ceil(warmup + emapt_duration + 5))
        info('*** starting helper background TCP flows\n')
        bg_processes = []
        for helper in helpers:
            proc, logf = _popen_in_node(
                helper,
                f'iperf -c 10.0.0.100 -p {best_effort_port} -t {background_duration} -i 5',
                f'logs/{helper.name}_tcp_{args.results_tag}_{timestamp}.log',
            )
            bg_processes.append((proc, logf))

        base = f'logs/emapt_{args.results_tag}_{timestamp}'
        rx_logs = []
        for helper in helpers:
            log_path = f'{base}_rx_{helper.name}.log'
            proc, logf = _popen_in_node(
                helper,
                f'python3 measurements/emapt_receiver.py --port {emapt_port} --log {log_path}',
            )
            rx_logs.append((proc, logf))

        if warmup > 0:
            info(f'*** warm-up for {warmup:.1f}s before dissemination trigger\n')
            time.sleep(warmup)

        _apply_stage_policies(sta1, helpers, helper_udp_ports, args.scenario, profile)

        info('*** starting cooperative helper UDP flows and emergency dissemination\n')
        helper_udp_rate = _rate_str(profile['helper_udp_mbit'])
        helper_udp_processes = []
        for helper, port in zip(helpers, helper_udp_ports):
            proc, logf = _popen_in_node(
                helper,
                f'iperf -u -c 10.0.0.100 -p {port} -b {helper_udp_rate} -t {emapt_duration} -i 1',
                f'logs/{helper.name}_udp_{args.results_tag}_{timestamp}.log',
            )
            helper_udp_processes.append((proc, logf))

        tx_log = f'{base}_tx.log'
        dests = ','.join(helper.IP() for helper in helpers)
        proc, logf = _popen_in_node(
            sta1,
            f'python3 measurements/emapt_sender.py --dests {dests} --port {emapt_port} --log {tx_log}',
        )
        proc.wait()
        if logf:
            logf.close()

        for proc, logf in helper_udp_processes:
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
        for _proc, logf in server_processes:
            if logf:
                logf.close()

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
