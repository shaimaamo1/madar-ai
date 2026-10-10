# Windows PowerShell 5.1+. No host Node/Python, resets, stashes, deletes or policy changes.
. (Join-Path $PSScriptRoot 'Madar.Local.ps1')

function Get-MadarGitCommand {
    $found = Get-Command git.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found -and $found.Source) { return [string]$found.Source }
    throw 'Git prerequisite unavailable.'
}

function Invoke-MadarGit {
    param([string[]]$GitArgs, [int[]]$AllowedCodes = @(0))
    # Capture all native output: it may contain remote URLs or credential diagnostics.
    $ErrorActionPreference = 'Continue'
    try {
        $lines = & $script:MadarGitExe @GitArgs 2>&1
        $code = $LASTEXITCODE
    } catch { throw 'Git operation unavailable.' }
    if ($code -notin $AllowedCodes) { throw 'Git operation failed; raw output omitted.' }
    return [pscustomobject]@{ Output = ($lines | Out-String).Trim(); ExitCode = $code }
}

function New-MadarUpdateBackup {
    param([string]$RepoRoot, [string]$Before)
    $private = Join-Path $RepoRoot '.madar-local'
    if (-not (Test-Path -LiteralPath $private)) { $null = New-Item -ItemType Directory -Path $private -ErrorAction Stop }
    Protect-MadarPath $private -Directory -Target 'settings-directory'
    $stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
    $backup = Join-Path $private ('backups/update-' + $stamp)
    $null = New-Item -ItemType Directory -Path $backup -ErrorAction Stop
    Protect-MadarPath $backup -Directory -Target 'settings-directory'
    $bundle = Join-Path $backup 'repository.bundle'
    # The code backup stays private. Ignored env files are never added to Git.
    $null = Invoke-MadarGit @('bundle', 'create', $bundle, '--all')
    Protect-MadarPath $bundle
    $script:MadarDockerExe = Get-MadarDockerCommand
    $version = Get-MadarComposeVersion (Assert-MadarDocker @('compose', 'version', '--short'))
    if ($version -lt [version]'2.24.4') { throw 'Compose minimum version required.' }
    if ($env:DOCKER_HOST -and $env:DOCKER_HOST -notmatch '^npipe:////\./pipe/') { throw 'Remote Docker override refused.' }
    $endpoint = Assert-MadarDocker @('context', 'inspect', '--format', '{{.Endpoints.docker.Host}}')
    if ($endpoint -notmatch '^npipe:////\./pipe/') { throw 'Local Docker Desktop required.' }
    $running = Assert-MadarDocker @('ps', '--filter', 'label=com.docker.compose.project=madar-ai', '--filter', 'label=com.docker.compose.service=app', '--format', '{{.ID}}')
    $containers = @($running -split "`r?`n" | Where-Object { $_.Trim() })
    if ($containers.Count -gt 1) { throw 'Multiple MADAR app containers; update refused.' }
    $recoveryImage = ''
    $databaseBackup = ''
    if ($containers.Count -eq 1) {
        $container = $containers[0].Trim()
        if ($container -notmatch '^[a-f0-9]{12,64}$') { throw 'Unexpected container identifier.' }
        $image = Assert-MadarDocker @('inspect', '--format', '{{.Image}}', $container)
        if ($image -notmatch '^sha256:[a-f0-9]{64}$') { throw 'Unexpected image identifier.' }
        $recoveryImage = 'madar-ai:recovery-' + $stamp.ToLowerInvariant()
        $null = Assert-MadarDocker @('image', 'tag', $image, $recoveryImage)
        $databaseBackup = '/app/var/backups/update-' + $stamp + '.sqlite3'
        # Online SQLite backup + integrity and isolated-restore checks in the current image.
        $null = Assert-MadarDocker @('exec', $container, 'python', '-m', 'scripts.backup', $databaseBackup)
    }
    # Safe references only: no env bytes, keys, HTTP bodies or Docker inspection dumps.
    $manifest = Join-Path $backup 'recovery.json'
    [IO.File]::WriteAllText($manifest, (@{ before = $Before; recovery_image = $recoveryImage; database_backup = $databaseBackup } | ConvertTo-Json))
    Protect-MadarPath $manifest
}

function Update-MadarLocal {
    param([string]$RepoRoot, [switch]$NoBrowser)
    $report = [ordered]@{}
    foreach ($name in @('Windows and Git', 'Clean update checkout', 'Fetch target branch', 'Recovery backup', 'Fast-forward update', 'MADAR startup')) {
        $report[$name] = [pscustomobject]@{ Component = $name; Status = 'FAIL'; Detail = 'Not completed because a prerequisite failed.' }
    }
    $state = @{}
    $mutex = $null
    $locked = $false
    $setupMutex = $null
    $setupLocked = $false
    Push-Location -LiteralPath $RepoRoot
    try {
        if (-not (Invoke-MadarStep $report 'Windows and Git' {
            if (-not (Test-MadarWindows)) { throw 'Windows required.' }
            $script:MadarGitExe = Get-MadarGitCommand
        } 'Windows PowerShell 5.1+ and Git available.' 'Install Git for Windows and use Windows PowerShell 5.1+.')) { return $false }
        # Serialize updates and block ordinary launchers until the merge finishes.
        $hash = [Security.Cryptography.SHA256]::Create()
        try { $identity = [BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($RepoRoot.ToLowerInvariant()))).Replace('-', '').Substring(0, 16) } finally { $hash.Dispose() }
        $mutex = [Threading.Mutex]::new($false, ('Local\MadarUpdate-' + $identity))
        $locked = Enter-MadarSetupLock $mutex
        if (-not $locked) { throw 'An update is already running.' }
        $setupMutex = [Threading.Mutex]::new($false, ('Local\MadarSetup-' + $identity))
        $setupLocked = Enter-MadarSetupLock $setupMutex
        if (-not $setupLocked) { throw 'A launcher is already running.' }
        if (-not (Invoke-MadarStep $report 'Clean update checkout' {
            $branch = (Invoke-MadarGit @('branch', '--show-current')).Output
            if ($branch -ne 'codex/self-hosted-n8n') { throw 'Unexpected branch.' }
            if ((Invoke-MadarGit @('status', '--porcelain', '--untracked-files=all')).Output) { throw 'Local modifications exist.' }
            $state.Before = (Invoke-MadarGit @('rev-parse', 'HEAD')).Output
            if ($state.Before -notmatch '^[a-f0-9]{40,64}$') { throw 'Invalid commit reference.' }
            # Refuse an unexpected remote rather than executing a user-modified URL.
            $origin = (Invoke-MadarGit @('config', '--get', 'remote.origin.url')).Output
            if ($origin -notmatch '^(https://github\.com/|git@github\.com:)shaimaamo1/madar-ai(?:\.git)?$') { throw 'Unexpected repository remote.' }
        } 'Expected branch/repository; clean tracked and untracked files. Ignored settings stay untouched.' 'Save local changes or resolve conflicts yourself; use the expected repository/branch. No changes were stashed, reset or overwritten.')) { return $false }
        if (-not (Invoke-MadarStep $report 'Fetch target branch' {
            $null = Invoke-MadarGit @('-c', 'credential.interactive=false', 'fetch', 'origin', 'codex/self-hosted-n8n')
            $state.Target = (Invoke-MadarGit @('rev-parse', 'FETCH_HEAD')).Output
            if ($state.Target -notmatch '^[a-f0-9]{40,64}$') { throw 'Invalid fetched reference.' }
            $ancestor = Invoke-MadarGit -GitArgs @('merge-base', '--is-ancestor', $state.Before, $state.Target) -AllowedCodes @(0,1)
            if ($ancestor.ExitCode -ne 0) { throw 'Branches diverged or local history is ahead.' }
        } 'Fetched expected branch and proved a fast-forward is possible.' 'Check Internet/GitHub access. Diverged or locally advanced history needs review; no forced merge or reset is attempted.')) { return $false }
        if (-not (Invoke-MadarStep $report 'Recovery backup' {
            New-MadarUpdateBackup -RepoRoot $RepoRoot -Before $state.Before
        } 'Private code bundle saved; running app image and verified SQLite backup retained when present.' 'Recovery preparation failed; application code has not been updated. Start local Docker Desktop and check private permissions.')) { return $false }
        if (-not (Invoke-MadarStep $report 'Fast-forward update' {
            # Check again after fetch/backup; refuse changes made while preparing.
            if ((Invoke-MadarGit @('status', '--porcelain', '--untracked-files=all')).Output -or (Invoke-MadarGit @('rev-parse','HEAD')).Output -ne $state.Before) { throw 'Checkout changed during update.' }
            $null = Invoke-MadarGit @('merge', '--ff-only', $state.Target)
        } 'Branch fast-forwarded. Private settings, n8n data and Docker volumes preserved.' 'Fast-forward failed; resolve the local checkout safely. No forced reset or data restore performed.')) { return $false }
        $setupMutex.ReleaseMutex()
        $setupLocked = $false
        if (-not (Invoke-MadarStep $report 'MADAR startup' {
            # Load the updated launcher after merging. The old app stays running
            # until the new image builds successfully; startup prints its own checks.
            . (Join-Path $RepoRoot 'scripts/windows/Madar.Local.ps1')
            if (-not (Start-MadarLocal -RepoRoot $RepoRoot -NoBrowser:$NoBrowser)) { throw 'Startup acceptance failed.' }
        } 'Updated application built, checked and started; existing workflows reused inactive.' 'Startup checks failed. Review the startup report. Recovery references are in private backups; no automatic destructive rollback was performed.')) { return $false }
        return $true
    } catch {
        Write-Host 'FAIL: Update prerequisite or concurrency check failed. Raw diagnostics omitted.'
        return $false
    } finally {
        if ($setupLocked) { $setupMutex.ReleaseMutex() }
        if ($setupMutex) { $setupMutex.Dispose() }
        if ($locked) { $mutex.ReleaseMutex() }
        if ($mutex) { $mutex.Dispose() }
        $report.Values | Format-Table Component, Status, Detail -Wrap -AutoSize | Out-Host
        Pop-Location
    }
}
