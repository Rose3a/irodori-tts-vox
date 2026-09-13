@echo off
setlocal
title Irodori-TTS Browser Session
set "BOX=%~dp0"
set "PAUSE_AT_END=1"
for %%A in (%*) do if /i "%%~A"=="--no-pause" set "PAUSE_AT_END=0"
set "PYTHON=%BOX%\irodori-tts\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=%BOX%\.local\venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo Python runtime was not found in .local\venv or irodori-tts\.venv.
  if "%PAUSE_AT_END%"=="1" pause
  exit /b 1
)
echo Irodori-TTS browser session is starting...
echo This console stays open while the web editor is running.
echo Close this console to stop the engine and Vite server.
echo.
echo DEBUG MODE: engine/UI logs and per-line generation timings are shown here.
echo.
set "IRODORI_DEBUG=1"
"%PYTHON%" -u "%BOX%tools\browser_session.py" --launcher "%~f0" --debug %*
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Browser session stopped with exit code %EXIT_CODE%.
if "%PAUSE_AT_END%"=="1" pause
exit /b %EXIT_CODE%
