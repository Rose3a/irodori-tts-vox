@echo off
setlocal
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
if not exist "%ROOT%\.venv\Scripts\python.exe" (
    call "%ROOT%\setup_venv.bat" --no-pause
    if errorlevel 1 exit /b 1
)
if not defined IRODORI_EMBED_DIR if exist "%ROOT%\embeddings" set "IRODORI_EMBED_DIR=%ROOT%\embeddings"
if not defined IRODORI_PLAN if exist "%ROOT%\bf16-fallback\fallback_bf16.plan" set "IRODORI_PLAN=%ROOT%\bf16-fallback\fallback_bf16.plan"
if not defined IRODORI_RUNTIME_DIR if exist "%ROOT%\runtime" set "IRODORI_RUNTIME_DIR=%ROOT%\runtime"
if not defined IRODORI_CHECKPOINT if exist "%ROOT%\models\model.safetensors" set "IRODORI_CHECKPOINT=%ROOT%\models\model.safetensors"
if not defined IRODORI_HF_HOME set "IRODORI_HF_HOME=%ROOT%\.cache\huggingface"
if not defined IRODORI_CACHE_DIR set "IRODORI_CACHE_DIR=%ROOT%\.cache\irodori"
cd /d "%ROOT%"
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\wrapper\interactive.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo [exit] %RC%
pause
exit /b %RC%
