# Native Windows-only test. Uses a NEW dummy fixture, never an owner's configuration.
param([string]$RepoRoot, [string]$OutputRoot)
$ErrorActionPreference = 'Stop'
. (Join-Path $RepoRoot 'scripts/windows/Madar.Local.ps1')
if (-not (Test-MadarWindows)) { throw 'This test requires actual Windows PowerShell 5.1+ on Windows.' }
if (Test-Path -LiteralPath $OutputRoot) { throw 'Use a new fixture directory; existing paths will not be modified.' }
$null = New-Item -ItemType Directory -Path $OutputRoot
$originalDirectoryAcl = Get-Acl -LiteralPath $OutputRoot
Protect-MadarPath $OutputRoot -Directory -Target 'settings-directory'
$envFile = Join-Path $OutputRoot '.env'
[IO.File]::WriteAllText($envFile, "N8N_API_KEY=dummy-native-test-key`r`nMADAR_BRIDGE_TOKEN=dummy-preserved-bridge`r`n")
$before = [IO.File]::ReadAllBytes($envFile)
$originalFileAcl = Get-Acl -LiteralPath $envFile
Protect-MadarPath $envFile
$directoryAcl = Get-Acl -LiteralPath $OutputRoot
$fileAcl = Get-Acl -LiteralPath $envFile
foreach ($pair in @(@($originalDirectoryAcl, $directoryAcl), @($originalFileAcl, $fileAcl))) {
    if ($pair[0].Owner -ne $pair[1].Owner -or $pair[0].Group -ne $pair[1].Group) { throw 'Access protection changed ownership or group.' }
}
$identity = Get-MadarPrivateIdentity
$inherit = [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
if (-not (Test-MadarPrivateAcl $directoryAcl $identity $inherit)) { throw 'Directory ACL verification failed.' }
if (-not (Test-MadarPrivateAcl $fileAcl $identity ([Security.AccessControl.InheritanceFlags]::None))) { throw 'File ACL verification failed.' }
$directorySddl = $directoryAcl.Sddl
$fileSddl = $fileAcl.Sddl
Protect-MadarPath $OutputRoot -Directory -Target 'settings-directory'
Protect-MadarPath $envFile
if ((Get-Acl -LiteralPath $OutputRoot).Sddl -ne $directorySddl -or (Get-Acl -LiteralPath $envFile).Sddl -ne $fileSddl) { throw 'Repeat protection changed secure ACLs.' }
if ([Convert]::ToBase64String($before) -ne [Convert]::ToBase64String([IO.File]::ReadAllBytes($envFile))) { throw 'Fixture env bytes changed.' }
Write-Output 'Native Windows ACL: PASS (fixture only; no Docker, n8n or external integration calls).'
