@echo off
REM Installation script for WWV/WWVH Discrimination Application (Windows)

echo ==========================================
echo WWV/WWVH Discrimination App - Installation
echo ==========================================
echo.

REM Check Python
echo Checking Python version...
python --version
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.8 or later.
    pause
    exit /b 1
)
echo.

REM Create virtual environment
echo Creating virtual environment...
if exist venv (
    echo Virtual environment already exists. Skipping...
) else (
    python -m venv venv
    echo Virtual environment created.
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Upgrade pip, setuptools, and packaging
echo Upgrading pip, setuptools, and packaging...
pip install --upgrade pip setuptools packaging
echo.

REM Install ka9q-python
echo Installing ka9q-python...
if exist ka9q-python (
    echo ka9q-python directory already exists.
    echo Reinstalling from existing directory...
    cd ka9q-python
    pip install -e .
    cd ..
) else (
    echo Cloning ka9q-python repository...
    git clone https://github.com/mijahauan/ka9q-python.git
    cd ka9q-python
    pip install -e .
    cd ..
)
echo.

REM Install application requirements
echo Installing application requirements...
pip install -r requirements.txt
echo.

REM Verify installation
echo Verifying installation...
python -c "from ka9q import RadiodControl; print('✓ ka9q successfully installed')"
python -c "import numpy; print('✓ numpy successfully installed')"
python -c "import scipy; print('✓ scipy successfully installed')"
python -c "import matplotlib; print('✓ matplotlib successfully installed')"
echo.

echo ==========================================
echo Installation complete!
echo ==========================================
echo.
echo To use the application:
echo   1. Activate the virtual environment:
echo      venv\Scripts\activate
echo.
echo   2. Run the application:
echo      python main.py --radiod radiod.local
echo.
echo   3. Or try the examples:
echo      python example_usage.py
echo.
echo See QUICKSTART.md for more information.
echo.
pause
