"""Prepara a demonstração online: cria as tabelas no Neon, carrega o catálogo fictício
e as solicitações de exemplo. Pergunta os dois segredos no terminal (a digitação fica oculta).

    python db/preparar_online.py

Pode rodar de novo: o que já existe é pulado (exceto os clientes de exemplo, que se repetem).
"""
import getpass
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import demo_data  # noqa: E402
import migrate  # noqa: E402
import seed_ficticio  # noqa: E402

SITE_PADRAO = "https://meuguardiao.vercel.app"


def perguntar(env, texto, oculto=True):
    valor = os.environ.get(env)
    if valor:
        return valor
    return (getpass.getpass if oculto else input)(texto).strip()


def main():
    print("== Preparar a demonstração online ==\n")
    url_banco = perguntar("DATABASE_URL", "Cole a connection string do Neon (não aparece ao colar) e Enter: ")
    site = perguntar("SITE_URL", f"Endereço do site [{SITE_PADRAO}]: ", oculto=False) or SITE_PADRAO
    chave = perguntar("BACKOFFICE_KEY", "Chave do backoffice que você definiu na Vercel (não aparece) e Enter: ")
    if not url_banco.startswith("postgres"):
        sys.exit("Isso não parece uma connection string do Postgres (deve começar com postgresql://).")

    print("\n1/3 Criando as tabelas...")
    print("    aplicadas:", migrate.migrar(url_banco) or "nenhuma (já estavam em dia)")
    print("2/3 Carregando as seguradoras fictícias...")
    print("    carregadas:", seed_ficticio.carregar(url_banco) or "nenhuma (já existiam)")
    print("3/3 Criando as solicitações de exemplo pelo site...")
    demo_data.API = site.rstrip("/") + "/api"
    demo_data.CHAVE = chave
    demo_data.main()
    print(f"\nPronto. Abra {site}/diagnostico?demo=1  e  {site}/backoffice")


if __name__ == "__main__":
    main()
