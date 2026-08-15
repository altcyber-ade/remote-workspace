@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo Remote Workspace - Windows AMD64 Builder
echo =========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python launcher "py" was not found.
    echo Install 64-bit Python 3.13 from python.org first.
    pause
    exit /b 1
)

echo [1/6] Checking Python 3.13 x64...
py -3.13 -c "import struct,platform,sys; print(sys.version); print('Machine:',platform.machine()); print('Bits:',struct.calcsize('P')*8); assert struct.calcsize('P')*8 == 64"
if errorlevel 1 goto :fail

echo.
echo [2/6] Creating clean build environment...
if exist .build-venv rmdir /s /q .build-venv
py -3.13 -m venv .build-venv
if errorlevel 1 goto :fail

call .build-venv\Scripts\activate.bat
if errorlevel 1 goto :fail

echo.
echo [3/6] Installing dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :fail

echo.
echo [4/6] Cleaning old output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [5/6] Building Windows AMD64 application...
python -m PyInstaller --clean --noconfirm RemoteWorkspace-Windows.spec
if errorlevel 1 goto :fail

echo.
echo [6/6] Verifying output...
if not exist "dist\Remote Workspace\Remote Workspace.exe" goto :fail

echo.
echo SUCCESS

echo Portable app folder:
echo   %CD%\dist\Remote Workspace

echo Main executable:
echo   %CD%\dist\Remote Workspace\Remote Workspace.exe

echo Copy the entire "Remote Workspace" folder to another Windows x64 PC.
echo Python is not required on the destination machine.
echo.
pause
exit /b 0

:fail
echo.
echo BUILD FAILED. Review the error above.
pause
exit /b 1
