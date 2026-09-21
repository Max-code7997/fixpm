# fixpm installer for Windows PowerShell.
#
# One-line install:
#   irm https://raw.githubusercontent.com/Max-code7997/fixpm/main/scripts/install.ps1 | iex
#
# Overrides (testing / mirrors):
#   $env:FIXPM_RELEASE_BASE  download base URL (default: latest GitHub release)
#   $env:FIXPM_INSTALL_DIR   target directory   (default: $env:LOCALAPPDATA\fixpm\bin)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # Invoke-WebRequest is unusably slow with the progress bar

$Repo = "Max-code7997/fixpm"
$Base = if ($env:FIXPM_RELEASE_BASE) { $env:FIXPM_RELEASE_BASE }
        else { "https://github.com/$Repo/releases/latest/download" }
$DestDir = if ($env:FIXPM_INSTALL_DIR) { $env:FIXPM_INSTALL_DIR }
           else { Join-Path $env:LOCALAPPDATA "fixpm\bin" }
$Asset = "fixpm-windows-x64.exe"

# Older Windows PowerShell defaults to TLS 1.0, which GitHub rejects.
[Net.ServicePointManager]::SecurityProtocol = `
    [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

$tmp = New-Item -ItemType Directory -Force -Path (Join-Path $env:TEMP "fixpm-install")
$exePath = Join-Path $tmp $Asset
$sumPath = Join-Path $tmp "$Asset.sha256"

Write-Host "downloading $Asset from $Base ..."
Invoke-WebRequest -Uri "$Base/$Asset" -OutFile $exePath -UseBasicParsing
Invoke-WebRequest -Uri "$Base/$Asset.sha256" -OutFile $sumPath -UseBasicParsing

$expected = (Get-Content $sumPath -Raw).Split(" ", 2)[0].Trim().ToLower()
$actual = (Get-FileHash $exePath -Algorithm SHA256).Hash.ToLower()
if ($expected -ne $actual) {
    throw "sha256 mismatch for ${Asset}: expected $expected, got $actual"
}
Write-Host "checksum ok"

New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
$installed = Join-Path $DestDir "fixpm.exe"
Copy-Item $exePath $installed -Force
Write-Host "installed: $installed"

# The compiled probe is what the shell hook runs on the prompt path. Releases
# from 0.3.1 carry it; an older release has no such asset, which is a note
# rather than a failure — the hook falls back to the Python CLI.
$ProbeAsset = "fixpm-probe-windows-x64.exe"
$probePath = Join-Path $tmp $ProbeAsset
$probeSum = Join-Path $tmp "$ProbeAsset.sha256"
try {
    Invoke-WebRequest -Uri "$Base/$ProbeAsset" -OutFile $probePath -UseBasicParsing
    Invoke-WebRequest -Uri "$Base/$ProbeAsset.sha256" -OutFile $probeSum -UseBasicParsing
    $probeExpected = (Get-Content $probeSum -Raw).Split(" ", 2)[0].Trim().ToLower()
    $probeActual = (Get-FileHash $probePath -Algorithm SHA256).Hash.ToLower()
    if ($probeExpected -ne $probeActual) { throw "sha256 mismatch for ${ProbeAsset}" }
    $probeInstalled = Join-Path $DestDir "fixpm-probe.exe"
    Copy-Item $probePath $probeInstalled -Force
    Write-Host "installed: $probeInstalled (fast probe)"
} catch {
    Write-Host "note: no fast probe installed ($($_.Exception.Message))"
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($userPath -split ";") -notcontains $DestDir) {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$DestDir", "User")
    Write-Host "added $DestDir to your user PATH - restart your terminal to pick it up"
}

& $installed --version
