@echo off
title SISMAT - Agendar Backup Mensal
color 0A
echo.
echo ================================================
echo   SISMAT - Agendar Backup Mensal Automatico
echo ================================================
echo.
echo Esta acao vai criar uma tarefa no Agendador do Windows
echo para fazer backup automatico do banco SISMAT todo dia 1
echo de cada mes, as 03:00 da manha.
echo.
echo Os backups serao salvos em:
echo    %~dp0instance\backups\
echo.
echo Para que o backup va para uma pasta sincronizada com nuvem
echo (OneDrive, Google Drive), edite este .bat e mude PASTA.
echo.

set PASTA=%~dp0instance\backups
set SCRIPT="%~dp0.venv\Scripts\python.exe" "%~dp0scripts\backup_db.py" --pasta "%PASTA%"

echo Pressione ENTER para continuar ou Ctrl+C para cancelar...
pause >nul

schtasks /Create /TN "SISMAT Backup Mensal" /SC MONTHLY /D 1 /ST 03:00 ^
    /TR "%SCRIPT%" /F

if errorlevel 1 (
    color 0C
    echo.
    echo [ERRO] Falha ao agendar tarefa. Tente executar como Administrador.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   AGENDAMENTO CRIADO COM SUCESSO
echo ================================================
echo.
echo Tarefa: SISMAT Backup Mensal
echo Quando: Dia 1 de cada mes, as 03:00
echo Pasta:  %PASTA%
echo.
echo Para ver/editar/remover, abra o "Agendador de Tarefas"
echo do Windows (taskschd.msc).
echo.
echo Para fazer um backup MANUAL agora, execute:
echo    python scripts\backup_db.py
echo.
pause
