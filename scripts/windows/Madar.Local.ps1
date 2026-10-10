# Windows PowerShell 5.1+; no Python, Node, Bash, elevation or global policy changes.
Set-StrictMode -Version 2.0

function Test-MadarWindows {
    return $env:OS -eq 'Windows_NT' -and $PSVersionTable.PSVersion -ge [version]'5.1'
}

function Invoke-MadarPrivateOperation {
    param(
        [ValidateSet('settings-directory', 'settings-file', 'legacy-env')][string]$Target,
        [ValidateSet('directory-create', 'path-inspection', 'drive-inspection', 'identity', 'acl-read', 'acl-construct', 'acl-write', 'acl-verify', 'legacy-copy', 'env-create', 'env-read', 'production-guard')][string]$Stage,
        [scriptblock]$Action
    )
    $ErrorActionPreference = 'Stop'
    try { & $Action } catch {
        # Never retain/print the original message, path, stack, inner exception or env.
        $cause = $_.Exception
        while ($cause.InnerException) { $cause = $cause.InnerException }
        $kind = switch ($cause.GetType().FullName) {
            'System.UnauthorizedAccessException' { 'access-denied' }
            'System.Security.SecurityException' { 'security-policy' }
            'System.Security.AccessControl.PrivilegeNotHeldException' { 'privilege-not-held' }
            'System.ArgumentException' { 'argument-error' }
            'System.Management.Automation.MethodException' { 'method-binding' }
            'System.Management.Automation.ParameterBindingException' { 'parameter-binding' }
            'System.IO.IOException' { 'io-error' }
            default { 'operation-error' }
        }
        $safe = 'Target={0}; Stage={1}; Kind={2}; Category={3}; HResult=0x{4:X8}.' -f $Target, $Stage, $kind, $_.CategoryInfo.Category, $cause.HResult
        $failure = [InvalidOperationException]::new('Private configuration operation failed.')
        $failure.Data['MadarPrivateDiagnostic'] = $safe
        throw $failure
    }
}

function Get-MadarPrivateIdentity {
    return [pscustomobject]@{
        Owner = [Security.Principal.WindowsIdentity]::GetCurrent().User
        System = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
    }
}

function Get-MadarDriveFormat {
    param([string]$Path)
    return [IO.DriveInfo]::new([IO.Path]::GetPathRoot($Path)).DriveFormat
}

function New-MadarPrivateRule {
    param($Identity, [Security.AccessControl.InheritanceFlags]$Inheritance)
    # Typed constructors and enums avoid New-Object's overload/string coercion.
    # ::new is supported by Windows PowerShell 5.1; no PowerShell 7 APIs required.
    return [Security.AccessControl.FileSystemAccessRule]::new(
        $Identity, [Security.AccessControl.FileSystemRights]::FullControl, $Inheritance,
        [Security.AccessControl.PropagationFlags]::None, [Security.AccessControl.AccessControlType]::Allow)
}

function Set-MadarPrivateAcl {
    param([string]$Path, $Acl, [switch]$Directory)
    # Set-Acl copies security-descriptor sections and may request owner/group/audit
    # privileges. Persist an Access-only descriptor directly instead.
    if ($Directory) {
        $accessOnly = [Security.AccessControl.DirectorySecurity]::new()
        $item = [IO.DirectoryInfo]::new($Path)
    } else {
        $accessOnly = [Security.AccessControl.FileSecurity]::new()
        $item = [IO.FileInfo]::new($Path)
    }
    $accessOnly.SetSecurityDescriptorBinaryForm($Acl.GetSecurityDescriptorBinaryForm(), [Security.AccessControl.AccessControlSections]::Access)
    if ($PSVersionTable.PSVersion.Major -le 5) {
        # .NET Framework instance API used by Windows PowerShell 5.1.
        $item.SetAccessControl($accessOnly)
    } else {
        # .NET Core exposes the same operation through extension APIs.
        [IO.FileSystemAclExtensions]::SetAccessControl($item, $accessOnly)
    }
}

function Test-MadarPrivateAcl {
    param($Acl, $Identity, [Security.AccessControl.InheritanceFlags]$Inheritance)
    if (-not $Acl.AreAccessRulesProtected -or $Acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $Identity.Owner.Value) { return $false }
    $rules = @($Acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
    if ($rules.Count -ne 2) { return $false }
    foreach ($sid in @($Identity.Owner, $Identity.System)) {
        $matching = @($rules | Where-Object { $_.IdentityReference.Value -eq $sid.Value })
        if ($matching.Count -ne 1) { return $false }
        $rule = $matching[0]
        if ($rule.IsInherited -or $rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
            $rule.FileSystemRights -ne [Security.AccessControl.FileSystemRights]::FullControl -or
            $rule.InheritanceFlags -ne $Inheritance -or $rule.PropagationFlags -ne [Security.AccessControl.PropagationFlags]::None) { return $false }
    }
    return $true
}

function Protect-MadarPath {
    param([string]$Path, [switch]$Directory, [ValidateSet('settings-directory', 'settings-file', 'legacy-env')][string]$Target = 'settings-file')
    $item = Invoke-MadarPrivateOperation $Target 'path-inspection' {
        $found = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
        if (($found.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $found.PSIsContainer -ne [bool]$Directory) {
            throw 'Private settings must have the expected type and must not be a reparse point.'
        }
        return $found
    }
    $null = Invoke-MadarPrivateOperation $Target 'drive-inspection' {
        if ((Get-MadarDriveFormat $item.FullName) -notin @('NTFS', 'ReFS')) { throw 'Local Windows access controls required.' }
    }
    $identity = Invoke-MadarPrivateOperation $Target 'identity' { Get-MadarPrivateIdentity }
    $acl = Invoke-MadarPrivateOperation $Target 'acl-read' { Get-Acl -LiteralPath $Path -ErrorAction Stop }
    $inherit = [Security.AccessControl.InheritanceFlags]::None
    if ($Directory) { $inherit = [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit' }
    $alreadyPrivate = Invoke-MadarPrivateOperation $Target 'acl-verify' {
        if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $identity.Owner.Value) {
            throw 'Private settings must already belong to the current Windows user; ownership will not be changed.'
        }
        Test-MadarPrivateAcl $acl $identity $inherit
    }
    if ($alreadyPrivate) { return }
    $null = Invoke-MadarPrivateOperation $Target 'acl-construct' {
        # Modify only the existing DACL. Do not mark owner/group/SACL for writing:
        # SetOwner on a fresh descriptor needlessly requests WRITE_OWNER privileges.
        $acl.SetAccessRuleProtection($true, $false)
        foreach ($rule in @($acl.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier]))) {
            $acl.RemoveAccessRuleSpecific($rule)
        }
        foreach ($sid in @($identity.Owner, $identity.System)) {
            $acl.AddAccessRule((New-MadarPrivateRule $sid $inherit))
        }
    }
    $null = Invoke-MadarPrivateOperation $Target 'acl-write' { Set-MadarPrivateAcl -Path $Path -Acl $acl -Directory:$Directory }
    $null = Invoke-MadarPrivateOperation $Target 'acl-verify' {
        $verified = Get-Acl -LiteralPath $Path -ErrorAction Stop
        if (-not (Test-MadarPrivateAcl $verified $identity $inherit)) { throw 'Private access rules could not be verified.' }
    }
}

function Get-MadarDockerInstallRoots {
    if ($env:ProgramFiles) { Join-Path $env:ProgramFiles 'Docker/Docker' }
    if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop' }
}

function New-MadarDockerFailure {
    param([ValidateSet('cli-not-found', 'compose-version-invalid', 'compose-version-too-old', 'command-failed', 'desktop-not-found')][string]$Code, [int]$ExitCode)
    $failure = [InvalidOperationException]::new('Docker prerequisite or operation failed.')
    $detail = 'DockerCode=' + $Code + '.'
    if ($PSBoundParameters.ContainsKey('ExitCode')) { $detail += ' ExitCode=' + $ExitCode + '.' }
    $failure.Data['MadarDockerDiagnostic'] = $detail
    return $failure
}

function Get-MadarDockerCommand {
    # Resolve the Windows executable explicitly; discard additional PATH matches.
    # Application-only lookup ignores aliases/functions and .cmd/.ps1 wrappers.
    $command = Get-Command docker.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command -and -not [string]::IsNullOrWhiteSpace($command.Source)) { return [string]$command.Source }
    foreach ($root in @(Get-MadarDockerInstallRoots)) {
        $candidate = Join-Path $root 'resources/bin/docker.exe'
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    throw (New-MadarDockerFailure 'cli-not-found')
}

function Get-MadarComposeVersion {
    param([AllowNull()][AllowEmptyString()][string]$Output)
    # Do not use PowerShell's mutable $Matches, including in compound conditions.
    # Accept official short/full output, v prefix and Desktop/build suffixes only.
    $found = [regex]::Match([string]$Output, '\A\s*(?:Docker Compose version\s+)?v?(?<version>\d+\.\d+\.\d+)(?:-[0-9A-Za-z][0-9A-Za-z.-]*)?(?:\+[0-9A-Za-z][0-9A-Za-z.-]*)?\s*\z', [Text.RegularExpressions.RegexOptions]::CultureInvariant)
    $parsed = $null
    if (-not $found.Success) { throw (New-MadarDockerFailure 'compose-version-invalid') }
    if (-not [version]::TryParse($found.Groups['version'].Value, [ref]$parsed)) { throw (New-MadarDockerFailure 'compose-version-invalid') }
    return $parsed
}

function Enter-MadarSetupLock {
    param($Mutex)
    try { return $Mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] {
        # WaitOne grants ownership when a previous launcher died holding the lock.
        return $true
    }
}

function Invoke-MadarDocker {
    param([string[]]$DockerArgs, [AllowNull()][string]$InputText)
    # Never echo argv, stdin, expanded Compose configuration, or captured output.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    # Native commands update the global automatic variable. A caller's local
    # LASTEXITCODE can shadow it, and failed launches can leave an old zero behind.
    $global:LASTEXITCODE = 127
    try {
        if ($PSBoundParameters.ContainsKey('InputText')) {
            $output = @($InputText | & $script:MadarDockerExe @DockerArgs 2>&1)
        } else {
            $output = @(& $script:MadarDockerExe @DockerArgs 2>&1)
        }
        $code = [int]$global:LASTEXITCODE
    } catch {
        $code = 127
        $output = @()  # Do not expose a native launch exception or argv/stdin.
    } finally { $ErrorActionPreference = $previous }
    return [pscustomobject]@{ ExitCode = $code; Output = ($output | Out-String).Trim() }
}

function Assert-MadarDocker {
    param([string[]]$DockerArgs, [AllowNull()][string]$InputText)
    $options = @{ DockerArgs = $DockerArgs }
    if ($PSBoundParameters.ContainsKey('InputText')) { $options.InputText = $InputText }
    $result = Invoke-MadarDocker @options
    if ($result.ExitCode -ne 0) { throw (New-MadarDockerFailure 'command-failed' -ExitCode $result.ExitCode) }
    return $result.Output
}

function Start-MadarDockerDesktop {
    foreach ($root in @(Get-MadarDockerInstallRoots)) {
        $desktop = Join-Path $root 'Docker Desktop.exe'
        if (Test-Path -LiteralPath $desktop -PathType Leaf) {
            Start-Process -FilePath $desktop -ErrorAction Stop | Out-Null
            return
        }
    }
    throw (New-MadarDockerFailure 'desktop-not-found')
}

function Test-MadarPortFree {
    param([int]$Port)
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
    try { $listener.Start(); return $true } catch { return $false } finally { $listener.Stop() }
}

function Test-MadarN8nPort {
    $client = [Net.Sockets.TcpClient]::new()
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
        $reader = [IO.StreamReader]::new($response.GetResponseStream())
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
        $detail = $Fail
        if ($_.Exception.Data.Contains('MadarPrivateDiagnostic')) { $detail += ' ' + $_.Exception.Data['MadarPrivateDiagnostic'] }
        if ($_.Exception.Data.Contains('MadarDockerDiagnostic')) { $detail += ' ' + $_.Exception.Data['MadarDockerDiagnostic'] }
        $Report[$Name] = [pscustomobject]@{ Component = $Name; Status = 'FAIL'; Detail = $detail }
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
        $mutex = [Threading.Mutex]::new($false, ('Local\MadarSetup-' + $identity))
        $locked = Enter-MadarSetupLock $mutex
        if (-not $locked) { $report['Windows PowerShell'].Status = 'FAIL'; $report['Windows PowerShell'].Detail = 'Another MADAR launcher is already running for this checkout.'; return $false }
        if (-not (Invoke-MadarStep $report 'Docker dependencies' {
            $script:MadarDockerExe = Get-MadarDockerCommand
            $composeOutput = Assert-MadarDocker @('compose', 'version', '--short')
            $composeVersion = Get-MadarComposeVersion $composeOutput
            if ($composeVersion -lt [version]'2.24.4') { throw (New-MadarDockerFailure 'compose-version-too-old') }
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
            $null = Invoke-MadarPrivateOperation 'settings-directory' 'directory-create' {
                if (-not (Test-Path -LiteralPath $state.Private -ErrorAction Stop)) { $null = New-Item -ItemType Directory -Path $state.Private -ErrorAction Stop }
            }
            Protect-MadarPath $state.Private -Directory -Target 'settings-directory'
            if (-not (Test-Path -LiteralPath $state.EnvFile)) {
                $legacy = Join-Path $RepoRoot '.env'
                if (Test-Path -LiteralPath $legacy) {
                    Protect-MadarPath $legacy -Target 'legacy-env'
                    $null = Invoke-MadarPrivateOperation 'settings-file' 'legacy-copy' { Copy-Item -LiteralPath $legacy -Destination $state.EnvFile -ErrorAction Stop }
                } else { $null = Invoke-MadarPrivateOperation 'settings-file' 'env-create' { [IO.File]::WriteAllText($state.EnvFile, '') } }
            }
            Protect-MadarPath $state.EnvFile
            $existing = Invoke-MadarPrivateOperation 'settings-file' 'env-read' { [IO.File]::ReadAllText($state.EnvFile) }
            $null = Invoke-MadarPrivateOperation 'settings-file' 'production-guard' {
                if ($existing -match '(?m)^\s*MADAR_ENV\s*=\s*["'']?production\b') { throw 'Production settings cannot be converted' }
            }
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
                $portProperty = $null
                if ($bindings) { $portProperty = $bindings.PSObject.Properties['8000/tcp'] }
                if ($portProperty -and $portProperty.Value) {
                    $binding = @($portProperty.Value)[0]
                    $hostPort = $binding.PSObject.Properties['HostPort']
                    if ($hostPort -and $hostPort.Value) { $ownPort = [int]$hostPort.Value }
                }
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
                $network = $null
                if ($networks) { $network = $networks.PSObject.Properties['madar-local'] }
                if (-not $network) { $null = Assert-MadarDocker @('network', 'connect', '--alias', 'n8n', 'madar-local', $state.N8nContainer) }
                else {
                    $aliases = $network.Value.PSObject.Properties['Aliases']
                    if ($aliases -and @($aliases.Value) -contains 'n8n') { return }
                    $ipProperty = $network.Value.PSObject.Properties['IPAddress']
                    if (-not $ipProperty -or -not $ipProperty.Value) { throw 'Existing n8n network has no IP address' }
                    $ip = [string]$ipProperty.Value
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
            $assetMatch = [regex]::Match($page.Content, 'src="(?<asset>/assets/[^"\s]+\.js)"')
            if ($page.StatusCode -ne 200 -or -not [regex]::IsMatch($page.Content, 'id="root"') -or -not $assetMatch.Success) { throw 'Frontend HTML missing' }
            $asset = $assetMatch.Groups['asset'].Value
            $bundle = Get-MadarHttp ($state.Url + $asset)
            if ($bundle.StatusCode -ne 200 -or $bundle.Content.Length -lt 100) { throw 'Frontend bundle missing' }
            $state.Frontend = $true
        } 'Built React dashboard HTML and JavaScript bundle are served.' 'Frontend HTML/bundle check failed; rebuild MADAR and retry.'
        $runtimeSafe = Invoke-MadarStep $report 'External sends disabled' {
            $code = "import os; assert os.getenv('MADAR_ALLOW_EXTERNAL_SEND') == 'false'; assert os.getenv('MADAR_ALLOW_MODEL_USAGE') == 'false'; print('disabled')"
            $null = Assert-MadarDocker ($state.Compose + @('exec', '-T', 'app', 'python', '-c', $code))
        } 'Real external messaging and billable model inference remain disabled.' 'Runtime safety flags were not verified; do not activate external delivery.'
        $prepared = Invoke-MadarStep $report 'Importable workflows' {
            $null = Assert-MadarDocker ($state.Helper + @('prepare'))
        } 'Ten inactive, callback-adjusted JSON files prepared in var/n8n-import/.' 'Workflow export failed; source JSON remains in workflows/.'
        $bridge = Invoke-MadarStep $report 'n8n API and bridge' {
            if (-not $state.N8nReady -or -not $state.Healthy -or -not $runtimeSafe) { throw 'Local prerequisite unavailable' }
            $helper = $state.Compose + @('run', '--rm', '--no-deps', '-T', '--volume', ($RepoRoot + ':/workspace'), '--workdir', '/workspace', '--entrypoint', 'python', '-e', 'MADAR_TEST_APP_URL=http://app:8000', 'app', '-m', 'scripts.local_n8n', '--env-file', '/workspace/.madar-local/.env', 'test', '--n8n-url', $state.Route)
            $null = Assert-MadarDocker $helper
        } 'n8n workflow-read permission and authenticated MADAR bridge verified; no dispatch called.' 'Check the local key/scopes and Docker-to-n8n routing. Native n8n must be reachable from Docker Desktop via host.docker.internal; Windows/WSL routes require local testing.'
        $null = Invoke-MadarStep $report 'Workflow import' {
            if (-not $bridge -or -not $prepared) { throw 'n8n check required' }
            $null = Assert-MadarDocker ($state.Helper + @('deploy', '--n8n-url', $state.Route))
        } 'Ten managed workflows imported/updated without activation; repeat runs reuse them.' 'Import failed. Check workflow/credential API scopes; deactivate managed workflows before updating; resolve any ambiguous same-name imports locally.'
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
