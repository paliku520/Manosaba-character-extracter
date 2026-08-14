@echo off
rem launcher - ASCII only (avoid cmd encoding issues)
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

rem Usage: start.bat [electron|py|help]

set MODE=%~1
if "%MODE%"=="" set MODE=electron
if /i "%MODE%"=="-h" set MODE=help
if /i "%MODE%"=="/?" set MODE=help
if /i "%MODE%"=="help" goto :help
if /i "%MODE%"=="py" set MODE=pywebview
if /i "%MODE%"=="python" set MODE=pywebview
if /i "%MODE%"=="pywebview" goto :pywebview
if /i "%MODE%"=="electron" goto :electron
goto :help

:pywebview
echo.
echo  [MCE] Starting PyWebView mode...
echo  [MCE] Note: keep this window open, closing it quits the app.
echo.
python run.py
goto :end

:electron
echo.
echo  [MCE] Starting Electron mode...
echo.
rem Detect Python interpreter for the backend child process (override via MCE_PYTHON)
if not defined MCE_PYTHON (
    if exist ".venv\Scripts\python.exe" set "MCE_PYTHON=%CD%\.venv\Scripts\python.exe"
    if exist "venv\Scripts\python.exe" set "MCE_PYTHON=%CD%\venv\Scripts\python.exe"
    if not defined MCE_PYTHON if exist "D:\Python\python.exe" set "MCE_PYTHON=D:\Python\python.exe"
    if not defined MCE_PYTHON set "MCE_PYTHON=python"
)
if exist "electron\node_modules\electron\dist\electron.exe" (
    echo  [MCE] Python: %MCE_PYTHON%
    "electron\node_modules\electron\dist\electron.exe" electron
) else (
    echo.
    echo  [MCE] Electron not found. Install first:
    echo       cd electron
    echo       npm install
    echo.
    pause
)
goto :end

:help
echo.
echo  MCE launcher
echo  ===========================
echo    start.bat           Electron mode (default, frameless + Aero Snap)
echo    start.bat py        PyWebView mode (native window)
echo    start.bat help      Show this help
echo.
goto :end

:end
endlocal
