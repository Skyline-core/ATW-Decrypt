@echo off
setlocal
cd /d "%~dp0"

set VENV_DIR=.venv

if not exist "%VENV_DIR%\Scripts\activate.bat" (
  echo Creating virtual environment in %VENV_DIR% ...
  python -m venv %VENV_DIR%
  if errorlevel 1 exit /b 1
)

call "%VENV_DIR%\Scripts\activate.bat"

echo Installing / updating PyInstaller in venv ...
python -m pip install --upgrade pip pyinstaller
if errorlevel 1 exit /b 1

python -m PyInstaller --onefile --clean --name atw622g-decrypt --console atw622g_decrypt.py
if errorlevel 1 exit /b 1

echo.
echo Binary: dist\atw622g-decrypt.exe
dir dist\atw622g-decrypt.exe
