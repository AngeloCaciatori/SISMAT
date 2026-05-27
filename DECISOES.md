# SISMAT — Log de Decisões

| ID    | Decisão | Detalhe |
|-------|---------|---------|
| D-020 | Distribuição via Inno Setup 6 com Python 3.12 embed offline | Instalador único `.exe` substitui `instalar.bat` para usuários finais. Pasta `installer/` em `C:\sismat\installer\` contém: `app_source/`, `python_embed/` (usuário baixa), `wheels/` (usuário baixa), `docs/`, `brasao.ico`, `setup.iss`, `compilar.bat`. Após compilar: `Output\Setup_SISMAT_1.0.0.exe`. O `instalar.bat` e `iniciar.bat` originais continuam válidos para devs. |
