#!/bin/bash
# background_policy.sh
# Apply a flat cap to background senders so the total offered load remains fixed.

set -e

rate=${1:-}
intf=${2:-}

if [ -z "$rate" ]; then
    echo "Usage: $0 <rate> [interface]"
    exit 1
fi

if [ -z "$intf" ]; then
    intf=$(ip -o link show | awk -F': ' '/wlan/ {print $2; exit}')
fi
if [ -z "$intf" ]; then
    echo "[background_policy] could not determine wireless interface; pass it explicitly."
    exit 1
fi

use_fq_codel=${SDNV_USE_FQ_CODEL:-0}

sudo tc qdisc del dev "$intf" root 2>/dev/null || true
sudo tc qdisc add dev "$intf" root handle 1: htb default 10
sudo tc class add dev "$intf" parent 1: classid 1:10 htb rate "$rate" ceil "$rate"

if [ "$use_fq_codel" = "1" ]; then
    sudo tc qdisc add dev "$intf" parent 1:10 handle 110: fq_codel
fi

echo "[background_policy] flat sender cap applied at $rate."
