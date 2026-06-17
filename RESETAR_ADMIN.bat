@echo off
title SISMAT - Resetar Senha do Admin
color 0E
cd /d "%~dp0"

:: Força Python a usar UTF-8 (resolve UnicodeEncodeError no console Windows)
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo.
echo ================================================
echo   SISMAT - Resetar Senha do Admin
echo ================================================
echo.
echo Este script reseta APENAS a senha do admin para
echo o padrao 'sismat123', preservando todos os outros
echo dados (militares, cautelas, materiais, etc.).
echo.
echo Use quando o admin esqueceu a senha e nenhum
echo outro admin pode reseta-la.
echo.

if not exist ".venv\Scripts\python.exe" (
    color 0C
    echo [ERRO] Ambiente virtual nao encontrado em .venv\
    echo Execute primeiro o instalar.bat ou REPARAR.bat
    pause
    exit /b 1
)

echo Pressione qualquer tecla para confirmar o reset...
pause >nul

.venv\Scripts\python.exe scripts\resetar_admin.py

echo.
pause
