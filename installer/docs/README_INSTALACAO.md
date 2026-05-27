# SISMAT — Guia de Compilação do Instalador

> **Para quem é este guia:** quem vai GERAR o arquivo `.exe` distribuível.  
> Se você recebeu o `Setup_SISMAT_1.0.0.exe` pronto, vá direto para `MANUAL_RAPIDO.md`.

---

## Pré-requisitos

- Windows 10/11 (x64)
- Python 3.x instalado (para baixar os pacotes `.whl`)
- Conexão com internet **apenas nesta etapa** (para baixar o embed e os wheels)

---

## Passos para gerar o instalador

### Passo 0 — (Recomendado) Incluir o Python no instalador

Para que o SISMAT instale o Python automaticamente nos PCs destino:

1. Baixe o instalador do Python 3.12:  
   👉 **https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe** (~26 MB)

2. Coloque o arquivo na pasta `installer\python_installer\`  
   O nome deve ser exatamente `python-3.12.7-amd64.exe`

Se deixar a pasta vazia, o PC destino precisará ter Python já instalado manualmente.

---

### Passo 1 — Instalar o Inno Setup 6

Baixe e instale o Inno Setup 6:  
👉 **https://jrsoftware.org/isdl.php**

Escolha "Inno Setup 6.x.x" (versão estável). A instalação é padrão (Next → Next → Finish).

---

### Passo 2 — Baixar o Python 3.12 Embeddable

1. Baixe o arquivo:  
   👉 **https://www.python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip**

2. Extraia o conteúdo do `.zip` diretamente na pasta:  
   `installer\python_embed\`

   Após extrair, deve existir o arquivo `installer\python_embed\python.exe`.

---

### Passo 3 — Baixar os pacotes Python offline

1. Abra o **Prompt de Comando** (cmd) como Administrador.

2. Navegue até a pasta `installer\wheels\`:
   ```
   cd C:\sismat\installer\wheels
   ```

3. Execute:
   ```
   pip download -r ..\app_source\requirements.txt -d . --platform win_amd64 --python-version 3.12 --only-binary=:all:
   ```

4. Aguarde o download terminar. A pasta ficará com vários arquivos `.whl`.

---

### Passo 4 — Compilar o instalador

Na pasta `installer\`, dê **duplo clique** em:  
📄 **`compilar.bat`**

O script verificará os pré-requisitos e chamará o Inno Setup automaticamente.  
A compilação leva entre 1 e 5 minutos dependendo do tamanho dos arquivos.

---

### Passo 5 — Distribuir

O instalador gerado estará em:  
📦 `installer\Output\Setup_SISMAT_1.0.0.exe`

Copie esse arquivo para um pen drive ou pasta de rede e execute no PC destino.

---

## Estrutura da pasta installer/

```
installer/
  app_source/       Código-fonte do SISMAT (gerado automaticamente)
  python_embed/     Python 3.12 portátil — VOCÊ BAIXA (Passo 2)
  wheels/           Pacotes Python offline — VOCÊ BAIXA (Passo 3)
  docs/             Esta documentação
  brasao.ico        Ícone do instalador
  setup.iss         Script do Inno Setup (não editar sem necessidade)
  compilar.bat      Atalho para compilar
  Output/           Aparece após compilar — contém o .exe final
```

---

## Solução de problemas

| Problema | Solução |
|---|---|
| `ISCC não encontrado` | Instale o Inno Setup 6 (Passo 1) |
| `python_embed\python.exe não encontrado` | Extraia o zip do Python embed (Passo 2) |
| `Nenhum .whl em wheels\` | Execute o pip download (Passo 3) |
| Erro de compilação no Inno Setup | Verifique se `brasao.ico` existe em `installer\` |
| Erro na instalação no PC destino | No PC destino, execute como Administrador |

---

## Atualizar a versão

Para gerar uma nova versão do instalador:

1. Atualize os arquivos em `app_source\` com o novo código
2. Edite `setup.iss` e altere `#define MyAppVersion` e `MyOutputBase`
3. Execute `compilar.bat` novamente
