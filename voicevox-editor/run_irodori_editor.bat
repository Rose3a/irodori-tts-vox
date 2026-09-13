@echo off
setlocal
rem Browser build of the official VOICEVOX Editor, configured for Irodori-TTS.
set "NODE_HOME=C:\Users\rose\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"
set "FALLBACK_HOME=C:\Users\rose\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback"
set "PATH=%NODE_HOME%;%FALLBACK_HOME%;%PATH%"
set "VITE_TARGET=browser"
node node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5175
