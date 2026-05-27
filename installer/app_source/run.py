"""Inicializador do servidor SISMAT.

Modos de uso:
    python run.py                       # roda escutando em todas as interfaces (LAN)
    python run.py --localhost           # roda só localmente (127.0.0.1)
    python run.py --port 8080           # muda a porta
"""

import sys
import socket
from app import create_app
from config import Config


def detectar_ip_lan() -> str:
    """Tenta descobrir o IP que outros PCs da rede usariam para acessar."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    host = Config.HOST
    port = Config.PORT

    if "--localhost" in sys.argv:
        host = "127.0.0.1"
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])

    app = create_app()

    ip_lan = detectar_ip_lan()
    print("=" * 60)
    print("  SISMAT — Sistema de Controle de Material")
    print("=" * 60)
    print(f"  Servidor escutando em {host}:{port}")
    print()
    print("  Acesso:")
    print(f"    Neste PC:     http://localhost:{port}")
    if host == "0.0.0.0":
        print(f"    Outros PCs:   http://{ip_lan}:{port}")
        print()
        print("  ⚠  Para outro PC acessar, garanta que:")
        print("     1. Os dois PCs estão na mesma rede.")
        print("     2. O firewall do Windows libera a porta.")
    print()
    print("  Pressione Ctrl+C para parar.")
    print("=" * 60)

    # debug=False em produção/uso real (não recarrega automaticamente)
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
