@echo off
set "BOX=%~dp0.."
set IRODORI_RUNTIME_DIR=%BOX%\runtime
set IRODORI_TRT_LAB_DIR=%BOX%\runtime\trt-lab
set IRODORI_CHECKPOINT=%BOX%\models\model.safetensors
set IRODORI_HF_HOME=%BOX%\.cache\huggingface
set IRODORI_EMBED_DIR=%BOX%\speakers
set IRODORI_OUT_DIR=%BOX%\outputs
if not exist "%BOX%\logs" mkdir "%BOX%\logs"
"%BOX%\irodori-tts\.venv\Scripts\python.exe" -u "%BOX%\irodori-tts\wrapper\voicevox_engine.py" --backend cpu --port 50021 1>"%BOX%\logs\launch_backend_50021.log" 2>&1
