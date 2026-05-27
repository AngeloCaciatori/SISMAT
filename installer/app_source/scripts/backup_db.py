"""Cria uma cópia de backup do banco SQLite do SISMAT.

Uso:
    python scripts/backup_db.py
    python scripts/backup_db.py --pasta "C:\\Users\\Eu\\OneDrive\\backups-sismat"

Sem argumentos, salva em <projeto>/instance/backups/sismat-AAAAMMDD-HHMM.db.

Para automatizar mensalmente no Windows, use o Agendador de Tarefas:
    schtasks /Create /TN "SISMAT Backup Mensal" /SC MONTHLY /D 1 /ST 03:00 \
             /TR "python C:\\caminho\\sismat\\scripts\\backup_db.py"
ou execute o agendar_backup.bat na raiz do projeto.
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB = BASE_DIR / "instance" / "sismat.db"


def main():
    if not DB.exists():
        print(f"❌ Banco não encontrado: {DB}")
        print("   Inicialize o sistema primeiro com: python scripts/init_db.py")
        sys.exit(1)

    pasta_destino = None
    if "--pasta" in sys.argv:
        idx = sys.argv.index("--pasta")
        if idx + 1 < len(sys.argv):
            pasta_destino = Path(sys.argv[idx + 1])

    if pasta_destino is None:
        pasta_destino = BASE_DIR / "instance" / "backups"

    pasta_destino.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    nome = f"sismat-{timestamp}.db"
    destino = pasta_destino / nome

    # Copia o arquivo (cópia binária preserva o DB SQLite intacto)
    shutil.copy2(DB, destino)

    tamanho_kb = destino.stat().st_size / 1024
    print(f"✓ Backup criado: {destino}")
    print(f"  Tamanho: {tamanho_kb:.1f} KB")

    # Lista últimos 5 backups
    backups = sorted(pasta_destino.glob("sismat-*.db"), reverse=True)[:5]
    if len(backups) > 1:
        print("\nÚltimos backups nesta pasta:")
        for b in backups:
            kb = b.stat().st_size / 1024
            print(f"  {b.name} ({kb:.1f} KB)")


if __name__ == "__main__":
    main()
