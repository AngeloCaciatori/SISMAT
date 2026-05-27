============================================================
  SISMAT — Python Embeddable (pasta python_embed)
============================================================

AÇÃO NECESSÁRIA antes de compilar o instalador:

1. Acesse o link abaixo e baixe o arquivo:
   https://www.python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip

2. Extraia o conteúdo do .zip DIRETAMENTE NESTA PASTA (python_embed\).
   Ao terminar, esta pasta deve conter python.exe, python312.dll, etc.

   Estrutura esperada:
     python_embed\
       python.exe
       python312.dll
       python312.zip
       pythonw.exe
       ...

3. Continue para a pasta wheels\ e siga o README de lá.

POR QUÊ embed?
  O Python embeddable é uma versão portátil e compacta (~15 MB)
  que funciona sem instalar Python no PC do usuário final.
  O instalador do SISMAT inclui essa cópia e a usa para criar
  o ambiente virtual da aplicação.

DÚVIDAS? Veja docs\README_INSTALACAO.md para o passo a passo completo.
