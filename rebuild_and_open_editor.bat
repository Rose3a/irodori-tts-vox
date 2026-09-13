@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
set "EDITOR_DIR=%ROOT%voicevox-editor"
set "LOG=%ROOT%logs\editor-build.log"
set "TARGET=%EDITOR_DIR%\dist_electron\win-unpacked\Irodori VOICEVOX Editor.exe"
set "ENGINE_BAT=%ROOT%bat\serve_editor_engine.bat"
set "ENGINE_LOG=%ROOT%logs\editor-engine-launch.log"
set "NO_PAUSE=0"
set "CI_WAS_SET=%CI%"

if /i "%~1"=="--no-pause" set "NO_PAUSE=1"
if not exist "%EDITOR_DIR%" (
  echo Editor directory not found: "%EDITOR_DIR%"
  exit /b 2
)
if not exist "%ROOT%logs" mkdir "%ROOT%logs" >nul 2>&1
if not exist "%ROOT%logs" (
  echo Cannot create log directory: "%ROOT%logs"
  exit /b 2
)

rem CI prevents pnpm from asking for a TTY confirmation.
set "CI=true"
set "PNPM_MODE="
set "PNPM_CMD="
set "RUNNER_PATH_MODE="
set "FALLBACK_BIN="
set "FALLBACK_NODE_BIN="
set "LOCAL_NODE=%ROOT%.local\node\24.11.1"

rem Prefer the portable setup created by tools\setup.ps1.
if exist "%LOCAL_NODE%\pnpm.cmd" (
  set "PNPM_MODE=direct"
  set "PNPM_CMD=%LOCAL_NODE%\pnpm.cmd"
  set "RUNNER_PATH_MODE=local"
  goto :run_build
)
if exist "%LOCAL_NODE%\npx.cmd" (
  set "PNPM_MODE=npx"
  set "PNPM_CMD=%LOCAL_NODE%\npx.cmd"
  set "RUNNER_PATH_MODE=local"
  goto :run_build
)
if exist "%LOCAL_NODE%\corepack.cmd" (
  set "PNPM_MODE=corepack"
  set "PNPM_CMD=%LOCAL_NODE%\corepack.cmd"
  set "RUNNER_PATH_MODE=local"
  goto :run_build
)
if exist "%LOCAL_NODE%\npm.cmd" (
  set "PNPM_MODE=npm-exec"
  set "PNPM_CMD=%LOCAL_NODE%\npm.cmd"
  set "RUNNER_PATH_MODE=local"
  goto :run_build
)

rem Fall back to a normal pnpm available on PATH.
for /f "delims=" %%P in ('where.exe pnpm.cmd 2^>nul') do if not defined PNPM_CMD (
  set "PNPM_MODE=direct"
  set "PNPM_CMD=%%P"
)
if defined PNPM_CMD goto :run_build
for /f "delims=" %%P in ('where.exe pnpm 2^>nul') do if not defined PNPM_CMD (
  set "PNPM_MODE=direct"
  set "PNPM_CMD=%%P"
)
if defined PNPM_CMD goto :run_build

echo No usable pnpm runner was found.
echo Checked the project portable Node setup (run bat\first_setup.bat) and pnpm on PATH.
exit /b 3

:run_build
cd /d "%EDITOR_DIR%"
if /i "%RUNNER_PATH_MODE%"=="local" set "PATH=%LOCAL_NODE%;%PATH%"
if /i "%RUNNER_PATH_MODE%"=="fallback" set "PATH=%FALLBACK_NODE_BIN%;%FALLBACK_BIN%;%PATH%"
echo Building editor directory for local launch. Log: "%LOG%"
if /i "%PNPM_MODE%"=="direct" call "%PNPM_CMD%" run electron:build:dir > "%LOG%" 2>&1
if /i "%PNPM_MODE%"=="npx" call "%PNPM_CMD%" --yes pnpm@10.28.2 run electron:build:dir > "%LOG%" 2>&1
if /i "%PNPM_MODE%"=="corepack" call "%PNPM_CMD%" pnpm run electron:build:dir > "%LOG%" 2>&1
if /i "%PNPM_MODE%"=="npm-exec" call "%PNPM_CMD%" exec --yes --package=pnpm@10.28.2 pnpm run electron:build:dir > "%LOG%" 2>&1
if errorlevel 1 (
  echo Build failed. See "%LOG%".
  if "%NO_PAUSE%"=="0" if /i not "%CI_WAS_SET%"=="true" timeout /t 10 /nobreak >nul
  exit /b 1
)

if not exist "%TARGET%" (
  echo Build completed but launcher was not found: "%TARGET%"
  echo See "%LOG%" for build details.
  if "%NO_PAUSE%"=="0" if /i not "%CI_WAS_SET%"=="true" timeout /t 10 /nobreak >nul
  exit /b 4
)
if not exist "%ENGINE_BAT%" (
  echo Engine launcher was not found: "%ENGINE_BAT%"
  exit /b 6
)
echo Starting Irodori engine. Log: "%ENGINE_LOG%"
start "" /b "%ComSpec%" /d /c call "%ENGINE_BAT%" >> "%ENGINE_LOG%" 2>&1
if errorlevel 1 (
  echo Failed to start engine launcher: "%ENGINE_BAT%"
  exit /b 6
)
start "" "%TARGET%"
if errorlevel 1 (
  echo Failed to start launcher: "%TARGET%"
  exit /b 5
)
exit /b 0
