@echo off
echo Building OpenBench Wizard for Windows...
echo.

REM Install dependencies
pip install pyinstaller pyside6 pyyaml psutil

REM Build executable
pyinstaller --clean build_windows.spec

echo.
echo Build complete! Executable is in: dist\OpenBench_Wizard.exe
pause
