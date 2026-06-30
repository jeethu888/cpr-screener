@echo off
setlocal

echo ===============================================
echo   CPR Screener - 1-Click Cloud Trigger
echo ===============================================
echo.

cd /d "%~dp0"

python trigger_cloud.py

echo.
pause
