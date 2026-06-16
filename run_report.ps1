$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $Root
try {
  .\run_figures.ps1
  New-Item -ItemType Directory -Force -Path outputs\pdf | Out-Null
  Copy-Item -Force report\refs.bib outputs\pdf\refs.bib
  latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=outputs\pdf report\main.tex
  $Seq = "$([char]0x5E8F)$([char]0x53F7)"
  $Name = "$([char]0x59D3)$([char]0x540D)"
  $FinalName = "$Seq+SDTrack+${Name}1+${Name}2+${Name}3+${Name}4.pdf"
  Copy-Item -Force outputs\pdf\main.pdf (Join-Path "outputs" $FinalName)
} finally {
  Pop-Location
}
