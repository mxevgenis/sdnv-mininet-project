#!/bin/bash
# latency.sh
# Measure round-trip latency from sta1 to h1 using ping.

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <destination-ip>"
    exit 1
fi

dst=$1
scenario=${2:-baseline}

mkdir -p results/$scenario
ping -c 20 $dst | tee results/$scenario/latency_$(date +%s).log
