#!/usr/bin/env python3
"""
Cooperative staged ECM v4 experiment runner.

Scenario:
  - sta1 is the emergency vehicle
  - every other vehicle becomes a helper when ECM is activated
  - helpers always run background TCP
  - helpers start cooperative UDP after the emergency trigger
  - only SDNV enforces staged local HTB splits on helper nodes
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


def _int_env(key, default):
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return int(default)


def _parse_rate_mbit(value):
    text = str(value).strip().lower()
    if text.endswith('mbit'):
        return float(text[:-4])
    if text.endswith('m'):
        return float(text[:-1])
    if text.endswith('gbit'):
        return float(text[:-4]) * 1000.0
    if text.endswith('g'):
        return float(text[:-1]) * 1000.0
    if text.endswith('kbit'):
        return float(text[:-4]) / 1000.0
    if text.endswith('k'):
        return float(text[:-1]) / 1000.0
    return float(text)


def _rate_str(mbit):
    return f'{mbit:.3f}mbit'


def _popen_in_node(node, cmd, log_path=None):
    if log_path:
        log_file = open(log_path, 'w')
        proc = node.popen(cmd, shell=True, stdout=log_file, stderr=subprocess.STDOUT)
        return proc, log_file
    proc = node.popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc, None


def _stage_profile(stage_pct, helper_count):
    emergency_rate = _parse_rate_mbit(os.environ.get('EMERGENCY_RATE', '10m'))
    helper_total = _float_env('SDNV_HELPER_TOTAL_MBIT', 12.5)
    helper_udp_floor = _float_env('SDNV_HELPER_MIN_UDP_MBIT', 0.5)
    total_load = emergency_rate + helper_count * helper_total
    target_udp_total = total_load * (stage_pct / 100.0)
    helper_udp_total = max(helper_udp_floor * helper_count, target_udp_total - emergency_rate)
    helper_udp_each = min(helper_total, helper_udp_total / max(1, helper_count))
    helper_tcp_each = max(0.1, helper_total - helper_udp_each)
    achieved_udp_total = emergency_rate + helper_udp_each * helper_count
    achieved_pct = (
        achieved_udp_total / (achieved_udp_total + helper_tcp_each * helper_count) * 100.0
    )
    return {
        'stage_pct': stage_pct,
        'emergency_rate_mbit': emergency_rate,
        'helper_total_mbit': helper_total,
        'helper_udp_mbit': helper_udp_each,
        'helper_tcp_mbit': helper_tcp_each,
        'target_udp_pct': stage_pct,
        'configured_udp_pct': achieved_pct,
    }


def _write_stage_meta(path, profile, helper_count, helper_ports):
    with open(path, 'w') as f:
        f.write(f"stage_pct={profile['stage_pct']:.3f}\n")
        f.write(f"target_udp_pct={profile['target_udp_pct']:.3f}\n")
        f.write(f"configured_udp_pct={profile['configured_udp_pct']:.3f}\n")
        f.write(f"emergency_rate_mbit={profile['emergency_rate_mbit']:.3f}\n")
        f.write(f"helper_total_mbit={profile['helper_total_mbit']:.3f}\n")
        f.write(f"helper_udp_mbit={profile['helper_udp_mbit']:.3f}\n")
        f.write(f"helper_tcp_mbit={profile['helper_tcp_mbit']:.3f}\n")
        f.write(f"helper_count={helper_count}\n")
        f.write(f"helper_udp_ports={','.join(str(p) for p in helper_ports)}\n")


def _apply_emergency_policy(sta1):
    total = os.environ.get('SDNV_TOTAL_RATE', '40mbit')
    cmd = (
        f'SDNV_TOTAL_RATE={total} '
        f'SDNV_TOTAL_CEIL={os.environ.get("SDNV_TOTAL_CEIL", total)} '
        f'SDNV_HP_RATE={os.environ.get("SDNV_EMERGENCY_HP_RATE", total)} '
        f'SDNV_HP_CEIL={os.environ.get("SDNV_EMERGENCY_HP_CEIL", total)} '
        f'SDNV_BE_RATE={os.environ.get("SDNV_EMERGENCY_BE_RATE", "0.100mbit")} '
        f'SDNV_BE_CEIL={os.environ.get("SDNV_EMERGENCY_BE_CEIL", "0.100mbit")} '
        f'SDNV_PRIORITY_PORTS={os.environ.get("SDNV_EMERGENCY_PRIORITY_PORTS", "5001,5003,6000")} '
        f'SDNV_USE_FQ_CODEL={os.environ.get("SDNV_USE_FQ_CODEL", "1")} '
        'bash vehicle/sdnv_policy.sh'
    )
    proc, _ = _popen_in_node(sta1, cmd)
    proc.wait()


def _apply_helper_policy(helper, helper_udp_port, profile):
    total = _rate_str(profile['helper_total_mbit'])
    udp_rate = _rate_str(profile['helper_udp_mbit'])
    tcp_rate = _rate_str(profile['helper_tcp_mbit'])
    cmd = (
        f'SDNV_TOTAL_RATE={total} '
        f'SDNV_TOTAL_CEIL={total} '
        f'SDNV_HP_RATE={udp_rate} '
        f'SDNV_HP_CEIL={total} '
        f'SDNV_BE_RATE={tcp_rate} '
        f'SDNV_BE_CEIL={tcp_rate} '
        f'SDNV_PRIORITY_PORTS={helper_udp_port},6000 '
        f'SDNV_USE_FQ_CODEL={os.environ.get("SDNV_USE_FQ_CODEL", "1")} '
        'bash vehicle/sdnv_policy.sh'
    )
    proc, _ = _popen_in_node(helper, cmd)
    proc.wait()


def _apply_stage_policies(sta1, helpers, helper_ports, scenario, policy_log, profile):
    if scenario != 'sdnv':
        info('*** emergency trigger: baseline keeps flat helper policies\n')
        return

    info('*** emergency trigger: applying SDNV ECM policy on emergency and helper vehicles\n')
    policy_start = time.time()
    _apply_emergency_policy(sta1)
    for helper, port in zip(helpers, helper_ports):
        _apply_helper_policy(helper, port, profile)
    policy_end = time.time()
    with open(policy_log, 'w') as f:
        f.write(f'policy_start_epoch={policy_start:.6f}\n')
        f.write(f'policy_end_epoch={policy_end:.6f}\n')
        f.write(f'policy_reaction_s={policy_end - policy_start:.6f}\n')


def main():
    parser = argparse.ArgumentParser(description='Cooperative staged ECM v4 experiment runner')
    parser.add_argument('--scenario', choices=['baseline', 'sdnv'], default='baseline')
    parser.add_argument('--results-tag', default=None)
    parser.add_argument('--duration', type=int, default=60)
    parser.add_argument('--warmup', type=float, default=None)
    parser.add_argument('--num-vehicles', type=int, default=None)
    parser.add_argument('--area-size', type=float, default=None)
    parser.add_argument('--speed-kmh', type=float, default=None)
    parser.add_argument('--stage', type=int, required=True,
                        help='Target ECM stage as overall UDP percentage (e.g. 20,40,60,80)')
    parser.add_argument('--ryu-ip', default='127.0.0.1')
    parser.add_argument('--ryu-port', type=int, default=6653)
    args = parser.parse_args()

    results_tag = args.results_tag or f'{args.scenario}_stage{args.stage}'
    os.makedirs('logs', exist_ok=True)
    os.makedirs(f'results/{results_tag}', exist_ok=True)

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
    stage_meta = f'results/{results_tag}/stage_meta_{timestamp}.log'
    _write_stage_meta(stage_meta, profile, helper_count, helper_udp_ports)

    best_effort_port = int(os.environ.get('SDNV_BEST_EFFORT_PORT', '5002'))
    emergency_port = int(os.environ.get('SDNV_EMERGENCY_PORT', '5001'))
    latency_port = int(os.environ.get('SDNV_LATENCY_PORT', '5003'))
    latency_interval = _float_env('SDNV_LATENCY_INTERVAL', 0.2)

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
        helper_total_rate = _rate_str(profile['helper_total_mbit'])
        for helper in helpers:
            proc, _ = _popen_in_node(helper, f'bash vehicle/background_policy.sh {helper_total_rate}')
            proc.wait()

        result_dir = f'results/{results_tag}'

        if warmup > 0:
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
        _apply_stage_policies(sta1, helpers, helper_udp_ports, args.scenario, policy_log, profile)

        info('*** starting post-trigger helper TCP, emergency UDP, cooperative UDP, and emergency latency probe\n')
        run_processes = []

        for helper in helpers:
            proc, logf = _popen_in_node(
                helper,
                f'iperf -c 10.0.0.100 -p {best_effort_port} -t {args.duration} -i 5 '
                f'| tee {result_dir}/helper_tcp_{helper.name}_{timestamp}.log',
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
