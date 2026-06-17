# SISMAT — Sistema de Controle de Material

Sistema de controle de material da Subtenência (Bia C AD/5). Funciona offline em
um único PC ou como servidor local na rede do quartel (sem dependência de
internet externa).

## O que está pronto nesta versão

- ✅ Estrutura completa do projeto Flask
- ✅ Modelos do banco SQLite (9 tabelas: efetivo, operadores, materiais, cautelas, etc.)
- ✅ Sistema de login com hash bcrypt e sessão protegida (CSRF)
- ✅ Dashboard com estatísticas reais consultadas do banco
- ✅ Solicitação de redefinição de senha (registrada para o admin atender)
- ✅ Inicialização automática (admin inicial criado pelo script)
- 🛠 CRUDs (Efetivo, Material, Cautelas, Documentação, Ração, Operadores) — em construção

## Pré-requisitos

- **Python 3.10 ou superior** instalado
- Pip funcionando

## Instalação (passo a passo)

### 1. Abra o Prompt de Comando na pasta do projeto

```cmd
cd C:\caminho\para\sismat
```

### 2. (Recomendado) Crie um ambiente virtual

```cmd
python -m venv .venv
.venv\Scripts\activate
```

### 3. Instale as dependências

```cmd
pip install -r requirements.txt
```

### 4. Inicialize o banco e crie o admin

```cmd
python scripts/init_db.py
```

Saída esperada:
```
▶ Criando tabelas...
✓ Tabelas criadas.
✓ Admin 'admin' criado (senha inicial: 'sismat123')
✓ Modelos de documento padrão cadastrados.
=== SISMAT pronto para uso ===
Login: admin
Senha: sismat123
```

### 5. Inicie o servidor

```cmd
python run.py
```

Você verá:
```
============================================================
  SISMAT — Sistema de Controle de Material
============================================================
  Servidor escutando em 0.0.0.0:5000

  Acesso:
    Neste PC:     http://localhost:5000
    Outros PCs:   http://192.168.x.x:5000
============================================================
```

### 6. Acesse no navegador

- **Neste PC**: <http://localhost:5000>
- **Outro PC da mesma rede**: copie o IP que aparecer (ex.: `http://192.168.1.10:5000`)

Faça login com:
- **Login**: `admin`
- **Senha**: `sismat123`

⚠ **Troque a senha após o primeiro login** (será obrigatório quando o módulo de operadores estiver implementado).

## Modos de execução

```cmd
python run.py                  # LAN (todos os PCs da rede acessam)
python run.py --localhost      # só local (apenas este PC)
python run.py --port 8080      # muda a porta
```

## Liberar firewall do Windows (se quiser acesso pela rede)

1. Abra "Firewall do Windows Defender com Segurança Avançada"
2. Regras de Entrada → Nova Regra → Porta → TCP → 5000
3. Permitir conexão → Aplicar a Domínio + Privada (não Pública)
4. Nome: "SISMAT - Porta 5000"

## Estrutura do projeto

```
sismat/
├── app/
│   ├── __init__.py        # Application factory
│   ├── extensions.py      # db, login_manager, csrf
│   ├── models.py          # Modelos do banco (9 tabelas)
│   ├── auth.py            # Decoradores (admin_required)
│   ├── routes/            # Blueprints (uma seção por arquivo)
│   ├── templates/         # HTML Jinja2
│   └── static/
│       ├── css/           # Estilo SISMAT (verde militar)
│       └── uploads/       # Fotos dos militares
├── scripts/
│   └── init_db.py         # Cria tabelas + admin
├── instance/
│   └── sismat.db          # Banco SQLite (criado automaticamente)
├── data/csv_legacy/       # Onde vão os CSVs do Access antigo
├── config.py              # Configurações gerais
├── run.py                 # Inicia o servidor
└── requirements.txt
```
## Backup

O banco inteiro fica em `instance/sismat.db`. Para fazer backup, basta copiar
esse arquivo. Para restaurar, basta sobrescrever.
