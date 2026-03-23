#!/bin/bash
# emergency_flow.sh
# Generate UDP traffic from sta1 to h1 port 5001

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <destination-ip>"
    exit 1
fi

dst=$1
rate=${EMERGENCY_RATE:-10m}

echo "Starting emergency UDP flow to $dst:5001"
iperf -u -c $dst -p 5001 -b $rate -t 60 -i 5
