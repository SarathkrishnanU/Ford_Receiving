@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 run_app.py --bootstrap-only
) else (
    python run_app.py --bootstrap-only
)

if errorlevel 1 (
    echo.
    echo Dependency bootstrap failed.
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m PyInstaller login_cpars_v2.spec --clean --noconfirm
) else (
    python -m PyInstaller login_cpars_v2.spec --clean --noconfirm
)

if errorlevel 1 (
    echo.
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Build complete: dist\LoginCPARS_v2\LoginCPARS_v2.exe
pause