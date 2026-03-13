# SDNV Mininet-WiFi Testbed

This repository implements a Mininet-WiFi based testbed for experimenting with
Software-Defined Networked Vehicles (SDNV). The goal is to compare a baseline
SDN VANET architecture with a proposed architecture where the vehicle itself
participates in network control.

## Why This Testbed

The testbed was developed to provide a reproducible, lightweight environment
for SDNV experiments that can run on a single Linux host. It allows us to
compare baseline SDN behavior with a vehicle-assisted SDN policy under
controlled traffic and mobility conditions.

## Purpose

Use this testbed to:
1. Evaluate how in-vehicle policy enforcement (traffic control) impacts
   emergency and best-effort flows.
2. Measure latency, jitter, and throughput under controlled congestion.
3. Reproduce experiments for papers or course projects without needing
   physical vehicular hardware.

## How It Is Built

The testbed is a small Mininet-WiFi network plus a Ryu controller:
1. Mininet-WiFi topology with 4 stations, 2 RSU access points, 1 OVS switch,
   and 1 host (`h1`) acting as an edge/cloud service.
2. A Ryu OpenFlow 1.3 controller that implements a simple L2 learning
   switch and a high-priority rule for emergency UDP traffic (dst port 5001).
3. Vehicle-side policies implemented as `tc` scripts to shape traffic at the
   station interface.
4. Traffic generators based on `iperf` for emergency (UDP), background
   (TCP), and congestion flows.
5. Measurement scripts for latency (ping), jitter (iperf UDP), and throughput
   (iperf TCP).

## How It Works

1. Start the controller.
2. Launch the topology and connect stations to APs.
3. Apply baseline or SDNV policy on `sta1`.
4. Run emergency and background traffic, optionally with congestion.
5. Collect KPI logs and summarize results.

## Structure

```
sdnv-mininet-project/
│
├── topology/
│   └── sdnv_topology.py
│
├── controller/
│   └── sdnv_controller.py
│
├── vehicle/
│   ├── baseline_policy.sh
│   └── sdnv_policy.sh
│
├── traffic/
│   ├── emergency_flow.sh
│   ├── background_flow.sh
│   └── congestion_flows.sh
│
├── experiments/
│   ├── run_baseline.sh
│   └── run_sdnv.sh
│   └── auto_run.py
│
├── measurements/
│   ├── latency.sh
│   ├── jitter.sh
│   └── throughput.sh
│   └── parse_results.py
│   └── plot_results.py
│
├── results/
│   ├── baseline/
│   └── sdnv/
│
├── logs/
│
└── README.md
```

## Getting Started

1. Install Mininet-WiFi and dependencies on Ubuntu.
2. For manual runs, launch the controller:

   ```sh
   ryu-manager controller/sdnv_controller.py
   ```

   If your controller listens on a non-default port, set `RYU_PORT` when
   launching the topology (default is `6653`).

3. Manual run (interactive CLI):

   ```sh
   sudo bash experiments/run_baseline.sh
   # or
   sudo bash experiments/run_sdnv.sh
   ```

4. Automated run (headless-friendly, runs measurements end-to-end):

   ```sh
   sudo python3 experiments/auto_run.py --scenario baseline
   # or
   sudo python3 experiments/auto_run.py --scenario sdnv
   ```

   The automation starts iperf servers on `h1`, runs congestion flows from
   `sta2-4`, applies the policy on `sta1`, and collects latency/jitter/throughput.

5. Summarize results:

   ```sh
   python3 measurements/parse_results.py
   ```

6. Plot results:

   ```sh
   python3 measurements/plot_results.py
   ```

7. Check the `results/` directory for output and `logs/` for debug logs.

## Experiment Parameters You Can Change

Topology and mobility:
1. Station/AP positions and mobility path: `topology/sdnv_topology.py`
2. Number of stations/APs or their SSIDs and channels: `topology/sdnv_topology.py`
3. Mobility timing (start/stop and duration): `topology/sdnv_topology.py`

Controller behavior:
1. Emergency traffic match and priority: `controller/sdnv_controller.py`
2. Default forwarding behavior: `controller/sdnv_controller.py`

Vehicle policies (traffic control):
1. Class rates/ceilings and queueing parameters: `vehicle/sdnv_policy.sh`
2. Baseline behavior (no shaping): `vehicle/baseline_policy.sh`

Traffic generation:
1. UDP/TCP ports and rates: `traffic/emergency_flow.sh`, `traffic/background_flow.sh`
2. Number of congestion flows and duration: `traffic/congestion_flows.sh`
3. Run duration for all flows: `experiments/auto_run.py` (`--duration`)

Measurements:
1. Ping count and interval: `measurements/latency.sh`
2. iperf sampling interval and duration: `measurements/jitter.sh`,
   `measurements/throughput.sh`

## Example Usage Patterns

1. Baseline vs SDNV, headless:

   ```sh
   sudo python3 experiments/auto_run.py --scenario baseline
   sudo python3 experiments/auto_run.py --scenario sdnv
   python3 measurements/parse_results.py
   python3 measurements/plot_results.py
   ```

2. Longer flows (e.g., 120 seconds):

   ```sh
   sudo python3 experiments/auto_run.py --scenario baseline --duration 120
   ```

## Notes and Tips

1. This testbed is intentionally minimal. Extend it by adding more stations,
   multiple mobility patterns, or additional controller policies.
2. The automated runner is headless-friendly and avoids `xterm` usage.
3. Results are stored under `results/` with timestamps; logs are under `logs/`.

## License

MIT
