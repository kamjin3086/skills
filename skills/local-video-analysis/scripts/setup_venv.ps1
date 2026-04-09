param(
    [string]$PythonExe = "python",
    [switch]$InstallTransformers
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $root ".venv"
$requirements = Join-Path $root "requirements.txt"
$requirementsTf = Join-Path $root "requirements-transformers.txt"

Write-Host "[1/4] Creating venv at $venvPath"
& $PythonExe -m venv $venvPath

$python = Join-Path $venvPath "Scripts\python.exe"
if (!(Test-Path $python)) {
    throw "Failed to create venv python at $python"
}

Write-Host "[2/4] Upgrading pip"
& $python -m pip install --upgrade pip

Write-Host "[3/4] Installing Python dependencies"
& $python -m pip install -r $requirements

if ($InstallTransformers) {
    Write-Host "Installing Transformers/MLX extras (may take longer)"
    & $python -m pip install -r $requirementsTf
}

Write-Host "[4/4] Verifying ffmpeg/ffprobe"
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
$ffprobe = Get-Command ffprobe -ErrorAction SilentlyContinue
if ($null -eq $ffmpeg -or $null -eq $ffprobe) {
    Write-Warning "ffmpeg/ffprobe not found in PATH."
    Write-Host "Install via winget:"
    Write-Host "  winget install Gyan.FFmpeg"
} else {
    Write-Host "ffmpeg OK: $($ffmpeg.Source)"
    Write-Host "ffprobe OK: $($ffprobe.Source)"
}

Write-Host ""
Write-Host "Done. Use the venv Python:"
Write-Host "  $python scripts\run_video_pipeline.py <video.mp4> --sampling hybrid --max-side 640 --segment-seconds 120"
