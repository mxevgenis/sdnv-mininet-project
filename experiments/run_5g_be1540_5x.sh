#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [ -f "${SCRIPT_DIR}/params_base.env" ]; then
  set -a
  . "${SCRIPT_DIR}/params_base.env"
  set +a
fi

RUNS=${RUNS:-5}
EMERGENCY_RATE=${EMERGENCY_RATE:-10m}

SDNV_HP_RATE=${SDNV_HP_RATE:-15mbit}
SDNV_HP_CEIL=${SDNV_HP_CEIL:-40mbit}
SDNV_BE_RATE=${SDNV_BE_RATE:-15mbit}
SDNV_BE_CEIL=${SDNV_BE_CEIL:-40mbit}

export EMERGENCY_RATE SDNV_HP_RATE SDNV_HP_CEIL SDNV_BE_RATE SDNV_BE_CEIL

echo "5G BE 15/40 sweep: runs=${RUNS}, emergency=${EMERGENCY_RATE}"
echo "SDNV shaping: HP ${SDNV_HP_RATE}/${SDNV_HP_CEIL}, BE ${SDNV_BE_RATE}/${SDNV_BE_CEIL}"

for i in $(seq 1 "${RUNS}"); do
  echo ""
  echo "=== Run ${i}/${RUNS} ==="
  python3 experiments/auto_run.py --scenario baseline --results-tag "baseline_5g_be1540_r${i}"
  python3 experiments/auto_run.py --scenario sdnv --results-tag "sdnv_5g_be1540_r${i}"
  python3 experiments/emapt_run.py --scenario baseline --results-tag "emapt_baseline_5g_be1540_r${i}"
  python3 experiments/emapt_run.py --scenario sdnv --results-tag "emapt_sdnv_5g_be1540_r${i}"
done

echo "Runs complete."
