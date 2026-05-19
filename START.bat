@echo off
chcp 65001 >nul
title Rasd Monitoring App

echo.
echo  ============================================
echo   Rasd Monitoring App
echo  ============================================
echo.

cd /d "%~dp0backend"

REM Install requirements quietly if missing
python -c "import fastapi, uvicorn, requests" 2>nul
if errorlevel 1 (
    echo [+] Installing requirements...
    python -m pip install -q -r requirements.txt
)

REM Start backend (also serves the frontend at /)
echo [+] Starting server on http://127.0.0.1:8765 ...
echo.
start "" "http://127.0.0.1:8765"
python main.py
