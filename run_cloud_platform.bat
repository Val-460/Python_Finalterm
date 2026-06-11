@echo off
title Hybrid Edge-to-Local Launcher
cd /d "%~dp0"

echo ========================================================
echo   [1/2] Starting Local Backend (Python FastAPI)...
echo ========================================================
start "Local Backend Server" /min cmd /c run_backend.bat

echo Waiting for backend to initialize (approx 3 seconds)...
timeout /t 3 /nobreak >nul

echo.
echo ========================================================
echo   [2/2] Opening Vercel Cloud Frontend...
echo ========================================================
set VERCEL_URL=https://python-finalterm.vercel.app
start "" "%VERCEL_URL%"

echo.
echo ========================================================
echo SUCCESS!
echo.
echo You can now use the website in your browser.
echo The website will automatically connect to this local backend.
echo.
echo WARNING: DO NOT CLOSE THIS BLACK WINDOW while using the site!
echo.
echo Press any key to stop the backend and exit.
echo ========================================================
pause

echo Stopping local backend...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /f /t /pid %%a >nul 2>&1
)
echo Goodbye!
