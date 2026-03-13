#!/bin/bash
# run_sdnv.sh
# Automate one experiment run in SDNV mode (vehicle policies enabled).

set -e

mode=${1:-interactive}

if [ "$mode" = "auto" ]; then
    echo "[run_sdnv] running automated SDNV experiment..."
    sudo python3 experiments/auto_run.py --scenario sdnv
    exit $?
fi

echo "[run_sdnv] starting Ryu controller..."
ryu-manager controller/sdnv_controller.py &> logs/controller_sdnv.log &
CTRL_PID=$!
sleep 2

echo "[run_sdnv] launching topology (you may need sudo)"
sudo python3 topology/sdnv_topology.py &
NET_PID=$!

echo "[run_sdnv] topology process PID is $NET_PID"
echo "[run_sdnv] logs available under logs/"
echo "[run_sdnv] press Ctrl-C to stop everything when done."

wait $NET_PID || true
kill $CTRL_PID || true
