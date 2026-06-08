@echo off
title Motor Data Analysis - Backend API Server
set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\backend_launch.log"
echo [LOG START] %date% %time% > "%LOG_FILE%"

echo Starting FastAPI backend server...
echo Starting FastAPI backend server... >> "%LOG_FILE%"

cd /d "%~dp0"

set "PY_CMD=python"
if exist "C:\Users\LINia\AppData\Local\Python\pythoncore-3.14-64\python.exe" (
    set "PY_CMD=C:\Users\LINia\AppData\Local\Python\pythoncore-3.14-64\python.exe"
)
echo Using Python: %PY_CMD% >> "%LOG_FILE%"

cd backend

if not exist "venv\Scripts\activate.bat" goto no_venv1
echo Activating virtual environment (venv)...
call "venv\Scripts\activate.bat"
set "PY_CMD=python"
goto venv_done
:no_venv1

if not exist ".venv\Scripts\activate.bat" goto venv_done
echo Activating virtual environment (.venv)...
call ".venv\Scripts\activate.bat"
set "PY_CMD=python"
:venv_done

echo Starting Uvicorn server on http://127.0.0.1:8000...
echo Starting Uvicorn server on http://127.0.0.1:8000... >> "%LOG_FILE%"

:: Use PowerShell to show console output and log to file at the same time
:: Runs server.py directly in CWD backend/ so reload works perfectly
powershell -Command "& '%PY_CMD%' server.py 2>&1 | Tee-Object -FilePath '%LOG_FILE%' -Append"

echo Backend server stopped.
echo Backend server stopped. >> "%LOG_FILE%"
:end
