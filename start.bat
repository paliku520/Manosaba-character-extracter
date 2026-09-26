@echo off
rem MCE launcher - ASCII only (avoid cmd encoding issues)
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

rem Usage: start.bat [help]
rem Only one launch path exists: Electron shell + Python backend subprocess.

if /i "%~1"=="-h" goto :help
if /i "%~1"=="/?" goto :help
if /i "%~1"=="help" goto :help

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
echo  MCE launcher (Electron)
echo  ===========================
echo    start.bat           Electron mode (frameless + Aero Snap)
echo    start.bat help      Show this help
echo.
goto :end

:end
endlocal
