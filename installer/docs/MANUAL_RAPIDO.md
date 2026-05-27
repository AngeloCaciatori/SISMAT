# SISMAT — Manual Rápido do Usuário

> **Sistema de Controle de Material — Bia C AD/5 — Subtenência**

---

## Primeiro acesso após instalação

### 1. Iniciar o servidor

Dê duplo clique no atalho **"Iniciar SISMAT"** na Área de Trabalho  
*(ou execute `C:\SISMAT\iniciar.bat`)*

Uma janela preta (CMD) abrirá — **não feche essa janela** enquanto usar o sistema.

### 2. Abrir no navegador

No mesmo PC onde o servidor está rodando, abra o navegador e acesse:  
👉 **http://localhost:5000**

De outro PC na mesma rede, use o IP do servidor:  
👉 **http://192.168.x.x:5000** *(substitua pelo IP real)*

---

## Login inicial

| Campo | Valor padrão |
|---|---|
| Usuário | `admin` |
| Senha | `sismat123` |

> ⚠️ **Na primeira entrada, o sistema obrigará a troca de senha.**  
> Escolha uma senha segura e anote em local seguro.

---

## Troca de senha

1. No canto superior direito, clique no ícone 🔑
2. Informe a senha atual e a nova senha (2×)
3. Clique em **Salvar**

Operadores com senha temporária (gerada pelo admin) são redirecionados automaticamente para este menu.

---

## Acesso pela rede local (outro PC)

1. No PC servidor, descubra o IP:  
   Abra o CMD e digite `ipconfig` → anote o **Endereço IPv4** (ex.: `192.168.1.50`)

2. No PC cliente (mesma rede), abra o navegador:  
   `http://192.168.1.50:5000`

3. Se não conectar, verifique se a regra de firewall foi criada durante a instalação  
   *(tarefa "Liberar porta 5000" — se não foi marcada, execute como admin):*
   ```
   netsh advfirewall firewall add rule name="SISMAT 5000" dir=in action=allow protocol=TCP localport=5000
   ```

---

## Backups

### Onde ficam
Os backups automáticos e manuais ficam em:  
`C:\SISMAT\instance\backups\`

O banco de dados principal fica em:  
`C:\SISMAT\instance\sismat.db`

### Fazer backup manual
Na barra lateral, vá em **Administração → Operadores → Backup**.  
Clique em **Gerar Backup Agora**.

### Restaurar backup
1. Pare o servidor (feche a janela do CMD)
2. Copie o arquivo de backup desejado para `C:\SISMAT\instance\sismat.db`  
   *(substituindo o arquivo atual — faça uma cópia de segurança antes!)*
3. Reinicie o servidor

---

## Recadastrar operadores

Apenas o administrador pode gerenciar operadores.

1. Vá em **Administração → Operadores**
2. Clique em **+ Novo Operador** para criar
3. Para resetar a senha de um operador: clique em **Resetar Senha**  
   Uma senha temporária será gerada — anote e passe presencialmente ao operador

---

## Operações principais

| Aba | O que faz |
|---|---|
| **Efetivo** | Cadastro dos militares, fotos, medidas para fardamento |
| **Material** | Catálogo do almoxarifado, prateleiras, fichas SISCOFIS |
| **Cautelas** | Registrar empréstimos, devoluções, imprimir FIDU |
| **Documentação** | Editor de documentos, modelos, impressão |
| **Administração** | Operadores, backup (apenas admin) |

---

## Resolver problemas comuns

| Problema | Solução |
|---|---|
| Página não abre | Verifique se a janela do servidor (CMD) está aberta |
| "Erro interno" ao entrar | Reinicie o servidor; se persistir, contate o responsável |
| Esqueci a senha de admin | Chame o Subten ou responsável pelo sistema |
| PC cliente não acessa | Verifique firewall e se estão na mesma rede |
| Banco de dados corrompido | Restaure o último backup de `instance\backups\` |

---

## Encerrar o sistema

Feche a janela preta do servidor (CMD) ou pressione `Ctrl+C` nela.

---

*SISMAT v1.0.0 — Bia C AD/5 — Subtenência / Reserva de Material — Curitiba/PR*
