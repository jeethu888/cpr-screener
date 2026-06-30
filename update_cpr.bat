@echo off
setlocal

echo =========================================
echo   CPR Screener - Daily Data Updater
echo =========================================
echo.

:: Change to the repo directory
cd /d "%~dp0"

:: Prompt for Fyers App ID (Client ID)
if "%FYERS_CLIENT_ID%"=="" (
    echo Your Fyers App ID is shown in your Fyers API dashboard.
    echo Example: WY1A1JUOA0-100
    echo.
    set /p FYERS_CLIENT_ID="Fyers App ID (Client ID): "
)

if "%FYERS_CLIENT_ID%"=="" (
    echo ERROR: No App ID provided. Exiting.
    pause
    exit /b 1
)

:: Prompt for Fyers Access Token
echo.
echo Your Fyers Access Token is the long string from your daily login.
echo Get it from: https://myapi.fyers.in  -^> API dashboard -^> Access Token
echo Paste just the token string (starts with eyJ...) - NOT AppId:Token
echo.
if "%FYERS_ACCESS_TOKEN%"=="" (
    set /p FYERS_ACCESS_TOKEN="Fyers Access Token: "
)

if "%FYERS_ACCESS_TOKEN%"=="" (
    echo ERROR: No token provided. Exiting.
    pause
    exit /b 1
)

echo.
echo [1/3] Running CPR data generator...
python generate_cpr.py
if errorlevel 1 (
    echo.
    echo ERROR: Python script failed. Check output above.
    pause
    exit /b 1
)

echo.
echo [2/3] Committing updated data files to Git...
git add cpr_data*.json available_dates.json
git diff --staged --quiet
if errorlevel 1 (
    for /f "tokens=1-3 delims=/" %%a in ("%date%") do set TODAY=%%c-%%b-%%a
    git commit -m "EOD CPR update %TODAY%"
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
