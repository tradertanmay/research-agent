@echo off
REM ==============================================================================
REM Autonomous Research Agent - Windows 1-Click Launcher
REM ==============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================
echo    Autonomous Research Agent - Launcher (Windows)
echo ========================================================
echo.

REM 1. Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found on your PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check the box "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM 2. Check Virtual Environment
if not exist ".venv" (
    echo [INFO] Virtual environment not found. Setting it up now...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [INFO] Installing dependencies...
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\pip.exe install -r requirements.txt
    .venv\Scripts\pip.exe install -e .
    
    if not exist ".env" (
        copy .env.example .env >nul
    )
    if not exist "vault\reports" mkdir vault\reports
    if not exist "vault\conversations" mkdir vault\conversations
    echo [OK] Setup complete!
    echo.
)

REM 3. Run Agent
if "%~1"=="" (
    echo [INFO] Starting Web Dashboard...
    .venv\Scripts\python.exe run.py web --port 8080
) else (
    .venv\Scripts\python.exe run.py %*
)
