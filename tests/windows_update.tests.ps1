param([string]$RepoRoot, [string]$FixtureRoot, [string]$GitExe, [string]$Scenario)
$ErrorActionPreference = 'Stop'
. (Join-Path $RepoRoot 'scripts/windows/Madar.Update.ps1')
# OS discovery and Windows-only ACLs are simulated. Git operations are real,
# against isolated fixtures redirected to a local bare repository, never GitHub.
function Test-MadarWindows { return $true }
function Get-MadarGitCommand { return $GitExe }
function Protect-MadarPath { param([string]$Path,[switch]$Directory,[string]$Target) }
function Get-MadarDockerCommand { return 'dummy Docker; never invoked' }
$script:DockerCalls = [Collections.Generic.List[object]]::new()
function Assert-MadarDocker {
    param([string[]]$DockerArgs)
    $script:DockerCalls.Add($DockerArgs)
    if ($Scenario -eq 'backup-failure') { throw 'private-test-secret must be suppressed' }
    if ($DockerArgs[0] -eq 'compose') { return 'v2.30.0-desktop.1' }
    if ($DockerArgs[0] -eq 'context') { return 'npipe:////./pipe/dockerDesktopLinuxEngine' }
    if ($DockerArgs[0] -eq 'ps') { return 'abcdefabcdef' }
    if ($DockerArgs[0] -eq 'inspect') { return 'sha256:' + ('a' * 64) }
    return ''
}
$script:Started = $false
# Dot-sourcing the newly merged launcher is tested using a fixture source that
# overrides this function. No actual application/container is started by tests.
$before = (& $GitExe -C $FixtureRoot rev-parse HEAD).Trim()
$private = Join-Path $FixtureRoot '.madar-local/.env'
$bytes = [Convert]::ToBase64String([IO.File]::ReadAllBytes($private))
$result = Update-MadarLocal -RepoRoot $FixtureRoot -NoBrowser
$after = (& $GitExe -C $FixtureRoot rev-parse HEAD).Trim()
$expectedSuccess = $Scenario -in @('success','already-current')
if ([bool]$result -ne $expectedSuccess) { throw 'Unexpected update result.' }
if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($private)) -ne $bytes) { throw 'Existing private bytes changed.' }
if (-not $expectedSuccess -and $before -ne $after) { throw 'Rejected update changed HEAD.' }
if ($expectedSuccess) {
    if (-not $script:Started) { throw 'Updated launcher did not run.' }
    if (-not ($script:DockerCalls | Where-Object { $_ -contains 'scripts.backup' })) { throw 'SQLite backup was not requested.' }
    if (-not ($script:DockerCalls | Where-Object { $_ -contains 'tag' })) { throw 'Previous image was not retained.' }
    if (@(Get-ChildItem -LiteralPath (Join-Path $FixtureRoot '.madar-local/backups') -Recurse -Filter repository.bundle).Count -ne 1) { throw 'Code recovery bundle missing.' }
}
foreach ($call in $script:DockerCalls) {
    if ($call -contains 'down' -or $call -contains 'rm' -or $call -contains 'prune') { throw 'Destructive Docker operation found.' }
}
Write-Output ('Update fixture PASS: ' + $Scenario + '; real local Git, simulated Windows/Docker/ACLs.')
