#!/bin/bash
set -euo pipefail

# Scale experiments across vehicle counts.
# Defaults target the scalability scenario: 1000x1000 area, 60 km/h.

START=${SDNV_START:-5}
STEP=${SDNV_STEP:-4}
END=${SDNV_END:-20}
AREA=${SDNV_AREA_SIZE:-1000}
SPEED=${SDNV_SPEED_KMH:-60}
DURATION=${SDNV_DURATION:-60}
EMERGENCY_RATE=${EMERGENCY_RATE:-10m}

# Default to tuned2 shaping unless overridden by environment.
SDNV_HP_RATE=${SDNV_HP_RATE:-15mbit}
SDNV_HP_CEIL=${SDNV_HP_CEIL:-40mbit}
SDNV_BE_RATE=${SDNV_BE_RATE:-15mbit}
SDNV_BE_CEIL=${SDNV_BE_CEIL:-40mbit}

export EMERGENCY_RATE SDNV_HP_RATE SDNV_HP_CEIL SDNV_BE_RATE SDNV_BE_CEIL

echo "Scale run: vehicles ${START}..${END} step ${STEP}"
echo "Area: ${AREA} x ${AREA}, speed: ${SPEED} km/h, duration: ${DURATION}s"
echo "Emergency rate: ${EMERGENCY_RATE}"
echo "SDNV shaping: HP ${SDNV_HP_RATE}/${SDNV_HP_CEIL}, BE ${SDNV_BE_RATE}/${SDNV_BE_CEIL}"

last=""
for n in $(seq ${START} ${STEP} ${END}); do
  last="${n}"
  tag="scale_v${n}"
  echo ""
  echo "=== Vehicles: ${n} ==="

  python3 experiments/auto_run.py \
    --scenario baseline \
    --results-tag "baseline_${tag}" \
    --num-vehicles "${n}" \
    --area-size "${AREA}" \
    --speed-kmh "${SPEED}" \
    --duration "${DURATION}"

  python3 experiments/auto_run.py \
    --scenario sdnv \
    --results-tag "sdnv_${tag}" \
    --num-vehicles "${n}" \
    --area-size "${AREA}" \
    --speed-kmh "${SPEED}" \
    --duration "${DURATION}"

  python3 experiments/emapt_run.py \
    --scenario baseline \
    --results-tag "emapt_baseline_${tag}" \
    --num-vehicles "${n}" \
    --area-size "${AREA}" \
    --speed-kmh "${SPEED}"

  python3 experiments/emapt_run.py \
    --scenario sdnv \
    --results-tag "emapt_sdnv_${tag}" \
    --num-vehicles "${n}" \
    --area-size "${AREA}" \
    --speed-kmh "${SPEED}"
done

# Ensure the exact END value is included even if the step doesn't land on it.
if [ -n "${last}" ] && [ "${last}" -ne "${END}" ]; then
  n="${END}"
  tag="scale_v${n}"
  echo ""
  echo "=== Vehicles: ${n} ==="

  python3 experiments/auto_run.py \
    --scenario baseline \
    --results-tag "baseline_${tag}" \
    --num-vehicles "${n}" \
    --area-size "${AREA}" \
    --speed-kmh "${SPEED}" \
    --duration "${DURATION}"

  python3 experiments/auto_run.py \
    --scenario sdnv \
    --results-tag "sdnv_${tag}" \
    --num-vehicles "${n}" \
    --area-size "${AREA}" \
    --speed-kmh "${SPEED}" \
    --duration "${DURATION}"

  python3 experiments/emapt_run.py \
    --scenario baseline \
    --results-tag "emapt_baseline_${tag}" \
    --num-vehicles "${n}" \
    --area-size "${AREA}" \
    --speed-kmh "${SPEED}"

  python3 experiments/emapt_run.py \
    --scenario sdnv \
    --results-tag "emapt_sdnv_${tag}" \
    --num-vehicles "${n}" \
    --area-size "${AREA}" \
    --speed-kmh "${SPEED}"
fi

echo "Scale run completed."
