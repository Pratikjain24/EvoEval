Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "   Starting SAGE Evaluation Dashboard..." -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$pyExe = if (Test-Path "$scriptDir\.venv\Scripts\python.exe") { "$scriptDir\.venv\Scripts\python.exe" } else { "python" }

Write-Host "[1/2] Starting FastAPI Backend on http://localhost:8000..." -ForegroundColor Green
Start-Process "cmd.exe" -ArgumentList "/k", "`"$pyExe`" -m uvicorn sage.dashboard_backend.main:app --port 8000"

Write-Host "[2/2] Starting Next.js Frontend on http://localhost:3000..." -ForegroundColor Green
Start-Process "cmd.exe" -ArgumentList "/k", "cd /d `"$scriptDir\sage\dashboard_frontend`" && npm run dev"

Write-Host "Waiting 5 seconds for servers to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "Opening browser at http://localhost:3000..." -ForegroundColor Green
Start-Process "http://localhost:3000"

Write-Host "Done! Leave the two open terminal windows running during your demo." -ForegroundColor Cyan
Write-Host ""
Write-Host "TIP: After running 'sage run ...', refresh the dashboard DB with:" -ForegroundColor Yellow
Write-Host "     Invoke-WebRequest -Uri 'http://localhost:8000/admin/sync' -Method POST" -ForegroundColor Yellow
