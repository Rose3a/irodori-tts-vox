@echo off
"%~dp0..\.local\venv\Scripts\python.exe" "%~dp0..\tools\verify.py" --synthesize >> "%~dp0..\logs\verify.log" 2>&1
pause
