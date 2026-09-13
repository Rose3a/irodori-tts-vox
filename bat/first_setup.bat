@echo off
if not exist "%~dp0..\logs" mkdir "%~dp0..\logs"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\tools\setup.ps1" %* >> "%~dp0..\logs\first_setup.log" 2>&1
set "SETUP_EXIT=%errorlevel%"
if not "%SETUP_EXIT%"=="0" pause
exit /b %SETUP_EXIT%
