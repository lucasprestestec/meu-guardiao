"""Campos da proposta exigidos por seguradora (rodada 3).

Fonte: telas reais de contratação da Azos e da Icatu (PARA-O-LUCAS-3, item 4) e as capturas
conferidas em 14/10/2026. Seguradora sem perfil conhecido usa o perfil COMUM (campos comuns às
duas), que é o caso dos produtos fictícios da demonstração.

Estas funções não tocam o banco: recebem dados e devolvem a lista de erros em português.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

COMUM, AZOS, ICATU = "COMUM", "AZOS", "ICATU"

# Comuns às duas seguradoras. Os quatro primeiros já vivem em `dados` (DadosIn).
CAMPOS_COMUNS = (
    "profissao", "estado_civil", "cidade", "uf",
    "sexo", "renda_mensal", "peso_kg", "altura_cm",
    "cep", "logradouro", "numero_endereco", "bairro",
)
CAMPOS_AZOS = ("pep", "fumante_24_meses")
CAMPOS_ICATU = (
    "aposentado", "nacionalidade", "pais_nascimento", "pais_residencia",
    "pais_residencia_fiscal", "us_person", "origem_recurso",
)
CAMPOS_POR_PERFIL = {
    COMUM: CAMPOS_COMUNS,
    AZOS: CAMPOS_COMUNS + CAMPOS_AZOS,
    ICATU: CAMPOS_COMUNS + CAMPOS_ICATU,
}

# Lista fechada da Icatu (tela do portal do corretor).
PARENTESCOS = {
    ICATU: ["COMPANHEIRA", "COMPANHEIRO", "ESPOSA", "ESPOSO", "FILHA", "FILHO",
            "IRMÃ", "IRMÃO", "MÃE", "OUTROS", "PAI"],
    # Lista da Azos vista só até "Tio / Tia": a tela mostrava rolagem com mais itens. COMPLETAR
    # a partir do portal do corretor antes de publicar.
    AZOS: ["Cônjuge", "Filhos / Netos", "Enteados", "Pais / Avós", "Irmão / Irmã",
           "Companheiro(a) / Namorado(a)", "Tio / Tia"],
    COMUM: ["Cônjuge ou companheiro(a)", "Filho(a)", "Pai ou mãe", "Irmão ou irmã", "Outro"],
}
LISTA_PARENTESCO_COMPLETA = {ICATU: True, AZOS: False, COMUM: True}

ORIGENS_RECURSO = [
    "Aplicações financeiras", "Aposentadoria", "Bens imóveis", "Comissões",
    "Desejo não fornecer", "Doações", "Herança", "Salário/pró-labore", "Outros",
]
# Valores da API da Icatu; os rótulos em português são nossos.
APOSENTADO = {
    "nao": "Não",
    "portempo": "Sim, por tempo de contribuição",
    "invalidezpordoenca": "Sim, por invalidez por doença",
    "invalidezporacidente": "Sim, por invalidez por acidente",
}
MAX_BENEFICIARIOS = 10


def perfil_de(seguradora: str) -> str:
    n = unicodedata.normalize("NFKD", seguradora or "").encode("ascii", "ignore").decode().lower()
    if "azos" in n:
        return AZOS
    if "icatu" in n:
        return ICATU
    return COMUM


def aceita_beneficiarios_legais(perfil: str) -> bool:
    """Só a Azos documenta "deixar para beneficiários legais"; a Icatu pede ao menos um nome."""
    return perfil != ICATU


def campos_da_seguradora(seguradora: str) -> Dict[str, Any]:
    p = perfil_de(seguradora)
    return {
        "perfil": p,
        "exigidos": list(CAMPOS_POR_PERFIL[p]),
        "parentescos": PARENTESCOS[p],
        "lista_parentesco_completa": LISTA_PARENTESCO_COMPLETA[p],
        "aceita_beneficiarios_legais": aceita_beneficiarios_legais(p),
        "origens_recurso": ORIGENS_RECURSO if p == ICATU else [],
        "aposentado": [{"valor": k, "texto": v} for k, v in APOSENTADO.items()] if p == ICATU else [],
        "max_beneficiarios": MAX_BENEFICIARIOS,
    }


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------


class _Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _limpo(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = " ".join(v.split())
    return v or None


class BeneficiarioIn(_Estrito):
    nome: str = Field(min_length=3, max_length=120)
    data_nascimento: date
    parentesco: str = Field(max_length=60)
    percentual: Decimal = Field(gt=0, le=100, max_digits=5, decimal_places=2)

    @field_validator("nome", "parentesco")
    @classmethod
    def _txt(cls, v):
        v = _limpo(v)
        if not v:
            raise ValueError("preencha o campo")
        return v


class PropostaIn(_Estrito):
    nome_social: Optional[str] = Field(None, max_length=120)
    sexo: Optional[str] = Field(None, pattern="^[MF]$")
    renda_mensal: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)
    peso_kg: Optional[Decimal] = Field(None, ge=20, le=400, max_digits=5, decimal_places=1)
    altura_cm: Optional[int] = Field(None, ge=100, le=250)
    cep: Optional[str] = None
    logradouro: Optional[str] = Field(None, max_length=160)
    numero_endereco: Optional[str] = Field(None, max_length=20)  # "S/N" quando sem número
    complemento: Optional[str] = Field(None, max_length=80)
    bairro: Optional[str] = Field(None, max_length=80)
    # Azos
    pep: Optional[bool] = None
    fumante_24_meses: Optional[bool] = None
    # Icatu
    aposentado: Optional[str] = None
    nacionalidade: Optional[str] = Field(None, max_length=60)
    pais_nascimento: Optional[str] = Field(None, max_length=60)
    pais_residencia: Optional[str] = Field(None, max_length=60)
    pais_residencia_fiscal: Optional[str] = Field(None, max_length=60)
    us_person: Optional[bool] = None
    origem_recurso: Optional[str] = Field(None, max_length=60)
    beneficiarios_legais: bool = False
    beneficiarios: List[BeneficiarioIn] = Field(default_factory=list, max_length=MAX_BENEFICIARIOS)

    @field_validator("cep")
    @classmethod
    def _cep(cls, v):
        if v is None:
            return None
        v = re.sub(r"\D", "", v)
        if not re.fullmatch(r"[0-9]{8}", v):
            raise ValueError("CEP deve ter 8 dígitos")
        return v

    @field_validator("aposentado")
    @classmethod
    def _aposentado(cls, v):
        if v is not None and v not in APOSENTADO:
            raise ValueError(f"valor inválido; use um de {sorted(APOSENTADO)}")
        return v

    @field_validator(
        "nome_social", "logradouro", "numero_endereco", "complemento", "bairro", "nacionalidade",
        "pais_nascimento", "pais_residencia", "pais_residencia_fiscal", "origem_recurso",
    )
    @classmethod
    def _espacos(cls, v):
        return _limpo(v)


# ---------------------------------------------------------------------------
# Regras por seguradora
# ---------------------------------------------------------------------------

_ROTULOS = {
    "profissao": "profissão", "estado_civil": "estado civil", "cidade": "cidade", "uf": "UF",
    "sexo": "sexo", "renda_mensal": "renda mensal", "peso_kg": "peso", "altura_cm": "altura",
    "cep": "CEP", "logradouro": "logradouro", "numero_endereco": "número do endereço",
    "bairro": "bairro", "pep": "pessoa politicamente exposta", "fumante_24_meses":
    "fumou nos últimos 24 meses", "aposentado": "aposentadoria", "nacionalidade": "nacionalidade",
    "pais_nascimento": "país de nascimento", "pais_residencia": "país de residência atual",
    "pais_residencia_fiscal": "país de residência fiscal", "us_person": "US Person",
    "origem_recurso": "origem do recurso",
}


def validar_proposta(
    perfil: str, campos: Dict[str, Any], beneficiarios: List[Dict[str, Any]],
    legais: bool, sexo_cotacao: Optional[str], fumante_cotacao: Optional[bool],
    hoje: Optional[date] = None,
) -> List[str]:
    """Erros em português. `campos` junta os dados pessoais e os da proposta (nome do campo -> valor)."""
    hoje = hoje or date.today()
    erros: List[str] = []

    for k in CAMPOS_POR_PERFIL[perfil]:
        v = campos.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            erros.append(f"Falta informar: {_ROTULOS[k]}.")

    # Preço depende de sexo e de fumante: o que entra na proposta tem de ser o que foi cotado.
    sexo = campos.get("sexo")
    if sexo and sexo_cotacao and sexo != sexo_cotacao:
        erros.append("O sexo informado difere do usado na cotação. O preço depende dele: "
                     "refaça a comparação.")
    fum = campos.get("fumante_24_meses")
    if perfil == AZOS and fum is not None and fumante_cotacao is not None and fum != fumante_cotacao:
        erros.append("A resposta sobre fumar difere da usada na cotação. O preço depende dela: "
                     "refaça a comparação.")
    if perfil == ICATU and campos.get("origem_recurso") and campos["origem_recurso"] not in ORIGENS_RECURSO:
        erros.append("Origem do recurso fora da lista da seguradora.")

    erros += _validar_beneficiarios(perfil, beneficiarios, legais, hoje)
    return erros


def _validar_beneficiarios(perfil: str, bens: List[Dict[str, Any]], legais: bool, hoje: date) -> List[str]:
    if legais:
        if not aceita_beneficiarios_legais(perfil):
            return ["Esta seguradora exige indicar ao menos um beneficiário."]
        return ["Escolha entre indicar beneficiários e deixar para os beneficiários legais, não os dois."] \
            if bens else []
    if not bens:
        return ["Indique ao menos um beneficiário" + (
            " ou escolha deixar para os beneficiários legais." if aceita_beneficiarios_legais(perfil) else ".")]
    erros: List[str] = []
    validos = PARENTESCOS[perfil]
    for i, b in enumerate(bens, start=1):
        if b["parentesco"] not in validos:
            erros.append(f"Beneficiário {i}: grau de parentesco fora da lista da seguradora.")
        if b["data_nascimento"] > hoje:
            erros.append(f"Beneficiário {i}: data de nascimento no futuro.")
    total = sum((Decimal(b["percentual"]) for b in bens), Decimal(0))
    if total != Decimal(100):
        erros.append(f"A soma dos percentuais dos beneficiários deve ser 100%; está em {total}%.")
    return erros
