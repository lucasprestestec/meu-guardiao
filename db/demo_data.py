"""Popula a demonstração: uma persona com diagnóstico e solicitações em vários status.

Precisa da API rodando com PERMITIR_TARIFA_FICTICIA=1 e BACKOFFICE_KEY definida,
e do catálogo fictício carregado (db/seed_ficticio.py). Tudo é ficção: nomes,
CPFs gerados só para passar na validação, e-mails @exemplo.com.

    python db/demo_data.py                # usa http://localhost:8000 e BACKOFFICE_KEY
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

API = os.environ.get("API_URL", "http://localhost:8000")
CHAVE = os.environ.get("BACKOFFICE_KEY", "")
CONSENTIMENTOS = ["VERACIDADE", "TRATAMENTO_DADOS", "TERMOS", "VALORES_SUJEITOS_ANALISE"]


def chamar(caminho, corpo=None, headers=None):
    req = urllib.request.Request(
        API + caminho, method="POST" if corpo is not None else "GET",
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={"content-type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"{caminho}: {e.code} {e.read().decode()[:300]}")


def cpf_ficticio(base9: str) -> str:
    d = [int(c) for c in base9]
    for n in (9, 10):
        d.append((sum(d[i] * (n + 1 - i) for i in range(n)) * 10 % 11) % 10)
    return "".join(map(str, d))


DIAGNOSTICO_DANIEL = {
    "idade": 34, "renda_mensal_liquida": 15000, "custo_familiar_mensal": 10000,
    "situacao_profissional": "CLT", "dependentes": [{"idade": 5, "financeiramente_dependente": True}],
    "dividas": {"imobiliaria": 300000, "imobiliaria_tem_prestamista": True},
    "patrimonio_liquido": 0, "patrimonio_inventariavel": 0, "meses_de_reserva": 3,
    "seguro_atual": {"morte": 1350000, "invalidez": 1500000, "doenca_grave": 180000, "dit_diaria": 190},
}

# nome, idade, sexo, capitais (None = usa o diagnóstico), qual opção (destaque), status final
CLIENTES = [
    ("Daniel Souza", 34, "M", None, "recomendado", ["EM_PREPARACAO"]),
    ("Ana Carolina Silva", 38, "F", {"NEC_MORTE": 1500000, "NEC_INVALIDEZ": 1500000, "NEC_DOENCA_GRAVE": 400000, "NEC_RENDA": 600}, "recomendado", ["EM_PREPARACAO", "ENVIADA", "EM_ANALISE"]),
    ("João Mendes", 45, "M", {"NEC_MORTE": 1000000, "NEC_INVALIDEZ": 1000000, "NEC_DOENCA_GRAVE": 300000}, "menor_preco", ["EM_PREPARACAO", "ENVIADA"]),
    ("Mariana Ribeiro", 29, "F", {"NEC_MORTE": 800000, "NEC_INVALIDEZ": 800000, "NEC_DOENCA_GRAVE": 200000, "NEC_RENDA": 300}, "recomendado", ["EM_PREPARACAO", "ENVIADA", "EM_ANALISE", ("PENDENCIA", "Enviar documento pessoal com foto")]),
    ("Carlos Ferreira", 52, "M", {"NEC_MORTE": 1200000, "NEC_INVALIDEZ": 1200000, "NEC_DOENCA_GRAVE": 300000, "NEC_RENDA": 400}, "recomendado", ["EM_PREPARACAO", "ENVIADA", "EM_ANALISE", "APROVADA", ("EMITIDA", "8400213")]),
    ("Beatriz Lima", 41, "F", {"NEC_MORTE": 2000000, "NEC_INVALIDEZ": 2000000, "NEC_DOENCA_GRAVE": 500000, "NEC_RENDA": 700}, "recomendado", []),
    ("Rafael Costa", 36, "M", {"NEC_MORTE": 1500000, "NEC_INVALIDEZ": 1500000, "NEC_DOENCA_GRAVE": 400000, "NEC_RENDA": 500}, "recomendado", ["EM_PREPARACAO", "ENVIADA", "EM_ANALISE", "APROVADA"]),
]


def main():
    if not CHAVE:
        sys.exit("Defina BACKOFFICE_KEY (a mesma da API).")
    saude = chamar("/v1/saude")
    if not saude["modo_demonstracao"]:
        sys.exit("A API não está em modo demonstração (PERMITIR_TARIFA_FICTICIA=1).")
    hdr = {"x-backoffice-key": CHAVE}
    ano = date.today().year

    diag = chamar("/v1/diagnostico", DIAGNOSTICO_DANIEL)
    print(f"Persona Daniel: Protection Score {diag['protection_score']}  ->  /mapa/{diag['necessidade_id']}")

    for i, (nome, idade, sexo, capitais, destaque, trajeto) in enumerate(CLIENTES):
        r = chamar("/v1/comparar", {
            "necessidade_id": diag["necessidade_id"] if capitais is None else None,
            "idade": idade, "sexo": sexo, "fumante": False, "capitais_escolhidos": capitais})
        pv = r["destaques"][destaque] or r["destaques"]["recomendado"]
        sol = chamar("/v1/solicitacoes", {
            "cotacao_id": r["cotacao_id"], "produto_versao_id": pv,
            "dados": {
                "nome": nome, "cpf": cpf_ficticio(f"{123456780 + i * 7:09d}"),
                "data_nascimento": f"{ano - idade}-01-01",
                "email": nome.lower().replace(" ", ".").replace("ã", "a").replace("é", "e") + "@exemplo.com",
                "celular": f"119{80000000 + i * 1111:08d}", "cidade": "São Paulo", "uf": "SP"},
            "consentimentos": CONSENTIMENTOS})
        for passo in trajeto:
            status, extra = (passo, None) if isinstance(passo, str) else passo
            corpo = {"status": status, "por": "demo"}
            if status == "PENDENCIA":
                corpo["pendencia"] = extra
            if status == "EMITIDA":
                corpo["numero_apolice"] = extra
            chamar(f"/v1/backoffice/solicitacoes/{sol['id']}/status", corpo, hdr)
        print(f"  {nome:<20} {trajeto[-1] if trajeto else 'RECEBIDA'}  ->  /acompanhar/{sol['id']}")


if __name__ == "__main__":
    main()
