#!/usr/bin/env python3
"""
Run multiple baseline/SDNV experiments and summarize results.
"""

import argparse
import subprocess
import time


def run_scenario(scenario, runs, duration):
    for i in range(1, runs + 1):
        print(f"[batch] running {scenario} {i}/{runs}")
        cmd = ["sudo", "python3", "experiments/auto_run.py",
               "--scenario", scenario,
               "--duration", str(duration)]
        subprocess.check_call(cmd)
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description='Batch SDNV experiment runner')
    parser.add_argument('--runs', type=int, default=5)
    parser.add_argument('--duration', type=int, default=60)
    args = parser.parse_args()

    run_scenario('baseline', args.runs, args.duration)
    run_scenario('sdnv', args.runs, args.duration)

    subprocess.check_call(["python3", "measurements/parse_results.py"])
    subprocess.check_call(["python3", "measurements/plot_results.py"])


if __name__ == '__main__':
    main()
