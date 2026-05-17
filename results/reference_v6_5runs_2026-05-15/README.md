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
| 5 | 3.54 +- 0.26 | 1.33 +- 0.41 | 3.28 +- 0.35 | 14.97 +- 4.57 |
| 10 | 4.75 +- 0.41 | 1.44 +- 0.27 | 4.66 +- 0.55 | 31.02 +- 45.58 |
| 15 | 7.37 +- 0.52 | 2.26 +- 0.16 | 7.12 +- 0.94 | 34.37 +- 52.46 |
| 20 | 23.32 +- 8.65 | 4.19 +- 2.72 | 23.08 +- 8.07 | 60.83 +- 68.64 |

## Throughput summary
| Vehicles | Total UDP Baseline (Mb/s) | Total UDP SDNV (Mb/s) | TCP Baseline (Mb/s) | TCP SDNV (Mb/s) |
| ---: | ---: | ---: | ---: | ---: |
| 5 | 20.00 +- 0.00 | 20.00 +- 0.00 | 90.88 +- 1.32 | 9.40 +- 0.04 |
| 10 | 19.99 +- 0.00 | 19.99 +- 0.00 | 90.27 +- 1.17 | 9.51 +- 0.04 |
| 15 | 19.99 +- 0.01 | 20.00 +- 0.00 | 88.95 +- 0.45 | 9.54 +- 0.03 |
| 20 | 19.61 +- 0.73 | 19.87 +- 0.26 | 74.01 +- 7.18 | 9.58 +- 0.04 |

## Auxiliary metrics
| Vehicles | UDP Share B (%) | UDP Share S (%) | TSE S (%) | PRT S (ms) | PER B | PER S | EMAPT-50 B/S (ms) | EMAPT-90 B/S (ms) | EMAPT-100 B/S (ms) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| 5 | 18.04 | 68.02 | 89.65 +- 0.18 | 1257.87 +- 200.32 | 0.110 | 1.064 | 5.78 / 111.76 | 7.82 / 113.84 | 8.96 / 123.28 |
| 10 | 18.13 | 67.75 | 89.46 +- 0.16 | 2491.46 +- 168.15 | 0.111 | 1.051 | 9.23 / 111.51 | 19.00 / 132.23 | 226.12 / 139.54 |
| 15 | 18.35 | 67.69 | 89.27 +- 0.07 | 3727.17 +- 144.93 | 0.112 | 1.048 | 27.89 / 99.53 | 33.84 / 122.80 | 686.51 / 176.13 |
| 20 | 21.03 | 67.47 | 86.95 +- 1.33 | 6766.35 +- 1347.72 | 0.133 | 1.035 | 43.45 / 81.23 | 100.74 / 111.58 | 654.04 / 133.05 |
