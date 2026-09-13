@echo off
setlocal
rem ----------------------------------------------------------- Irodori TTS HTTP server
rem Usage:
rem   serve.bat
rem   serve.bat --port 9000
rem
rem Listens on 127.0.0.1 by default. POST /synthesize, GET /speakers.

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "PYEXE=%ROOT%\.venv\Scripts\python.exe"
set "SCRIPT=%ROOT%\wrapper\tts_cli.py"

if not defined IRODORI_EMBED_DIR if exist "%ROOT%\embeddings" set "IRODORI_EMBED_DIR=%ROOT%\embeddings"
if not defined IRODORI_PLAN if exist "%ROOT%\bf16-fallback\fallback_bf16.plan" set "IRODORI_PLAN=%ROOT%\bf16-fallback\fallback_bf16.plan"
if not defined IRODORI_RUNTIME_DIR if exist "%ROOT%\runtime" set "IRODORI_RUNTIME_DIR=%ROOT%\runtime"
if not defined IRODORI_CHECKPOINT if exist "%ROOT%\models\model.safetensors" set "IRODORI_CHECKPOINT=%ROOT%\models\model.safetensors"
if not defined IRODORI_HF_HOME set "IRODORI_HF_HOME=%ROOT%\.cache\huggingface"
if not defined IRODORI_CACHE_DIR set "IRODORI_CACHE_DIR=%ROOT%\.cache\irodori"

if not exist "%PYEXE%" set "PYEXE=E:\tts\trt-lab-20260905\.venv\Scripts\python.exe"

if not exist "%ROOT%\.venv\Scripts\python.exe" if exist "%ROOT%\setup_venv.bat" (
    call "%ROOT%\setup_venv.bat" --no-pause
    if errorlevel 1 exit /b 1
    set "PYEXE=%ROOT%\.venv\Scripts\python.exe"
)

if not exist "%PYEXE%" (
    echo [error] python.exe not found: %PYEXE%
    exit /b 1
)
if not exist "%SCRIPT%" (
    echo [error] wrapper script not found: %SCRIPT%
    exit /b 1
)

set "ARGS="
:loop
if "%~1"=="" goto :run
set "ARGS=%ARGS% %~1"
shift
goto :loop

:run
echo [info] starting serve on 127.0.0.1 (default port 8765)
"%PYEXE%" "%SCRIPT%" --mode serve %ARGS%
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo [exit] %RC%
exit /b %RC%
