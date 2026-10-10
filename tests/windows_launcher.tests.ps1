# Runs on PowerShell Core using fake Windows/Docker/HTTP functions. No network calls.
param([string]$RepoRoot, [string]$OutputRoot)
$ErrorActionPreference = 'Stop'
. (Join-Path $RepoRoot 'scripts/windows/Madar.Local.ps1')
function Assert-Test { param([bool]$Condition, [string]$Message) if (-not $Condition) { throw $Message } }
function Test-MadarWindows { return $true }
function Protect-MadarPath {
    param([string]$Path, [switch]$Directory, [string]$Target)
    if ($script:Scenario -eq 'private-acl-failure') {
        Invoke-MadarPrivateOperation 'settings-directory' 'acl-write' { throw [UnauthorizedAccessException]::new('test-private-stdin-key sensitive-native-output-must-stay-private') }
    }
}
function Get-MadarDockerCommand { return 'fake-docker-never-executed' }
function Start-MadarDockerDesktop { $script:DesktopStarts++ }
function Test-MadarPortFree { param([int]$Port) return $Port -ne 8000 }
function Test-MadarN8nPort { return $script:Scenario -ne 'missing-n8n' }
function Read-MadarApiKey { $script:Prompts++; return ConvertTo-SecureString 'test-private-stdin-key' -AsPlainText -Force }
function Open-MadarDashboard { param([string]$Url) $script:Opened.Add($Url) }
function Write-Host { param($Object) $script:Messages.Add([string]$Object) }
function Out-Host { param([Parameter(ValueFromPipeline=$true)]$InputObject) process { } }
function Get-MadarHttp {
    param([string]$Url)
    if ($Url.EndsWith('/api/health')) { $content = '{"status":"ok","service":"madar-ai"}' }
    elseif ($Url.Contains('/assets/')) { $content = 'x' * 150 }
    else { $content = '<div id="root"></div><script src="/assets/madar.js"></script>' }
    return [pscustomobject]@{ StatusCode = 200; Content = $content }
}
function Invoke-MadarDocker {
    param([string[]]$DockerArgs, [AllowNull()][string]$InputText)
    $script:Commands.Add([pscustomobject]@{ Argv = $DockerArgs; Stdin = $PSBoundParameters.ContainsKey('InputText') })
    $output = 'ok'; $code = 0
    if ($DockerArgs -contains 'version') { $output = '2.30.0' }
    elseif ($DockerArgs -contains 'context') { $output = if ($script:Scenario -eq 'remote-docker') { 'ssh://remote.example' } else { 'npipe:////./pipe/dockerDesktopLinuxEngine' } }
    elseif ($DockerArgs -contains 'info') {
        $script:InfoAttempts++
        $output = 'linux'
        if ($script:Scenario -eq 'desktop-start' -and $script:InfoAttempts -eq 1) { $code = 1 }
    }
    elseif ($DockerArgs -contains 'ps') {
        if ($DockerArgs -contains 'publish=5678' -and $script:Scenario -in @('docker', 'docker-connected')) { $output = 'custom-automation:test|abcdef1234' }
        elseif ($DockerArgs -contains 'publish=5678' -and $script:Scenario -eq 'ambiguous-docker') { $output = "n8nio/n8n:test|abcdef1234`nn8nio/n8n:test|abcdef5678" }
        else { $output = '' }
    }
    elseif ($DockerArgs -contains 'inspect') {
        $output = if ($script:Scenario -eq 'docker-connected') { '{"madar-local":{"Aliases":["custom-n8n"],"IPAddress":"172.22.0.8"}}' } else { '{}' }
    }
    elseif ($DockerArgs -contains 'build' -and $script:Scenario -eq 'build-failure') { $code = 1; $output = 'sensitive-native-output-must-stay-private' }
    elseif ($DockerArgs -contains 'init') {
        if ($PSBoundParameters.ContainsKey('InputText')) { Assert-Test ($InputText -eq 'test-private-stdin-key') 'Key did not arrive exclusively through stdin.' }
        $private = Join-Path $script:Fixture '.madar-local/.env'
        [IO.File]::WriteAllText($private, "N8N_API_KEY=test-private-stdin-key`nMADAR_ENV=development`n")
    }
    elseif ($DockerArgs -contains 'test' -and $script:Scenario -eq 'api-failure') { $code = 1; $output = 'sensitive-native-output-must-stay-private' }
    return [pscustomobject]@{ ExitCode = $code; Output = $output }
}

$checks = 0
$savedDockerHost = $env:DOCKER_HOST
foreach ($scenario in @('native', 'docker', 'docker-connected', 'missing-n8n', 'build-failure', 'api-failure', 'reuse-key', 'desktop-start', 'remote-docker', 'ambiguous-docker', 'remote-override', 'private-acl-failure', 'production-config')) {
    $env:DOCKER_HOST = if ($scenario -eq 'remote-override') { 'tcp://remote.example:2375' } else { $null }
    $script:Scenario = $scenario
    $script:Commands = New-Object 'Collections.Generic.List[object]'
    $script:Messages = New-Object 'Collections.Generic.List[string]'
    $script:Opened = New-Object 'Collections.Generic.List[string]'
    $script:Prompts = 0; $script:DesktopStarts = 0; $script:InfoAttempts = 0
    $script:Fixture = Join-Path $OutputRoot $scenario
    $null = New-Item -ItemType Directory -Path $script:Fixture -Force
    if ($scenario -in @('reuse-key', 'private-acl-failure', 'production-config')) {
        $null = New-Item -ItemType Directory -Path (Join-Path $script:Fixture '.madar-local') -Force
        $savedSettings = "N8N_API_KEY=existing-test-key`nMADAR_BRIDGE_TOKEN=preserved-test-bridge`n"
        if ($scenario -eq 'production-config') { $savedSettings += "MADAR_ENV=production`n" }
        [IO.File]::WriteAllText((Join-Path $script:Fixture '.madar-local/.env'), $savedSettings)
    }
    $success = Start-MadarLocal -RepoRoot $script:Fixture
    $rows = Get-Content -Raw -LiteralPath (Join-Path $script:Fixture 'var/windows-setup-report.json') | ConvertFrom-Json
    $expected = $scenario -in @('native', 'docker', 'docker-connected', 'reuse-key', 'desktop-start')
    Assert-Test ($success -eq $expected) ('Incorrect overall result: ' + $scenario)
    Assert-Test (@($rows).Count -eq 16) 'Not every component received a report row.'
    Assert-Test (@($rows | Where-Object { $_.Status -notin @('PASS', 'FAIL') }).Count -eq 0) 'Invalid report status.'
    if ($expected) { Assert-Test (@($rows | Where-Object { $_.Status -eq 'FAIL' }).Count -eq 0) 'Successful flow reports a failed stage.' }
    Assert-Test (($script:Messages -join ' ') -notmatch 'test-private-stdin-key|sensitive-native-output') 'Sensitive content leaked to output.'
    $argv = $script:Commands | ForEach-Object { $_.Argv -join ' ' }
    Assert-Test (($argv -join ' ') -notmatch 'test-private-stdin-key|N8N_API_KEY=') 'Key leaked into command arguments.'
    Assert-Test (@($script:Commands | Where-Object { $_.Argv -contains 'up' -and $_.Argv[-1] -ne 'app' }).Count -eq 0) 'A duplicate n8n service was started.'
    if ($scenario -in @('build-failure', 'remote-docker', 'remote-override', 'private-acl-failure', 'production-config')) { Assert-Test ($script:Prompts -eq 0 -and $script:Opened.Count -eq 0) 'Failed prerequisite requested a secret or opened an unhealthy app.' }
    else {
        Assert-Test ($script:Opened.Count -eq 1 -and $script:Opened[0] -eq 'http://localhost:8001') 'Healthy dashboard did not open on the chosen free port.'
        $initialization = @($script:Commands | Where-Object { $_.Argv -contains '--public-url' })[0]
        Assert-Test ($initialization.Argv -contains '--disable-external') 'Safety gates were not passed to initialization.'
        $expectedPrompts = if ($scenario -eq 'reuse-key') { 0 } else { 1 }
        Assert-Test ($script:Prompts -eq $expectedPrompts) 'Saved private key was not reused correctly.'
    }
    if ($scenario -eq 'docker') {
        Assert-Test (@($script:Commands | Where-Object { $_.Argv -contains 'connect' -and $_.Argv -contains 'abcdef1234' }).Count -eq 1) 'Existing n8n was not connected to MADAR network.'
    }
    if ($scenario -eq 'docker-connected') {
        Assert-Test (@($script:Commands | Where-Object { $_.Argv -contains 'connect' -or $_.Argv -contains 'disconnect' }).Count -eq 0) 'Existing network attachment was disrupted.'
        Assert-Test (($argv -join ' ') -match 'http://172.22.0.8:5678') 'Existing n8n IP route was not configured.'
    }
    if ($scenario -in @('missing-n8n', 'api-failure', 'ambiguous-docker', 'remote-docker', 'remote-override')) {
        Assert-Test (@($script:Commands | Where-Object { $_.Argv -contains 'deploy' }).Count -eq 0) 'Import proceeded without verified n8n access.'
    }
    if ($scenario -in @('private-acl-failure', 'production-config')) {
        $privateRow = @($rows | Where-Object { $_.Component -eq 'Private configuration' })[0]
        $expectedStage = if ($scenario -eq 'private-acl-failure') { 'acl-write' } else { 'production-guard' }
        Assert-Test ($privateRow.Status -eq 'FAIL' -and $privateRow.Detail -match ('Stage=' + $expectedStage + ';')) 'Private failure lacks redacted stage diagnosis.'
        Assert-Test (($rows | ConvertTo-Json -Depth 4) -notmatch 'test-private-stdin-key|sensitive-native-output') 'Secret leaked to report.'
        Assert-Test ([IO.File]::ReadAllText((Join-Path $script:Fixture '.madar-local/.env')) -eq $savedSettings) 'Existing private settings changed after failure.'
        Assert-Test (@($script:Commands | Where-Object { $_.Argv -contains 'build' -or $_.Argv -contains 'init' -or $_.Argv -contains 'deploy' -or $_.Argv -contains 'up' }).Count -eq 0) 'Private failure changed runtime or workflows.'
    }
    if ($scenario -eq 'desktop-start') { Assert-Test ($script:DesktopStarts -eq 1) 'Docker Desktop was not started automatically.' }
    $checks++
}
$env:DOCKER_HOST = $savedDockerHost
Write-Output ('PowerShell orchestration: ' + $checks + ' scenarios PASS (fake Windows/Docker/HTTP; no network).')
