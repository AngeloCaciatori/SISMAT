============================================================
  SISMAT — Instalador do Python (pasta python_installer)
============================================================

ACAO NECESSARIA antes de compilar o instalador:

1. Acesse o link abaixo e baixe o arquivo:
   https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe

2. Coloque o arquivo DIRETAMENTE NESTA PASTA (python_installer\).
   O nome deve ser exatamente: python-3.12.7-amd64.exe

   Estrutura esperada:
     python_installer\
       python-3.12.7-amd64.exe   (~26 MB)
       README.txt                (este arquivo)

O instalador do SISMAT detectara automaticamente se o Python
ja esta instalado no PC destino:
  - Se SIM: pula esta etapa
  - Se NAO: instala Python 3.12 silenciosamente (sem janelas)

TAMANHO: o arquivo python-3.12.7-amd64.exe tem cerca de 26 MB.
O .exe final do SISMAT ficara com aproximadamente +26 MB.

Se preferir NAO incluir o Python no instalador, deixe esta
pasta vazia. Nesse caso, o PC destino precisara ter Python
instalado manualmente antes de rodar o Setup_SISMAT.exe.
