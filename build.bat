@echo off

echo.
echo  ========================================
echo   OBD-II Diagnostics - Build Script
echo  ========================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found!
    echo  Download: https://www.python.org/downloads/
    echo  Check "Add Python to PATH" during install!
    pause
    exit /b 1
)

echo  [1/4] Python OK. Updating pip...
python -m pip install --upgrade pip --quiet --quiet

echo  [2/4] Installing packages...
pip install obd pyinstaller --quiet --quiet
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to install packages!
    pause
    exit /b 1
)

echo  [3/4] Building exe...
pyinstaller --onefile --windowed --name "OBD2_Diagnostics" --add-data "updater.py;." car_diagnostics_gui.py
if %errorlevel% neq 0 (
    echo  [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo  [4/4] DONE!
echo  File: dist\OBD2_Diagnostics.exe
echo.
pause
