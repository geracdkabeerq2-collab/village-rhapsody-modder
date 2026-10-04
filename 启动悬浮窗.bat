@echo off
chcp 65001 >nul
title Village Rhapsody Floating Modder
cd /d "%~dp0"

echo ============================================
echo   Village Rhapsody - Floating Window Modder
echo ============================================
echo.
echo Starting floating window...

REM Python env with pywebview installed
set "PY=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if not exist "%PY%" (
    echo [ERROR] Python environment not found!
    echo Expected: %PY%
    pause
    exit /b 1
)

"%PY%" floating.py

if errorlevel 1 (
    echo.
    echo [ERROR] Floating window exited with an error. See message above.
)
pause
