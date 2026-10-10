# Portable regression tests exercise the actual permission algorithm with fake ACLs.
# Only the Windows OS ACL boundary is replaced; no Docker, provider or network calls.
param([string]$RepoRoot, [string]$OutputRoot)
$ErrorActionPreference = 'Stop'
. (Join-Path $RepoRoot 'scripts/windows/Madar.Local.ps1')
function Assert-Test { param([bool]$Condition, [string]$Message) if (-not $Condition) { throw $Message } }
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.AccessControl;
public class MadarTestSid { public string Value; public MadarTestSid(string value) { Value = value; } }
public class MadarTestRule {
    public MadarTestSid IdentityReference;
    public FileSystemRights FileSystemRights = FileSystemRights.FullControl;
    public InheritanceFlags InheritanceFlags;
    public PropagationFlags PropagationFlags = PropagationFlags.None;
    public AccessControlType AccessControlType = AccessControlType.Allow;
    public bool IsInherited;
}
public class MadarTestAcl {
    public MadarTestSid Owner;
    public bool AreAccessRulesProtected;
    public List<MadarTestRule> Rules = new List<MadarTestRule>();
    public MadarTestSid GetOwner(Type ignored) { return Owner; }
    public MadarTestRule[] GetAccessRules(bool explicitRules, bool inheritedRules, Type ignored) {
        return Rules.Where(r => r.IsInherited ? inheritedRules : explicitRules).ToArray();
    }
    public void SetAccessRuleProtection(bool protect, bool preserve) {
        AreAccessRulesProtected = protect;
        if (protect && !preserve) Rules.RemoveAll(r => r.IsInherited);
    }
    public void RemoveAccessRuleSpecific(MadarTestRule rule) { Rules.Remove(rule); }
    public void AddAccessRule(MadarTestRule rule) { Rules.Add(rule); }
    public MadarTestAcl Copy() {
        var copy = new MadarTestAcl { Owner = Owner, AreAccessRulesProtected = AreAccessRulesProtected };
        copy.Rules.AddRange(Rules);
        return copy;
    }
}
'@
$script:OwnerSid = [MadarTestSid]::new('S-1-5-21-fixture')
$script:SystemSid = [MadarTestSid]::new('S-1-5-18')
function Get-MadarPrivateIdentity { return [pscustomobject]@{ Owner = $script:OwnerSid; System = $script:SystemSid } }
function Get-MadarDriveFormat { param([string]$Path) return $script:DriveFormat }
function New-MadarPrivateRule {
    param($Identity, [Security.AccessControl.InheritanceFlags]$Inheritance)
    $rule = [MadarTestRule]::new()
    $rule.IdentityReference = $Identity; $rule.InheritanceFlags = $Inheritance
    return $rule
}
function Get-Acl {
    [CmdletBinding()]param([string]$LiteralPath)
    $script:Reads++
    if ($script:ReadFails) { throw [UnauthorizedAccessException]::new('secret-env-value username private-path') }
    return $script:StoredAcl.Copy()
}
function Set-MadarPrivateAcl {
    param([string]$Path, $Acl, [switch]$Directory)
    $script:Writes++
    if ($script:WriteFails) { throw [UnauthorizedAccessException]::new('secret-env-value username private-path') }
    if (-not $script:IgnoreWrite) { $script:StoredAcl = $Acl.Copy() }
}
function Get-Item {
    [CmdletBinding()]param([string]$LiteralPath, [switch]$Force)
    $item = Microsoft.PowerShell.Management\Get-Item -LiteralPath $LiteralPath -Force:$Force -ErrorAction Stop
    if ($script:Reparse) { return [pscustomobject]@{ Attributes = [IO.FileAttributes]::ReparsePoint; PSIsContainer = $item.PSIsContainer; FullName = $item.FullName } }
    return $item
}
function Reset-Fixture {
    param([bool]$Directory = $false, [bool]$Private = $false)
    $script:DriveFormat = 'NTFS'; $script:Writes = 0; $script:Reads = 0
    $script:ReadFails = $false; $script:WriteFails = $false; $script:IgnoreWrite = $false; $script:Reparse = $false
    $script:StoredAcl = [MadarTestAcl]::new(); $script:StoredAcl.Owner = $script:OwnerSid
    $script:Inheritance = [Security.AccessControl.InheritanceFlags]::None
    if ($Directory) { $script:Inheritance = [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit' }
    if ($Private) {
        $script:StoredAcl.AreAccessRulesProtected = $true
        foreach ($sid in @($script:OwnerSid, $script:SystemSid)) { $script:StoredAcl.AddAccessRule((New-MadarPrivateRule $sid $script:Inheritance)) }
    } else {
        $outsider = New-MadarPrivateRule ([MadarTestSid]::new('S-1-1-0')) $script:Inheritance
        $outsider.IsInherited = $true; $script:StoredAcl.AddAccessRule($outsider)
    }
}
function Assert-SafeFailure {
    param([string]$Stage, [scriptblock]$Action)
    $report = [ordered]@{}
    $ok = Invoke-MadarStep $report 'Private configuration' $Action 'private' 'Private check failed.'
    Assert-Test (-not $ok) 'Unsafe configuration was accepted.'
    $json = $report.Values | ConvertTo-Json -Depth 4
    Assert-Test ($json -match ('Stage=' + $Stage + ';')) ('Wrong diagnostic stage: ' + $Stage)
    Assert-Test ($json -notmatch 'secret-env-value|username|private-path') 'Original exception leaked.'
}
$null = New-Item -ItemType Directory -Path $OutputRoot -Force
$file = Join-Path $OutputRoot '.env'
[IO.File]::WriteAllText($file, "N8N_API_KEY=secret-env-value`r`nMADAR_BRIDGE_TOKEN=preserve-test-bridge`r`n")
$before = [IO.File]::ReadAllBytes($file)
$checks = 0
foreach ($directory in @($false, $true)) {
    $path = if ($directory) { $OutputRoot } else { $file }
    foreach ($already in @($false, $true)) {
        Reset-Fixture -Directory:$directory -Private:$already
        Protect-MadarPath $path -Directory:$directory
        $expectedWrites = if ($already) { 0 } else { 1 }
        Assert-Test ($script:Writes -eq $expectedWrites) 'Private ACL should be reused; permissive ACL must be replaced.'
        Assert-Test (Test-MadarPrivateAcl $script:StoredAcl (Get-MadarPrivateIdentity) $script:Inheritance) 'Resulting ACL grants excess or insufficient access.'
        Assert-Test ($script:StoredAcl.Owner.Value -eq $script:OwnerSid.Value) 'Ownership changed.'
        Protect-MadarPath $path -Directory:$directory
        Assert-Test ($script:Writes -eq $expectedWrites) 'Repeat protection unexpectedly wrote ACL.'
        $checks++
    }
}
Reset-Fixture -Private:$true
$script:StoredAcl.AddAccessRule((New-MadarPrivateRule ([MadarTestSid]::new('S-1-1-0')) $script:Inheritance))
Protect-MadarPath $file
Assert-Test ($script:Writes -eq 1 -and $script:StoredAcl.Rules.Count -eq 2) 'Protected ACL with extra user was trusted.'
$checks++
Reset-Fixture -Private:$true
$script:StoredAcl.Rules[0].FileSystemRights = [Security.AccessControl.FileSystemRights]::Read
Protect-MadarPath $file
Assert-Test ($script:Writes -eq 1) 'Insufficient owner rights were not repaired.'
$checks++
Reset-Fixture -Directory:$true -Private:$true
$script:StoredAcl.Rules[0].InheritanceFlags = [Security.AccessControl.InheritanceFlags]::None
Protect-MadarPath $OutputRoot -Directory
Assert-Test ($script:Writes -eq 1) 'Missing directory inheritance was not repaired.'
$checks++
Reset-Fixture
$script:StoredAcl.Owner = [MadarTestSid]::new('S-1-5-21-other')
Assert-SafeFailure 'acl-verify' { Protect-MadarPath $file }
Assert-Test ($script:Writes -eq 0) 'Foreign ownership was taken over.'
$checks++
Reset-Fixture
$script:WriteFails = $true
Assert-SafeFailure 'acl-write' { Protect-MadarPath $file }
$checks++
Reset-Fixture
$script:ReadFails = $true
Assert-SafeFailure 'acl-read' { Protect-MadarPath $file }
$checks++
Reset-Fixture
$script:IgnoreWrite = $true
Assert-SafeFailure 'acl-verify' { Protect-MadarPath $file }
$checks++
Reset-Fixture
$script:Reparse = $true
Assert-SafeFailure 'path-inspection' { Protect-MadarPath $file }
Assert-Test ($script:Reads -eq 0 -and $script:Writes -eq 0) 'Reparse point was accessed.'
$checks++
Reset-Fixture
$script:DriveFormat = 'FAT32'
Assert-SafeFailure 'drive-inspection' { Protect-MadarPath $file }
Assert-Test ($script:Reads -eq 0 -and $script:Writes -eq 0) 'Unsupported filesystem ACL was accessed.'
$checks++
Reset-Fixture
Assert-SafeFailure 'path-inspection' { Protect-MadarPath $OutputRoot }
$checks++
Assert-SafeFailure 'env-read' { Invoke-MadarPrivateOperation 'settings-file' 'env-read' { throw [IO.IOException]::new('secret-env-value username private-path') } }
$checks++
Assert-SafeFailure 'acl-construct' { Invoke-MadarPrivateOperation 'settings-file' 'acl-construct' { throw [ArgumentException]::new('secret-env-value username private-path') } }
$checks++
Assert-Test ([Convert]::ToBase64String($before) -eq [Convert]::ToBase64String([IO.File]::ReadAllBytes($file))) 'Existing env bytes changed.'
Write-Output ('Private ACL algorithm: ' + $checks + ' scenarios PASS (simulated OS ACLs; Windows not verified).')
