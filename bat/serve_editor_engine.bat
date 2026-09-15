@echo off
setlocal
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
set "BOX=%~dp0.."
set "PYTHON=%BOX%\.local\venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=%BOX%\irodori-tts\.venv\Scripts\python.exe"
if not exist "%BOX%\logs" mkdir "%BOX%\logs"
powershell.exe -NoProfile -Command "try { $p=(Get-NetTCPConnection -LocalPort 50125 -State Listen -ErrorAction Stop).OwningProcess; Write-Output ('Irodori Engine is already running (PID ' + $p + ').'); exit 0 } catch { exit 1 }" >> "%BOX%\logs\browser-engine.log" 2>&1
if not errorlevel 1 exit /b 0
"%PYTHON%" -u "%BOX%\irodori-tts\wrapper\editor_engine.py" --host 127.0.0.1 --port 50125 > "%BOX%\logs\browser-engine.log" 2>&1
