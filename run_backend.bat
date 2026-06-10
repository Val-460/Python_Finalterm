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
if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" (
    set "PY_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
) else if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
) else if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe" (
    set "PY_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe"
) else if exist "C:\Users\LINia\AppData\Local\Python\pythoncore-3.14-64\python.exe" (
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

echo Checking backend dependencies...
echo Checking backend dependencies... >> "%LOG_FILE%"
"%PY_CMD%" -c "import fastapi, uvicorn, sqlalchemy, pandas, matplotlib, requests, bs4, openpyxl" >> "%LOG_FILE%" 2>&1
if not errorlevel 1 goto has_backend_deps
echo Installing required backend dependencies from requirements.txt...
echo Installing required backend dependencies from requirements.txt... >> "%LOG_FILE%"
"%PY_CMD%" -m pip install -r ..\requirements.txt >> "%LOG_FILE%" 2>&1
:has_backend_deps

echo Starting Uvicorn server on http://127.0.0.1:8000...
echo Starting Uvicorn server on http://127.0.0.1:8000... >> "%LOG_FILE%"

:: Use PowerShell to show console output and log to file at the same time
:: Runs server.py directly in CWD backend/ so reload works perfectly
powershell -Command "& '%PY_CMD%' server.py 2>&1 | Tee-Object -FilePath '%LOG_FILE%' -Append"

echo Backend server stopped.
echo Backend server stopped. >> "%LOG_FILE%"
:end
