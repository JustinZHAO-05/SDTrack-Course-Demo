param(
  [string]$SourceRoot = $(if ($env:SDTRACK_SOURCE_ROOT) { $env:SDTRACK_SOURCE_ROOT } else { "external_data\raw" }),
  [string]$WorkRoot = $(if ($env:SDTRACK_WORK_ROOT) { $env:SDTRACK_WORK_ROOT } else { "external_data\work" }),
  [ValidateSet("none", "fe108", "visevent", "all")]
  [string]$ExtractDatasets = "none",
  [switch]$SkipOfficialExtract
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "python"
}

Push-Location $Root
try {
  $argsList = @(
    "-m", "src.data_setup",
    "--source-root", $SourceRoot,
    "--work-root", $WorkRoot,
    "--repo-root", $Root,
    "--extract-datasets", $ExtractDatasets
  )
  if ($SkipOfficialExtract) {
    $argsList += "--skip-official-extract"
  }
  & $Python @argsList
} finally {
  Pop-Location
}
