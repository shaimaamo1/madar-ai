[CmdletBinding()]
param([switch]$ReplaceApiKey, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'scripts/windows/Madar.Local.ps1')
$result = Start-MadarLocal -RepoRoot $PSScriptRoot -ReplaceApiKey:$ReplaceApiKey -NoBrowser:$NoBrowser
if ($result) { exit 0 } else { exit 1 }
