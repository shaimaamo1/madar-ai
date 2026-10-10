# Prepare and start the full system without automatically opening a browser.
[CmdletBinding()]
param([switch]$ReplaceApiKey)
& (Join-Path $PSScriptRoot 'Start-Madar.ps1') -NoBrowser -ReplaceApiKey:$ReplaceApiKey
if ($LASTEXITCODE) { exit $LASTEXITCODE }
