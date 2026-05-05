@echo off
chcp 65001 >nul
title DeepReviser - AI长篇小说改文助手

:: ============================================
::  DeepReviser 一键启动脚本
:: ============================================

set "PROJECT_DIR=H:\AI\personalCode\deep-reviser"
set "VENV_PYTHON=%PROJECT_DIR%\venv\Scripts\python.exe"

cd /d "%PROJECT_DIR%"

:: 检查 .env 是否存在
if not exist ".env" (
    echo [WARN] 未找到 .env 文件，请复制 .env.example 并填入 DEEPSEEK_API_KEY
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════╗
echo ║       DeepReviser —  AI长篇小说改文助手      ║
echo ╚══════════════════════════════════════════════╝
echo.
echo [INFO] 启动时间: %date% %time%
echo [INFO] 项目路径: %PROJECT_DIR%
echo.

:: 启动 FastAPI
echo [INFO] 启动 FastAPI 后端 (端口 8001) ...
start "DeepReviser-API" cmd /c ""%VENV_PYTHON%" -m uvicorn src.api.app:app --host 127.0.0.1 --port 8001 2>&1"
echo [INFO]   API 文档: http://127.0.0.1:8001/docs

:: 等待 API 启动
echo [INFO] 等待 API 启动中...
:wait_api
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:8001/health >nul 2>&1
if errorlevel 1 goto wait_api
echo [OK]   FastAPI 已就绪

:: 启动 Gradio UI
echo.
echo [INFO] 启动 Gradio Web UI (端口 7860) ...
start "DeepReviser-UI" cmd /c ""%VENV_PYTHON%" src/ui/app.py 2>&1"
echo [INFO]   Gradio UI: http://127.0.0.1:7860

echo.
echo ╔══════════════════════════════════════════════╗
echo ║  全部服务已启动!                            ║
echo ║                                            ║
echo ║  API:   http://127.0.0.1:8001/docs         ║
echo ║  UI:    http://127.0.0.1:7860              ║
echo ║                                            ║
echo ║  关闭此窗口即可停止所有服务                 ║
echo ╚══════════════════════════════════════════════╝
echo.
echo 按任意键打开 Gradio UI ...
pause >nul
start http://127.0.0.1:7860
