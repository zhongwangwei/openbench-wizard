@echo off
chcp 65001 >nul
echo ========================================
echo   Building OpenBench Wizard for Windows
echo ========================================
echo.

REM Check Python
echo [1/7] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)
python --version

REM Install dependencies from requirements.txt
echo.
echo [2/7] Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

REM Install PyInstaller
echo.
echo [3/7] Installing PyInstaller...
pip install -q --upgrade pyinstaller
if errorlevel 1 (
    echo Error: Failed to install PyInstaller
    pause
    exit /b 1
)

REM ========================================
REM  PySide6 Diagnostics
REM ========================================
echo.
echo [4/7] Diagnosing PySide6 environment...

REM Check if PySide6 is installed
python -c "import PySide6; print(f'  PySide6 version: {PySide6.__version__}')" 2>nul
if errorlevel 1 (
    echo Error: PySide6 is not installed
    echo Please run: pip install PySide6
    pause
    exit /b 1
)

REM Check if QtCore can be imported (the actual problem)
echo   Testing QtCore import...
python -c "from PySide6.QtCore import QCoreApplication; print('  QtCore import: OK')" 2>nul
if errorlevel 1 (
    echo.
    echo ========================================
    echo   PySide6 QtCore import failed!
    echo ========================================
    echo.
    echo Possible causes:
    echo   1. Missing Visual C++ Redistributable
    echo   2. Incomplete PySide6 installation
    echo   3. Corrupted or missing DLL files
    echo.
    echo Solutions:
    echo   1. Install VC++ Redistributable:
    echo      winget install Microsoft.VCRedist.2015+.x64
    echo.
    echo   2. Reinstall PySide6:
    echo      pip uninstall PySide6 PySide6-Essentials PySide6-Addons shiboken6 -y
    echo      pip cache purge
    echo      pip install PySide6
    echo.
    pause
    exit /b 1
)

REM Show PySide6 path
for /f "delims=" %%i in ('python -c "import PySide6; print(PySide6.__path__[0])"') do set PYSIDE6_PATH=%%i
echo   PySide6 path: %PYSIDE6_PATH%

REM Add PySide6 to PATH to ensure DLLs are found during build
echo   Adding PySide6 to PATH...
set PATH=%PYSIDE6_PATH%;%PATH%

REM Check for potential Qt conflicts
echo.
echo [5/7] Checking Qt-related packages...
python -c "import pkg_resources; pkgs = [p.key for p in pkg_resources.working_set if 'qt' in p.key.lower() or 'pyside' in p.key.lower() or 'pyqt' in p.key.lower()]; print('  Installed:', ', '.join(pkgs) if pkgs else 'None')"

REM Clean previous build
echo.
echo [6/7] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build executable
echo.
echo [7/7] Building application...
echo ----------------------------------------
pyinstaller --clean openbench_wizard.spec
if errorlevel 1 (
    echo.
    echo ========================================
    echo   Build failed!
    echo ========================================
    echo.
    echo If you see QtLibraryInfo warnings, try:
    echo   1. Ensure all PySide6 diagnostics above passed
    echo   2. Run this script as Administrator
    echo   3. Retry in a clean virtual environment
    echo.
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
