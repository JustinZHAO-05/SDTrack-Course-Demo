param(
  [switch]$PrepareData,
  [ValidateSet("none", "fe108", "visevent", "all")]
  [string]$ExtractDatasets = "none",
  [switch]$RunOfficial,
  [switch]$RunOfficialVisEvent,
  [switch]$RunAtrTracker,
  [string]$GtpImageDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "python"
}
$LogDir = Join-Path $Root "outputs\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Get-FirstExisting([string[]]$Candidates) {
  foreach ($Candidate in $Candidates) {
    if (Test-Path $Candidate) {
      return $Candidate
    }
  }
  return $null
}

Push-Location $Root
try {
  if ($PrepareData) {
    .\run_data_setup.ps1 -ExtractDatasets $ExtractDatasets
  }

  & $Python -m src.environment_report --out outputs/logs/environment_report.json
  & $Python -m src.ablate_gtp --protocol-only --output-dir outputs/gtp_ablation

  if ($GtpImageDir -ne "") {
    & $Python -m src.ablate_gtp --input-dir $GtpImageDir --output-dir outputs/gtp_ablation --all
  }

  if ($RunOfficial) {
    $Dataset = Join-Path $Root "data\FE108\test"
    $Checkpoint = Join-Path $Root "outputs\checkpoints\train\SDTrack\SDTrack-tiny-fe108\SDTrack_ep0100.pth.tar"
    if ((Test-Path $Dataset) -and (Test-Path $Checkpoint)) {
      Push-Location (Join-Path $Root "external\SDTrack\SDTrack-Event")
      try {
        & $Python tracking/test.py SDTrack SDTrack-tiny-fe108 --dataset_name eotb --threads 0 --num_gpus 1 2>&1 |
          Tee-Object -FilePath (Join-Path $LogDir "official_fe108_test.log")
      } finally {
        Pop-Location
      }
    } else {
      $Missing = @()
      if (-not (Test-Path $Dataset)) { $Missing += "data\FE108\test" }
      if (-not (Test-Path $Checkpoint)) { $Missing += "outputs\checkpoints\train\SDTrack\SDTrack-tiny-fe108\SDTrack_ep0100.pth.tar" }
      $Message = "Official FE108 run skipped; missing: " + ($Missing -join ", ")
      $Message | Tee-Object -FilePath (Join-Path $LogDir "official_fe108_test.log")
    }
  }

  $LocalFePred = Join-Path $Root "outputs\test\tracking_results\SDTrack\SDTrack-tiny-fe108"
  $LocalFeGt = Get-FirstExisting @(
    (Join-Path $Root "data\official_results_E\FE108_eval\FE108\annos\gt_rect"),
    (Join-Path $Root "data\official_results\FE108_eval\FE108\annos\gt_rect")
  )
  $LocalFeAbsent = Get-FirstExisting @(
    (Join-Path $Root "data\official_results_E\FE108_eval\FE108\annos\absent"),
    (Join-Path $Root "data\official_results\FE108_eval\FE108\annos\absent")
  )
  if ((Test-Path $LocalFePred) -and ($null -ne $LocalFeGt)) {
    $cmd = @("-m", "src.eval_sdtrack", "--pred", $LocalFePred, "--gt", $LocalFeGt, "--out", "outputs/metrics/fe108_local_official_tiny", "--tracker-name", "Local-SDTrack-Tiny-FE108")
    if ($null -ne $LocalFeAbsent) { $cmd += @("--absent-dir", $LocalFeAbsent) }
    & $Python @cmd 2>&1 |
      Tee-Object -FilePath (Join-Path $LogDir "fe108_local_official_eval.log")
  }

  if ($RunOfficialVisEvent) {
    $Dataset = Join-Path $Root "data\VisEvent\test"
    $Checkpoint = Join-Path $Root "outputs\checkpoints\train\SDTrack\SDTrack-tiny-visevent\SDTrack_ep0100.pth.tar"
    if ((Test-Path $Dataset) -and (Test-Path $Checkpoint)) {
      Push-Location (Join-Path $Root "external\SDTrack\SDTrack-Event")
      try {
        & $Python tracking/test.py SDTrack SDTrack-tiny-visevent --dataset_name visevent --threads 0 --num_gpus 1 2>&1 |
          Tee-Object -FilePath (Join-Path $LogDir "official_visevent_test.log")
      } finally {
        Pop-Location
      }
    } else {
      $Missing = @()
      if (-not (Test-Path $Dataset)) { $Missing += "data\VisEvent\test" }
      if (-not (Test-Path $Checkpoint)) { $Missing += "outputs\checkpoints\train\SDTrack\SDTrack-tiny-visevent\SDTrack_ep0100.pth.tar" }
      $Message = "Official VisEvent run skipped; missing: " + ($Missing -join ", ")
      $Message | Tee-Object -FilePath (Join-Path $LogDir "official_visevent_test.log")
    }
  }

  $LocalVisPred = Join-Path $Root "outputs\test\tracking_results\SDTrack\SDTrack-tiny-visevent"
  $LocalVisGt = Get-FirstExisting @(
    (Join-Path $Root "data\official_results_E\VisEvent_eval\VisEvent\annos\gt_rect"),
    (Join-Path $Root "data\official_results\VisEvent_eval\VisEvent\annos\gt_rect")
  )
  $LocalVisAbsent = Get-FirstExisting @(
    (Join-Path $Root "data\official_results_E\VisEvent_eval\VisEvent\annos\absent"),
    (Join-Path $Root "data\official_results\VisEvent_eval\VisEvent\annos\absent")
  )
  if ((Test-Path $LocalVisPred) -and ($null -ne $LocalVisGt)) {
    $cmd = @("-m", "src.eval_sdtrack", "--pred", $LocalVisPred, "--gt", $LocalVisGt, "--out", "outputs/metrics/visevent_local_official_tiny", "--tracker-name", "Local-SDTrack-Tiny-VisEvent")
    if ($null -ne $LocalVisAbsent) { $cmd += @("--absent-dir", $LocalVisAbsent) }
    & $Python @cmd 2>&1 |
      Tee-Object -FilePath (Join-Path $LogDir "visevent_local_official_eval.log")
  }

  if ($RunAtrTracker) {
    & $Python -m src.atr_gtp_tracker_eval 2>&1 |
      Tee-Object -FilePath (Join-Path $LogDir "atr_gtp_tracker_eval_wrapper.log")
  }

  $OfficialResults = Get-FirstExisting @(
    (Join-Path $Root "data\official_results_E\FE108_results\FE108_tracking_results"),
    (Join-Path $Root "data\official_results\FE108_results\FE108_tracking_results")
  )
  $OfficialGt = Get-FirstExisting @(
    (Join-Path $Root "data\official_results_E\FE108_eval\FE108\annos\gt_rect"),
    (Join-Path $Root "data\official_results\FE108_eval\FE108\annos\gt_rect")
  )
  $OfficialAbsent = Get-FirstExisting @(
    (Join-Path $Root "data\official_results_E\FE108_eval\FE108\annos\absent"),
    (Join-Path $Root "data\official_results\FE108_eval\FE108\annos\absent")
  )
  if (($null -ne $OfficialResults) -and ($null -ne $OfficialGt)) {
    $cmd = @("-m", "src.eval_official_bundle", "--results-root", $OfficialResults, "--gt", $OfficialGt, "--out", "outputs/metrics/fe108_official_methods")
    if ($null -ne $OfficialAbsent) {
      $cmd += @("--absent-dir", $OfficialAbsent)
    }
    & $Python @cmd 2>&1 | Tee-Object -FilePath (Join-Path $LogDir "fe108_official_bundle_eval.log")
  }

  $VisResults = Get-FirstExisting @(
    (Join-Path $Root "data\official_results_E\VisEvent_results\VISEVENT_tracking_results"),
    (Join-Path $Root "data\official_results\VisEvent_results\VISEVENT_tracking_results")
  )
  $VisGt = Get-FirstExisting @(
    (Join-Path $Root "data\official_results_E\VisEvent_eval\VisEvent\annos\gt_rect"),
    (Join-Path $Root "data\official_results\VisEvent_eval\VisEvent\annos\gt_rect")
  )
  $VisAbsent = Get-FirstExisting @(
    (Join-Path $Root "data\official_results_E\VisEvent_eval\VisEvent\annos\absent"),
    (Join-Path $Root "data\official_results\VisEvent_eval\VisEvent\annos\absent")
  )
  if (($null -ne $VisResults) -and ($null -ne $VisGt)) {
    $cmd = @("-m", "src.eval_official_bundle", "--results-root", $VisResults, "--gt", $VisGt, "--out", "outputs/metrics/visevent_official_methods")
    if ($null -ne $VisAbsent) {
      $cmd += @("--absent-dir", $VisAbsent)
    }
    & $Python @cmd 2>&1 | Tee-Object -FilePath (Join-Path $LogDir "visevent_official_bundle_eval.log")
  }

  & $Python -m src.reproduction_summary --repo-root $Root
} finally {
  Pop-Location
}
