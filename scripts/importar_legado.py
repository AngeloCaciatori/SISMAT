"""Importa os dados do Access (CSVs) para o banco SQLite do SISMAT.

Espera os CSVs em data/csv_legacy/ (gerados pelo extrair_access.py):
    DADOS DO EFETIVO.csv  -> Militar
    ITENS.csv             -> Material
    MEDIDAS.csv           -> Medidas
    TBLUsers.csv          -> Operador (com bcrypt nas senhas em texto puro)
    CAUTELA.csv           -> Cautela + ItemCautelado
    RAÇÃO OPERACIONAL.csv -> RacaoOperacional

Tabelas IGNORADAS (decidido remover):
    PRDU, LISTA PRDU, SALDO SISCOFIS, SEÇÕES, Erros ao colar

Uso:
    python scripts/importar_legado.py

O script é IDEMPOTENTE: pode ser rodado várias vezes sem duplicar dados.
Identidade é por: CPF (militares), Código (materiais), login (operadores),
e (cpf+nomenclatura+data) para itens cautelados.
"""

import csv
import sys
import re
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

# Habilita import do pacote app/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models import (
    Militar, Material, Medidas, Operador, Cautela, ItemCautelado,
    RacaoOperacional, NIVEL_ADMIN, NIVEL_OPERADOR,
)

CSV_DIR = Path(__file__).resolve().parent.parent / "data" / "csv_legacy"


# ============================================================
#  Helpers
# ============================================================

def ler_csv(nome_arquivo: str):
    """Lê um CSV exportado pelo extrair_access.py (UTF-8 BOM, separador ';')."""
    caminho = CSV_DIR / nome_arquivo
    if not caminho.exists():
        print(f"  [!] Arquivo não encontrado: {caminho}")
        return []
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def s(v, default=None):
    """Normaliza string vazia para None."""
    if v is None:
        return default
    s = str(v).strip()
    return s if s else default


def i(v, default=None):
    """Converte para int. None se inválido/vazio."""
    if v is None or v == "":
        return default
    try:
        return int(float(str(v).replace(",", ".")))
    except (ValueError, TypeError):
        return default


def f(v, default=None):
    """Converte para float."""
    if v is None or v == "":
        return default
    try:
        return float(str(v).replace(",", "."))
    except (ValueError, TypeError):
        return default


def dec(v, default=None):
    """Converte para Decimal."""
    if v is None or v == "":
        return default
    try:
        return Decimal(str(v).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return default


def parse_data(v):
    """Converte string de data (várias formas) para datetime.date."""
    if not v or not str(v).strip():
        return None
    txt = str(v).strip()
    # Formatos vistos no Access exportado: "2025-06-02 00:00:00"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            continue
    return None


def separar_grad_nome(grad_completo: str):
    """Algumas linhas vêm com 'GRAD NOME' juntos (ex.: '2° SGT BURGOS').
    Retorna (graduacao, nome_extraido_ou_None).
    """
    if not grad_completo:
        return ("", None)
    s = grad_completo.strip()

    PATRONS = [
        r"^(GEN\s*EXE|GEN\s*DIV|GEN\s*BRIG|TEN\s*CEL|SUB\s*TEN|"
        r"\d°\s*SGT|\d°\s*TEN|"
        r"CAP|MAJ|CEL|CB|SD\s*EV|SD\s*EP|"
        r"\d°SGT|\d°TEN|"
        r"ASP\s*OF|1°SGT|2°SGT|3°SGT|1°TEN|2°TEN)"
    ]
    for pat in PATRONS:
        m = re.match(pat, s, re.IGNORECASE)
        if m:
            grad = m.group(1).strip()
            resto = s[m.end():].strip()
            return (grad.upper(), resto if resto else None)

    return (s, None)


# ============================================================
#  Importadores
# ============================================================

def importar_efetivo():
    print("\n=== EFETIVO (Militares) ===")
    rows = ler_csv("DADOS DO EFETIVO.csv")
    novos = atualizados = pulados = 0

    for row in rows:
        cpf = s(row.get("CPF"))
        if not cpf:
            pulados += 1
            continue

        grad_raw = s(row.get("GRAD")) or ""
        graduacao, nome_extraido = separar_grad_nome(grad_raw)

        m = Militar.query.filter_by(cpf=cpf).first()
        if not m:
            m = Militar(cpf=cpf, graduacao=graduacao or "—", nome_guerra=s(row.get("GUERRA")) or cpf[-4:])
            db.session.add(m)
            novos += 1
        else:
            atualizados += 1

        m.graduacao = graduacao or m.graduacao
        m.nome_guerra = s(row.get("GUERRA")) or m.nome_guerra
        m.nome_completo = s(row.get("NOME")) or nome_extraido or m.nome_completo
        m.antiguidade = f(row.get("Ant")) or m.antiguidade
        m.numero = s(row.get("NR")) or m.numero
        m.ri = s(row.get("RI")) or m.ri
        m.telefone1 = s(row.get("Telefone 1")) or m.telefone1
        m.telefone2 = s(row.get("Telefone 2")) or m.telefone2
        m.om = s(row.get("OM")) or "Bia C AD/5"
        m.excluido = (str(row.get("EXCLUIDO", "")).strip().lower() in ("true", "1", "sim", "verdadeiro"))

    db.session.commit()
    print(f"  Novos: {novos} | Atualizados: {atualizados} | Pulados (sem CPF): {pulados}")
    return novos, atualizados


def importar_materiais():
    print("\n=== MATERIAIS (ITENS) ===")
    rows = ler_csv("ITENS.csv")
    novos = atualizados = 0

    for row in rows:
        codigo = i(row.get("Código"))
        if codigo is None:
            continue
        nomenclatura = s(row.get("Nomenclatura")) or "(sem nome)"

        m = db.session.get(Material, codigo)
        if not m:
            m = Material(id=codigo, nomenclatura=nomenclatura,
                         tipo=(s(row.get("Tipo")) or "OUTROS").upper())
            db.session.add(m)
            novos += 1
        else:
            atualizados += 1

        m.nomenclatura = nomenclatura
        m.ficha_siscofis = s(row.get("Ficha"))
        m.dependencia = s(row.get("Dependência"))
        m.conta_contabil = s(row.get("Conta-contábil"))
        m.tipo = (s(row.get("Tipo")) or "OUTROS").upper()
        m.prateleira = s(row.get("Prateleira"))
        m.qnt_siscofis = i(row.get("QNT SISCOFIS")) or 0
        m.valor_unitario = dec(row.get("Valor Un"))
        m.obs = s(row.get("Obs"))

    db.session.commit()
    print(f"  Novos: {novos} | Atualizados: {atualizados}")
    return novos, atualizados


def importar_medidas():
    print("\n=== MEDIDAS ===")
    rows = ler_csv("MEDIDAS.csv")
    novos = atualizados = pulados_sem_militar = 0

    for row in rows:
        cpf = s(row.get("CPF"))
        if not cpf:
            continue
        militar = Militar.query.filter_by(cpf=cpf).first()
        if not militar:
            pulados_sem_militar += 1
            continue

        med = militar.medidas
        if not med:
            med = Medidas(militar_id=militar.id)
            db.session.add(med)
            novos += 1
        else:
            atualizados += 1

        med.ombro = s(row.get("OMBRO"))
        med.cintura = s(row.get("CINTURA"))
        med.quadril = s(row.get("QUADRIL"))
        med.cabeca = s(row.get("CABEÇA"))
        med.pe = s(row.get("PÉ"))
        med.braco = s(row.get("BRAÇO"))

    db.session.commit()
    print(f"  Novos: {novos} | Atualizados: {atualizados} | Sem militar correspondente: {pulados_sem_militar}")
    return novos, atualizados


def importar_operadores():
    """Importa logins do TBLUsers, hasheando senhas com bcrypt."""
    print("\n=== OPERADORES (TBLUsers) ===")
    rows = ler_csv("TBLUsers.csv")
    novos = atualizados = 0

    for row in rows:
        login = s(row.get("User"))
        senha_clara = s(row.get("Senha"))
        if not login or not senha_clara:
            continue

        login = login.lower()
        nivel = i(row.get("NivelSeguranca")) or NIVEL_OPERADOR
        secao = s(row.get("SEÇÃO")) or "Reserva de Material"

        op = Operador.query.filter_by(login=login).first()
        if not op:
            op = Operador(
                login=login,
                nivel_seguranca=nivel,
                secao=secao,
                ativo=True,
                # senha do Access era texto puro -> consideramos temporária
                senha_temporaria=True,
            )
            op.definir_senha(senha_clara)
            db.session.add(op)
            novos += 1
        else:
            atualizados += 1

    db.session.commit()
    print(f"  Novos: {novos} | Atualizados: {atualizados}")
    print(f"  ⚠  Senhas migradas marcadas como TEMPORÁRIAS — operadores")
    print(f"     serão obrigados a trocar no 1º login.")
    return novos, atualizados


def importar_cautelas():
    """Importa CAUTELA.csv. Cada linha vira 1 ItemCautelado.

    Como o Access antigo não tinha 'numero da cautela', agrupamos por
    (CPF, data_da_cautela) — uma cautela legada por dia/militar.
    Se a data está vazia, agrupa todas como 'L-NoData/<CPF>'.
    """
    print("\n=== CAUTELAS ===")
    rows = ler_csv("CAUTELA.csv")
    cautelas_criadas = itens_criados = pulados = 0
    cautelas_cache = {}  # chave -> Cautela

    # Carregamos um operador fictício "legado" se admin existir
    operador = Operador.query.filter_by(login="admin").first()
    if not operador:
        print("  [!] Admin não encontrado — rode init_db primeiro.")
        return 0, 0
    operador_id_padrao = operador.id

    for row in rows:
        cpf = s(row.get("CPF"))
        nomenclatura_id = i(row.get("Nomenclatura"))
        qnt = i(row.get("Qnt")) or 1
        data = parse_data(row.get("Data da cautela"))
        obs = s(row.get("Obs"))

        if not cpf or not nomenclatura_id:
            pulados += 1
            continue

        militar = Militar.query.filter_by(cpf=cpf).first()
        material = db.session.get(Material, nomenclatura_id)
        if not militar or not material:
            pulados += 1
            continue

        chave = (cpf, data)
        cautela = cautelas_cache.get(chave)

        if not cautela:
            sufixo = data.strftime("%Y%m%d") if data else "NODATA"
            numero = f"L-{sufixo}-{cpf[-4:]}"

            cautela = Cautela.query.filter_by(numero=numero).first()
            if not cautela:
                cautela = Cautela(
                    numero=numero,
                    militar_id=militar.id,
                    operador_id=operador_id_padrao,
                    om_tipo="interna",
                    data_cautela=data or date(2020, 1, 1),
                    devolvida=False,
                    finalidade="(Importado do Access)",
                )
                db.session.add(cautela)
                db.session.flush()  # garante id
                cautelas_criadas += 1
            cautelas_cache[chave] = cautela

        # Verifica se este item já existe na cautela
        existente = ItemCautelado.query.filter_by(
            cautela_id=cautela.id, material_id=material.id
        ).first()
        if not existente:
            item = ItemCautelado(
                cautela_id=cautela.id,
                material_id=material.id,
                quantidade=qnt,
                obs=obs,
            )
            db.session.add(item)
            itens_criados += 1

    db.session.commit()
    print(f"  Cautelas criadas: {cautelas_criadas} | Itens cautelados: {itens_criados} | Pulados: {pulados}")
    return cautelas_criadas, itens_criados


def importar_racao():
    print("\n=== RAÇÃO OPERACIONAL ===")
    rows = ler_csv("RAÇÃO OPERACIONAL.csv")
    novos = 0

    for row in rows:
        codigo = i(row.get("Código"))
        if codigo is None:
            continue
        if db.session.get(RacaoOperacional, codigo):
            continue

        r = RacaoOperacional(
            id=codigo,
            tipo=s(row.get("TIPO")) or "—",
            quantidade=i(row.get("QNT")) or 0,
            validade=parse_data(row.get("Validade")),
            obs=s(row.get("OBS")),
        )
        db.session.add(r)
        novos += 1

    db.session.commit()
    print(f"  Novos: {novos}")
    return novos, 0


# ============================================================
#  Main
# ============================================================

def main():
    if not CSV_DIR.exists():
        print(f"❌ Pasta não existe: {CSV_DIR}")
        print("   Coloque os CSVs do Access em data/csv_legacy/ e tente de novo.")
        sys.exit(1)

    csvs = list(CSV_DIR.glob("*.csv"))
    if not csvs:
        print(f"❌ Nenhum CSV encontrado em {CSV_DIR}")
        print("   Use o extrair_access.py para gerar os CSVs primeiro.")
        sys.exit(1)

    print("=" * 60)
    print("  SISMAT — Importação de dados do Access")
    print("=" * 60)
    print(f"Pasta de origem: {CSV_DIR}")
    print(f"CSVs encontrados: {[c.name for c in csvs]}")

    app = create_app()
    with app.app_context():
        # Ordem importa: Militar -> Medidas (por CPF), Material -> Cautelas, etc.
        importar_efetivo()
        importar_materiais()
        importar_medidas()
        importar_operadores()
        importar_racao()
        importar_cautelas()  # depende de Militar + Material + Operador

    print("\n" + "=" * 60)
    print("  Importação concluída!")
    print("=" * 60)


if __name__ == "__main__":
    main()
