@echo off
title DeepReviser - AI Novel Revision Assistant

:: ============================================
::  DeepReviser One-Click Launcher
:: ============================================

set "PROJECT_DIR=H:\AI\personalCode\deep-reviser"
set "VENV_PYTHON=%PROJECT_DIR%\venv\Scripts\python.exe"

cd /d "%PROJECT_DIR%"

:: Check .env
if not exist ".env" (
    echo [WARN] .env file not found
    echo        Copy .env.example to .env and fill in DEEPSEEK_API_KEY
    pause
    exit /b 1
)

echo.
echo ============================================
echo   DeepReviser - AI Novel Revision Assistant
echo ============================================
echo.
echo Started: %date% %time%
echo.

:: Start FastAPI
echo Starting FastAPI backend (port 8001) ...
start "DeepReviser-API" cmd /c ""%VENV_PYTHON%" -m uvicorn src.api.app:app --host 127.0.0.1 --port 8001"
echo   API docs: http://127.0.0.1:8001/docs

:: Wait for API
echo Waiting for API to be ready...
:wait_api
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:8001/health >nul 2>&1
if errorlevel 1 goto wait_api
echo   FastAPI ready.

:: Start Gradio UI
echo.
echo Starting Gradio Web UI (port 7860) ...
start "DeepReviser-UI" cmd /c ""%VENV_PYTHON%" -m src.ui.app"
echo   Gradio UI: http://127.0.0.1:7860

echo.
echo ============================================
echo   All services started.
echo.
echo   API:  http://127.0.0.1:8001/docs
echo   UI:   http://127.0.0.1:7860
echo.
echo   Close the API and UI windows to stop.
echo ============================================
echo.
pause
start http://127.0.0.1:7860
