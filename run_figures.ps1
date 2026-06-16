$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "python"
}
Push-Location $Root
try {
  & $Python -m src.make_figures --out outputs/figures --table data/official_event_benchmark.csv --tables-out outputs/tables
  $CaseFile = "outputs/metrics/fe108_official_methods/sdtrack_tiny/failure_cases.json"
  if (-not (Test-Path $CaseFile)) {
    $CaseFile = "outputs/metrics/failure_cases.json"
  }
  & $Python -m src.visualize_cases --cases $CaseFile --out outputs/cases --data-root data/FE108
  & $Python -m src.visualize_sequences `
    --data-root data/FE108 `
    --gt-dir data/official_results_E/FE108_eval/FE108/annos/gt_rect `
    --baseline-dir outputs/test/tracking_results/SDTrack/SDTrack-tiny-fe108 `
    --atr-dir outputs/atr_gtp_tracking/results/adaptive_smooth/SDTrack/SDTrack-tiny-fe108 `
    --atr-input-root outputs/atr_gtp_tracking/datasets/adaptive_smooth `
    --out-dir outputs/sequence_viz `
    --fig-dir outputs/cases `
    --table-dir outputs/tables `
    --sequences star_motion bike_low
  & $Python -m src.ablate_gtp --protocol-only --output-dir outputs/gtp_ablation
  if (Test-Path "outputs/gtp_ablation/atr_gtp_transform_log.csv") {
    & $Python -m src.analyze_atr_gtp --log outputs/gtp_ablation/atr_gtp_transform_log.csv --out-fig outputs/figures/atr_gtp_transform_stats.png --out-table outputs/tables/atr_gtp_transform_summary.csv
  }
} finally {
  Pop-Location
}
