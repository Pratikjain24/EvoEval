@echo off
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m sage.runner.cli %*
) else (
    python -m sage.runner.cli %*
)
