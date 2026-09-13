@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "BACKEND=auto"
set "YES="
set "KEEPFRONTEND="
set "KEEPCACHES="
set "NOPAUSE="
set "DRYRUN="
:parse
if "%~1"=="" goto run
if /i "%~1"=="--backend" goto backend_value
if /i "%~1"=="-backend" goto backend_value
if /i "%~1"=="--yes" set "YES=-Yes" & shift & goto parse
if /i "%~1"=="-yes" set "YES=-Yes" & shift & goto parse
if /i "%~1"=="--keep-frontend" set "KEEPFRONTEND=-KeepFrontend" & shift & goto parse
if /i "%~1"=="-keep-frontend" set "KEEPFRONTEND=-KeepFrontend" & shift & goto parse
if /i "%~1"=="--keep-caches" set "KEEPCACHES=-KeepCaches" & shift & goto parse
if /i "%~1"=="-keep-caches" set "KEEPCACHES=-KeepCaches" & shift & goto parse
if /i "%~1"=="--no-pause" set "NOPAUSE=-NoPause" & shift & goto parse
if /i "%~1"=="-no-pause" set "NOPAUSE=-NoPause" & shift & goto parse
if /i "%~1"=="--dry-run" set "DRYRUN=-DryRun" & shift & goto parse
if /i "%~1"=="-dry-run" set "DRYRUN=-DryRun" & shift & goto parse
echo Unknown option: %~1
exit /b 64
:backend_value
if "%~2"=="" echo Missing backend value.& exit /b 64
set "BACKEND=%~2"
if /i not "!BACKEND!"=="auto" if /i not "!BACKEND!"=="cuda" if /i not "!BACKEND!"=="cpu" if /i not "!BACKEND!"=="radeon" echo Invalid backend: !BACKEND!& exit /b 64
shift
shift
goto parse
:run
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\rebuild_environment.ps1" -Backend "%BACKEND%" %YES% %KEEPFRONTEND% %KEEPCACHES% %NOPAUSE% %DRYRUN%
set "RESULT=%errorlevel%"
if not "%RESULT%"=="0" if not defined NOPAUSE pause
exit /b %RESULT%
