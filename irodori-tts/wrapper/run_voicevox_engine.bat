@echo off
setlocal
set "PROJECT=%~dp0.."
set "PYTHON=%PROJECT%\.venv\Scripts\python.exe"
set "IRODORI_RUNTIME_DIR=%PROJECT%\runtime"
rem Set IRODORI_CHECKPOINT before calling this script to use another model,
rem for example the MeanFlow v4.1-Small-MF safetensors file.
if not defined IRODORI_CHECKPOINT set "IRODORI_CHECKPOINT=%PROJECT%\models\model.safetensors"
set "IRODORI_HF_HOME=%PROJECT%\.cache\huggingface"
set "IRODORI_EMBED_DIRS=D:\tts\embeddings"
if "%~1"=="" goto usage
set "BACKEND=%~1"
set "PORT=%~2"
if "%PORT%"=="" set "PORT=50021"
"%PYTHON%" "%PROJECT%\wrapper\voicevox_engine.py" --backend "%BACKEND%" --port "%PORT%"
exit /b %ERRORLEVEL%

:usage
echo Usage: run_voicevox_engine.bat cpu^|cuda^|trt^|radeon [port]
echo Example: run_voicevox_engine.bat cpu 50021
exit /b 2
