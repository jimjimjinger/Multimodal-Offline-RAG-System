$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$OllamaExe = Join-Path $Root "runtime\ollama\ollama.exe"
$OllamaHome = Join-Path $Root "runtime\ollama_home"
$OllamaModels = Join-Path $Root "runtime\ollama_models"

if (-not (Test-Path $OllamaExe)) {
    throw "Ollama executable not found: $OllamaExe"
}

New-Item -ItemType Directory -Force -Path $OllamaHome, $OllamaModels | Out-Null

$env:USERPROFILE = $OllamaHome
$env:HOME = $OllamaHome
$env:OLLAMA_MODELS = $OllamaModels

Write-Host "Starting Ollama at http://127.0.0.1:11434"
& $OllamaExe serve
