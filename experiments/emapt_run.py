#!/usr/bin/env python3
"""
Run EMAPT/coverage measurement for emergency broadcast.
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
        ['ryu-manager', '--ofp-listen-host', ryu_ip,
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=['baseline', 'sdnv'], default='sdnv')
    parser.add_argument('--results-tag', default='emapt')
    parser.add_argument('--num-vehicles', type=int, default=None,
                        help='Number of vehicle stations (default from SDNV_NUM_VEHICLES)')
    parser.add_argument('--area-size', type=float, default=None,
                        help='Area size (square) in the topology coordinate system')
    parser.add_argument('--speed-kmh', type=float, default=None,
                        help='Fix sta1 mobility speed in km/h (optional)')
    parser.add_argument('--ryu-ip', default='127.0.0.1')
    parser.add_argument('--ryu-port', type=int, default=6653)
    args = parser.parse_args()

    os.makedirs('logs', exist_ok=True)
    tag = args.results_tag
    timestamp = int(time.time())

    info('*** starting controller\n')
    ctrl_log = f"logs/controller_{tag}_{timestamp}.log"
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
    stations = sorted(net.stations, key=lambda s: s.name)
    recv_stations = [s for s in stations if s.name != 'sta1']

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

        if args.scenario == 'sdnv':
            info('*** applying SDNV policy on sta1\n')
            proc, _ = popen_in_node(sta1, 'bash vehicle/sdnv_policy.sh')
            proc.wait()

        base = f"logs/emapt_{tag}_{timestamp}"

        # start receivers on all stations except sta1
        rx_logs = []
        for sta in recv_stations:
            log_path = f"{base}_rx_{sta.name}.log"
            cmd = f"python3 measurements/emapt_receiver.py --port 6000 --log {log_path}"
            proc, logf = popen_in_node(sta, cmd)
            rx_logs.append((proc, logf))

        time.sleep(1)

        # send broadcast from sta1
        tx_log = f"{base}_tx.log"
        dests = ",".join([sta.IP() for sta in recv_stations])
        cmd = ("python3 measurements/emapt_sender.py "
               f"--dests {dests} "
               f"--port 6000 --log {tx_log}")
        proc, logf = popen_in_node(sta1, cmd)
        proc.wait()
        if logf:
            logf.close()

        # allow receivers to finish
        time.sleep(2)

        for proc, logf in rx_logs:
            if logf:
                logf.close()

        # analyze
        out_path = f"results/emapt_{tag}_{timestamp}.csv"
        analyze_cmd = (
            f"python3 measurements/emapt_analyze.py --logs {base} --out {out_path}"
        )
        subprocess.check_call(analyze_cmd, shell=True)

        # write/refresh coverage curve CSV for plotting
        if args.scenario in ('baseline', 'sdnv'):
            try:
                with open(out_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = [ln.strip() for ln in f.readlines()]
                header_idx = None
                for i, line in enumerate(lines):
                    if line.startswith('coverage_curve_'):
                        header_idx = i
                        break
                if header_idx is not None:
                    header = lines[header_idx]
                    if header.startswith('coverage_curve_ms'):
                        out_header = 'time_ms,coverage'
                    elif header.startswith('coverage_curve_seconds'):
                        out_header = 'time_s,coverage'
                    else:
                        out_header = 'time_ms,coverage'
                    coverage_out = f"results/coverage_curve_{args.scenario}.csv"
                    with open(coverage_out, 'w') as f:
                        f.write(out_header + "\n")
                        for line in lines[header_idx + 1:]:
                            if not line:
                                continue
                            f.write(line + "\n")
            except Exception:
                pass

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
