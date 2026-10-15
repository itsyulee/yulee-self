@echo off
setlocal EnableExtensions EnableDelayedExpansion
title NeuraSelf Installer
cd /d "%~dp0"
chcp 65001 >nul

set "INSTALL_DIR=%USERPROFILE%\Desktop\NeuraSelf"
set "REPO_URL=https://github.com/routo-loop/neura-self.git"
set "PYTHON_VER=3.10.11"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VER%/python-%PYTHON_VER%-amd64.exe"

color 0B

echo.
echo  [SYSTEM] NeuraSelf Installer
echo.

set "PY_CMD="

call :FindPython py
if defined PY_CMD goto PythonFound

call :FindPython python
if defined PY_CMD goto PythonFound

call :FindPython python3
if defined PY_CMD goto PythonFound

echo  [!] Python 3.10+ not found.
echo  [#] Downloading Python installer...

powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%TEMP%\py_inst.exe'"

if errorlevel 1 (
    echo.
    echo  [X] Failed to download Python.
    echo  Please install Python manually:
    echo  https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo  [#] Installing Python...

start /wait powershell -Command "Start-Process '%TEMP%\py_inst.exe' -ArgumentList '/passive InstallAllUsers=1 PrependPath=1 Include_test=0' -Verb RunAs -Wait"

if errorlevel 1 (
    echo.
    echo  [X] Python installation failed.
    del "%TEMP%\py_inst.exe" >nul 2>&1
    pause
    exit /b 1
)

del "%TEMP%\py_inst.exe" >nul 2>&1

set "PY_CMD=python"

:PythonFound

echo  [OK] Using Python: %PY_CMD%

where git >nul 2>&1

if errorlevel 1 (

    echo.
    echo  [!] Git not found.

    where winget >nul 2>&1

    if not errorlevel 1 (
        echo  [#] Installing Git with winget...
        winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
    ) else (
        where choco >nul 2>&1

        if not errorlevel 1 (
            echo  [#] Installing Git with Chocolatey...
            choco install git -y
        ) else (
            echo.
            echo  [X] Neither Winget nor Chocolatey is available.
            echo  Please install Git manually:
            echo  https://git-scm.com/download/win
            pause
            exit /b 1
        )
    )

    where git >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  [X] Git installation failed.
        pause
        exit /b 1
    )
)

echo  [OK] Git found.

if exist "%INSTALL_DIR%\.git" (

    echo.
    echo  [#] Updating existing installation...

    pushd "%INSTALL_DIR%"
    git pull
    if errorlevel 1 (
        popd
        echo  [X] Failed to update repository.
        pause
        exit /b 1
    )
    popd

) else (

    if exist "%INSTALL_DIR%" (
        rmdir /s /q "%INSTALL_DIR%"
    )

    echo.
    echo  [#] Cloning repository...

    git clone "%REPO_URL%" "%INSTALL_DIR%"

    if errorlevel 1 (
        echo.
        echo  [X] Clone failed.
        pause
        exit /b 1
    )
)

echo.
echo  [#] Launching setup...

pushd "%INSTALL_DIR%"

%PY_CMD% neura_setup.py --quick

if errorlevel 1 (
    popd
    echo.
    echo  [X] Setup failed.
    pause
    exit /b 1
)

popd

echo.
echo  [OK] Installation complete.
echo.
echo  Installed to:
echo  %INSTALL_DIR%
echo.
echo  Run:
echo  %INSTALL_DIR%\neura.py
echo.

pause
exit /b 0


:FindPython

%~1 --version >nul 2>&1
if errorlevel 1 exit /b

for /f "tokens=2" %%V in ('%~1 --version 2^>^&1') do (
    set "VER=%%V"
)

echo !VER! | findstr /R "^3\.1[0-9]\." >nul

if not errorlevel 1 (
    set "PY_CMD=%~1"
)

exit /b