# V6 Reference Experiment

This archive contains the completed `v6` cooperative emergency scalability experiment with **5 repetitions per vehicle count**.

## Experiment profile
- Counts: `5, 10, 15, 20` vehicles
- Repetitions: `5` per count
- Speed: `60 km/h`
- Area: `1000 x 1000 m`
- Emergency UDP: `10 Mbit/s`
- Aggregate helper UDP: `10 Mbit/s`
- Aggregate helper TCP offered load: `80 Mbit/s`
- Aggregate helper TCP cap under SDNV after trigger: `10 Mbit/s`
- Wireless mode: `802.11g`
- Single-AP contention mode for the experiment: `SDNV_USE_BOTH_APS=0`, `SDNV_AUTO_ASSOCIATION=0`

## Archive contents
- `run_artifacts/`: per-run directories, EMAPT CSVs, summary CSVs
- `plots/`: regenerated latency, throughput, and EMAPT figures
- `logs/`: controller, traffic, and EMAPT logs
- `pseudocode.md`: paper-ready pseudocode description
- `commands.md`: commands to rerun and regenerate outputs

## Latency summary
| Vehicles | UDP Latency Baseline (ms) | UDP Latency SDNV (ms) | TCP Latency Baseline (ms) | TCP Latency SDNV (ms) |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 3.68 +- 0.26 | 1.41 +- 0.30 | 3.19 +- 0.31 | 37.48 +- 49.71 |
| 10 | 4.57 +- 0.40 | 1.50 +- 0.31 | 4.60 +- 0.42 | 56.74 +- 62.99 |
| 15 | 7.37 +- 0.52 | 2.26 +- 0.16 | 7.12 +- 0.94 | 34.37 +- 52.46 |
| 20 | 23.32 +- 8.65 | 4.19 +- 2.72 | 23.08 +- 8.07 | 60.83 +- 68.64 |

## Throughput summary
| Vehicles | Total UDP Baseline (Mb/s) | Total UDP SDNV (Mb/s) | TCP Baseline (Mb/s) | TCP SDNV (Mb/s) |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 20.00 +- 0.00 | 20.00 +- 0.00 | 90.92 +- 1.28 | 9.40 +- 0.04 |
| 10 | 19.99 +- 0.01 | 19.99 +- 0.00 | 90.46 +- 1.23 | 9.49 +- 0.05 |
| 15 | 19.99 +- 0.01 | 20.00 +- 0.00 | 88.95 +- 0.45 | 9.54 +- 0.03 |
| 20 | 19.61 +- 0.73 | 19.87 +- 0.26 | 74.01 +- 7.18 | 9.58 +- 0.04 |

## Auxiliary metrics
| Vehicles | UDP Share B (%) | UDP Share S (%) | TSE S (%) | PRT S (ms) | PER B | PER S | EMAPT-50 B/S (ms) | EMAPT-90 B/S (ms) | EMAPT-100 B/S (ms) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| 5 | 18.03 | 68.03 | 89.66 +- 0.18 | 1247.43 +- 201.47 | 0.110 | 1.064 | 5.60 / 107.63 | 8.04 / 109.97 | 9.63 / 116.87 |
| 10 | 18.10 | 67.81 | 89.51 +- 0.18 | 2512.42 +- 211.23 | 0.111 | 1.054 | 14.07 / 367.40 | 23.58 / 389.08 | 25.87 / 398.23 |
| 15 | 18.35 | 67.69 | 89.27 +- 0.07 | 3727.17 +- 144.93 | 0.112 | 1.048 | 27.89 / 99.53 | 33.84 / 122.80 | 686.51 / 176.13 |
| 20 | 21.03 | 67.47 | 86.95 +- 1.33 | 6766.35 +- 1347.72 | 0.133 | 1.035 | 43.45 / 81.23 | 100.74 / 111.58 | 654.04 / 133.05 |
