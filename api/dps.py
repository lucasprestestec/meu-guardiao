"""DPS (declaração pessoal de saúde) coletada no nosso site, uma por seguradora (rodada 3).

Decisão do cliente: o cliente nunca sai do nosso site. A DPS é respondida aqui, guardada de forma
imutável e a equipe transcreve para o portal da seguradora. Por isso:
  * a redação é a da seguradora, palavra por palavra, sem paráfrase (a transcrição vira cópia);
  * cada seguradora tem o seu questionário, sem fundir os dois;
  * o que foi mostrado (texto das perguntas) é guardado junto com as respostas e um hash.

Cada pergunta tem `confirmada`: True = a redação foi conferida com o que a seguradora mostra. Questionário
com pergunta não confirmada não vale para produto real (ver `questionario_valido_para_producao`).

Fontes: tela da DPS da Icatu (capturas de 10/2026) e anexo do PARA-O-LUCAS-3 para a Azos. Onde o anexo e a
tela divergem na Icatu, vale a tela.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from .proposta import AZOS, ICATU

VERSAO = "2026-10-v1"
SIM_NAO, UNICA, MULTIPLA, NUMERO = "sim_nao", "unica", "multipla", "numero"


def _p(id, texto, tipo=SIM_NAO, opcoes=None, exclusiva=None, depende=None, unidade=None,
       confirmada=True, fonte="tela"):
    return {
        "id": id, "texto": texto, "tipo": tipo, "opcoes": opcoes or [], "exclusiva": exclusiva,
        "depende": depende,  # {"id": "I9", "valor": True}
        "unidade": unidade, "confirmada": confirmada, "fonte": fonte,
    }


# ---------------------------------------------------------------------------
# Icatu: 13 perguntas, uma por tela no portal. O peso e a altura (pergunta 1) já vêm do cadastro da
# proposta e não são perguntados de novo; a declaração de que estão corretos entra na conferência.
# ---------------------------------------------------------------------------
_ICATU = [
    _p("I2", "Sofreu alguma alteração de peso (perda ou ganho) de mais de 10kg nos últimos 6 meses?"),
    _p("I3", "Você sofre, já sofreu ou está em investigação diagnóstica para algumas das seguintes "
             "condições: câncer, hipertensão arterial, diabetes mellitus, pré-diabetes, dislipidemia, "
             "doenças cardiovasculares, pulmonares, renais, da tireoide, neurológicas, do esôfago, "
             "estômago, intestino, fígado, baço, pâncreas, reumáticas, psíquicas, do sistema "
             "geniturinário, infectocontagiosas ou qualquer outra doença crônica?"),
    _p("I4", "Você já foi submetido(a) a alguma cirurgia ou possui alguma cirurgia indicada ou "
             "programada para realização?", confirmada=False, fonte="anexo"),
    _p("I5", "Você já realizou ou possui indicação para realizar algum procedimento hospitalar, tais "
             "como biópsia, diálise, internação hospitalar, punção, quimioterapia, radioterapia, entre "
             "outros?"),
    _p("I6", "Você faz uso diário ou habitual de medicamentos?"),
    _p("I7", "Sofre de alguma deficiência nos órgãos, nos membros ou nos sentidos?",
       confirmada=False, fonte="anexo"),
    _p("I8", "Algum membro da sua família (pais ou irmãos) sofre ou já sofreu de alguma doença grave?"),
    _p("I9", "Você consome bebida alcoólica?", confirmada=False, fonte="anexo"),
    # Sub-perguntas: só aparecem quando a 9 for "Sim" (perguntar dose a quem não bebe é erro visível).
    _p("I9.1", "Houve necessidade de tratamento para dependência química?",
       depende={"id": "I9", "valor": True}, confirmada=False, fonte="tela (resumo)"),
    _p("I9.1.1", "Quantas doses de cerveja você consome por semana, considerando uma lata (350ml) "
                 "como 1 dose?", NUMERO, depende={"id": "I9", "valor": True}, unidade="unidades/semana"),
    _p("I9.1.2", "Quantas doses de vinho você consome por semana, considerando uma taça de vinho "
                 "(150ml) como 1 dose?", NUMERO, depende={"id": "I9", "valor": True},
       unidade="unidades/semana"),
    _p("I9.1.3", "Quantas doses de bebidas destiladas você consome por semana, considerando um copo "
                 "(45ml) como 1 dose?", NUMERO, depende={"id": "I9", "valor": True},
       unidade="unidades/semana"),
    _p("I10", "Você é fumante?"),
    _p("I11", "Você fez ou fez uso de algum tipo de droga nos últimos 6 anos?"),
    _p("I12", "Você pratica alguma modalidade esportiva de caráter profissional ou amador?"),
    _p("I13", "Alguma companhia já comprou, agravou/ajustou ou cancelou algum seguro de vida ou "
              "acidentes pessoais em seu nome?", confirmada=False, fonte="tela (sidebar cortada)"),
]

# ---------------------------------------------------------------------------
# Azos: blocos de múltipla escolha, cada um com saída "Nenhum desses". Texto do anexo do cliente; os
# blocos 2, 8 e 11 foram conferidos com a tela do portal do corretor.
# ---------------------------------------------------------------------------
_ENUNCIADO_COND = ("Independentemente da data, você já foi diagnosticado(a), tratado(a) clinicamente ou "
                   "submetido(a) a alguma cirurgia para: (Selecione todas as opções que se apliquem).")

_AZOS = [
    _p("A1", _ENUNCIADO_COND, MULTIPLA, exclusiva="Nenhum desses", opcoes=[
        "Abuso de álcool", "Hipertensão ou Pressão alta", "Pré-diabetes ou Diabetes (exceto gestacional)",
        "Derrame (AVC, TIA, \"Mini-stroke\", etc.)",
        "Distúrbio convulsivo devido a epilepsia, lesão cerebral ou outros motivos",
        "Transplante de órgãos (doador ou receptor)", "Condições renais, incluindo pedra nos rins", "Lúpus",
        "Condições da tireoide (hipertireoidismo, nódulos, cistos, dentre outros)",
        "Perda de peso (cirurgia bariátrica)", "Hérnia de disco, protrusão, extrusão ou abaulamento",
        "Doenças pulmonares (asma, bronquite, pneumonia, doença pulmonar obstrutiva crônica, enfisema, "
        "dentre outras)",
        "Condições do aparelho digestivo (diverticulose, diverticulite, esofagite, gastrite, hérnia de "
        "hiato, refluxo ou úlcera)", "Nenhum desses"],
       confirmada=False, fonte="anexo (enunciado deduzido do bloco 2)"),
    _p("A2", _ENUNCIADO_COND, MULTIPLA, exclusiva="Nenhuma dessas.", opcoes=[
        "Amputações ou encurtamento de membros.", "Perda ou deficiência auditiva, na fala ou visual.",
        "Doenças ortopédicas (artrite psoriática/reumatoide, osteoartrose, espondilite anquilosante, "
        "osteoporose).", "Lesões ortopédicas (Fraturas, Lesões ligamentares e de tendões, dentre outras).",
        "Esforço repetitivo (LER/DORT).", "Luxações (somente em casos com menos de 12 meses).",
        "Entorses ou torções (somente em casos com menos de 1 mês).", "Paralisia cerebral.",
        "Tetraplegia ou quadriplegia irreversíveis.",
        "Outra condição ortopédica, motora ou sensorial (vertigem, tontura, labirintite).",
        "Nenhuma dessas."]),
    _p("A3", "Nos últimos 5 anos, você realizou biópsia investigativa ou recebeu o diagnóstico de: "
             "nódulos, cistos ou tumores? (Exceto: Nódulos/cistos na tireoide, endometriose, nevos, "
             "psoríase, distúrbios de pele, pólipos e biópsias realizadas em colonoscopia.)", UNICA,
       opcoes=["Sim, mas o resultado ainda não saiu",
               "Sim, com resultado inconclusivo (mais exames serão necessários para concluir a "
               "investigação médica)", "Sim, foi diagnosticada uma condição maligna",
               "Sim, foi diagnosticada condição benigna", "Não"], fonte="anexo"),
    _p("A4", "Nos últimos 5 anos, realizou alguma cirurgia ou ficou internado(a)? (desconsidere cesárea, "
             "cirurgias plásticas e casos já mencionados anteriormente).", UNICA,
       opcoes=["Sim, cirurgia (com internação ou sem internação)", "Sim, apenas internação", "Não"],
       fonte="anexo"),
    _p("A5", "Está ciente de alguma condição médica que não foi mencionada e possa resultar em uma "
             "internação ou cirurgia?", UNICA,
       opcoes=["Sim, irei iniciar tratamento para uma condição descoberta recentemente",
               "Sim, estou em fase de investigação ou irei iniciar uma investigação médica", "Não"],
       fonte="anexo"),
    _p("A6", "Viajou nos últimos 2 anos ou tem a intenção de viajar em aeronaves pequenas (táxis aéreos, "
             "aeronaves particulares, helicópteros, ultraleves, etc)?", fonte="anexo"),
    _p("A7", "Nos últimos 2 anos ou no próximo ano, você fez ou planeja fazer / praticar:", MULTIPLA,
       exclusiva="Nenhuma dessas atividades", opcoes=[
           "Corridas de automóveis, kart, caminhões e similares",
           "Motocross, trilhas, rally, enduro ou corridas de motocicleta (qualquer tipo)",
           "Escaladas ao ar livre que requer equipamento especializado", "Esportes de neve (Ski, Snowboard)",
           "Lutas ou artes marciais: Jiu-Jitsu, Judo, Luta Livre, MMA, Muay Thai, Karate e Boxe "
           "(desconsiderar treinos fitness)", "Mergulhar em profundidade superior a 30 metros",
           "Mountain bike, BMX, ciclismo de aventura ou downhill",
           "Paraquedas, bungee jump, asa delta ou similar", "Skate, longboard ou patins",
           "Nenhuma dessas atividades"], fonte="anexo"),
    _p("A8", "Você utiliza ou pretende utilizar motocicleta como piloto ou passageiro?", UNICA,
       opcoes=["Lazer (Apenas passeios ou viagens)", "Locomoção ao trabalho (somente ida e/ou volta) + Lazer",
               "Uso comercial / prestação de serviço / entregas + Lazer",
               "Não utilizo motocicleta de nenhuma forma"]),
    _p("A9", "Você mora atualmente ou tem planos de morar fora do Brasil (em outro país, por mais de 60 "
             "dias), nos próximos 12 meses?", fonte="anexo"),
    _p("A10", "Você já possui algum seguro de vida individual para as coberturas que está realizando a "
              "cotação na Azos?", UNICA,
       opcoes=["Sim, planejo manter outros seguros além do seguro com a Azos",
               "Sim, mas vou cancelar todos os outros seguros e manter apenas com a Azos", "Não"],
       fonte="anexo"),
    _p("A11", "Independentemente da data, você tem conhecimento de alguma doença, condição de saúde, "
              "lesão ou fratura ainda não informada nas respostas anteriores?"),
    _p("A12", "Você está ou esteve em investigação médica nos últimos 12 meses, ou pretende iniciar uma "
              "para avaliar uma condição ainda não conclusiva? (exceto check-up)", fonte="anexo"),
    _p("A13", "Você usa regularmente ou recebeu orientação médica para usar algum medicamento devido a "
              "condições não declaradas anteriormente? (exceto anticoncepcionais, suplementos e "
              "vitaminas).", UNICA,
       opcoes=["Sim, por conta própria", "Sim, por recomendação médica", "Não"], fonte="anexo"),
]

_BANCO = {AZOS: _AZOS, ICATU: _ICATU}


def questionario_de(perfil: str) -> Optional[Dict[str, Any]]:
    """Questionário da seguradora, ou None se ela não tem DPS neste sistema (ex.: perfil COMUM)."""
    perguntas = _BANCO.get(perfil)
    if perguntas is None:
        return None
    return {"perfil": perfil, "versao": VERSAO, "perguntas": perguntas,
            "confirmado": all(p["confirmada"] for p in perguntas)}


def questionario_valido_para_producao(q: Dict[str, Any]) -> bool:
    return bool(q["confirmado"])


def _visivel(p: Dict[str, Any], respostas: Dict[str, Any]) -> bool:
    d = p["depende"]
    return d is None or respostas.get(d["id"]) == d["valor"]


def perguntas_visiveis(q: Dict[str, Any], respostas: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [p for p in q["perguntas"] if _visivel(p, respostas)]


def validar_respostas(q: Dict[str, Any], respostas: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
    """(erros, respostas normalizadas). Resposta a pergunta que não aparece é descartada, não aceita."""
    erros: List[str] = []
    out: Dict[str, Any] = {}
    conhecidas = {p["id"] for p in q["perguntas"]}
    for k in respostas:
        if k not in conhecidas:
            erros.append(f"Pergunta desconhecida: {k}.")
    for p in perguntas_visiveis(q, respostas):
        v = respostas.get(p["id"])
        erro = _erro_da_resposta(p, v)
        if erro:
            erros.append(erro)
        else:
            out[p["id"]] = v
    return erros, out


def _erro_da_resposta(p: Dict[str, Any], v: Any) -> Optional[str]:
    i, t = p["id"], p["tipo"]
    if v is None:
        return f"Responda a pergunta {i}."
    if t == SIM_NAO and not isinstance(v, bool):
        return f"Pergunta {i}: responda sim ou não."
    if t == UNICA and v not in p["opcoes"]:
        return f"Pergunta {i}: escolha uma das opções."
    if t == MULTIPLA:
        if not isinstance(v, list) or not v or any(o not in p["opcoes"] for o in v) or len(set(v)) != len(v):
            return f"Pergunta {i}: marque ao menos uma opção da lista."
        if p["exclusiva"] in v and len(v) > 1:
            return f"Pergunta {i}: \"{p['exclusiva']}\" não pode vir junto com outras opções."
    if t == NUMERO and (isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0 or v > 1000):
        return f"Pergunta {i}: informe um número entre 0 e 1000."
    return None


def texto_da_resposta(p: Dict[str, Any], v: Any) -> str:
    if p["tipo"] == SIM_NAO:
        return "Sim" if v else "Não"
    if p["tipo"] == MULTIPLA:
        return "; ".join(v)
    if p["tipo"] == NUMERO:
        return f"{v:g} {p['unidade'] or ''}".strip()
    return str(v)


def instantaneo(q: Dict[str, Any], respostas: Dict[str, Any]) -> Dict[str, Any]:
    """O que foi MOSTRADO e respondido: pergunta (texto exato) + resposta, só das perguntas visíveis.
    É a prova se houver divergência com a seguradora, por isso inclui o texto e não só o id."""
    itens = [{"id": p["id"], "pergunta": p["texto"], "tipo": p["tipo"], "opcoes": p["opcoes"],
              "resposta": respostas[p["id"]], "resposta_texto": texto_da_resposta(p, respostas[p["id"]])}
             for p in perguntas_visiveis(q, respostas) if p["id"] in respostas]
    return {"perfil": q["perfil"], "versao": q["versao"], "confirmado": q["confirmado"], "itens": itens}


def hash_dps(snapshot: Dict[str, Any]) -> str:
    canon = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()
