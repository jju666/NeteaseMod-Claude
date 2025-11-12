@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ========================================
echo   MODSDK Notification System Installer
echo ========================================
echo.

REM Detect Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    where python3 >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] Python not found
        echo        Please install Python 3.7+
        pause
        exit /b 1
    )
    set PYTHON_CMD=python3
) else (
    set PYTHON_CMD=python
)

for /f "tokens=*" %%i in ('%PYTHON_CMD% --version') do set PYTHON_VERSION=%%i
echo [OK] Detected Python: %PYTHON_VERSION%
echo.

REM Check if plyer is installed
%PYTHON_CMD% -c "import plyer" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] plyer library is already installed
    for /f "tokens=*" %%i in ('%PYTHON_CMD% -c "import plyer; print(plyer.__version__)"') do set PLYER_VERSION=%%i
    echo      Version: !PLYER_VERSION!
    echo.
    echo [SUCCESS] Notification system is ready!
    echo.
    echo Test notifications:
    echo   python templates\.claude\hooks\vscode_notify.py
    pause
    exit /b 0
)

REM Install plyer
echo [INFO] Installing plyer library...
echo.

%PYTHON_CMD% -m pip install plyer
if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] plyer installed successfully!
    echo.
    echo ========================================
    echo   Test Notifications
    echo ========================================
    echo.
    echo Run this command to test:
    echo   python templates\.claude\hooks\vscode_notify.py
    echo.
    echo Or trigger in project:
    echo   /mc "test task"
    echo.
    echo [TIP] If no notification appears:
    echo   1. Open Settings - System - Notifications
    echo   2. Find "Python" or "Windows Terminal"
    echo   3. Enable "Show notification banners"
    echo.
) else (
    echo.
    echo [ERROR] Failed to install plyer
    echo.
    echo Possible reasons:
    echo   1. Network connection issue
    echo   2. pip is outdated
    echo   3. Insufficient permissions
    echo.
    echo Manual installation:
    echo   %PYTHON_CMD% -m pip install --user plyer
    echo.
    echo Note: Notifications will still work without plyer
    echo       (fallback to colored terminal output)
)

pause
