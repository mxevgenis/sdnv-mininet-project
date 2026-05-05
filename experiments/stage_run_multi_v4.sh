#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [ -f "${SCRIPT_DIR}/params_stage_v4.env" ]; then
  set -a
  . "${SCRIPT_DIR}/params_stage_v4.env"
  set +a
fi

VEHICLES=${SDNV_NUM_VEHICLES:-5}
AREA=${SDNV_AREA_SIZE:-1000}
SPEED=${SDNV_SPEED_KMH:-60}
DURATION=${SDNV_DURATION:-60}
RUNS=${RUNS:-5}
RUN_EMAPT=${RUN_EMAPT:-1}
STAGES=${SDNV_STAGE_TARGETS:-20,40,60,80}

echo "Stage run v4: vehicles=${VEHICLES}, stages=${STAGES}, runs=${RUNS}"
echo "Emergency rate: ${EMERGENCY_RATE:-10m}, helper total cap: ${SDNV_HELPER_TOTAL_MBIT:-12.5} Mbit"
echo "Emergency priority ports: ${SDNV_EMERGENCY_PRIORITY_PORTS:-5001,5003,6000}"

for stage in $(echo "${STAGES}" | tr ',' ' '); do
  for i in $(seq 1 ${RUNS}); do
    tag="v4_v${VEHICLES}_p${stage}_r${i}"
    echo ""
    echo "=== Stage ${stage}% UDP target (run ${i}/${RUNS}) ==="

    python3 experiments/auto_run_v4.py \
      --scenario baseline \
      --results-tag "baseline_${tag}" \
      --num-vehicles "${VEHICLES}" \
      --area-size "${AREA}" \
      --speed-kmh "${SPEED}" \
      --duration "${DURATION}" \
      --stage "${stage}"

    python3 experiments/auto_run_v4.py \
      --scenario sdnv \
      --results-tag "sdnv_${tag}" \
      --num-vehicles "${VEHICLES}" \
      --area-size "${AREA}" \
      --speed-kmh "${SPEED}" \
      --duration "${DURATION}" \
      --stage "${stage}"

    if [ "${RUN_EMAPT}" -eq 1 ]; then
      python3 experiments/emapt_run_v4.py \
        --scenario baseline \
        --results-tag "emapt_baseline_${tag}" \
        --num-vehicles "${VEHICLES}" \
        --area-size "${AREA}" \
        --speed-kmh "${SPEED}" \
        --stage "${stage}"

      python3 experiments/emapt_run_v4.py \
        --scenario sdnv \
        --results-tag "emapt_sdnv_${tag}" \
        --num-vehicles "${VEHICLES}" \
        --area-size "${AREA}" \
        --speed-kmh "${SPEED}" \
        --stage "${stage}"
    fi
  done
done

echo "Stage run v4 completed."
