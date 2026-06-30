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
echo This will open a browser login. Follow the steps below.
echo.

:: Run the login script and capture the token
python fyers_login.py > fyers_token_output.txt 2>&1
if errorlevel 1 (
    type fyers_token_output.txt
    echo.
    echo ERROR: Login script failed. See output above.
    del fyers_token_output.txt 2>nul
    pause
    exit /b 1
)

:: Show the output to the user
type fyers_token_output.txt

:: Extract the access token from the output
:: The token appears after "=== YOUR ACCESS TOKEN ===" line
set "FOUND_TOKEN=0"
set "FYERS_ACCESS_TOKEN="
for /f "delims=" %%L in (fyers_token_output.txt) do (
    if "!FOUND_TOKEN!"=="1" (
        if not "%%L"=="=========================" (
            set "FYERS_ACCESS_TOKEN=%%L"
            set "FOUND_TOKEN=2"
        )
    )
    if "%%L"=="=== YOUR ACCESS TOKEN ===" set "FOUND_TOKEN=1"
)
del fyers_token_output.txt 2>nul

if "!FYERS_ACCESS_TOKEN!"=="" (
    echo.
    echo Could not auto-extract token. Please paste it manually:
    set /p FYERS_ACCESS_TOKEN="Access Token: "
)

if "!FYERS_ACCESS_TOKEN!"=="" (
    echo ERROR: No token. Exiting.
    pause
    exit /b 1
)

echo.
echo Token captured successfully!
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
