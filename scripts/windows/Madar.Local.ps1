# Windows PowerShell 5.1+; no Python, Node, Bash, elevation or global policy changes.
Set-StrictMode -Version 2.0

function Test-MadarWindows {
    return $env:OS -eq 'Windows_NT' -and $PSVersionTable.PSVersion -ge [version]'5.1'
}

function Protect-MadarPath {
    param([string]$Path, [switch]$Directory)
    if ((Get-Item -LiteralPath $Path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'Private settings must not be a junction or symbolic link.'
    }
    $drive = New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($Path))
    if ($drive.DriveFormat -notin @('NTFS', 'ReFS')) { throw 'Use a local folder supporting Windows access controls.' }
    $owner = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $system = New-Object Security.Principal.SecurityIdentifier 'S-1-5-18'
    if ($Directory) {
        $acl = New-Object Security.AccessControl.DirectorySecurity
        $inherit = [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
    } else {
        $acl = New-Object Security.AccessControl.FileSecurity
        $inherit = [Security.AccessControl.InheritanceFlags]::None
    }
    $acl.SetOwner($owner)
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($sid in @($owner, $system)) {
        $rule = New-Object Security.AccessControl.FileSystemAccessRule($sid, 'FullControl', $inherit, 'None', 'Allow')
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}

function Get-MadarDockerCommand {
    $command = Get-Command docker -CommandType Application -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $candidate = Join-Path $env:ProgramFiles 'Docker/Docker/resources/bin/docker.exe'
    if (Test-Path -LiteralPath $candidate) { return $candidate }
    throw 'Install Docker Desktop with Linux containers, then run this script again.'
}

function Invoke-MadarDocker {
    param([string[]]$DockerArgs, [AllowNull()][string]$InputText)
    # Never echo argv, stdin, expanded Compose configuration, or captured output.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        if ($PSBoundParameters.ContainsKey('InputText')) {
            $output = @($InputText | & $script:MadarDockerExe @DockerArgs 2>&1)
        } else {
            $output = @(& $script:MadarDockerExe @DockerArgs 2>&1)
        }
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previous }
    return [pscustomobject]@{ ExitCode = $code; Output = ($output | Out-String).Trim() }
}

function Assert-MadarDocker {
    param([string[]]$DockerArgs, [AllowNull()][string]$InputText)
    $options = @{ DockerArgs = $DockerArgs }
    if ($PSBoundParameters.ContainsKey('InputText')) { $options.InputText = $InputText }
    $result = Invoke-MadarDocker @options
    if ($result.ExitCode -ne 0) { throw 'Docker operation failed; captured output omitted to protect credentials.' }
    return $result.Output
}

function Start-MadarDockerDesktop {
    $desktop = Join-Path $env:ProgramFiles 'Docker/Docker/Docker Desktop.exe'
    if (-not (Test-Path -LiteralPath $desktop)) { throw 'Start Docker Desktop and enable Linux containers.' }
    Start-Process -FilePath $desktop | Out-Null
}

function Test-MadarPortFree {
    param([int]$Port)
    $listener = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, $Port)
    try { $listener.Start(); return $true } catch { return $false } finally { $listener.Stop() }
}

function Test-MadarN8nPort {
    $client = New-Object Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync('127.0.0.1', 5678)
        return $task.Wait(2500) -and $client.Connected
    } catch { return $false } finally { $client.Dispose() }
}

function Get-MadarHttp {
    param([string]$Url)
    $uri = [uri]$Url
    if (-not $uri.IsLoopback -or $uri.Scheme -notin @('http', 'https')) { throw 'Only local dashboard checks are supported.' }
    $request = [Net.HttpWebRequest]::Create($uri)
    $request.Proxy = $null
    $request.Timeout = 3000
    $request.AllowAutoRedirect = $false
    $response = $request.GetResponse()
    try {
        $reader = New-Object IO.StreamReader($response.GetResponseStream())
        try { $content = $reader.ReadToEnd() } finally { $reader.Dispose() }
        return [pscustomobject]@{ StatusCode = [int]$response.StatusCode; Content = $content }
    } finally { $response.Dispose() }
}

function Open-MadarDashboard {
    param([string]$Url)
    Start-Process -FilePath $Url | Out-Null
}

function Read-MadarApiKey {
    return Read-Host 'Local n8n API key (hidden; stays on this computer)' -AsSecureString
}

function Invoke-MadarInit {
    param([string[]]$DockerArgs, [switch]$Prompt)
    if (-not $Prompt) { $null = Assert-MadarDocker -DockerArgs $DockerArgs; return }
    $secure = Read-MadarApiKey
    $pointer = [IntPtr]::Zero
    $plain = $null
    try {
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        if ([string]::IsNullOrWhiteSpace($plain) -or $plain.Contains("`n") -or $plain.Contains("`r")) { throw 'A nonempty single-line key is required.' }
        # Key is sent only through stdin; never an argument or environment variable.
        $null = Assert-MadarDocker -DockerArgs ($DockerArgs + @('--api-key-stdin')) -InputText $plain
    } finally {
        $plain = $null
        if ($pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
        if ($secure) { $secure.Dispose() }
    }
}

function Invoke-MadarStep {
    param($Report, [string]$Name, [scriptblock]$Action, [string]$Pass, [string]$Fail)
    Write-Host ("Checking {0}..." -f $Name)
    try {
        $null = & $Action
        $Report[$Name] = [pscustomobject]@{ Component = $Name; Status = 'PASS'; Detail = $Pass }
        return $true
    } catch {
        # Exceptions/HTTP bodies/native stderr could contain sensitive values.
        $Report[$Name] = [pscustomobject]@{ Component = $Name; Status = 'FAIL'; Detail = $Fail }
        return $false
    }
}

function Start-MadarLocal {
    param([string]$RepoRoot, [switch]$ReplaceApiKey, [switch]$NoBrowser)
    $names = @('Windows PowerShell', 'Docker dependencies', 'Docker Desktop', 'Private configuration', 'Existing n8n port', 'Dashboard port', 'Docker build', 'Local settings', 'Backend startup', 'Backend health', 'Frontend health', 'External sends disabled', 'Importable workflows', 'n8n API and bridge', 'Workflow import')
    if (-not $NoBrowser) { $names += 'Dashboard browser' }
    $report = [ordered]@{}
    foreach ($name in $names) { $report[$name] = [pscustomobject]@{ Component = $name; Status = 'FAIL'; Detail = 'Not completed because a prerequisite failed.' } }
    $state = @{ Root = $RepoRoot; Port = 8000; Route = 'http://host.docker.internal:5678'; Callback = ''; Healthy = $false; N8nReady = $false }
    $originalPort = $env:MADAR_PORT
    $originalRoute = $env:N8N_CONTAINER_URL
    $mutex = $null
    $locked = $false
    Push-Location -LiteralPath $RepoRoot
    try {
        if (-not (Invoke-MadarStep $report 'Windows PowerShell' { if (-not (Test-MadarWindows)) { throw 'Windows required' } } 'Windows PowerShell 5.1+ available.' 'Run this launcher in Windows PowerShell 5.1+ on your laptop.')) { return $false }
        $hash = [Security.Cryptography.SHA256]::Create()
        try { $identity = [BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($RepoRoot.ToLowerInvariant()))).Replace('-', '').Substring(0, 16) } finally { $hash.Dispose() }
        $mutex = New-Object Threading.Mutex($false, ('Local\MadarSetup-' + $identity))
        $locked = $mutex.WaitOne(0)
        if (-not $locked) { $report['Windows PowerShell'].Status = 'FAIL'; $report['Windows PowerShell'].Detail = 'Another MADAR launcher is already running for this checkout.'; return $false }
        if (-not (Invoke-MadarStep $report 'Docker dependencies' {
            $script:MadarDockerExe = Get-MadarDockerCommand
            $version = Assert-MadarDocker @('compose', 'version', '--short')
            if ($version -notmatch '(\d+\.\d+\.\d+)' -or [version]$Matches[1] -lt [version]'2.24.4') { throw 'Compose version unsupported' }
        } 'Docker CLI and Compose 2.24.4+ available; host Python/Node/Bash unnecessary.' 'Install/update Docker Desktop with Compose 2.24.4+ and rerun.')) { return $false }
        if (-not (Invoke-MadarStep $report 'Docker Desktop' {
            if ($env:DOCKER_HOST -and $env:DOCKER_HOST -notmatch '^npipe:////\./pipe/') { throw 'A remote Docker override is not supported' }
            $endpoint = Assert-MadarDocker @('context', 'inspect', '--format', '{{.Endpoints.docker.Host}}')
            if ($endpoint -notmatch '^npipe:////\./pipe/') { throw 'Local Windows Docker Desktop context required' }
            $info = Invoke-MadarDocker @('info', '--format', '{{.OSType}}')
            if ($info.ExitCode -ne 0) {
                Start-MadarDockerDesktop
                for ($attempt = 0; $attempt -lt 45; $attempt++) {
                    Start-Sleep -Seconds 2
                    $info = Invoke-MadarDocker @('info', '--format', '{{.OSType}}')
                    if ($info.ExitCode -eq 0) { break }
                }
            }
            if ($info.ExitCode -ne 0 -or $info.Output.Trim() -ne 'linux') { throw 'Linux Docker not ready' }
        } 'Local Docker Desktop daemon ready in Linux-container mode.' 'Start Docker Desktop, select its local Linux-container context, and rerun. Remote Docker contexts are not supported.')) { return $false }
        if (-not (Invoke-MadarStep $report 'Private configuration' {
            $state.Private = Join-Path $RepoRoot '.madar-local'
            $state.EnvFile = Join-Path $state.Private '.env'
            $null = New-Item -ItemType Directory -Path $state.Private -Force
            Protect-MadarPath $state.Private -Directory
            if (-not (Test-Path -LiteralPath $state.EnvFile)) {
                $legacy = Join-Path $RepoRoot '.env'
                if (Test-Path -LiteralPath $legacy) { Protect-MadarPath $legacy; Copy-Item -LiteralPath $legacy -Destination $state.EnvFile } else { [IO.File]::WriteAllText($state.EnvFile, '') }
            }
            Protect-MadarPath $state.EnvFile
            $existing = [IO.File]::ReadAllText($state.EnvFile)
            if ($existing -match '(?m)^\s*MADAR_ENV\s*=\s*["'']?production\b') { throw 'Production settings cannot be converted' }
            $state.HasKey = $existing -match '(?m)^\s*N8N_API_KEY\s*=\s*[^\r\n]+' -and $existing -notmatch '(?m)^\s*N8N_API_KEY\s*=\s*(?:""|'''')?\s*$'
            $state.Compose = @('compose', '--project-name', 'madar-ai', '--env-file', $state.EnvFile, '-f', (Join-Path $RepoRoot 'docker-compose.windows.yml'))
        } 'Ignored settings restricted to your Windows account and SYSTEM; existing tokens preserved.' 'Use a local NTFS/ReFS checkout with writable permissions and development settings. Private ACL/configuration check failed.')) { return $false }
        $null = Invoke-MadarStep $report 'Existing n8n port' {
            if (-not (Test-MadarN8nPort)) { throw 'No existing n8n listener' }
            $containers = Assert-MadarDocker @('ps', '--filter', 'publish=5678', '--format', '{{.Image}}|{{.ID}}')
            $candidates = @($containers -split "`r?`n" | Where-Object { $_ -match '^.+\|[a-f0-9]+$' })
            if ($candidates.Count -gt 1) { throw 'Ambiguous existing n8n containers' }
            if ($candidates.Count -eq 1) { $state.N8nContainer = ($candidates[0] -split '\|')[-1]; $state.Route = 'http://n8n:5678' }
            $state.N8nReady = $true
        } 'Your existing local n8n is listening on 5678; no n8n container will be created.' 'Start your existing n8n on Windows localhost:5678; keep only one intended n8n container publishing that port.'
        if (-not (Invoke-MadarStep $report 'Dashboard port' {
            $own = Assert-MadarDocker ($state.Compose + @('ps', '-q', 'app'))
            $ownPort = 0
            if ($own) {
                $bindings = (Assert-MadarDocker @('inspect', '--format', '{{json .NetworkSettings.Ports}}', $own.Trim()) | ConvertFrom-Json)
                if ($bindings.'8000/tcp') { $ownPort = [int]$bindings.'8000/tcp'[0].HostPort }
            }
            for ($port = 8000; $port -le 8010; $port++) {
                if ($port -eq $ownPort -or (Test-MadarPortFree $port)) { $state.Port = $port; $state.PortFound = $true; break }
            }
            if (-not $state.PortFound) { throw 'All dashboard ports occupied' }
            $state.Url = 'http://localhost:' + $state.Port
            $state.Callback = $state.Url
            if ($state.ContainsKey('N8nContainer')) { $state.Callback = 'http://app:8000' }
            $env:MADAR_PORT = [string]$state.Port
            $env:N8N_CONTAINER_URL = $state.Route
        } 'Available dashboard port selected automatically (8000-8010).' 'Free one port from 8000-8010; existing unrelated listeners are never stopped.')) { return $false }
        if (-not (Invoke-MadarStep $report 'Docker build' {
            Write-Host 'Building MADAR; the first run downloads dependencies and can take several minutes.'
            $null = Assert-MadarDocker ($state.Compose + @('build', 'app'))
        } 'Backend and production frontend built in Docker.' 'Docker build failed. Check Docker Desktop resources and Internet access to image/npm/Python registries, then rerun.')) { return $false }
        $state.Helper = $state.Compose + @('run', '--rm', '--no-deps', '-T', '--interactive', '--volume', ($RepoRoot + ':/workspace'), '--workdir', '/workspace', '--entrypoint', 'python', 'app', '-m', 'scripts.local_n8n', '--env-file', '/workspace/.madar-local/.env')
        if (-not (Invoke-MadarStep $report 'Local settings' {
            $initOptions = $state.Helper + @('init', '--n8n-url', 'http://localhost:5678', '--container-url', $state.Route, '--callback-url', $state.Callback, '--public-url', $state.Url, '--disable-external')
            Invoke-MadarInit $initOptions -Prompt:($ReplaceApiKey -or -not $state.HasKey)
            Protect-MadarPath $state.EnvFile
            $null = Assert-MadarDocker ($state.Compose + @('config', '--quiet'))
        } 'API key stored privately without logging; local tokens and URLs configured.' 'Local initialization failed. Enter a valid single-line key and verify private settings/permissions.')) { return $false }
        if (-not (Invoke-MadarStep $report 'Backend startup' {
            $null = Assert-MadarDocker ($state.Compose + @('up', '-d', '--no-build', 'app'))
            if ($state.ContainsKey('N8nContainer')) {
                # Avoid embedded quotes in native argv: Windows PowerShell 5.1
                # uses legacy argument marshalling. Parse the JSON locally.
                $networks = Assert-MadarDocker @('inspect', '--format', '{{json .NetworkSettings.Networks}}', $state.N8nContainer) | ConvertFrom-Json
                $network = $networks.PSObject.Properties['madar-local']
                if (-not $network) { $null = Assert-MadarDocker @('network', 'connect', '--alias', 'n8n', 'madar-local', $state.N8nContainer) }
                elseif (@($network.Value.Aliases) -notcontains 'n8n') {
                    $ip = [string]$network.Value.IPAddress
                    if (-not $ip) { throw 'Existing n8n network has no IP address' }
                    $state.Route = 'http://' + $ip + ':5678'
                    $env:N8N_CONTAINER_URL = $state.Route
                    $null = Assert-MadarDocker ($state.Helper + @('init', '--container-url', $state.Route))
                    $null = Assert-MadarDocker ($state.Compose + @('up', '-d', '--no-build', 'app'))
                }
            }
        } 'MADAR app started; existing n8n reused without account/volume changes.' 'Could not start MADAR or attach existing n8n. Check Docker Desktop networking and the selected app port.')) { return $false }
        $null = Invoke-MadarStep $report 'Backend health' {
            for ($attempt = 0; $attempt -lt 30; $attempt++) {
                try {
                    $health = (Get-MadarHttp ($state.Url + '/api/health')).Content | ConvertFrom-Json
                    if ($health.service -eq 'madar-ai' -and $health.status -eq 'ok') { $state.Healthy = $true; break }
                } catch { }
                Start-Sleep -Seconds 1
            }
            if (-not $state.Healthy) { throw 'API/database not ready' }
        } 'Backend API and SQLite database healthy.' 'Backend health failed. Inspect MADAR Docker app logs locally; do not share credentials or expanded Compose settings.'
        $null = Invoke-MadarStep $report 'Frontend health' {
            if (-not $state.Healthy) { throw 'Backend not ready' }
            $page = Get-MadarHttp $state.Url
            if ($page.StatusCode -ne 200 -or $page.Content -notmatch 'id="root"' -or $page.Content -notmatch 'src="(/assets/[^"\s]+\.js)"') { throw 'Frontend HTML missing' }
            $asset = $Matches[1]
            $bundle = Get-MadarHttp ($state.Url + $asset)
            if ($bundle.StatusCode -ne 200 -or $bundle.Content.Length -lt 100) { throw 'Frontend bundle missing' }
            $state.Frontend = $true
        } 'Built React dashboard HTML and JavaScript bundle are served.' 'Frontend HTML/bundle check failed; rebuild MADAR and retry.'
        $null = Invoke-MadarStep $report 'External sends disabled' {
            $code = "import os; assert os.getenv('MADAR_ALLOW_EXTERNAL_SEND') == 'false'; assert os.getenv('MADAR_ALLOW_MODEL_USAGE') == 'false'; print('disabled')"
            $null = Assert-MadarDocker ($state.Compose + @('exec', '-T', 'app', 'python', '-c', $code))
        } 'Real external messaging and billable model inference remain disabled.' 'Runtime safety flags were not verified; do not activate external delivery.'
        $prepared = Invoke-MadarStep $report 'Importable workflows' {
            $null = Assert-MadarDocker ($state.Helper + @('prepare'))
        } 'Four inactive, callback-adjusted JSON files prepared in var/n8n-import/.' 'Workflow export failed; source JSON remains in workflows/.'
        $bridge = Invoke-MadarStep $report 'n8n API and bridge' {
            if (-not $state.N8nReady -or -not $state.Healthy) { throw 'Local prerequisite unavailable' }
            $helper = $state.Compose + @('run', '--rm', '--no-deps', '-T', '--volume', ($RepoRoot + ':/workspace'), '--workdir', '/workspace', '--entrypoint', 'python', '-e', 'MADAR_TEST_APP_URL=http://app:8000', 'app', '-m', 'scripts.local_n8n', '--env-file', '/workspace/.madar-local/.env', 'test', '--n8n-url', $state.Route)
            $null = Assert-MadarDocker $helper
        } 'n8n workflow-read permission and authenticated MADAR bridge verified; no dispatch called.' 'Check the local key/scopes and Docker-to-n8n routing. Native n8n must be reachable from Docker Desktop via host.docker.internal; Windows/WSL routes require local testing.'
        $null = Invoke-MadarStep $report 'Workflow import' {
            if (-not $bridge -or -not $prepared) { throw 'n8n check required' }
            $null = Assert-MadarDocker ($state.Helper + @('deploy', '--n8n-url', $state.Route))
        } 'Four managed workflows imported/updated without activation; repeat runs reuse them.' 'Import failed. Check workflow/credential API scopes; deactivate managed workflows before updating; resolve any ambiguous same-name imports locally.'
        if (-not $NoBrowser) {
            $null = Invoke-MadarStep $report 'Dashboard browser' {
                if (-not $state.Healthy -or -not $state.Frontend) { throw 'Dashboard not ready' }
                Open-MadarDashboard $state.Url
            } 'Ready dashboard opened in your default browser.' 'Open the reported dashboard URL manually if browser launch is blocked.'
        }
        return @($report.Values | Where-Object { $_.Status -eq 'FAIL' }).Count -eq 0
    } finally {
        $env:MADAR_PORT = $originalPort
        $env:N8N_CONTAINER_URL = $originalRoute
        if ($locked) { $mutex.ReleaseMutex() }
        if ($mutex) { $mutex.Dispose() }
        Write-Host ''
        $report.Values | Format-Table Component, Status, Detail -Wrap -AutoSize | Out-Host
        if ($state.ContainsKey('Url')) { Write-Host ('Dashboard: ' + $state.Url) }
        try {
            $directory = Join-Path $RepoRoot 'var'
            $null = New-Item -ItemType Directory -Path $directory -Force
            $reportPath = Join-Path $directory 'windows-setup-report.json'
            $report.Values | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $reportPath -Encoding UTF8
            Write-Host 'PASS/FAIL report saved to var/windows-setup-report.json (no secrets).'
        } catch { Write-Host 'FAIL: Could not save the report; console results are shown above.' }
        Pop-Location
    }
}
