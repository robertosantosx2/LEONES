<#
.SYNOPSIS
Installs Kinetic for the current user on Windows.

.DESCRIPTION
Downloads a Kinetic release from GitHub (the full build, which runs on
NVIDIA GPUs through CUDA, on AMD and Intel GPUs through Vulkan and on the
CPU; -Cpu takes the smaller CPU-only build), checks it against the release's
SHA256SUMS, unpacks it into %LOCALAPPDATA%\Programs\kinetic and puts that
folder on the user's PATH. Needs no administrator rights.

.EXAMPLE
irm https://raw.githubusercontent.com/Veloresearch/kinetic/main/scripts/install.ps1 | iex

.EXAMPLE
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/Veloresearch/kinetic/main/scripts/install.ps1))) -Version 0.1.0 -Cpu
#>
param(
    # A release such as 0.1.0; the latest by default.
    [string]$Version = '',
    # Install the smaller CPU-only build.
    [switch]$Cpu
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$repo = 'Veloresearch/kinetic'
$dir = Join-Path $env:LOCALAPPDATA 'Programs\kinetic'

if (-not [Environment]::Is64BitOperatingSystem) {
    throw 'Kinetic needs 64-bit Windows.'
}

if (-not $Version) {
    $latest = Invoke-RestMethod "https://api.github.com/repos/$repo/releases/latest" -Headers @{ 'User-Agent' = 'kinetic-install' }
    $Version = $latest.tag_name
}
$Version = $Version.TrimStart('v')

# the cuda archive is the full build: CUDA, Vulkan and the CPU in one binary
$variant = if ($Cpu) { 'cpu' } else { 'cuda' }
$name = "kinetic-$Version-windows-x86_64-$variant"
$base = "https://github.com/$repo/releases/download/v$Version"

$tmp = Join-Path ([IO.Path]::GetTempPath()) "kinetic-install-$PID"
New-Item -ItemType Directory -Force $tmp | Out-Null
try {
    Write-Host "Downloading Kinetic $Version ($variant build)"
    Invoke-WebRequest "$base/$name.zip" -OutFile (Join-Path $tmp "$name.zip") -UseBasicParsing
    Invoke-WebRequest "$base/SHA256SUMS" -OutFile (Join-Path $tmp 'SHA256SUMS') -UseBasicParsing

    $line = Get-Content (Join-Path $tmp 'SHA256SUMS') | Where-Object { $_ -match "\s\*?$([regex]::Escape("$name.zip"))$" }
    if (-not $line) { throw "SHA256SUMS does not list $name.zip" }
    $expected = ($line -split '\s+')[0].ToLowerInvariant()
    $actual = (Get-FileHash -Algorithm SHA256 (Join-Path $tmp "$name.zip")).Hash.ToLowerInvariant()
    if ($actual -ne $expected) { throw "checksum mismatch for $name.zip: expected $expected, got $actual" }

    Expand-Archive (Join-Path $tmp "$name.zip") -DestinationPath $tmp -Force
    New-Item -ItemType Directory -Force $dir | Out-Null
    Copy-Item -Path (Join-Path $tmp "$name\*") -Destination $dir -Recurse -Force
}
finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}

$path = [Environment]::GetEnvironmentVariable('Path', 'User')
$entries = @($path -split ';' | Where-Object { $_ })
if ($entries -notcontains $dir) {
    [Environment]::SetEnvironmentVariable('Path', (($entries + $dir) -join ';'), 'User')
    $env:Path = "$env:Path;$dir"
    Write-Host "Added $dir to your PATH; new terminals will find kinetic."
}

& (Join-Path $dir 'kinetic.exe') --version
Write-Host "Installed in $dir. Try: kinetic doctor"
