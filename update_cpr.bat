@echo off
setlocal EnableDelayedExpansion

echo ===============================================
echo      CPR Screener - Data Update Manager
echo ===============================================
echo.

cd /d "%~dp0"

echo How would you like to update the CPR data?
echo.
echo   [1] Run in the CLOUD (Recommended)
echo       - Triggers GitHub servers to fetch 200+ stocks.
echo       - You can close the window immediately.
echo.
echo   [2] Run LOCALLY on this PC
echo       - Fetches 200+ stocks directly from your computer.
echo       - Takes ~60 seconds to complete.
echo.
set /p choice="Enter your choice (1 or 2): "

if "%choice%"=="1" (
    echo.
    echo ===============================================
    echo   Starting Cloud Update...
    echo ===============================================
    python trigger_cloud.py
    echo.
    pause
    exit /b 0
)

if "%choice%"=="2" (
    echo.
    echo ===============================================
    echo   Starting Local Update...
    echo ===============================================
    
    :: Delete any stale token file
    if exist fyers_token.txt del fyers_token.txt

    echo STEP 1: Generate your Fyers Access Token
    echo -----------------------------------------
    python fyers_login.py
    if errorlevel 1 (
        echo ERROR: Login script failed.
        pause
        exit /b 1
    )

    if not exist fyers_token.txt (
        echo ERROR: Token file not found. Login may have failed.
        pause
        exit /b 1
    )

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
        echo ERROR: CPR data generation failed.
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
        echo ERROR: Git push failed.
        pause
        exit /b 1
    )

    echo.
    echo =========================================
    echo   ALL DONE!
    echo   Refresh jeethu888.github.io/cpr-screener
    echo =========================================
    echo.
    pause
    exit /b 0
)

echo Invalid choice. Exiting...
pause
