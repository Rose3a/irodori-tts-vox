@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Create a project-local Python virtual environment.
rem Usage:
rem   setup_venv.bat

set "ROOT=%~dp0"
pushd "%ROOT%"

set "VENV=%ROOT%.venv"
set "PY_CMD="
set "INSTALL_TRT=0"
set "LOG=%ROOT%setup_venv.log"
set "PAUSE_AT_END=1"
if /i "%~1"=="--no-pause" set "PAUSE_AT_END=0"
rem Set this outside parenthesized blocks so cmd expands it correctly.
if "%TORCH_INDEX_URL%"=="" set "TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128"
set "MODEL_ID=Aratako/Irodori-TTS-v4.1-Small"
rem Pin the checkpoint so a later re-run cannot pick up different weights.
if "%MODEL_REVISION%"=="" set "MODEL_REVISION=2b28324dc263ed5e6638b3cf3dd94c82ead07b4b"
set "MODEL_DIR=%ROOT%models"
set "RUNTIME_DIR=%ROOT%runtime"
set "TRT_LAB_DIR=%RUNTIME_DIR%\trt-lab"

>"%LOG%" echo Irodori TTS virtual environment setup
>>"%LOG%" echo Started: %DATE% %TIME%
>>"%LOG%" echo Project: %ROOT%
echo [info] log file: %LOG%

rem Use nvidia-smi's short GPU listing because some older drivers reject
rem the CSV header option. Capture errors in the main log.
set "GPU_LOG=%ROOT%setup_gpu.log"
where nvidia-smi >nul 2>&1
if not errorlevel 1 (
    echo [info] checking NVIDIA GPU
    cmd /d /c nvidia-smi -L >"%GPU_LOG%" 2>>"%LOG%"
    if errorlevel 1 (
        echo [warning] nvidia-smi failed; trying Windows display adapters
        >>"%LOG%" echo WARNING: nvidia-smi query failed
        type "%GPU_LOG%" >>"%LOG%"
    ) else (
        type "%GPU_LOG%"
        type "%GPU_LOG%" >>"%LOG%"
        findstr /i /c:"RTX" "%GPU_LOG%" >nul
        if not errorlevel 1 set "INSTALL_TRT=1"
    )
)
if "%INSTALL_TRT%"=="0" (
    echo [info] checking Windows display adapters
    where powershell >nul 2>&1
    if not errorlevel 1 (
        cmd /d /c powershell -NoProfile -NonInteractive -Command "$ErrorActionPreference='Stop'; (Get-CimInstance Win32_VideoController).Name" >"%GPU_LOG%" 2>>"%LOG%"
        if errorlevel 1 (
            echo [warning] Windows GPU query failed; see setup_venv.log
            >>"%LOG%" echo WARNING: Windows GPU query failed
        ) else (
            type "%GPU_LOG%"
            type "%GPU_LOG%" >>"%LOG%"
            findstr /i /c:"RTX" "%GPU_LOG%" >nul
            if not errorlevel 1 set "INSTALL_TRT=1"
        )
    )
)

if "%INSTALL_TRT%"=="1" (
    echo [info] RTX GPU detected; TensorRT will be installed
    >>"%LOG%" echo TensorRT: enabled - RTX detected
) else (
    echo [info] no RTX GPU detected; installing common dependencies only
    >>"%LOG%" echo TensorRT: skipped - no RTX detected
)

rem Diagnostic mode performs no installs and still waits for a key.
if /i "%~1"=="--check-gpu" (
    set "RC=0"
    goto :finish
)

rem Prefer Python 3.11 when the Python launcher is available, then use any
rem installed Python 3.10+ version.
where py >nul 2>&1
if not errorlevel 1 (
    py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3.11"
    if not defined PY_CMD (
        py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
        if not errorlevel 1 set "PY_CMD=py -3"
    )
)

if not defined PY_CMD (
    where python >nul 2>&1
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
        if not errorlevel 1 set "PY_CMD=python"
    )
)

if not defined PY_CMD (
    echo [error] Python 3.10 or newer was not found.
    echo         Install Python from https://www.python.org/downloads/windows/
    echo         and enable the Python Launcher or add python.exe to PATH.
    >>"%LOG%" echo ERROR: compatible Python was not found
    set "RC=1"
    goto :finish
)

if not exist "%VENV%\Scripts\python.exe" (
    echo [info] creating %VENV%
    >>"%LOG%" echo Command: %PY_CMD% -m venv "%VENV%"
    %PY_CMD% -m venv "%VENV%" >>"%LOG%" 2>&1
    if errorlevel 1 goto :failed
) else (
    echo [info] using existing %VENV%
    >>"%LOG%" echo Reusing existing venv: %VENV%
)

set "VENV_PY=%VENV%\Scripts\python.exe"
echo [info] upgrading pip
>>"%LOG%" echo Command: "%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install --upgrade pip >>"%LOG%" 2>&1
if errorlevel 1 goto :failed

echo [info] installing common dependencies
>>"%LOG%" echo Command: "%VENV_PY%" -m pip install -r "%ROOT%requirements.txt"
"%VENV_PY%" -m pip install -r "%ROOT%requirements.txt" >>"%LOG%" 2>&1
if errorlevel 1 goto :failed

echo [info] installing Irodori runtime dependencies
>>"%LOG%" echo Command: "%VENV_PY%" -m pip install -r "%ROOT%requirements-runtime.txt"
"%VENV_PY%" -m pip install -r "%ROOT%requirements-runtime.txt" >>"%LOG%" 2>&1
if errorlevel 1 goto :failed

echo [info] installing DACVAE codec without conflicting dependency resolution
>>"%LOG%" echo Command: "%VENV_PY%" -m pip install --no-deps dacvae
"%VENV_PY%" -m pip install --upgrade --no-deps "dacvae @ https://github.com/facebookresearch/dacvae/archive/414c20785fc3a28373073ea8ef7a1316eeeaca6e.zip" >>"%LOG%" 2>&1
if errorlevel 1 goto :failed

echo [info] aligning protobuf for ONNX/TensorRT export
rem descript-audiotools declares an old protobuf pin, but ONNX 1.22 uses
rem the modern protobuf runtime.  Install the runtime-compatible version
rem after the audio stack, then install ONNX without re-solving DACVAE.
>>"%LOG%" echo Command: "%VENV_PY%" -m pip install "protobuf>=4.25.1,<6" "ml_dtypes>=0.5.4"
"%VENV_PY%" -m pip install --upgrade "protobuf>=4.25.1,<6" "ml_dtypes>=0.5.4" >>"%LOG%" 2>&1
if errorlevel 1 goto :failed

echo [info] installing ONNX for TensorRT export
>>"%LOG%" echo Command: "%VENV_PY%" -m pip install --no-deps onnx
"%VENV_PY%" -m pip install --upgrade --no-deps onnx >>"%LOG%" 2>&1
if errorlevel 1 goto :failed

if not exist "%MODEL_DIR%\model.safetensors" (
    echo [info] downloading model: %MODEL_ID%
    mkdir "%MODEL_DIR%" >nul 2>&1
    >>"%LOG%" echo Command: Hugging Face snapshot_download %MODEL_ID%
    "%VENV_PY%" -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='%MODEL_ID%', revision='%MODEL_REVISION%', local_dir=r'%MODEL_DIR%')" >>"%LOG%" 2>&1
    if errorlevel 1 goto :failed
) else (
    echo [info] model already exists: %MODEL_DIR%\model.safetensors
    >>"%LOG%" echo Reusing model: %MODEL_DIR%\model.safetensors
)

set "IRODORI_RUNTIME_DIR=%RUNTIME_DIR%"
set "IRODORI_TRT_LAB_DIR=%TRT_LAB_DIR%"
set "IRODORI_CHECKPOINT=%MODEL_DIR%\model.safetensors"
set "IRODORI_HF_HOME=%ROOT%.cache\huggingface"
if not exist "%IRODORI_HF_HOME%" mkdir "%IRODORI_HF_HOME%" >nul 2>&1

if "%INSTALL_TRT%"=="1" (
    rem Install a CUDA-enabled Torch wheel before TensorRT. Override this URL
    rem with TORCH_INDEX_URL if the target machine uses another CUDA channel.
    echo [info] installing CUDA-enabled PyTorch from %TORCH_INDEX_URL%
    >>"%LOG%" echo Command: "%VENV_PY%" -m pip install --upgrade --force-reinstall torch torchaudio --index-url "%TORCH_INDEX_URL%"
    "%VENV_PY%" -m pip install --upgrade --force-reinstall torch torchaudio --index-url "%TORCH_INDEX_URL%" >>"%LOG%" 2>&1
    if errorlevel 1 goto :failed

    echo [info] installing TensorRT dependency for RTX
    >>"%LOG%" echo Command: "%VENV_PY%" -m pip install -r "%ROOT%requirements-trt.txt"
    "%VENV_PY%" -m pip install -r "%ROOT%requirements-trt.txt" >>"%LOG%" 2>&1
    if errorlevel 1 goto :failed

    echo [info] exporting ONNX for this runtime
    >>"%LOG%" echo Command: "%VENV_PY%" "%TRT_LAB_DIR%\trt_experiment.py" export
    "%VENV_PY%" "%TRT_LAB_DIR%\trt_experiment.py" export >>"%LOG%" 2>&1
    if errorlevel 1 goto :failed

    echo [info] exporting BF16 TensorRT candidate
    >>"%LOG%" echo Command: "%VENV_PY%" "%ROOT%bf16-fallback\fallback_bf16.py" export
    "%VENV_PY%" "%ROOT%bf16-fallback\fallback_bf16.py" export >>"%LOG%" 2>&1
    if errorlevel 1 goto :failed

    echo [info] building TensorRT plan for this GPU
    >>"%LOG%" echo Command: "%VENV_PY%" "%ROOT%bf16-fallback\fallback_bf16.py" build
    "%VENV_PY%" "%ROOT%bf16-fallback\fallback_bf16.py" build >>"%LOG%" 2>&1
    if errorlevel 1 goto :failed
)

echo.
echo [done] Virtual environment is ready:
echo        %VENV_PY%
if "%INSTALL_TRT%"=="1" (
    echo        TensorRT installed because an RTX GPU was detected.
    echo        Plan generated: %ROOT%bf16-fallback\fallback_bf16.plan
) else (
    echo        Torch backend and model installed. TensorRT was skipped.
)
echo.
echo Next:
echo   wrapper\run.bat --list-speakers
echo   wrapper\run.bat --speaker SPEAKER --text "hello" --out outputs\hello.wav
set "RC=0"
goto :finish

:failed
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" set "RC=1"
echo [error] Virtual environment setup failed. See setup_venv.log for details.
>>"%LOG%" echo ERROR: setup failed with exit code %RC%

:finish
>>"%LOG%" echo Finished: %DATE% %TIME% - exit code %RC%
echo.
echo [info] Full log saved to:
echo        %LOG%
echo [info] Press any key to close this window.
if "%PAUSE_AT_END%"=="1" pause >nul
popd
exit /b %RC%
