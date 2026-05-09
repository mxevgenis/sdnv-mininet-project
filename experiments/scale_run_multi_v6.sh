#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [ -f "${SCRIPT_DIR}/params_scale_v6.env" ]; then
  set -a
  . "${SCRIPT_DIR}/params_scale_v6.env"
  set +a
fi

COUNTS=${SDNV_COUNTS:-5,10,15,20}
AREA=${SDNV_AREA_SIZE:-1000}
SPEED=${SDNV_SPEED_KMH:-60}
DURATION=${SDNV_DURATION:-60}
RUNS=${RUNS:-5}
RUN_EMAPT=${RUN_EMAPT:-1}

echo "Scale run v6: vehicles=${COUNTS}, runs=${RUNS}"
echo "Traffic model: emergency UDP ${EMERGENCY_RATE:-10m}, helper UDP total ${SDNV_V6_HELPER_UDP_TOTAL_MBIT:-10} Mbit, helper TCP offered total ${SDNV_V6_HELPER_TCP_TOTAL_MBIT:-80} Mbit"
echo "SDNV helper TCP cap total after trigger: ${SDNV_V6_HELPER_TCP_LIMIT_TOTAL_MBIT:-10} Mbit"

IFS=',' read -r -a COUNT_ARRAY <<< "${COUNTS}"
for n in "${COUNT_ARRAY[@]}"; do
  n=$(echo "${n}" | xargs)
  [ -n "${n}" ] || continue
  for i in $(seq 1 "${RUNS}"); do
    tag="v6_scale_v${n}_r${i}"
    echo ""
    echo "=== Vehicles: ${n} (run ${i}/${RUNS}) ==="

    python3 experiments/auto_run_v6.py \
      --scenario baseline \
      --results-tag "baseline_${tag}" \
      --num-vehicles "${n}" \
      --area-size "${AREA}" \
      --speed-kmh "${SPEED}" \
      --duration "${DURATION}"

    python3 experiments/auto_run_v6.py \
      --scenario sdnv \
      --results-tag "sdnv_${tag}" \
      --num-vehicles "${n}" \
      --area-size "${AREA}" \
      --speed-kmh "${SPEED}" \
      --duration "${DURATION}"

    if [ "${RUN_EMAPT}" -eq 1 ]; then
      python3 experiments/emapt_run_v6.py \
        --scenario baseline \
        --results-tag "emapt_baseline_${tag}" \
        --num-vehicles "${n}" \
        --area-size "${AREA}" \
        --speed-kmh "${SPEED}"

      python3 experiments/emapt_run_v6.py \
        --scenario sdnv \
        --results-tag "emapt_sdnv_${tag}" \
        --num-vehicles "${n}" \
        --area-size "${AREA}" \
        --speed-kmh "${SPEED}"
    fi
  done
done

echo "Scale run v6 completed."
