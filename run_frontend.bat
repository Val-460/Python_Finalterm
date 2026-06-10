@echo off
title Motor Data Analysis - Frontend Launcher
set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\frontend_launch.log"
echo [LOG START] %date% %time% > "%LOG_FILE%"

echo Starting Tkinter frontend control panel...
echo Starting Tkinter frontend control panel... >> "%LOG_FILE%"

cd /d "%~dp0"

if exist "requirements.txt" goto has_req
echo [ERROR] Cannot find requirements.txt. >> "%LOG_FILE%"
echo [ERROR] Cannot find requirements.txt. Please verify your project files.
pause
exit /b 1
:has_req

set "PY_CMD=python"
if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python313\python.exe" (
    set "PY_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python313\python.exe"
) else if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" (
    set "PY_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
) else if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
) else if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe" (
    set "PY_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe"
) else if exist "C:\Users\LINia\AppData\Local\Python\pythoncore-3.14-64\python.exe" (
    set "PY_CMD=C:\Users\LINia\AppData\Local\Python\pythoncore-3.14-64\python.exe"
)
echo Using Python path: %PY_CMD% >> "%LOG_FILE%"

:: Check and install dependencies
echo Checking dependencies...
echo Checking dependencies... >> "%LOG_FILE%"
"%PY_CMD%" -c "import requests, PIL" >> "%LOG_FILE%" 2>&1
if not errorlevel 1 goto has_deps
echo Installing required dependencies from requirements.txt...
echo Installing required dependencies from requirements.txt... >> "%LOG_FILE%"
"%PY_CMD%" -m pip install -r requirements.txt >> "%LOG_FILE%" 2>&1
:has_deps

echo Opening Tkinter window...
echo Opening Tkinter window... >> "%LOG_FILE%"

:: Use PowerShell to show console output and log to file at the same time
powershell -Command "& '%PY_CMD%' frontend\app.py 2>&1 | Tee-Object -FilePath '%LOG_FILE%' -Append"

if not errorlevel 1 goto end
echo.
echo [ERROR] Application failed to start. See logs\frontend_launch.log for details.
echo [ERROR] Application failed to start. >> "%LOG_FILE%"
pause
:end
