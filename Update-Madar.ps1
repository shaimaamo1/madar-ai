[CmdletBinding()]
param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'scripts/windows/Madar.Update.ps1')
$result = Update-MadarLocal -RepoRoot $PSScriptRoot -NoBrowser:$NoBrowser
if ($result) { exit 0 } else { exit 1 }
