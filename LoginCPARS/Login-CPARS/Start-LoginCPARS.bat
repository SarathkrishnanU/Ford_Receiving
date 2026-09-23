@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 run_app.py
) else (
    python run_app.py
)

if errorlevel 1 (
    echo.
    echo LoginCPARS failed to start. Review the message above or LoginCPARS.log.
    pause
)