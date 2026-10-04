@echo off
chcp 65001 >nul
title Village Rhapsody Save Modder
cd /d "%~dp0"

echo ============================================
echo   Village Rhapsody - Save File Modder
echo ============================================
echo.
echo Starting local server...

REM Find a usable Python
set "PY="
if exist "%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe" (
    set "PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
) else (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    if exist "%USERPROFILE%\.workbuddy\binaries\python\versions\3.13.12\python.exe" (
        set "PY=%USERPROFILE%\.workbuddy\binaries\python\versions\3.13.12\python.exe"
    )
)
if not defined PY (
    echo [ERROR] Python not found. Please install Python 3 first.
    pause
    exit /b 1
)

echo Using Python: %PY%
echo Keep this window OPEN. Browser will open automatically.
echo.

REM Open browser
start "" "http://127.0.0.1:8765/"

REM Start backend server
"%PY%" server.py

pause
