@echo off
title Irodori-TTS TensorRT setup
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\tools\trt_setup.ps1" %*
set "TRT_SETUP_EXIT=%errorlevel%"
echo.
if "%TRT_SETUP_EXIT%"=="0" (
  echo TensorRT setup completed successfully.
) else (
  echo TensorRT setup did not complete. See logs\trt-setup.log.
)
echo This window stays open so you can read the result.
pause
exit /b %TRT_SETUP_EXIT%
