# Exercise actual detection/parsing/lock code; replace only OS discovery/process start.
param([string]$RepoRoot, [string]$OutputRoot)
$ErrorActionPreference = 'Stop'
. (Join-Path $RepoRoot 'scripts/windows/Madar.Local.ps1')
Add-Type -TypeDefinition @'
using System.Threading;
public class MadarDockerTestMutex {
    private string behavior;
    public MadarDockerTestMutex(string value) { behavior = value; }
    public bool WaitOne(int timeout) {
        if (behavior == "abandoned") throw new AbandonedMutexException();
        return behavior == "free";
    }
}
'@
function Assert-Test { param([bool]$Condition, [string]$Message) if (-not $Condition) { throw $Message } }
function Get-Command {
    [CmdletBinding()]param([string]$Name, [string]$CommandType)
    Assert-Test ($Name -eq 'docker.exe') 'Lookup did not explicitly request docker.exe.'
    Assert-Test ($CommandType -eq 'Application') 'Lookup accepted aliases or functions.'
    return $script:Discoveries
}
function Start-Process {
    [CmdletBinding()]param([string]$FilePath)
    $script:Started.Add($FilePath)
}
function Assert-SafeFailure {
    param([string]$Code, [scriptblock]$Action)
    $report = [ordered]@{}
    $ok = Invoke-MadarStep $report 'Docker dependencies' $Action 'ready' 'Dependency check failed.'
    Assert-Test (-not $ok) 'Invalid dependency was accepted.'
    $json = $report.Values | ConvertTo-Json -Depth 4
    Assert-Test ($json -match ('DockerCode=' + $Code + '\.')) 'Missing safe Docker failure code.'
    Assert-Test ($json -notmatch 'sensitive-native-output|secret-version-value') 'Raw process output leaked.'
}
$savedProgramFiles = $env:ProgramFiles
$savedLocalAppData = $env:LOCALAPPDATA
$checks = 0
try {
    $env:ProgramFiles = Join-Path $OutputRoot 'Program Files'
    $env:LOCALAPPDATA = Join-Path $OutputRoot 'User Profile'
    $script:Started = [Collections.Generic.List[string]]::new()
    $script:Discoveries = @([pscustomobject]@{ Source = 'C:\First Docker\docker.exe' }, [pscustomobject]@{ Source = 'C:\Second Docker\docker.exe' })
    $selected = @(Get-MadarDockerCommand)
    Assert-Test ($selected.Count -eq 1 -and $selected[0] -eq 'C:\First Docker\docker.exe') 'Multiple Docker executables were not reduced to the first.'
    $checks++
    $script:Discoveries = @([pscustomobject]@{ Source = 'C:\Only Docker\docker.exe' })
    Assert-Test ((Get-MadarDockerCommand) -eq 'C:\Only Docker\docker.exe') 'Single PATH executable was not selected.'
    $checks++
    $script:Discoveries = @()
    Assert-SafeFailure 'cli-not-found' { Get-MadarDockerCommand }
    $checks++
    $userRoot = Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop'
    $userCli = Join-Path $userRoot 'resources/bin/docker.exe'
    $null = New-Item -ItemType Directory -Path (Split-Path $userCli) -Force
    [IO.File]::WriteAllText($userCli, 'dummy executable never invoked')
    Assert-Test ((Get-MadarDockerCommand) -eq $userCli) 'Per-user installation fallback failed.'
    $checks++
    $systemRoot = Join-Path $env:ProgramFiles 'Docker/Docker'
    $systemCli = Join-Path $systemRoot 'resources/bin/docker.exe'
    $null = New-Item -ItemType Directory -Path (Split-Path $systemCli) -Force
    [IO.File]::WriteAllText($systemCli, 'dummy executable never invoked')
    Assert-Test ((Get-MadarDockerCommand) -eq $systemCli) 'Program Files fallback order failed.'
    $checks++
    # A same-name directory is not a valid executable, even with an .exe suffix.
    Remove-Item -LiteralPath $systemCli
    $null = New-Item -ItemType Directory -Path $systemCli
    Assert-Test ((Get-MadarDockerCommand) -eq $userCli) 'An executable directory was accepted.'
    $checks++
    Assert-SafeFailure 'desktop-not-found' { Start-MadarDockerDesktop }
    $checks++
    $userDesktop = Join-Path $userRoot 'Docker Desktop.exe'
    [IO.File]::WriteAllText($userDesktop, 'dummy executable never invoked')
    Start-MadarDockerDesktop
    Assert-Test ($script:Started.Count -eq 1 -and $script:Started[0] -eq $userDesktop) 'Per-user Desktop was not selected.'
    $checks++
    $systemDesktop = Join-Path $systemRoot 'Docker Desktop.exe'
    [IO.File]::WriteAllText($systemDesktop, 'dummy executable never invoked')
    Start-MadarDockerDesktop
    Assert-Test ($script:Started.Count -eq 2 -and $script:Started[1] -eq $systemDesktop) 'System Desktop fallback order failed.'
    $checks++
    $env:ProgramFiles = $null
    Assert-Test ((Get-MadarDockerCommand) -eq $userCli) 'Missing ProgramFiles caused a binding failure.'
    $checks++
    $env:LOCALAPPDATA = $null
    Assert-SafeFailure 'cli-not-found' { Get-MadarDockerCommand }
    $checks++
    foreach ($case in @(
        @('2.24.4', '2.24.4'), @('v2.30.0', '2.30.0'), @('v2.30.0-desktop.1', '2.30.0'),
        @('Docker Compose version v2.40.1-desktop.1', '2.40.1'), @("  v2.24.4`r`n", '2.24.4'),
        @('v2.30.1+build.123', '2.30.1'), @('3.0.0', '3.0.0'), @('v2.24.3', '2.24.3')
    )) {
        # Pre-populate Matches, then assert extraction neither reads nor mutates it.
        $null = 'stale-version-secret' -match '(stale-version-secret)'
        $version = Get-MadarComposeVersion $case[0]
        Assert-Test ($version -is [version] -and $version.ToString() -eq $case[1]) 'Valid version output was misparsed.'
        Assert-Test ($Matches[1] -eq 'stale-version-secret') 'Parser depends on mutable Matches.'
        $checks++
    }
    foreach ($invalid in @('', $null, 'unknown', '2.24', '1.2.3.4', 'warning secret-version-value 2.30.0', "v2.30.0`nv2.40.0", '999999999999999999999.2.3')) {
        Assert-SafeFailure 'compose-version-invalid' { Get-MadarComposeVersion $invalid }
        $checks++
    }
    foreach ($behavior in @('free', 'held', 'abandoned')) {
        $mutex = [MadarDockerTestMutex]::new($behavior)
        Assert-Test ((Enter-MadarSetupLock $mutex) -eq ($behavior -ne 'held')) 'Setup-lock acquisition/recovery failed.'
        $checks++
    }
} finally {
    $env:ProgramFiles = $savedProgramFiles
    $env:LOCALAPPDATA = $savedLocalAppData
}
Write-Output ('Docker helpers: ' + $checks + ' cases PASS (simulated Windows discovery; no Docker calls).')
