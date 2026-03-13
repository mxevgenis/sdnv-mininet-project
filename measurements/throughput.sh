#!/bin/bash
# throughput.sh
# Measure TCP throughput between sta1 and h1.

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <destination-ip>"
    exit 1
fi

dst=$1
scenario=${2:-baseline}

mkdir -p results/$scenario
iperf -c $dst -p 5002 -t 60 -i 5 | tee results/$scenario/throughput_$(date +%s).log
