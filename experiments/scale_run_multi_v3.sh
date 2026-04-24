#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [ -f "${SCRIPT_DIR}/params_scale_v3.env" ]; then
  set -a
  . "${SCRIPT_DIR}/params_scale_v3.env"
  set +a
fi

START=${SDNV_START:-2}
STEP=${SDNV_STEP:-2}
END=${SDNV_END:-10}
AREA=${SDNV_AREA_SIZE:-1000}
SPEED=${SDNV_SPEED_KMH:-60}
DURATION=${SDNV_DURATION:-60}
RUNS=${RUNS:-5}
RUN_EMAPT=${RUN_EMAPT:-1}

echo "Scale run v3: vehicles ${START}..${END} step ${STEP}, runs=${RUNS}"
echo "Common budget: ${SDNV_TOTAL_RATE:-unlimited}, external BG total: ${SDNV_BG_TOTAL_MBIT:-20} Mbit"
echo "SDNV post-trigger classes: HP ${SDNV_HP_RATE:-n/a}/${SDNV_HP_CEIL:-n/a}, BE ${SDNV_BE_RATE:-n/a}/${SDNV_BE_CEIL:-n/a}"
echo "Priority ports: ${SDNV_PRIORITY_PORTS:-5001}"

for n in $(seq ${START} ${STEP} ${END}); do
  for i in $(seq 1 ${RUNS}); do
    tag="v3_scale_v${n}_r${i}"
    echo ""
    echo "=== Vehicles: ${n} (run ${i}/${RUNS}) ==="

    python3 experiments/auto_run_v3.py \
      --scenario baseline \
      --results-tag "baseline_${tag}" \
      --num-vehicles "${n}" \
      --area-size "${AREA}" \
      --speed-kmh "${SPEED}" \
      --duration "${DURATION}"

    python3 experiments/auto_run_v3.py \
      --scenario sdnv \
      --results-tag "sdnv_${tag}" \
      --num-vehicles "${n}" \
      --area-size "${AREA}" \
      --speed-kmh "${SPEED}" \
      --duration "${DURATION}"

    if [ "${RUN_EMAPT}" -eq 1 ]; then
      python3 experiments/emapt_run_v3.py \
        --scenario baseline \
        --results-tag "emapt_baseline_${tag}" \
        --num-vehicles "${n}" \
        --area-size "${AREA}" \
        --speed-kmh "${SPEED}"

      python3 experiments/emapt_run_v3.py \
        --scenario sdnv \
        --results-tag "emapt_sdnv_${tag}" \
        --num-vehicles "${n}" \
        --area-size "${AREA}" \
        --speed-kmh "${SPEED}"
    fi
  done
done

echo "Scale run v3 completed."
