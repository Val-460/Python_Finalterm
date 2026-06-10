@echo off
title Motor Data Analysis Platform - Integrated Launcher
cd /d "%~dp0"

echo Starting Backend API Server in a separate minimized window...
start "Backend API Server" /min cmd /c run_backend.bat

echo Waiting for Backend API Server to initialize (3 seconds)...
timeout /t 3 /nobreak >nul

echo Starting Frontend Control Panel...
call run_frontend.bat

echo Frontend window closed. Terminating backend server process tree...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Terminating backend process with PID %%a...
    taskkill /f /t /pid %%a >nul 2>&1
)
echo All processes cleaned up successfully.
pause
