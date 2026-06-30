@echo off
setlocal

echo =========================================
echo   CPR Screener - Daily Data Updater
echo =========================================
echo.

:: Change to the repo directory
cd /d "%~dp0"

:: Check if FYERS_ACCESS_TOKEN is already set in env
if "%FYERS_ACCESS_TOKEN%"=="" (
    echo Enter your Fyers Access Token below.
    echo Format: eyJ0eX... (just the token, not AppId)
    echo.
    set /p FYERS_ACCESS_TOKEN="Fyers Token: "
)

if "%FYERS_ACCESS_TOKEN%"=="" (
    echo ERROR: No token provided. Exiting.
    pause
    exit /b 1
)

:: Optional: set client ID (change this to your App ID if different)
if "%FYERS_CLIENT_ID%"=="" set FYERS_CLIENT_ID=WY1A1JUOA0-100

echo.
echo [1/3] Running CPR data generator...
python generate_cpr.py
if errorlevel 1 (
    echo ERROR: Python script failed. Check output above.
    pause
    exit /b 1
)

echo.
echo [2/3] Committing updated data files to Git...
git add cpr_data*.json available_dates.json
git diff --staged --quiet
if errorlevel 1 (
    git commit -m "EOD CPR update %date:~-4,4%-%date:~-10,2%-%date:~-7,2%"
    echo Committed!
) else (
    echo No changes detected, nothing to commit.
)

echo.
echo [3/3] Pushing to GitHub...
git push
if errorlevel 1 (
    echo ERROR: Git push failed. Check your network/credentials.
    pause
    exit /b 1
)

echo.
echo =========================================
echo   Done! Data updated on GitHub Pages.
echo   Refresh your browser to see new data.
echo =========================================
echo.
pause
