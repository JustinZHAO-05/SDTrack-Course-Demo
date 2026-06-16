$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeNode = if ($env:NODE_EXE) { $env:NODE_EXE } else { "node" }
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $Python) {
  $env:PYTHON = $Python
}
if (-not $env:HOME) {
  $env:HOME = $env:USERPROFILE
}
$SkillDir = $env:PRESENTATIONS_SKILL_DIR
if (-not $SkillDir -and $env:USERPROFILE) {
  $DefaultSkillDir = Join-Path $env:USERPROFILE ".codex\plugins\cache\openai-primary-runtime\presentations\26.601.10930\skills\presentations"
  if (Test-Path $DefaultSkillDir) {
    $SkillDir = $DefaultSkillDir
  }
}
if (-not $SkillDir -or -not (Test-Path (Join-Path $SkillDir "scripts\build_artifact_deck.mjs"))) {
  throw "Presentations runtime not found. Set PRESENTATIONS_SKILL_DIR to the Presentations skill directory, or run this script in a Codex environment with the Presentations plugin installed."
}
$Workspace = Join-Path $Root "outputs\manual-sdtrack\presentations\sdtrack-final"
$SlidesDir = Join-Path $Workspace "slides"
$PreviewDir = Join-Path $Workspace "preview"
$LayoutDir = Join-Path $Workspace "layout"
$OutputDir = Join-Path $Root "outputs"
$Seq = "$([char]0x5E8F)$([char]0x53F7)"
$Name = "$([char]0x59D3)$([char]0x540D)"
$Final = Join-Path $OutputDir "$Seq+SDTrack+${Name}1+${Name}2+${Name}3+${Name}4.pptx"

Push-Location $Root
try {
  .\run_figures.ps1
  New-Item -ItemType Directory -Force -Path $SlidesDir,$PreviewDir,$LayoutDir,$OutputDir | Out-Null
  Copy-Item -Force slides\*.mjs $SlidesDir
  & $RuntimeNode (Join-Path $SkillDir "scripts\build_artifact_deck.mjs") `
    --workspace $Workspace `
    --slides-dir $SlidesDir `
    --out $Final `
    --preview-dir $PreviewDir `
    --layout-dir $LayoutDir `
    --contact-sheet (Join-Path $PreviewDir "contact-sheet.png") `
    --slide-count 12 `
    --slide-size 1280x720
} finally {
  Pop-Location
}
