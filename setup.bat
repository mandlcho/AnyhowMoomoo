@echo off
REM One-command setup script for AnyhowMoomoo (Windows)
REM Usage: setup.bat

echo ==========================================
echo AnyhowMoomoo - Automated Setup
echo ==========================================
echo.

REM Check Python version
echo 1. Checking Python version...
python --version
if %errorlevel% neq 0 (
    echo    ERROR: Python not found. Please install Python 3.10+
    exit /b 1
)
echo    ✅ Python found
echo.

REM Install dependencies
echo 2. Installing dependencies...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo    ERROR: Failed to install dependencies
    exit /b 1
)
echo    ✅ Dependencies installed
echo.

REM Create .env from template if it doesn't exist
echo 3. Setting up environment file...
if not exist .env (
    copy .env.example .env >nul
    echo    ✅ .env file created from template
    echo    ⚠️  IMPORTANT: Edit .env with your moomoo credentials!
) else (
    echo    ℹ️  .env file already exists, skipping
)
echo.

REM Run verification
echo 4. Running setup verification...
echo.
python scripts/verify_setup.py
echo.

echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Edit .env file with your moomoo credentials
echo 2. Run: python scripts/test_config.py
echo 3. Run: python -m daemon.main (when OpenD is running)
echo.
echo Documentation:
echo - START_HERE.md    - Quick overview
echo - QUICKSTART.md    - 5-minute guide
echo - SETUP.md         - Detailed troubleshooting
echo.
pause
