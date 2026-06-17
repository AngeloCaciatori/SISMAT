@echo off
title SISMAT - Reparar Banco de Dados
color 0E
cd /d "%~dp0"

:: Força Python a usar UTF-8 (resolve UnicodeEncodeError no console Windows)
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo.
echo ================================================
echo   SISMAT - Reparar / Inicializar Banco de Dados
echo ================================================
echo.
echo Este script roda init_db.py e todas as migracoes.
echo Use quando:
echo  - O wizard de instalacao falhou silenciosamente
echo  - Aparece "no such table: operador" no login
echo  - Banco precisa ser reparado/atualizado
echo.

if not exist ".venv\Scripts\python.exe" (
    color 0C
    echo [ERRO] Ambiente virtual nao encontrado em .venv\
    echo Execute primeiro o instalar.bat
    echo.
    pause
    exit /b 1
)

echo Pressione qualquer tecla para iniciar...
pause >nul

echo.
echo [1/5] Criando tabelas do banco (init_db.py)...
.venv\Scripts\python.exe scripts\init_db.py
if errorlevel 1 (
    color 0C
    echo [ERRO] Falha em init_db.py
    pause
    exit /b 1
)

echo.
echo [2/5] Migracao v2 (excluido_em)...
.venv\Scripts\python.exe scripts\migrar_v2.py

echo.
echo [3/5] Migracao v3 (assinatura digital - tokens)...
.venv\Scripts\python.exe scripts\migrar_v3.py

echo.
echo [4/5] Migracao v4 (backup_log + situacao militar)...
.venv\Scripts\python.exe scripts\migrar_v4.py

echo.
echo [5/5] Migracao v5 (medidas: camisa/calca)...
.venv\Scripts\python.exe scripts\migrar_v5.py

echo.
color 0A
echo ================================================
echo   BANCO REPARADO COM SUCESSO
echo ================================================
echo.
echo Login i