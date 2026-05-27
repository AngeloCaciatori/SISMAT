============================================================
  SISMAT — Pacotes Python offline (pasta wheels)
============================================================

AÇÃO NECESSÁRIA antes de compilar o instalador:

1. Abra um Prompt de Comando (cmd) NESTA PASTA (installer\wheels\).

2. Execute o comando abaixo (precisa de Python e pip instalados no PC
   onde você está COMPILANDO o instalador — não no PC destino):

   pip download -r ..\app_source\requirements.txt ^
     -d . ^
     --platform win_amd64 ^
     --python-version 3.12 ^
     --only-binary=:all:

3. Aguarde o download de todos os pacotes .whl.
   Ao terminar, esta pasta terá arquivos como:
     flask-3.x.x-py3-none-any.whl
     sqlalchemy-2.x.x-cp312-cp312-win_amd64.whl
     ...

4. Volte para a pasta installer\ e execute compilar.bat.

OBSERVAÇÃO:
  Esses arquivos são os pacotes Python necessários para rodar o SISMAT.
  O instalador os copiará para o PC destino e os instalará sem internet.

DÚVIDAS? Veja docs\README_INSTALACAO.md para o passo a passo completo.
