#!/bin/bash
# congestion_flows.sh
# Kick off TCP flows from sta2, sta3, sta4 to h1 to create congestion.
# Usage: congestion_flows.sh <destination-ip>

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <destination-ip>"
    exit 1
fi

dst=$1

for sta in sta2 sta3 sta4; do
    echo "Starting congestion flow from $sta to $dst"
    # assume script is run in Mininet CLI so hosts can be referenced by name
    $sta iperf -c $dst -p 5002 -t 60 -i 5 > /tmp/${sta}_congestion.log 2>&1 &
done
