"""Backup SISMAT — sqlite3.backup() atomico + ZIP + politica GFS.

Uso:
    python scripts/backup_db.py --tipo diario
    python scripts/backup_db.py --tipo semanal
    python scripts/backup_db.py --tipo mensal
    python scripts/backup_db.py --tipo anual

Politica GFS (Avo-Pai-Filho):
    diario  -- mantem os 7 mais recentes
    semanal -- mantem os 4 mais recentes
    mensal  -- mantem os 12 mais recentes
    anual   -- mantem todos (permanentes)

Cada backup e um ZIP contendo:
    sismat.db      -- copia atomica via sqlite3.backup()
    uploads/       -- arquivos estaticos (fotos, imagens)
    metadata.json  -- data, tipo, md5, tamanho

Alem de instance/backups/, o ZIP e copiado automaticamente para:
    %USERPROFILE%\\Documents\\SISMAT\\

Para agendar no Windows (rodar como admin, uma unica vez):
    schtasks /Create /TN "SISMAT Backup Diario"   /SC DAILY   /ST 15:00 /TR "\".venv\\Scripts\\python.exe\" \"scripts\\backup_db.py\" --tipo diario"   /F
    schtasks /Create /TN "SISMAT Backup Semanal"  /SC WEEKLY  /D MON /ST 15:30 /TR "\".venv\\Scripts\\python.exe\" \"scripts\\backup_db.py\" --tipo semanal"  /F
    schtasks /Create /TN "SISMAT Backup Mensal"   /SC MONTHLY /D 1   /ST 15:45 /TR "\".venv\\Scripts\\python.exe\" \"scripts\\backup_db.py\" --tipo mensal"   /F
    schtasks /Create /TN "SISMAT Backup Anual"    /SC MONTHLY /D 1 /MO 12 /ST 15:45 /TR "\".venv\\Scripts\\python.exe\" \"scripts\\backup_db.py\" --tipo anual"    /F
"""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "instance" / "sismat.db"
UPLOADS_DIR = BASE_DIR / "app" / "static" / "uploads"

# Quantos backups manter por tipo (None = permanente)
GFS_LIMITE = {
    "diario": 7,
    "semanal": 4,
    "mensal": 12,
    "anual": None,
}


def md5_arquivo(caminho: Path) -> str:
    h = hashlib.md5()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def backup_atomico(db_origem: Path, db_destino: Path) -> None:
    """Copia o banco via sqlite3.backup() — seguro mesmo com escrita ativa."""
    origem = sqlite3.connect(str(db_origem))
    destino = sqlite3.connect(str(db_destino))
    try:
        origem.backup(destino)
    finally:
        destino.close()
        origem.close()


def criar_zip(tipo: str, pasta_destino: Path) -> tuple[Path, dict]:
    """Cria o arquivo ZIP e retorna (caminho_zip, metadados)."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    nome_zip = f"sismat-{timestamp}-{tipo}.zip"
    caminho_zip = pasta_destino / nome_zip

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_tmp = tmp / "sismat.db"
        backup_atomico(DB_PATH, db_tmp)
        md5_db = md5_arquivo(db_tmp)

        meta = {
            "timestamp": timestamp,
            "tipo": tipo,
            "md5_sismat_db": md5_db,
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
        }
        (tmp / "metadata.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with zipfile.ZipFile(caminho_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(db_tmp, "sismat.db")
            zf.write(tmp / "metadata.json", "metadata.json")

            if UPLOADS_DIR.exists():
                for arq in UPLOADS_DIR.rglob("*"):
                    if arq.is_file():
                        arcname = "uploads/" + arq.relative_to(UPLOADS_DIR).as_posix()
                        zf.write(arq, arcname)

    tamanho_kb = caminho_zip.stat().st_size / 1024
    meta["tamanho_kb"] = round(tamanho_kb, 1)
    meta["arquivo"] = nome_zip
    return caminho_zip, meta


def aplicar_gfs(pasta: Path, tipo: str) -> list[Path]:
    """Remove backups antigos do mesmo tipo conforme politica GFS."""
    limite = GFS_LIMITE.get(tipo)
    if limite is None:
        return []  # anual: permanente

    padrao = f"sismat-*-{tipo}.zip"
    todos = sorted(pasta.glob(padrao), key=lambda p: p.stat().st_mtime, reverse=True)
    removidos = []
    for antigo in todos[limite:]:
        try:
            antigo.unlink()
            removidos.append(antigo)
            print(f"  GFS removido: {antigo.name}")
        except OSError as e:
            print(f"  [AVISO] Nao foi possivel remover {antigo.name}: {e}")
    return removidos


def copiar_para_documentos(zip_path: Path) -> tuple[bool, str]:
    """Copia o ZIP para %USERPROFILE%\\Documents\\SISMAT\\."""
    try:
        perfil = Path(os.environ.get("USERPROFILE", Path.home()))
        pasta_docs = perfil / "Documents" / "SISMAT"
        pasta_docs.mkdir(parents=True, exist_ok=True)
        destino = pasta_docs / zip_path.name
        shutil.copy2(zip_path, destino)
        return True, str(destino)
    except Exception as e:
        return False, str(e)


def registrar_no_banco(
    meta: dict, ok: bool, erro_msg: str = "",
    destino_docs: str = "", copia_ok: bool = None, copia_erro: str = "",
) -> None:
    """Insere log na tabela backup_log (se existir — criada pela migrar_v4.py)."""
    try:
        con = sqlite3.connect(str(DB_PATH))
        con.execute(
            """
            INSERT INTO backup_log
                (arquivo, tipo, tamanho_kb, md5_db, ok, erro_msg,
                 destino_cloud, cloud_ok, cloud_erro, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                meta.get("arquivo", ""),
                meta.get("tipo", ""),
                meta.get("tamanho_kb", 0),
                meta.get("md5_sismat_db", ""),
                1 if ok else 0,
                erro_msg,
                destino_docs or None,
                (1 if copia_ok else 0) if copia_ok is not None else None,
                copia_erro or None,
                meta.get("gerado_em", datetime.now().isoformat(timespec="seconds")),
            ),
        )
        con.commit()
        con.close()
    except sqlite3.OperationalError:
        pass  # tabela backup_log ainda nao existe (antes de migrar_v4)


def main():
    parser = argparse.ArgumentParser(description="Backup SISMAT com politica GFS")
    parser.add_argument(
        "--tipo",
        choices=["diario", "semanal", "mensal", "anual"],
        default="diario",
        help="Tipo de backup (afeta politica GFS de retencao)",
    )
    parser.add_argument(
        "--pasta",
        default=None,
        help="Pasta de destino primaria (padrao: instance/backups/)",
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"[ERRO] Banco nao encontrado: {DB_PATH}")
        print("   Inicialize com: python scripts/init_db.py")
        sys.exit(1)

    pasta = Path(args.pasta) if args.pasta else BASE_DIR / "instance" / "backups"
    pasta.mkdir(parents=True, exist_ok=True)

    print(f"[INICIO] Backup [{args.tipo}] -> {pasta}")
    meta = {}
    try:
        caminho_zip, meta = criar_zip(args.tipo, pasta)
        print(f"[OK] Backup criado: {caminho_zip.name}  ({meta['tamanho_kb']:.1f} KB)")

        removidos = aplicar_gfs(pasta, args.tipo)
        if removidos:
            print(f"  GFS: {len(removidos)} backup(s) antigo(s) removido(s).")

        # Copia para Documentos\SISMAT
        ok_docs, res_docs = copiar_para_documentos(caminho_zip)
        if ok_docs:
            print(f"[DOCS] Copiado para: {res_docs}")
        else:
            print(f"[DOCS] Falha na copia: {res_docs}")

        registrar_no_banco(
            meta, ok=True,
            destino_docs=res_docs if ok_docs else "",
            copia_ok=ok_docs,
            copia_erro="" if ok_docs else res_docs,
        )
    except Exception as exc:
        msg = str(exc)
        print(f"[ERRO] Falha no backup: {msg}")
        registrar_no_banco(
            meta or {"tipo": args.tipo, "gerado_em": datetime.now().isoformat(timespec="seconds")},
            ok=False, erro_msg=msg,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
