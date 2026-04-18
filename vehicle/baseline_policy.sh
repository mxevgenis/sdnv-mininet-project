#!/bin/bash
# baseline_policy.sh
# No shaping: vehicle behaves as a normal host
# This script should be executed on sta1 when running the baseline scenario.

set -e

intf=${1:-}
if [ -z "$intf" ]; then
    intf=$(ip -o link show | awk -F': ' '/wlan/ {print $2; exit}')
fi
if [ -z "$intf" ]; then
    echo "[baseline_policy] could not determine wireless interface; pass it explicitly."
    exit 1
fi

# remove any existing qdiscs
sudo tc qdisc del dev "$intf" root 2>/dev/null || true

flat_shaping=${BASELINE_FLAT_SHAPING:-0}
total_rate=${SDNV_TOTAL_RATE:-40mbit}
total_ceil=${SDNV_TOTAL_CEIL:-$total_rate}
use_fq_codel=${SDNV_USE_FQ_CODEL:-0}

if [ "$flat_shaping" = "1" ]; then
    sudo tc qdisc add dev "$intf" root handle 1: htb default 10
    sudo tc class add dev "$intf" parent 1: classid 1:10 htb rate "$total_rate" ceil "$total_ceil"
    if [ "$use_fq_codel" = "1" ]; then
        sudo tc qdisc add dev "$intf" parent 1:10 handle 110: fq_codel
    fi
    echo "[baseline_policy] flat shaping enabled at $total_rate/$total_ceil."
else
    echo "[baseline_policy] no traffic control applied."
fi
