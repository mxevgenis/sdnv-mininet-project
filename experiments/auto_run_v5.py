#!/usr/bin/env python3
"""
Cooperative fixed-load ECM v5 experiment runner.

Scenario:
  - sta1 is the emergency vehicle
  - every other vehicle becomes a helper when ECM is activated
  - all helpers send cooperative UDP and background TCP after the trigger
  - baseline keeps flat helper shaping, so TCP keeps competing with UDP
  - SDNV switches helpers to HTB classes that protect helper UDP and
    aggressively throttle helper TCP
"""

import argparse
import math
import os
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
    _parse_rate_mbit,
    _popen_in_node,
    _rate_str,
    _start_controller,
    _stop_controller,
)


def _preflight_cleanup():
    subprocess.call('mn -c >/dev/null 2>&1 || true', shell=True)


def _helper_profile(helper_count):
    emergency_rate = _parse_rate_mbit(os.environ.get('EMERGENCY_RATE', '10m'))
    helper_udp_total = _float_env('SDNV_V5_HELPER_UDP_TOTAL_MBIT', 10.0)
    helper_tcp_total = _float_env('SDNV_V5_HELPER_TCP_TOTAL_MBIT', 40.0)
    helper_tcp_limit_total = _float_env('SDNV_V5_HELPER_TCP_LIMIT_TOTAL_MBIT', 10.0)
    helper_udp_floor = _float_env('SDNV_V5_HELPER_MIN_UDP_MBIT', 0.25)
    helper_tcp_floor = _float_env('SDNV_V5_HELPER_MIN_TCP_MBIT', 0.25)

    safe_helpers = max(1, helper_count)
    helper_udp_each = max(helper_udp_floor, helper_udp_total / safe_helpers)
    helper_tcp_offer_each = max(helper_tcp_floor, helper_tcp_total / safe_helpers)
    helper_tcp_limit_each = min(
        helper_tcp_offer_each,
        max(helper_tcp_floor, helper_tcp_limit_total / safe_helpers),
    )
    helper_total_cap_each = helper_udp_each + helper_tcp_offer_each

    return {
        'emergency_rate_mbit': emergency_rate,
        'helper_count': helper_count,
        'helper_udp_total_mbit': helper_udp_total,
        'helper_tcp_total_mbit': helper_tcp_total,
        'helper_tcp_limit_total_mbit': helper_tcp_limit_total,
        'helper_udp_mbit': helper_udp_each,
        'helper_tcp_offer_mbit': helper_tcp_offer_each,
        'helper_tcp_limit_mbit': helper_tcp_limit_each,
        'helper_total_cap_mbit': helper_total_cap_each,
    }


def _write_profile_meta(path, profile, helper_ports):
    with open(path, 'w') as f:
        f.write(f"emergency_rate_mbit={profile['emergency_rate_mbit']:.3f}\n")
        f.write(f"helper_count={profile['helper_count']}\n")
        f.write(f"helper_udp_total_mbit={profile['helper_udp_total_mbit']:.3f}\n")
        f.write(f"helper_tcp_total_mbit={profile['helper_tcp_total_mbit']:.3f}\n")
        f.write(
            f"helper_tcp_limit_total_mbit={profile['helper_tcp_limit_total_mbit']:.3f}\n"
        )
        f.write(f"helper_udp_mbit={profile['helper_udp_mbit']:.3f}\n")
        f.write(f"helper_tcp_offer_mbit={profile['helper_tcp_offer_mbit']:.3f}\n")
        f.write(f"helper_tcp_limit_mbit={profile['helper_tcp_limit_mbit']:.3f}\n")
        f.write(f"helper_total_cap_mbit={profile['helper_total_cap_mbit']:.3f}\n")
        f.write(f"helper_udp_ports={','.join(str(p) for p in helper_ports)}\n")


def _apply_v5_policies(sta1, helpers, helper_ports, scenario, policy_log, profile):
    if scenario != 'sdnv':
        info('*** emergency trigger: baseline keeps flat helper policies\n')
        return

    info('*** emergency trigger: applying SDNV helper throttling and emergency policy\n')
    policy_start = time.time()
    _apply_emergency_policy(sta1)
    helper_udp_profile = {
        'helper_total_mbit': profile['helper_total_cap_mbit'],
        'helper_udp_mbit': profile['helper_udp_mbit'],
        'helper_tcp_mbit': profile['helper_tcp_limit_mbit'],
    }
    for helper, port in zip(helpers, helper_ports):
        _apply_helper_policy(helper, port, helper_udp_profile)
    policy_end = time.time()
    with open(policy_log, 'w') as f:
        f.write(f'policy_start_epoch={policy_start:.6f}\n')
        f.write(f'policy_end_epoch={policy_end:.6f}\n')
        f.write(f'policy_reaction_s={policy_end - policy_start:.6f}\n')


def main():
    parser = argparse.ArgumentParser(description='Cooperative fixed-load ECM v5 experiment runner')
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

    warmup = args.warmup if args.warmup is not None else _float_env('SDNV_WARMUP', 10.0)
    num_vehicles = args.num_vehicles if args.num_vehicles is not None else _int_env('SDNV_NUM_VEHICLES', 5)
    helper_count = max(0, num_vehicles - 1)
    results_tag = args.results_tag or f'{args.scenario}_v5_v{num_vehicles}'
    os.makedirs('logs', exist_ok=True)
    os.makedirs(f'results/{results_tag}', exist_ok=True)

    timestamp = int(time.time())
    helper_udp_base = _int_env('SDNV_HELPER_UDP_PORT_BASE', 5100)
    helper_udp_ports = [helper_udp_base + idx for idx in range(helper_count)]
    helper_priority_ports = helper_udp_ports + [
        int(os.environ.get('SDNV_EMERGENCY_PORT', '5001')),
        int(os.environ.get('SDNV_LATENCY_PORT', '5003')),
        int(os.environ.get('SDNV_EMAPT_PORT', '6000')),
    ]
    os.environ['SDNV_PRIORITY_PORTS'] = ','.join(str(p) for p in helper_priority_ports)

    profile = _helper_profile(helper_count)
    meta_path = f'results/{results_tag}/profile_meta_{timestamp}.log'
    _write_profile_meta(meta_path, profile, helper_udp_ports)

    best_effort_port = int(os.environ.get('SDNV_BEST_EFFORT_PORT', '5002'))
    emergency_port = int(os.environ.get('SDNV_EMERGENCY_PORT', '5001'))
    latency_port = int(os.environ.get('SDNV_LATENCY_PORT', '5003'))
    background_latency_port = int(os.environ.get('SDNV_BACKGROUND_LATENCY_PORT', '5004'))
    latency_interval = _float_env('SDNV_LATENCY_INTERVAL', 0.2)

    info('*** cleaning stale Mininet state\n')
    _preflight_cleanup()

    info('*** starting controller\n')
    ctrl_log = f'logs/controller_{results_tag}_{timestamp}.log'
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
    probe_helper = helpers[0] if helpers else sta1

    try:
        info('*** waiting for stations to associate\n')
        try:
            net.waitConnected()
        except Exception:
            pass

        info('*** starting servers on h1\n')
        server_processes = []
        for cmd, name in (
            (f'iperf -s -u -p {emergency_port}', 'iperf_udp_server_emergency'),
            (f'iperf -s -p {best_effort_port}', 'iperf_tcp_server'),
            (f'python3 measurements/udp_echo_server.py --port {latency_port}', 'udp_echo_server'),
            (
                f'python3 measurements/tcp_echo_server.py --port {background_latency_port}',
                'tcp_echo_server',
            ),
        ):
            proc, logf = _popen_in_node(h1, cmd, f'logs/{name}_{results_tag}_{timestamp}.log')
            server_processes.append((proc, logf))
        for idx, port in enumerate(helper_udp_ports, start=1):
            proc, logf = _popen_in_node(
                h1,
                f'iperf -s -u -p {port}',
                f'logs/iperf_udp_server_helper{idx}_{results_tag}_{timestamp}.log',
            )
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

        info('*** applying common pre-trigger policies\n')
        proc, _ = _popen_in_node(sta1, 'bash vehicle/baseline_policy.sh')
        proc.wait()
        helper_total_rate = _rate_str(profile['helper_total_cap_mbit'])
        for helper in helpers:
            proc, _ = _popen_in_node(helper, f'bash vehicle/background_policy.sh {helper_total_rate}')
            proc.wait()

        result_dir = f'results/{results_tag}'

        if warmup > 0 and helpers:
            info('*** starting helper warm-up TCP flows\n')
            warmup_processes = []
            warmup_duration = max(1, int(math.ceil(warmup)))
            for helper in helpers:
                proc, logf = _popen_in_node(
                    helper,
                    f'iperf -c 10.0.0.100 -p {best_effort_port} -t {warmup_duration} -i 1',
                    f'logs/{helper.name}_tcp_warmup_{results_tag}_{timestamp}.log',
                )
                warmup_processes.append((proc, logf))
            info(f'*** warm-up for {warmup:.1f}s before emergency trigger\n')
            time.sleep(warmup)
            for proc, logf in warmup_processes:
                proc.wait()
                if logf:
                    logf.close()

        policy_log = f'logs/policy_timing_{results_tag}_{timestamp}.log'
        _apply_v5_policies(sta1, helpers, helper_udp_ports, args.scenario, policy_log, profile)

        info('*** starting concurrent emergency/helper traffic and latency probes\n')
        run_processes = []

        for helper in helpers:
            proc, logf = _popen_in_node(
                helper,
                f'iperf -c 10.0.0.100 -p {best_effort_port} '
                f'-t {args.duration} -i 5 | tee {result_dir}/helper_tcp_{helper.name}_{timestamp}.log',
                f'logs/{helper.name}_tcp_{results_tag}_{timestamp}.log',
            )
            run_processes.append((proc, logf))

        proc, logf = _popen_in_node(
            sta1,
            f'python3 measurements/udp_latency_client.py '
            f'--dest 10.0.0.100 --port {latency_port} '
            f'--duration {args.duration} --interval {latency_interval} '
            f'--log {result_dir}/emergency_latency_{timestamp}.log',
            f'logs/emergency_latency_{results_tag}_{timestamp}.log',
        )
        run_processes.append((proc, logf))

        proc, logf = _popen_in_node(
            probe_helper,
            f'python3 measurements/tcp_latency_client.py '
            f'--dest 10.0.0.100 --port {background_latency_port} '
            f'--duration {args.duration} --interval {latency_interval} '
            f'--log {result_dir}/background_latency_{timestamp}.log',
            f'logs/background_latency_{results_tag}_{timestamp}.log',
        )
        run_processes.append((proc, logf))

        proc, logf = _popen_in_node(
            sta1,
            f'iperf -u -c 10.0.0.100 -p {emergency_port} -b {os.environ.get("EMERGENCY_RATE", "10m")} '
            f'-t {args.duration} -i 1 | tee {result_dir}/emergency_udp_{timestamp}.log',
            f'logs/emergency_udp_{results_tag}_{timestamp}.log',
        )
        run_processes.append((proc, logf))

        helper_udp_rate = _rate_str(profile['helper_udp_mbit'])
        for helper, port in zip(helpers, helper_udp_ports):
            proc, logf = _popen_in_node(
                helper,
                f'iperf -u -c 10.0.0.100 -p {port} -b {helper_udp_rate} -t {args.duration} -i 1 '
                f'| tee {result_dir}/helper_udp_{helper.name}_{timestamp}.log',
                f'logs/{helper.name}_udp_{results_tag}_{timestamp}.log',
            )
            run_processes.append((proc, logf))

        for proc, logf in run_processes:
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
