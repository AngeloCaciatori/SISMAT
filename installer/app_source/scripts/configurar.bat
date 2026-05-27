@echo off
:: ============================================================
::  SISMAT - Configuracao pos-instalacao
::  Cria o ambiente virtual e instala dependencias offline
::  ATENCAO: sem 'pause' - projetado para rodar pelo instalador
:: ============================================================
cd /d "%~dp0.."
set "APP=%~dp0.."
set "LOG=%APP%configurar.log"
set "VENV=%APP%.venv"
set "WHEELS=%APP%wheels"

echo [%DATE% %TIME%] Iniciando configuracao... > "%LOG%"
echo Diretorio: %APP% >> "%LOG%"
echo. >> "%LOG%"

:: ---- Encontrar Python para criar o venv ----
set PYTHON_EXE=

py -3.12 --version >nul 2>nul
if not errorlevel 1 set PYTHON_EXE=py -3.12

if not defined PYTHON_EXE (
  py -3 --version >nul 2>nul
  if not errorlevel 1 set PYTHON_EXE=py -3
)

if not defined PYTHON_EXE (
  python --version >nul 2>nul
  if not errorlevel 1 set PYTHON_EXE=python
)

if not defined PYTHON_EXE (
  echo [ERRO] Python nao encontrado no sistema. >> "%LOG%"
  echo Instale Python 3.12 de https://www.python.org/downloads/ >> "%LOG%"
  echo Marque "Add Python to PATH" durante a instalacao. >> "%LOG%"
  echo.
  echo ============================================================
  echo   ERRO: Python nao encontrado.
  echo   Instale Python 3.12 em: https://www.python.org/downloads/
  echo   Marque "Add Python to PATH" e execute este arquivo novamente.
  echo ============================================================
  echo.
  exit /b 1
)

echo Python encontrado: %PYTHON_EXE% >> "%LOG%"

:: ---- Criar ambiente virtual ----
echo [%DATE% %TIME%] Criando ambiente virtual... >> "%LOG%"
echo Criando ambiente virtual...

if exist "%VENV%\Scripts\python.exe" (
  echo   Ambiente virtual ja existe. >> "%LOG%"
) else (
  %PYTHON_EXE% -m venv "%VENV%" >> "%LOG%" 2>&1
  if not exist "%VENV%\Scripts\python.exe" (
    echo [ERRO] Falha ao criar venv. Veja: %LOG%
    exit /b 1
  )
  echo   Ambiente virtual criado. >> "%LOG%"
)

:: ---- Instalar dependencias ----
echo [%DATE% %TIME%] Instalando dependencias... >> "%LOG%"
echo Instalando dependencias...

set HAS_WHEELS=0
for %%f in ("%WHEELS%\*.whl") do set HAS_WHEELS=1

if "%HAS_WHEELS%"=="1" (
  echo   Usando wheels offline. >> "%LOG%"
  "%VENV%\Scripts\python.exe" -m pip install --no-index --find-links="%WHEELS%" -r "%APP%requirements.txt" >> "%LOG%" 2>&1
) else (
  echo   Wheels nao encontrados, instalando com internet. >> "%LOG%"
  "%VENV%\Scripts\python.exe" -m pip install -r "%APP%requirements.txt" >> "%LOG%" 2>&1
)

if errorlevel 1 (
  echo [ERRO] Falha ao instalar dependencias. Veja: %LOG%
  exit /b 1
)
echo   Dependencias instaladas. >> "%LOG%"

:: ---- Inicializar banco ----
echo [%DATE% %TIME%] Inicializando banco de dados... >> "%LOG%"
echo Inicializando banco de dados...
"%VENV%\Scripts\python.exe" "%APP%scripts\init_db.py" >> "%LOG%" 2>&1

:: ---- Migracoes ----
echo [%DATE% %TIME%] Aplicando migracoes... >> "%LOG%"
echo Aplicando migracoes...
"%VENV%\Scripts\python.exe" "%APP%scripts\migrar_v2.py" >> "%LOG%" 2>&1

:: ---- Fim ----
echo. >> "%LOG%"
echo [%DATE% %TIME%] Configuracao concluida com sucesso! >> "%LOG%"
echo.
echo ============================================================
echo   Configuracao concluida! Log em: %LOG%
echo ============================================================
exit /b 0
