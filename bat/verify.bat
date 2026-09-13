@echo off
if not exist "%~dp0..\logs" mkdir "%~dp0..\logs"
if not exist "%~dp0..\.local\venv\Scripts\python.exe" (
  echo Python environment not found. Run bat\first_setup.bat first.
  pause
  exit /b 2
)
"%~dp0..\.local\venv\Scripts\python.exe" "%~dp0..\tools\verify.py" --synthesize >> "%~dp0..\logs\verify.log" 2>&1
if errorlevel 1 (
  echo Verification failed. See "%~dp0..\logs\verify.log".
) else (
  echo Verification passed. See "%~dp0..\logs\verification.json".
)
pause
