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
import os

from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.node import OVSKernelSwitch, RemoteController
from mn_wifi.net import Mininet_wifi
from mn_wifi.node import OVSKernelAP, Station
from mininet.link import TCLink


def build_network():
    net = Mininet_wifi(controller=None, accessPoint=OVSKernelAP,
                       switch=OVSKernelSwitch)

    info('*** Adding controller\n')
    ryu_ip = os.environ.get('RYU_IP', '127.0.0.1')
    ryu_port = int(os.environ.get('RYU_PORT', '6653'))
    c0 = net.addController('c0', controller=RemoteController,
                           ip=ryu_ip, port=ryu_port)

    info('*** Adding stations\n')
    sta1 = net.addStation('sta1', ip='10.0.0.1/8', position='20,30,0', range=50)
    sta2 = net.addStation('sta2', ip='10.0.0.2/8', position='25,35,0', range=50)
    sta3 = net.addStation('sta3', ip='10.0.0.3/8', position='25,25,0', range=50)
    sta4 = net.addStation('sta4', ip='10.0.0.4/8', position='35,30,0', range=50)

    info('*** Adding access points\n')
    ap1 = net.addAccessPoint('ap1', ssid='rsuA', mode='g', channel='1',
                             position='30,30,0', protocols='OpenFlow13', range=50)
    ap2 = net.addAccessPoint('ap2', ssid='rsuB', mode='g', channel='6',
                             position='80,30,0', protocols='OpenFlow13', range=50)

    info('*** Adding switch and host\n')
    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    h1 = net.addHost('h1', ip='10.0.0.100/8')

    info('*** Configuring wifi nodes\n')
    net.configureNodes()

    info('*** Associating stations\n')
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap1)
    net.addLink(sta3, ap1)
    net.addLink(sta4, ap1)

    info('*** Creating wired links\n')
    net.addLink(ap1, s1, cls=TCLink)
    net.addLink(ap2, s1, cls=TCLink)
    net.addLink(h1, s1, cls=TCLink)

    info('*** Starting network\n')
    net.build()
    net.start()

    info('*** Setting mobility\n')
    net.startMobility(time=0)
    # sta1 moves from 20->90 between 10s and 40s on x-axis
    net.mobility(sta1, 'start', time=10, position='20,30,0')
    net.mobility(sta1, 'stop', time=40, position='90,30,0')
    net.stopMobility(time=50)

    return net


def run_cli(net, cli_script=None):
    info('*** Running CLI\n')
    if os.environ.get('DISPLAY'):
        net.plotGraph(max_x=100, max_y=100)
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
