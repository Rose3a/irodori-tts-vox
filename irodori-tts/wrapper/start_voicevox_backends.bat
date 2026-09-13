@echo off
setlocal
set "PROJECT=%~dp0.."
start "Irodori CPU" cmd /k call "%PROJECT%\wrapper\run_voicevox_engine.bat" cpu 50021
start "Irodori CUDA" cmd /k call "%PROJECT%\wrapper\run_voicevox_engine.bat" cuda 50022
start "Irodori TensorRT" cmd /k call "%PROJECT%\wrapper\run_voicevox_engine.bat" trt 50023
start "Irodori Radeon" cmd /k call "%PROJECT%\wrapper\run_voicevox_engine.bat" radeon 50024
echo Started CPU(50021), CUDA(50022), TensorRT(50023), Radeon(50024).
