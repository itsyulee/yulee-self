@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
    python setup.py
) else (
    py -3 setup.py
)
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
