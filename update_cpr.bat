@echo off
setlocal EnableDelayedExpansion

echo =========================================
echo   CPR Screener - Daily Data Updater
echo =========================================
echo.

:: Change to the repo directory
cd /d "%~dp0"

echo STEP 1: Generate your Fyers Access Token
echo -----------------------------------------
echo Follow the prompts below to log in to Fyers.
echo.

:: Delete any stale token file
if exist fyers_token.txt del fyers_token.txt

:: Run login script interactively (user sees all prompts)
python fyers_login.py
if errorlevel 1 (
    echo.
    echo ERROR: Login script failed.
    pause
    exit /b 1
)

:: Read the token saved by fyers_login.py
if not exist fyers_token.txt (
    echo.
    echo ERROR: Token file not found. Login may have failed.
    pause
    exit /b 1
)

:: Read token into variable
set /p FYERS_ACCESS_TOKEN=<fyers_token.txt
del fyers_token.txt

if "!FYERS_ACCESS_TOKEN!"=="" (
    echo ERROR: Token is empty. Exiting.
    pause
    exit /b 1
)

echo.
echo Token captured! Starting data fetch...
echo.
echo =========================================
echo STEP 2: Fetching CPR data from Fyers API
echo =========================================
echo.

python generate_cpr.py
if errorlevel 1 (
    echo.
    echo ERROR: CPR data generation failed. Check output above.
    pause
    exit /b 1
)

echo.
echo =========================================
echo STEP 3: Pushing updated data to GitHub
echo =========================================
echo.

git add cpr_data*.json available_dates.json
git diff --staged --quiet
if errorlevel 1 (
    git commit -m "EOD CPR update %date%"
    echo Committed!
) else (
    echo No data changes detected.
)

git push
if errorlevel 1 (
    echo ERROR: Git push failed. Check network/credentials.
    pause
    exit /b 1
)

echo.
echo =========================================
echo   ALL DONE!
echo   Refresh jeethu888.github.io/cpr-screener
echo   to see updated data.
echo =========================================
echo.
pause
