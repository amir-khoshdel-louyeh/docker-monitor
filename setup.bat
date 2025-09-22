@echo off
echo Setting up Python virtual environment for Docker Monitor...

:: Check if python is available on the PATH
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: python is not installed or not in your PATH. Please install Python 3.8+ and try again.
    exit /b 1
)

:: Create virtual environment in a folder named 'venv'
python -m venv venv

:: Activate the environment and install dependencies
call .\\venv\\Scripts\\activate.bat
pip install -r requirements.txt

echo.
echo Setup complete!
echo To run the application in the future, first activate the environment with:
echo   .\\venv\\Scripts\\activate.bat
echo Then, run the application with:
echo   python app_tkinter.py