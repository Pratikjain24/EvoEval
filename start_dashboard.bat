@echo off
echo ===================================================
echo   Starting EvoEval Evaluation Dashboard...
echo ===================================================

echo [1/2] Starting FastAPI Backend on http://localhost:8000...
start "EvoEval Backend" cmd /k "%~dp0.venv\Scripts\python.exe -m uvicorn evaeval.dashboard_backend.main:app --port 8000"

echo [2/2] Starting Next.js Frontend on http://localhost:3000...
start "EvoEval Frontend" cmd /k "cd /d %~dp0evaeval\dashboard_frontend && npm run dev"

echo Waiting 5 seconds for servers to initialize...
timeout /t 5 >nul

echo Opening browser at http://localhost:3000...
start http://localhost:3000

echo Done! Leave the two open terminal windows running during your demo.
