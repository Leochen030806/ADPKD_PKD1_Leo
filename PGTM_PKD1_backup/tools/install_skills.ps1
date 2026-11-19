# Install the 5 PGT-M skills into Claude Code on Windows (%USERPROFILE%\.claude\skills).
#   powershell -ExecutionPolicy Bypass -File tools\install_skills.ps1
#   powershell -ExecutionPolicy Bypass -File tools\install_skills.ps1 -Zip   # zips into dist\ for claude.ai upload
param([switch]$Zip)
$Root = Split-Path -Parent $PSScriptRoot
$Skills = 'pgtm-str-panel-design','pgtm-str-panel-order','pgtm-ce-report-slides','pgtm-gel-titration-report','str-csv-allele-report'
if ($Zip) {
  New-Item -ItemType Directory -Force "$Root\dist" | Out-Null
  foreach ($s in $Skills) { Compress-Archive -Force -Path "$Root\skills\$s" -DestinationPath "$Root\dist\$s.zip"; "dist\$s.zip" }
} else {
  $Dest = Join-Path $env:USERPROFILE '.claude\skills'
  New-Item -ItemType Directory -Force $Dest | Out-Null
  foreach ($s in $Skills) { Remove-Item -Recurse -Force "$Dest\$s" -ErrorAction SilentlyContinue; Copy-Item -Recurse "$Root\skills\$s" $Dest; "installed $Dest\$s" }
}
