# Windows-only candidate; this script never reserves names, signs, uploads, or publishes.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$IdentityName,
    [Parameter(Mandatory=$true)][string]$Publisher,
    [Parameter(Mandatory=$true)][string]$PublisherDisplayName,
    [Parameter(Mandatory=$true)][string]$DisplayName,
    [Parameter(Mandatory=$true)][string]$ExePath,
    [Parameter(Mandatory=$true)][string]$AssetsDirectory,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+\.0$')][string]$Version
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$ExpectedBranch = 'codex/store-p1-image-privacy-20261023'
function Invoke-GitText {
    param([string[]]$GitArguments)
    $Output = & git @GitArguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Git command failed (exit $LASTEXITCODE): git $($GitArguments -join ' '); output: $Output" }
    return ($Output | Out-String).Trim()
}
Set-Location -LiteralPath $Root
$RemoteUrl = Invoke-GitText -GitArguments @('remote','get-url','origin')
if ($RemoteUrl -notmatch '(?i)github[.]com[:/]shihuiarenjinba-png/-Screenshot-Image-Privacy-Cleaner(?:[.]git)?$') { throw 'Wrong origin repository.' }
Invoke-GitText -GitArguments @('fetch','origin') | Out-Null
$Branch = Invoke-GitText -GitArguments @('branch','--show-current')
$SourceSha = Invoke-GitText -GitArguments @('rev-parse','HEAD')
$RemoteSha = Invoke-GitText -GitArguments @('rev-parse',('origin/' + $ExpectedBranch))
$DirtyState = Invoke-GitText -GitArguments @('status','--porcelain','--untracked-files=all')
if ($Branch -cne $ExpectedBranch) { throw "Wrong working branch: $Branch" }
if ($SourceSha -notmatch '^[0-9a-f]{40}$' -or $RemoteSha -cne $SourceSha) { throw 'Local and remote HEAD must be identical.' }
if ($DirtyState) { throw 'Uncommitted or untracked changes exist; stopped before packaging.' }
$AppExe = 'ImagePrivacyCleaner.exe'
$Description = 'Image privacy processing tool'
if ($IdentityName -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{1,48}$' -or
    $IdentityName -match '(?i)(placeholder|example|testidentity|yourname)') {
    throw 'Enter the exact Package Identity Name from this app in Partner Center, not a guess.'
}
if ($Publisher -notmatch '^CN=.+$' -or $Publisher -match '(?i)(placeholder|example|yourname)' -or
    [string]::IsNullOrWhiteSpace($PublisherDisplayName) -or
    [string]::IsNullOrWhiteSpace($DisplayName)) {
    throw 'Publisher/PublisherDisplayName/DisplayName must match the real Partner Center record.'
}
$fields = $Version.Split('.')
if ([int]$fields[0] -lt 1 -or ($fields | Where-Object { [long]$_ -gt 65535 }).Count -gt 0) {
    throw 'Invalid MSIX version; each field <=65535, major >=1, and the last component = 0.'
}
if (-not (Test-Path -LiteralPath $ExePath -PathType Leaf)) { throw "Missing EXE: $ExePath" }
if (-not (Test-Path -LiteralPath $AssetsDirectory -PathType Container)) {
    throw 'Missing approved brand assets folder. Do not use fake placeholder artwork.'
}
$MakeAppx = (Get-Command MakeAppx.exe -ErrorAction SilentlyContinue)
if ($null -eq $MakeAppx) {
    throw 'MakeAppx.exe not on PATH. Install Windows SDK and use its x64 bin folder.'
}
$Output = Join-Path $Root 'dist-store'
$PackagePath = Join-Path $Output ("ImagePrivacyCleaner_" + $Version + '_x64.msix')
if (Test-Path -LiteralPath $PackagePath) { throw 'Existing MSIX cannot be replaced; increment version and QA it.' }
$Stage = Join-Path $env:TEMP ('ImagePrivacyCleaner-stage-' + [guid]::NewGuid().ToString('N'))
$Roundtrip = Join-Path $env:TEMP ('ImagePrivacyCleaner-verify-' + [guid]::NewGuid().ToString('N'))
$created = $false
try {
    New-Item -ItemType Directory -Path (Join-Path $Stage 'Assets') -Force | Out-Null
    Copy-Item -LiteralPath $ExePath -Destination (Join-Path $Stage $AppExe) -ErrorAction Stop
    Set-Content -LiteralPath (Join-Path $Stage 'SOURCE_GIT_COMMIT.txt') -Value $SourceSha -Encoding ASCII
    foreach ($item in @(
        @('StoreLogo.png',50,50),
        @('Square44x44Logo.png',44,44),
        @('Square150x150Logo.png',150,150)
    )) {
        $filename = [string]$item[0]
        $original = Join-Path $AssetsDirectory $filename
        if (-not (Test-Path -LiteralPath $original -PathType Leaf)) { throw "Missing approved PNG: $filename" }
        $bytes = [IO.File]::ReadAllBytes($original)
        if ($bytes.Length -lt 24 -or $bytes[0] -ne 137 -or $bytes[1] -ne 80 -or
            $bytes[2] -ne 78 -or $bytes[3] -ne 71 -or $bytes[12] -ne 73 -or
            $bytes[13] -ne 72 -or $bytes[14] -ne 68 -or $bytes[15] -ne 82) {
            throw "Invalid PNG signature/IHDR: $filename"
        }
        $width = 0; $height = 0
        for ($i=16; $i -lt 20; $i++) { $width = ($width * 256) + [int]$bytes[$i] }
        for ($i=20; $i -lt 24; $i++) { $height = ($height * 256) + [int]$bytes[$i] }
        if ($width -ne [int]$item[1] -or $height -ne [int]$item[2]) {
            throw "Wrong PNG dimensions for $filename : $width x $height"
        }
        Copy-Item -LiteralPath $original -Destination (Join-Path (Join-Path $Stage 'Assets') $filename)
    }
    $id = [Security.SecurityElement]::Escape($IdentityName)
    $pub = [Security.SecurityElement]::Escape($Publisher)
    $pubname = [Security.SecurityElement]::Escape($PublisherDisplayName)
    $display = [Security.SecurityElement]::Escape($DisplayName)
    $manifest = @"
<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
         xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
         xmlns:uap10="http://schemas.microsoft.com/appx/manifest/uap/windows10/10"
         xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
         IgnorableNamespaces="uap uap10 rescap">
  <Identity Name="$id" Publisher="$pub" Version="$Version" ProcessorArchitecture="x64"/>
  <Properties>
    <DisplayName>$display</DisplayName>
    <PublisherDisplayName>$pubname</PublisherDisplayName>
    <Logo>Assets\StoreLogo.png</Logo>
  </Properties>
  <Resources><Resource Language="ja-JP"/></Resources>
  <Dependencies><TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.19041.0" MaxVersionTested="10.0.26100.0"/></Dependencies>
  <Applications>
    <Application Id="App" Executable="$AppExe" uap10:RuntimeBehavior="packagedClassicApp"
                 uap10:TrustLevel="mediumIL">
      <uap:VisualElements DisplayName="$display" Description="$Description"
          BackgroundColor="transparent"
          Square150x150Logo="Assets\Square150x150Logo.png"
          Square44x44Logo="Assets\Square44x44Logo.png"/>
    </Application>
  </Applications>
  <Capabilities><rescap:Capability Name="runFullTrust"/></Capabilities>
</Package>
"@
    [xml]$Xml = $manifest
    if ($Xml.Package.Identity.Name -ne $IdentityName -or $Xml.Package.Identity.Publisher -ne $Publisher) {
        throw 'Identity did not roundtrip; refusing to package.'
    }
    [IO.File]::WriteAllText((Join-Path $Stage 'AppxManifest.xml'), $manifest,
        (New-Object Text.UTF8Encoding($false)))
    if (-not (Test-Path -LiteralPath $Output)) { New-Item -ItemType Directory -Path $Output | Out-Null }
    & $MakeAppx.Source pack /d $Stage /p $PackagePath
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $PackagePath -PathType Leaf)) {
        throw 'MakeAppx packaging failed.'
    }
    $created = $true
    New-Item -ItemType Directory -Path $Roundtrip | Out-Null
    & $MakeAppx.Source unpack /p $PackagePath /d $Roundtrip
    if ($LASTEXITCODE -ne 0) { throw 'MSIX unpack verification failed.' }
    [xml]$RoundtripManifest = Get-Content -LiteralPath (Join-Path $Roundtrip 'AppxManifest.xml') -Raw -Encoding UTF8
    $Ns = New-Object System.Xml.XmlNamespaceManager($RoundtripManifest.NameTable)
    $Ns.AddNamespace('f','http://schemas.microsoft.com/appx/manifest/foundation/windows10')
    $Ns.AddNamespace('uap','http://schemas.microsoft.com/appx/manifest/uap/windows10')
    $IdNode = $RoundtripManifest.SelectSingleNode('/f:Package/f:Identity',$Ns)
    $PropsNode = $RoundtripManifest.SelectSingleNode('/f:Package/f:Properties',$Ns)
    $VisualNode = $RoundtripManifest.SelectSingleNode('/f:Package/f:Applications/f:Application/uap:VisualElements',$Ns)
    $DisplayNode = if ($null -ne $PropsNode) { $PropsNode.SelectSingleNode('f:DisplayName',$Ns) } else { $null }
    $PublisherNode = if ($null -ne $PropsNode) { $PropsNode.SelectSingleNode('f:PublisherDisplayName',$Ns) } else { $null }
    if ($null -eq $IdNode -or $null -eq $DisplayNode -or $null -eq $PublisherNode -or $null -eq $VisualNode -or
        $IdNode.GetAttribute('Name') -cne $IdentityName -or $IdNode.GetAttribute('Publisher') -cne $Publisher -or
        $IdNode.GetAttribute('Version') -cne $Version -or $IdNode.GetAttribute('ProcessorArchitecture') -cne 'x64' -or
        $DisplayNode.InnerText -cne $DisplayName -or $PublisherNode.InnerText -cne $PublisherDisplayName -or
        $VisualNode.GetAttribute('DisplayName') -cne $DisplayName) {
        throw 'Unpacked MSIX manifest does not match the requested Store identity.'
    }
    $EmbeddedSource = (Get-Content -LiteralPath (Join-Path $Roundtrip 'SOURCE_GIT_COMMIT.txt') -Raw -Encoding ASCII).Trim()
    if ($EmbeddedSource -cne $SourceSha) { throw 'Embedded source commit does not match build HEAD.' }
    $OriginalHash = (Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash
    $UnpackedHash = (Get-FileHash -LiteralPath (Join-Path $Roundtrip $AppExe) -Algorithm SHA256).Hash
    if ($OriginalHash -ne $UnpackedHash) { throw 'MSIX executable digest mismatch.' }
    $MsixHash = (Get-FileHash -LiteralPath $PackagePath -Algorithm SHA256).Hash
    Write-Host "STORE CANDIDATE ONLY: $PackagePath"
    Write-Host "MSIX SHA256: $MsixHash"
    Write-Host "SOURCE SHA: $SourceSha"
    Write-Host 'MANIFEST IDENTITY MATCH: PASS'
    Write-Host 'Unsigned candidate cannot be sideload-installed without an appropriate signature.'
    Write-Host 'Next: real Windows install/launch/save, optional WACK, rights and Partner Center validation.'
} catch {
    if ($created -or (Test-Path -LiteralPath $PackagePath)) {
        Remove-Item -LiteralPath $PackagePath -Force -ErrorAction SilentlyContinue
    }
    throw
} finally {
    if (Test-Path -LiteralPath $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force }
    if (Test-Path -LiteralPath $Roundtrip) { Remove-Item -LiteralPath $Roundtrip -Recurse -Force }
}
