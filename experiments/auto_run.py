#!/usr/bin/env python3
"""
Automated SDNV experiment runner (headless-friendly).
Starts controller, builds topology, runs policies and traffic,
collects measurements, and shuts everything down.
"""

import argparse
import os
import signal
import subprocess
import time

from mininet.log import setLogLevel, info

import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import topology.sdnv_topology as sdnv_topology


def _start_controller(log_path, ryu_ip, ryu_port):
    log_file = open(log_path, 'w')
    proc = subprocess.Popen(
        ['ryu-manager',
         '--ofp-listen-host', ryu_ip,
         '--ofp-tcp-listen-port', str(ryu_port),
         'controller/sdnv_controller.py'],
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


def main():
    parser = argparse.ArgumentParser(description='Automated SDNV experiment runner')
    parser.add_argument('--scenario', choices=['baseline', 'sdnv'], default='baseline')
    parser.add_argument('--results-tag', default=None,
                        help='Optional tag for results/logs (defaults to scenario)')
    parser.add_argument('--duration', type=int, default=60,
                        help='iperf duration in seconds for traffic flows')
    parser.add_argument('--num-vehicles', type=int, default=None,
                        help='Number of vehicle stations (default from SDNV_NUM_VEHICLES)')
    parser.add_argument('--area-size', type=float, default=None,
                        help='Area size (square) in the topology coordinate system')
    parser.add_argument('--speed-kmh', type=float, default=None,
                        help='Fix sta1 mobility speed in km/h (optional)')
    parser.add_argument('--ryu-ip', default='127.0.0.1')
    parser.add_argument('--ryu-port', type=int, default=6653)
    args = parser.parse_args()

    results_tag = args.results_tag or args.scenario
    os.makedirs('logs', exist_ok=True)
    os.makedirs(f"results/{results_tag}", exist_ok=True)
    timestamp = int(time.time())

    info('*** starting controller\n')
    ctrl_log = f"logs/controller_{results_tag}_{timestamp}.log"
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

    def popen_in_node(node, cmd, log_path=None):
        if log_path:
            log_file = open(log_path, 'w')
            proc = node.popen(cmd, shell=True, stdout=log_file, stderr=subprocess.STDOUT)
            return proc, log_file
        proc = node.popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc, None

    try:
        info('*** waiting for stations to associate\n')
        try:
            net.waitConnected()
        except Exception:
            pass
        info('*** starting iperf servers on h1\n')
        udp_srv, udp_log = popen_in_node(
            h1,
            "iperf -s -u -p 5001",
            f"logs/iperf_udp_server_{results_tag}_{timestamp}.log",
        )
        tcp_srv, tcp_log = popen_in_node(
            h1,
            "iperf -s -p 5002",
            f"logs/iperf_tcp_server_{results_tag}_{timestamp}.log",
        )
        time.sleep(1)

        info('*** quick connectivity check (sta1 -> h1)\n')
        ping_proc, ping_log = popen_in_node(
            sta1,
            "ping -c 3 10.0.0.100",
            f"logs/ping_{results_tag}_{timestamp}.log",
        )
        ping_proc.wait()
        if ping_log:
            ping_log.close()

        if args.scenario == 'sdnv':
            info('*** applying SDNV policy on sta1\n')
            policy_log = f"logs/policy_timing_{results_tag}_{timestamp}.log"
            policy_start = time.time()
            proc, logf = popen_in_node(sta1, 'bash vehicle/sdnv_policy.sh')
            proc.wait()
            policy_end = time.time()
            with open(policy_log, 'w') as f:
                f.write(f"policy_start_epoch={policy_start:.6f}\n")
                f.write(f"policy_end_epoch={policy_end:.6f}\n")
                f.write(f"policy_reaction_s={policy_end - policy_start:.6f}\n")
        else:
            info('*** applying baseline policy on sta1\n')
            proc, logf = popen_in_node(sta1, 'bash vehicle/baseline_policy.sh')
            proc.wait()

        info('*** starting congestion flows (all stations except sta1 -> h1)\n')
        for sta in other_stations:
            popen_in_node(
                sta,
                f"iperf -c 10.0.0.100 -p 5002 -t {args.duration} -i 5",
                f"logs/{sta.name}_congestion_{results_tag}_{timestamp}.log",
            )

        info('*** measuring latency, jitter, and throughput from sta1\n')
        for cmd, log_name in (
            (f"bash measurements/latency.sh 10.0.0.100 {results_tag}",
             f"logs/latency_run_{results_tag}_{timestamp}.log"),
            (f"bash measurements/jitter.sh 10.0.0.100 {results_tag}",
             f"logs/jitter_run_{results_tag}_{timestamp}.log"),
            (f"bash measurements/throughput.sh 10.0.0.100 {results_tag}",
             f"logs/throughput_run_{results_tag}_{timestamp}.log"),
        ):
            proc, logf = popen_in_node(sta1, cmd, log_name)
            proc.wait()
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
