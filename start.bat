@echo off
title NEON RPC v2
cd /d "%~dp0"

echo.
echo  [NEON RPC v2] Starting...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)

echo  [SETUP] Checking dependencies...
pip install -r requirements.txt --quiet --disable-pip-version-check

echo  [RPC] Launching...
echo.

python main.py

echo.
echo  [SYS] NEON RPC exited.
pause