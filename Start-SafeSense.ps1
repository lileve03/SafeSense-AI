param([switch]$SmokeTest)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$backendPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $backendPython)) { throw 'Backend environment missing. Follow README.md.' }
$launchArguments = @()
if ($SmokeTest) { $launchArguments += '--smoke-test' }
& $backendPython (Join-Path $projectRoot 'scripts\start_services.py') @launchArguments
if ($LASTEXITCODE -ne 0) { throw 'SafeSense stopped with an error. Inspect runtime\logs.' }
