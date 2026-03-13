#!/bin/bash
# jitter.sh
# Measure jitter via iperf UDP output.

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <destination-ip>"
    exit 1
fi

dst=$1
scenario=${2:-baseline}

mkdir -p results/$scenario
iperf -u -c $dst -p 5001 -b 1m -t 60 -i 1 | tee results/$scenario/jitter_$(date +%s).log
