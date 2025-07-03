@echo off
echo Starting BackupTool installation for Windows...

:: Ensure Python 3 and pip are available
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.8+ from python.org.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Check for pip
python -m pip --version >nul 2>nul
if %errorlevel% neq 0 (
    echo pip not found. Attempting to install pip...
    python -m ensurepip --default-pip
    if %errorlevel% neq 0 (
        echo Failed to install pip. Please install it manually.
        pause
        exit /b 1
    )
)

:: Create a virtual environment if it doesn't exist
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Activate virtual environment and install packages
echo Activating virtual environment and installing required Python packages...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

pip install paramiko cryptography ttkthemes
if %errorlevel% neq 0 (
    echo Failed to install Python packages. Please check your internet connection or try again.
    call venv\Scripts\deactivate.bat
    pause
    exit /b 1
)

:: Create a simple launcher batch file
echo @echo off > backuptool.bat
echo call venv\Scripts\activate.bat >> backuptool.bat
echo python main.py %%* >> backuptool.bat
echo call venv\Scripts\deactivate.bat >> backuptool.bat
echo echo. >> backuptool.bat
echo echo To close this window, press any key... >> backuptool.bat
echo pause >nul >> backuptool.bat

echo Installation complete!
echo You can now run BackupTool by double-clicking 'backuptool.bat' in this folder.
echo Or, open Command Prompt/PowerShell here and type 'backuptool.bat'.

call venv\Scripts\deactivate.bat
pause
