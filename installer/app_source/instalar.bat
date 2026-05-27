@echo off
title SISMAT - Instalacao
color 0A

REM Garante que estamos na pasta do .bat
cd /d "%~dp0"

echo.
echo ================================================
echo   SISMAT - Instalacao Automatica
echo ================================================
echo.

REM --- Detecta se a pasta esta dentro do sandbox do Claude / WindowsApps ---
echo %~dp0 | findstr /i "AppData\Local\Packages WindowsApps" >nul
if not errorlevel 1 (
    color 0E
    echo [AVISO] A pasta SISMAT esta dentro de uma area protegida do Windows:
    echo    %~dp0
    echo.
    echo Isso geralmente IMPEDE a criacao do ambiente virtual.
    echo.
    echo SOLUCAO: mova a pasta "sismat" para um lugar normal, por exemplo:
    echo    C:\SISMAT\
    echo    C:\Users\FONTES\Documents\SISMAT\
    echo    C:\Users\FONTES\Desktop\SISMAT\
    echo.
    echo Depois execute o instalar.bat de la.
    echo.
    echo Se mesmo assim quiser tentar aqui, pressione ENTER ^(pode falhar^).
    echo Para cancelar, feche esta janela.
    pause >nul
)

REM --- 1. Detecta Python (ignora o stub falso do Windows Store) ---
set PYTHON_EXE=

REM Tenta py launcher (mais confiavel no Windows)
py -3.12 --version >nul 2>nul
if not errorlevel 1 set PYTHON_EXE=py -3.12

if not defined PYTHON_EXE (
    py -3 --version >nul 2>nul
    if not errorlevel 1 set PYTHON_EXE=py -3
)

REM Testa se 'python' e real (o stub da Store falha em import sys)
if not defined PYTHON_EXE (
    python -c "import sys" >nul 2>nul
    if not errorlevel 1 set PYTHON_EXE=python
)

if not defined PYTHON_EXE (
    color 0C
    echo [ERRO] Python nao foi encontrado ^(ou e o stub da Microsoft Store^).
    echo.
    echo SOLUCAO:
    echo  1. Acesse https://www.python.org/downloads/
    echo  2. Baixe o Python 3.12 e instale
    echo  3. NA TELA DE INSTALACAO marque:
    echo       [x] Add Python to PATH
    echo       [x] Install Python Launcher
    echo  4. Apos instalar, execute este arquivo novamente
    echo.
    echo Se o problema persistir, desative o atalho da Store em:
    echo  Configuracoes ^> Aplicativos ^> Aliases de execucao
    echo  ^> desative as entradas "python.exe" e "python3.exe"
    echo.
    pause
    exit /b 1
)
echo [OK] Python detectado: %PYTHON_EXE%

REM --- 2. Cria ambiente virtual ---
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Criando ambiente virtual ^(.venv^)...
    %PYTHON_EXE% -m venv .venv
    if errorlevel 1 (
        color 0C
        echo.
        echo [ERRO] Nao foi possivel criar o ambiente virtual.
        echo.
        echo Causa provavel: a pasta esta em local protegido do Windows.
        echo SOLUCAO: mova a pasta sismat para C:\SISMAT\ ou Documentos
        echo e execute o instalar.bat de la.
        echo.
        pause
        exit /b 1
    )
) else (
    echo [OK] Ambiente virtual ja existe.
)

REM --- 3. Ativa ---
call ".venv\Scripts\activate.bat"

REM --- 4. Instala dependencias (offline se wheels/ existir, senao internet) ---
set HAS_WHEELS=0
for %%f in (wheels\*.whl) do set HAS_WHEELS=1

if "%HAS_WHEELS%"=="1" (
    echo [INFO] Instalando dependencias OFFLINE a partir de wheels\...
    .venv\Scripts\python.exe -m pip install --no-index --find-links=wheels -r requirements.txt --quiet
) else (
    echo [INFO] Pasta wheels\ vazia. Instalando via internet ^(pode demorar^)...
    echo [INFO] Se estiver em rede com proxy, isso pode falhar.
    .venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
)
if errorlevel 1 (
    color 0C
    echo [ERRO] Falha ao instalar dependencias.
    echo.
    echo Se estiver em rede com proxy ou sem internet, use instalacao offline:
    echo  1. Em um PC com internet, execute na pasta sismat\wheels\:
    echo     pip download -r ..\requirements.txt -d . --platform win_amd64 --python-version 3.12 --only-binary=:all:
    echo  2. Copie a pasta wheels\ para este PC
    echo  3. Execute instalar.bat novamente
    echo.
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas.

