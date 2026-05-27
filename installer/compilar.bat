@echo off
title Compilar Instalador SISMAT
cd /d "%~dp0"

echo.
echo ============================================================
echo   SISMAT - Compilador do Instalador
echo   Bia C AD/5 - Subtenencia / Reserva de Material
echo ============================================================
echo.

:: --- Localizar ISCC.exe ---
set ISCC_EXE=
where ISCC >nul 2>nul && set ISCC_EXE=ISCC

if not defined ISCC_EXE (
  if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC_EXE=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
  )
)
if not defined ISCC_EXE (
  if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC_EXE=C:\Program Files\Inno Setup 6\ISCC.exe"
  )
)
if not defined ISCC_EXE (
  echo [ERRO] Inno Setup 6 nao encontrado.
  echo Instale em: https://jrsoftware.org/isdl.php
  echo.
  goto :fim
)
echo Compilador: %ISCC_EXE%
echo.

:: --- Avisos (nao bloqueiam) ---
if not exist "python_embed\python.exe" (
  echo [AVISO] python_embed\python.exe nao encontrado.
  echo         Baixe e extraia em installer\python_embed\
  echo         https://www.python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip
  echo.
)

set WHEEL_COUNT=0
for %%f in (wheels\*.whl) do set /a WHEEL_COUNT+=1
if %WHEEL_COUNT% equ 0 (
  echo [AVISO] Nenhum .whl em installer\wheels\
  echo         Rode: pip download -r app_source\requirements.txt -d wheels\ --platform win_amd64 --python-version 3.12 --only-binary=:all:
  echo.
)

:: --- Compilar ---
echo Compilando setup.iss ... (aguarde, pode demorar alguns minutos)
echo Log salvo em: compilar.log
echo.

"%ISCC_EXE%" setup.iss > compilar.log 2>&1

if %ERRORLEVEL% equ 0 (
  echo ============================================================
  echo   SUCESSO!
  echo   Instalador gerado em: installer\Output\Setup_SISMAT_1.0.0.exe
  echo ============================================================
) else (
  echo [ERRO] Compilacao falhou. Detalhes no arquivo compilar.log:
  echo.
  type compilar.log
)

:fim
echo.
pause
