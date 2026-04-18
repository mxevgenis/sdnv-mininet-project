#!/usr/bin/env python3
"""
Simple Mininet-WiFi topology for the SDNV experiment.

Stations:
  sta1..sta4
APs:
  ap1 (RSU A) at (30,30)
  ap2 (RSU B) at (80,30)
Switch: s1 connects the two APs and the host
Host: h1 acts as edge/cloud service
Controller: external Ryu controller (c0)

Mobility: sta1 moves from (20,30) to (90,30) between 10s and 40s
"""

import argparse
import math
import os

from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.node import OVSKernelSwitch, RemoteController
from mn_wifi.net import Mininet_wifi
from mn_wifi.node import OVSKernelAP, Station
from mininet.link import TCLink


def _env_int(key, default):
    val = os.environ.get(key)
    if val is None or val == '':
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _env_float(key, default):
    val = os.environ.get(key)
    if val is None or val == '':
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _env_bool(key, default=False):
    val = os.environ.get(key)
    if val is None or val == '':
        return default
    return str(val).strip().lower() in ('1', 'true', 'yes', 'on')


def _grid_positions(count, center, spacing, area_size):
    if count <= 0:
        return []
    cols = int(math.ceil(math.sqrt(count)))
    rows = int(math.ceil(count / cols))
    start_x = center[0] - (cols - 1) * spacing / 2.0
    start_y = center[1] - (rows - 1) * spacing / 2.0
    positions = []
    for idx in range(count):
        r = idx // cols
        c = idx % cols
        x = start_x + c * spacing
        y = start_y + r * spacing
        x = min(max(0.0, x), area_size)
        y = min(max(0.0, y), area_size)
        positions.append((x, y))
    return positions


def _positions_around_centers(count, centers, spacing, area_size):
    if not centers:
        return []
    if len(centers) == 1:
        return _grid_positions(count, centers[0], spacing, area_size)

    positions = []
    base = count // len(centers)
    remainder = count % len(centers)
    for idx, center in enumerate(centers):
        local_count = base + (1 if idx < remainder else 0)
        positions.extend(_grid_positions(local_count, center, spacing, area_size))
    return positions


def build_network(num_vehicles=None, area_size=None, wifi_mode=None,
                  speed_kmh=None, mobility_start=None, mobility_stop=None):
    net = Mininet_wifi(controller=None, accessPoint=OVSKernelAP,
                       switch=OVSKernelSwitch)

    # Defaults preserve the original 4-station, 100x100 setup.
    area_size = area_size or _env_float('SDNV_AREA_SIZE', 100.0)
    num_vehicles = num_vehicles or _env_int('SDNV_NUM_VEHICLES', 4)
    wifi_mode = wifi_mode or os.environ.get('SDNV_WIFI_MODE', 'g')
    speed_kmh = speed_kmh if speed_kmh is not None else _env_float('SDNV_SPEED_KMH', None)
    mobility_start = mobility_start if mobility_start is not None else _env_float('SDNV_MOBILITY_START', 10.0)
    mobility_stop = mobility_stop if mobility_stop is not None else _env_float('SDNV_MOBILITY_STOP', None)

    num_vehicles = max(1, int(num_vehicles))

    range_scale = area_size / 100.0
    sta_range = _env_float('SDNV_STA_RANGE', 50.0 * range_scale)
    ap_range = _env_float('SDNV_AP_RANGE', 50.0 * range_scale)
    spacing = _env_float('SDNV_STA_SPACING', 5.0 * range_scale)
    use_both_aps = _env_bool('SDNV_USE_BOTH_APS', False)
    auto_association = _env_bool('SDNV_AUTO_ASSOCIATION', False)

    info('*** Adding controller\n')
    ryu_ip = os.environ.get('RYU_IP', '127.0.0.1')
    ryu_port = int(os.environ.get('RYU_PORT', '6653'))
    class NoCheckRemoteController(RemoteController):
        def checkListening(self):
            return

    c0 = net.addController('c0', controller=NoCheckRemoteController,
                           ip=ryu_ip, port=ryu_port)

    info('*** Adding stations\n')
    ap1_center = (0.30 * area_size, 0.30 * area_size)
    ap2_center = (0.80 * area_size, 0.30 * area_size)
    sta1_start = (0.20 * area_size, 0.30 * area_size)
    sta1_stop = (0.90 * area_size, 0.30 * area_size)
    station_positions = {'sta1': sta1_start}

    sta1 = net.addStation('sta1', ip='10.0.0.1/8',
                          position=f"{sta1_start[0]:.3f},{sta1_start[1]:.3f},0",
                          range=sta_range)

    extra_centers = [ap1_center, ap2_center] if use_both_aps else [ap1_center]
    extra_positions = _positions_around_centers(num_vehicles - 1, extra_centers, spacing, area_size)
    for idx, (x, y) in enumerate(extra_positions, start=2):
        station_positions[f"sta{idx}"] = (x, y)
        net.addStation(
            f"sta{idx}",
            ip=f"10.0.0.{idx}/8",
            position=f"{x:.3f},{y:.3f},0",
            range=sta_range,
        )

    info('*** Adding access points\n')
    ap1 = net.addAccessPoint('ap1', ssid='rsuA', mode=wifi_mode, channel='1',
                             position=f"{ap1_center[0]:.3f},{ap1_center[1]:.3f},0",
                             protocols='OpenFlow13', range=ap_range)
    ap2 = net.addAccessPoint('ap2', ssid='rsuB', mode=wifi_mode, channel='6',
                             position=f"{ap2_center[0]:.3f},{ap2_center[1]:.3f},0",
                             protocols='OpenFlow13', range=ap_range)

    info('*** Adding switch and host\n')
    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    h1 = net.addHost('h1', ip='10.0.0.100/8')

    info('*** Configuring wifi nodes\n')
    net.configureNodes()

    info('*** Associating stations\n')
    stations = sorted(net.stations, key=lambda s: s.name)
    if auto_association:
        info('*** auto association enabled; Mininet-WiFi will associate stations to the strongest AP\n')
    else:
        for sta in stations:
            ap_target = ap1
            if use_both_aps:
                x, y = station_positions.get(sta.name, ap1_center)
                dist_ap1 = math.hypot(x - ap1_center[0], y - ap1_center[1])
                dist_ap2 = math.hypot(x - ap2_center[0], y - ap2_center[1])
                ap_target = ap1 if dist_ap1 <= dist_ap2 else ap2
            net.addLink(sta, ap_target)

    info('*** Creating wired links\n')
    net.addLink(ap1, s1, cls=TCLink)
    net.addLink(ap2, s1, cls=TCLink)
    net.addLink(h1, s1, cls=TCLink)

    info('*** Starting network\n')
    net.build()
    net.start()

    info('*** Setting mobility\n')
    net.startMobility(time=0)
    # sta1 moves across the x-axis; speed can be fixed via SDNV_SPEED_KMH.
    if mobility_stop is None:
        if speed_kmh:
            speed_mps = (speed_kmh * 1000.0) / 3600.0
            distance = math.hypot(sta1_stop[0] - sta1_start[0],
                                  sta1_stop[1] - sta1_start[1])
            duration = distance / speed_mps if speed_mps > 0 else 30.0
            mobility_stop = mobility_start + duration
        else:
            mobility_stop = 40.0

    net.mobility(sta1, 'start', time=mobility_start,
                 position=f"{sta1_start[0]:.3f},{sta1_start[1]:.3f},0")
    net.mobility(sta1, 'stop', time=mobility_stop,
                 position=f"{sta1_stop[0]:.3f},{sta1_stop[1]:.3f},0")
    net.stopMobility(time=mobility_stop + 10.0)

    return net


def run_cli(net, cli_script=None):
    info('*** Running CLI\n')
    if os.environ.get('DISPLAY'):
        max_area = _env_float('SDNV_AREA_SIZE', 100.0)
        net.plotGraph(max_x=max_area, max_y=max_area)
        net.startTerms()
    else:
        info('*** DISPLAY not set; skipping plotGraph/startTerms\n')
    if cli_script:
        CLI(net, script=cli_script)
    else:
        CLI(net)

    info('*** Stopping network\n')
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    parser = argparse.ArgumentParser(description='SDNV Mininet-WiFi topology')
    parser.add_argument('--cli-script', default=None,
                        help='Optional Mininet CLI script to execute')
    parser.add_argument('--no-cli', action='store_true',
                        help='Build the network without entering the CLI')
    args = parser.parse_args()

    net = build_network()
    if args.no_cli:
        info('*** no-cli selected; stopping network\n')
        net.stop()
    else:
        run_cli(net, cli_script=args.cli_script)
