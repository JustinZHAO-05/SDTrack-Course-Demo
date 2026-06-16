param(
  [string[]]$Sequence = @("bike_low"),
  [switch]$LongDemo,
  [switch]$ReplayOnly,
  [switch]$NoBrowser,
  [switch]$ListSequences,
  [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "python"
}

$ArgsList = @(
  "-m", "src.demo_live",
  "--repo-root", $Root
)
foreach ($item in $Sequence) {
  if ($item -ne "") {
    $ArgsList += @("--sequence", $item)
  }
}
if ($LongDemo) { $ArgsList += "--long-demo" }
if ($ReplayOnly) { $ArgsList += "--replay-only" }
if ($NoBrowser) { $ArgsList += "--no-browser" }
if ($ListSequences) { $ArgsList += "--list-sequences" }
if ($OutDir -ne "") { $ArgsList += @("--out-dir", $OutDir) }

Push-Location $Root
try {
  & $Python @ArgsList
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
} finally {
  Pop-Location
}
