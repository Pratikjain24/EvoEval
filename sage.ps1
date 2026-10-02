if (Test-Path "$PSScriptRoot\.venv\Scripts\python.exe") {
    & "$PSScriptRoot\.venv\Scripts\python.exe" -m sage.runner.cli @args
} else {
    python -m sage.runner.cli @args
}
