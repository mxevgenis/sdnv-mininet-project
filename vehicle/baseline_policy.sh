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
sudo tc qdisc del dev $intf root 2>/dev/null || true

# nothing else to configure

echo "[baseline_policy] no traffic control applied."
