@echo off
chcp 65001 >nul
title 貳輪嶼大數據平台 - 混合雲啟動器 (Hybrid Edge-to-Local)
cd /d "%~dp0"

echo ========================================================
echo   [1/2] 正在啟動本機運算核心 (Python FastAPI)...
echo ========================================================
start "Local Backend Server" /min cmd /c run_backend.bat

echo 等待運算核心初始化 (約需 3 秒)...
timeout /t 3 /nobreak >nul

echo.
echo ========================================================
echo   [2/2] 正在開啟 Vercel 雲端前端網頁...
echo ========================================================
echo 請將下方網址替換為您實際在 Vercel 上的部署網址
set VERCEL_URL=https://python-finalterm.vercel.app
start %VERCEL_URL%

echo.
echo ========================================================
echo ✅ 啟動成功！
echo.
echo 現在您可以使用瀏覽器上的 Vercel 網頁，網頁將自動呼叫本機算力。
echo ⚠️ 警告：在使用網頁期間，請勿關閉這個黑色視窗！
echo.
echo 若要結束使用，請直接關閉此黑色視窗，或是按任意鍵結束並關閉後端。
echo ========================================================
pause

echo 正在關閉本機運算核心...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /f /t /pid %%a >nul 2>&1
)
echo 關閉完成。
