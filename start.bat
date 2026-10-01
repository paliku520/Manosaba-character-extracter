@echo off
rem MCE launcher - ASCII only (avoid cmd encoding issues)
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

rem Usage: start.bat [help]  or  start.bat clean [targets]
rem Only one launch path exists: Electron shell + Python backend subprocess.

if /i "%~1"=="-h" goto :help
if /i "%~1"=="/?" goto :help
if /i "%~1"=="help" goto :help
if /i "%~1"=="clean" goto :clean

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

:clean
rem Usage:
rem   start.bat clean                    temp + logs + build + pycache (default)
rem   start.bat clean temp               only temp\ scratch files
rem   start.bat clean logs               only logs\*.log
rem   start.bat clean build              only build\ - PyInstaller cache
rem   start.bat clean pycache            only __pycache__ + .pytest_cache
rem   start.bat clean dist               only dist\ - packaging output
rem   start.bat clean all                everything above
rem   start.bat clean temp logs build    combine any targets with spaces
rem NOTE: user data - data\ , output\ , builtin\ , electron\node_modules - is never touched.
set "DO_TEMP=0"
set "DO_LOGS=0"
set "DO_BUILD=0"
set "DO_PYCACHE=0"
set "DO_DIST=0"
set "SEEN=0"

:clean_next
shift
if "%~1"=="" goto :clean_run
set "SEEN=1"
set "KNOWN=0"
if /i "%~1"=="temp"    ( set "DO_TEMP=1"    & set "KNOWN=1" )
if /i "%~1"=="logs"    ( set "DO_LOGS=1"    & set "KNOWN=1" )
if /i "%~1"=="build"   ( set "DO_BUILD=1"   & set "KNOWN=1" )
if /i "%~1"=="pycache" ( set "DO_PYCACHE=1" & set "KNOWN=1" )
if /i "%~1"=="dist"    ( set "DO_DIST=1"    & set "KNOWN=1" )
if /i "%~1"=="all"     ( set "DO_TEMP=1" & set "DO_LOGS=1" & set "DO_BUILD=1" & set "DO_PYCACHE=1" & set "DO_DIST=1" & set "KNOWN=1" )
if /i "%~1"=="-a"      ( set "DO_TEMP=1" & set "DO_LOGS=1" & set "DO_BUILD=1" & set "DO_PYCACHE=1" & set "DO_DIST=1" & set "KNOWN=1" )
if "%KNOWN%"=="0" echo   [!] Unknown target: %~1   -  see: start.bat help
goto :clean_next

:clean_run
if "%SEEN%"=="0" (
    set "DO_TEMP=1"
    set "DO_LOGS=1"
    set "DO_BUILD=1"
    set "DO_PYCACHE=1"
)

echo.
echo  [MCE] Cleaning project leftovers...
echo.

if "%DO_TEMP%"=="1" if exist "temp\" (
    rmdir /s /q "temp"
    echo   [OK] temp\              scratch files
)
if "%DO_LOGS%"=="1" if exist "logs\*.log" (
    del /q "logs\*.log" >nul 2>nul
    echo   [OK] logs\*.log         log files
)
if "%DO_BUILD%"=="1" if exist "build\" (
    rmdir /s /q "build"
    echo   [OK] build\             PyInstaller cache
)
if "%DO_DIST%"=="1" if exist "dist\" (
    rmdir /s /q "dist"
    echo   [OK] dist\              packaging output
)
if "%DO_PYCACHE%"=="1" (
    if exist ".pytest_cache\" (
        rmdir /s /q ".pytest_cache"
        echo   [OK] .pytest_cache\     pytest cache
    )
    set "PYCACHE_COUNT=0"
    if exist "__pycache__\" (
        rmdir /s /q "__pycache__"
        set /a PYCACHE_COUNT+=1
    )
    rem Sweep only our own source trees - never .venv or electron\node_modules -
    rem because the root path of "for /d /r" is not variable-expanded: use :sweep_pycache.
    for %%r in ("src" "scripts" "builtin" "i18n") do call :sweep_pycache "%%~r"
    echo   [OK] __pycache__ x !PYCACHE_COUNT!
)

echo.
echo  [MCE] Done.
echo.
goto :end

:help
echo.
echo  MCE launcher (Electron)
echo  ===========================
echo    start.bat                Electron mode (frameless + Aero Snap)
echo    start.bat help           Show this help
echo.
echo  Cleanup:
echo    start.bat clean [target ...]
echo      no target  =  temp + logs + build + pycache
echo      temp       temp\ scratch files
echo      logs       logs\*.log
echo      build      build\ - PyInstaller cache
echo      pycache    __pycache__ + .pytest_cache
echo      dist       dist\ - packaging output
echo      all        everything above
echo    example: start.bat clean temp logs
echo.
goto :end

:sweep_pycache
rem Remove every __pycache__ under %~1 (recursive). Keeps the counter in the caller.
if not exist "%~1" goto :eof
pushd "%~1"
for /d /r "%CD%" %%d in (__pycache__) do (
    rd /s /q "%%~fd" >nul 2>nul
    set /a PYCACHE_COUNT+=1
)
popd
goto :eof

:end
endlocal
