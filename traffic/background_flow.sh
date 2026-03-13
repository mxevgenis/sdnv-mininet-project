#!/bin/bash
# background_flow.sh
# Generate best-effort TCP traffic from a vehicle to h1 port 5002

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <destination-ip>"
    exit 1
fi

dst=$1

echo "Starting background TCP flow to $dst:5002"
iperf -c $dst -p 5002 -t 60 -i 5
