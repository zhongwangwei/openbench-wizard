@echo off
chcp 65001 >nul
echo ========================================
echo   Building OpenBench Wizard for Windows
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install dependencies from requirements.txt
echo Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

REM Install PyInstaller
echo Installing PyInstaller...
pip install -q --upgrade pyinstaller
if errorlevel 1 (
    echo Error: Failed to install PyInstaller
    pause
    exit /b 1
)

REM Clean previous build
echo Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build executable
echo.
echo Building application...
pyinstaller --clean openbench_wizard.spec
if errorlevel 1 (
    echo Error: Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Build complete!
echo ========================================
echo.
echo Output location: dist\OpenBench_Wizard\
echo Run: dist\OpenBench_Wizard\OpenBench_Wizard.exe
echo.
pause
