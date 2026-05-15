# Commands

## Run the full v6 experiment (5 repetitions per count)
```bash
set -a
. experiments/params_scale_v6.env
set +a
RUNS=5 RUN_EMAPT=1 sudo -E bash experiments/scale_run_multi_v6.sh
```

## Regenerate the summary CSVs before archiving
```bash
python3 measurements/scale_analysis_v6.py --counts 5,10,15,20 --runs 5
```

## Regenerate the plots before archiving
```bash
MPLCONFIGDIR=/tmp/mpl python3 measurements/plot_scale_v6.py \
  --summary results/scale_summary_v6.csv \
  --outdir results/scale_metrics_v6
```

## Regenerate plots from the archived reference summary
```bash
MPLCONFIGDIR=/tmp/mpl python3 measurements/plot_scale_v6.py \
  --summary results/reference_v6_5runs_2026-05-15/run_artifacts/scale_summary_v6.csv \
  --outdir results/reference_v6_5runs_2026-05-15/plots_regenerated
```
