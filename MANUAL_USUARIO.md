# SISMAT — Manual do Usuário

**Sistema de Controle de Material** · Bia C AD/5 · Subtenência / Reserva de Material · Curitiba/PR

---

## 1. Iniciar o sistema

### No PC servidor (onde o SISMAT foi instalado)

1. Duplo clique no atalho **"Iniciar SISMAT"** na Área de Trabalho
   *(ou execute `C:\SISMAT\iniciar.bat`)*
2. Uma janela preta (CMD) abrirá — **não feche essa janela** enquanto estiver usando o sistema
3. O navegador abre automaticamente em `http://localhost:5000`

### De outro PC na mesma rede (Subtenência)

1. No PC servidor, descubra o IP: abra o CMD e digite `ipconfig` → anote o **Endereço IPv4** (ex.: `192.168.1.50`)
2. No PC cliente (mesma rede), abra o navegador em: `http://192.168.1.50:5000`
3. Se não conectar, peça ao administrador para verificar o firewall da porta 5000

### Do celular (rede do quartel)

Mesmo endereço do PC remoto (ex.: `http://192.168.1.50:5000`). O sistema detecta mobile automaticamente e mostra layout otimizado para celular.

---

## 2. Primeiro login

| Campo | Valor padrão |
|---|---|
| Usuário | `admin` |
| Senha | `sismat123` |

**Na primeira entrada, o sistema obriga você a trocar a senha.** Escolha uma segura e anote em local seguro.

---

## 3. Visão geral das abas

| Aba | Para que serve |
|---|---|
| **Página Inicial** | Painel com contadores: militares, materiais, cautelas ativas, atrasadas |
| **Efetivo** | Cadastro dos militares (foto, dados, medidas de fardamento) |
| **Material** | Catálogo do almoxarifado (prateleira, ficha SISCOFIS, quantidades) |
| **Cautelas** | Empréstimos de material: criar, devolver, imprimir FIDU |
| **Documentação** | Modelos de documento, impressão em lote, FIDU |
| **Operadores** | (Admin) Gerenciar quem acessa o sistema |
| **Backup** | (Admin) Cópias de segurança do banco |

---

## 4. Cadastrar um militar

1. Vá em **Efetivo → + Novo Militar**
2. Preencha graduação, nome de guerra, nome completo, CPF, OM
3. (Opcional) Tire foto pelo PC servidor (webcam) ou envie arquivo
4. (Opcional) Preencha medidas: camisa, calça, cabeça, pé
5. **Salvar**

> Para tirar foto pela webcam, é necessário acessar o sistema **diretamente no PC servidor** (`http://localhost:5000`). De outros PCs/celulares, use envio de arquivo.

---

## 5. Cadastrar um material

1. Vá em **Material → + Novo Item**
2. Preencha:
   - **Nomenclatura** (ex.: "FARDA COMPLETA M-2")
   - **Categoria** (Fardamento / Equipamento / Material / Outros)
   - **Reserva** (Reserva 1 ou Reserva 2)
   - **Prateleira** (número físico no almoxarifado, ex.: `87`)
   - **Ficha SISCOFIS** (texto livre — pode ter múltiplos lotes)
   - **Quantidade esperada**
   - (Opcional) **Valor unitário**
3. **Salvar**

### Imprimir Ficha de Prateleira

Cada material vira uma etiqueta cortável com nº da prateleira, SISCOFIS, tipo e contagem em branco.

1. Em **Material**, marque o checkbox dos itens desejados
2. Clique em **🖨 Imprimir Fichas de Prateleira**
3. Imprima e cole nas prateleiras físicas

### Lista de Conferência (CONTROLE DE MATERIAL)

Folha para o operador percorrer o almoxarifado anotando quantidades reais.

1. Em **Material**, marque os itens (ou clique "Marcar todos")
2. Clique em **📋 Lista de Conferência**
3. Imprima a folha — vá com ela ao almoxarifado

---

## 6. Fazer uma cautela

1. Vá em **Cautelas → + Nova Cautela**
2. Selecione o tipo de OM:
   - **Interna**: recebedor é militar do Efetivo (Bia C AD/5) — selecione na lista
   - **Externa**: militar de outra OM — preencha grad/nome/CPF/OM manualmente
3. Preencha **Finalidade** (ex.: "Operação 02/MAI", "Instrução de campanha")
4. Adicione os itens com **+ Adicionar item** — escolha material e quantidade
5. (Opcional) Defina **Devolução prevista**
6. Clique em **Confirmar Cautela**

### Assinatura digital via QR Code (opcional)

Após criar a cautela, o sistema mostra um QR Code. O recebedor:

1. Escaneia com o celular dele
2. Abre a página de assinatura — desenha a assinatura com o dedo
3. Confirma

O PC operador detecta automaticamente em ~2 segundos.

---

## 7. Devolver uma cautela

1. Vá em **Cautelas** → lista
2. Encontre a cautela (use a busca se necessário)
3. Clique em **↺ Devolver** ao lado dela
4. Confirme

A cautela some da lista de "Ativas" e vai para o histórico.

---

## 8. Imprimir FIDU (Ficha Individual de Distribuição de Uniformes)

### De uma cautela específica

1. Em **Cautelas**, abra a cautela
2. Clique em **📥 Imprimir Ficha (FIDU)**
3. Nova aba abre com o formato A4 oficial — `Ctrl+P` para imprimir

### De todas as cautelas ativas de um militar

1. Em **Efetivo**, abra o perfil do militar
2. Clique em **📥 Imprimir Cautelas (FIDU)**
3. Documento consolida tudo agrupado por categoria (Equipamento/Fardamento/Material/Outros)

### Em lote (impressão de várias FIDUs)

1. Vá em **Documentação → Impressão em Lote**
2. Filtre por período, militar ou tipo
3. Marque as cautelas desejadas
4. Clique em **🖨 Gerar PDF Único**

---

## 9. Trocar senha

1. Canto superior direito, clique no ícone 🔑 (Trocar Senha)
2. Informe senha atual + nova senha (2×)
3. **Salvar**

Operadores com senha temporária (gerada pelo admin) são redirecionados automaticamente.

---

## 10. Esqueci minha senha — o que fazer

**Não há recuperação por e-mail** (sistema offline). Procure o **administrador** presencialmente:

- Admin abre **Operadores**, encontra você na lista, clica **Resetar Senha**
- Sistema gera uma senha temporária aleatória
- Admin anota e te entrega presencialmente
- No próximo login, você será obrigado a trocar para uma senha pessoal

---

## 11. Tarefas do Administrador

### Cadastrar novo operador

1. **Operadores → + Novo Operador**
2. Informe login, nome completo, nível (Admin / Operador)
3. Defina senha temporária — anote e entregue presencialmente

### Backup manual

1. **Backup → Fazer backup agora**
2. Sistema gera um ZIP com banco + fotos + uploads
3. Cópia local automática + (se configurado) cloud Nextcloud

### Backups automáticos

O sistema agenda automaticamente na instalação:
- **Diário** às 15h
- **Semanal** segunda-feira às 15h30
- **Mensal** dia 1 às 15h45
- **Anual** dia 1 de janeiro às 15h45

Mantém: 7 últimos diários, 4 semanais, 12 mensais, 1 anual por ano (permanente).

### Restaurar backup

1. Feche o servidor (X na janela preta do CMD)
2. Vá em `C:\SISMAT\instance\backups\`
3. Descompacte o ZIP desejado em local seguro
4. Copie o `sismat.db` para `C:\SISMAT\instance\sismat.db` (sobrescreve)
5. Copie a pasta `uploads/` para `C:\SISMAT\app\static\uploads/` (sobrescreve)
6. Reinicie o servidor

---

## 12. Problemas comuns

| Problema | Solução |
|---|---|
| Página não abre | Verifique se a janela preta do servidor (CMD) está aberta |
| "Erro interno do servidor" | Reinicie o servidor (feche CMD e abra de novo) |
| "Login ou senha inválidos" | Confira maiúsculas/minúsculas. Se persistir, peça reset ao admin |
| PC remoto não acessa | Confirme que está na mesma rede do servidor e que o firewall liberou a porta 5000 |
| Câmera não abre (foto/QR) | Acesse via `http://localhost:5000` direto no PC servidor (webcam só funciona em conexão local segura) |
| Banco corrompido | Restaure o último backup de `C:\SISMAT\instance\backups\` |
| Esqueci a senha do admin | Execute `C:\SISMAT\RESETAR_ADMIN.bat` — volta para `admin` / `sismat123` |
| Sistema travou ou banco em estado estranho | Execute `C:\SISMAT\REPARAR.bat` — refaz tabelas e migrações |

---

## 13. Encerrar o sistema

Feche a janela preta do servidor (X no canto superior direito da CMD) ou pressione `Ctrl+C` nela.

O navegador pode ficar aberto — só fica sem conexão. Para reabrir o sistema, repita o passo 1.

---

## 14. Suporte

Em caso de dúvida ou problema não listado aqui, procure o responsável pela Subtenência ou o administrador do sistema.

---

*SISMAT v1.0.0 — Bia C AD/5 — Subtenência / Reserva de Material*
