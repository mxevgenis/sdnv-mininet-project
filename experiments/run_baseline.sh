#!/bin/bash
# run_baseline.sh
# Automate one experiment run in baseline mode.

set -e

mode=${1:-interactive}

if [ "$mode" = "auto" ]; then
    echo "[run_baseline] running automated baseline experiment..."
    sudo python3 experiments/auto_run.py --scenario baseline
    exit $?
fi

echo "[run_baseline] starting Ryu controller..."
ryu-manager controller/sdnv_controller.py &> logs/controller_baseline.log &
CTRL_PID=$!
sleep 2

echo "[run_baseline] launching topology (you may need sudo)"
sudo python3 topology/sdnv_topology.py &
NET_PID=$!

echo "[run_baseline] topology process PID is $NET_PID"
echo "[run_baseline] logs available under logs/"
echo "[run_baseline] press Ctrl-C to stop everything when done."

wait $NET_PID || true
kill $CTRL_PID || true
