# Back Quip Windows bootstrap: checks, installs (with consent), and starts the local AI runtime.
$ErrorActionPreference = 'Stop'
$api = 'http://127.0.0.1:11434/api/tags'
function Test-Engine {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $api -TimeoutSec 2
        return ($response.StatusCode -eq 200)
    } catch { return $false }
}
function Find-Engine {
    $cmd = Get-Command ollama.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $locations = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'),
        (Join-Path $env:ProgramFiles 'Ollama\ollama.exe')
    )
    foreach ($p in $locations) { if (Test-Path $p) { return $p } }
    return $null
}
if (Test-Engine) {
    Write-Host '[Back Quip] Local AI engine is already running.' -ForegroundColor Green
    exit 0
}
$exe = Find-Engine
if (-not $exe) {
    Write-Host '[Back Quip] Local AI engine is not installed.' -ForegroundColor Yellow
    $answer = Read-Host 'Install it now using Windows Package Manager? [Y/n]'
    if ($answer -and $answer -notmatch '^[Yy]') {
        Write-Host 'Installation skipped. Back Quip needs this local engine to generate replies.'
        exit 1
    }
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        Write-Host 'Windows Package Manager (winget) is unavailable. Install from https://ollama.com/download/windows and rerun start.bat.' -ForegroundColor Red
        exit 1
    }
    Write-Host '[Back Quip] Installing local AI engine. Follow any Windows installer prompts...'
    & winget install --id Ollama.Ollama --exact --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Automatic installation did not finish. Install from https://ollama.com/download/windows and rerun start.bat.' -ForegroundColor Red
        exit 1
    }
    $exe = Find-Engine
    if (-not $exe) {
        Write-Host 'The installer finished, but the engine executable was not found. Reopen the terminal or run the official installer, then retry.' -ForegroundColor Red
        exit 1
    }
}
if (-not (Test-Engine)) {
    Write-Host '[Back Quip] Starting local AI engine...'
    # Using the native CLI avoids relying on the tray application's specific filename.
    try { Start-Process -FilePath $exe -ArgumentList 'serve' -WindowStyle Hidden | Out-Null }
    catch {
        Write-Host "Could not launch the local engine: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}
for ($i = 0; $i -lt 45; $i++) {
    if (Test-Engine) {
        Write-Host '[Back Quip] Local AI engine ready.' -ForegroundColor Green
        exit 0
    }
    Start-Sleep -Seconds 1
}
Write-Host 'The local engine did not become ready. Open the Ollama application and rerun start.bat.' -ForegroundColor Red
exit 1
