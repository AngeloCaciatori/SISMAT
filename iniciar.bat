@echo off
title SISMAT - Servidor
color 0A

REM Garante que estamos na pasta do .bat (mesmo se for chamado de outro lugar)
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    color 0C
    echo [ERRO] O ambiente virtual ^(.venv^) nao foi encontrado nesta pasta:
    echo    %~dp0
    echo.
    echo Execute primeiro o arquivo: instalar.bat
    echo.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    color 0C
    echo [ERRO] Falha ao ativar o ambiente virtual.
    pause
    exit /b 1
)

REM Abre o navegador depois de 4s (tempo do Flask subir)
start "" /min cmd /c "timeout /t 4 /nobreak >nul & start http://localhost:5000"

python run.py
pause
