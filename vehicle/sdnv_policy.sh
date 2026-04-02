#!/bin/bash
# sdnv_policy.sh
# Configure local traffic control for the emergency SDV (sta1).
# - high-priority queue for UDP port 5001
# - HTB class for best-effort TCP

set -e

intf=${1:-}
if [ -z "$intf" ]; then
    intf=$(ip -o link show | awk -F': ' '/wlan/ {print $2; exit}')
fi
if [ -z "$intf" ]; then
    echo "[sdnv_policy] could not determine wireless interface; pass it explicitly."
    exit 1
fi

# clear existing qdisc
sudo tc qdisc del dev $intf root 2>/dev/null || true

# add root HTB qdisc
sudo tc qdisc add dev $intf root handle 1: htb default 20

# create classes: 10 for high-priority, 20 for best-effort
# rates/ceilings can be overridden via environment variables
hp_rate=${SDNV_HP_RATE:-15mbit}
hp_ceil=${SDNV_HP_CEIL:-40mbit}
be_rate=${SDNV_BE_RATE:-15mbit}
be_ceil=${SDNV_BE_CEIL:-40mbit}

sudo tc class add dev $intf parent 1: classid 1:10 htb rate $hp_rate ceil $hp_ceil
sudo tc class add dev $intf parent 1: classid 1:20 htb rate $be_rate ceil $be_ceil

# add filter for emergency UDP
sudo tc filter add dev $intf protocol ip parent 1:0 prio 1 u32 \
    match ip protocol 17 0xff \
    match ip dport 5001 0xffff \
    flowid 1:10

# best-effort (all other traffic) uses default class

echo "[sdnv_policy] HTB qdisc configured with priority for UDP/5001."
echo "[sdnv_policy] HP rate/ceil: $hp_rate/$hp_ceil, BE rate/ceil: $be_rate/$be_ceil"
