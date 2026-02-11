@echo off
echo Setting up University WiFi Quality Monitoring System...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.7 or higher.
    pause
    exit /b 1
)

REM Install Python packages
echo Installing required Python packages...
pip install -r requirements.txt

if errorlevel 1 (
    echo Failed to install Python packages. Please check requirements.txt
    pause
    exit /b 1
)

echo.
echo Setup completed successfully!
echo.
echo To start the system, run: python run_system.py
echo.

pause