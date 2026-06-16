param(
  [switch]$RunOfficial,
  [switch]$RunOfficialVisEvent,
  [switch]$PrepareData,
  [ValidateSet("none", "fe108", "visevent", "all")]
  [string]$ExtractDatasets = "none",
  [string]$GtpImageDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $Root
try {
  .\run_experiments.ps1 `
    -PrepareData:$PrepareData `
    -ExtractDatasets $ExtractDatasets `
    -RunOfficial:$RunOfficial `
    -RunOfficialVisEvent:$RunOfficialVisEvent `
    -GtpImageDir $GtpImageDir
  .\run_figures.ps1
  .\run_report.ps1
  .\run_slides.ps1
} finally {
  Pop-Location
}
