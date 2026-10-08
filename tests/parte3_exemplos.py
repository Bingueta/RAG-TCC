"""Parte 3: dados de exemplo e um Ollama falso, para testar sem modelo nenhum.

Tudo inventado (E001 a E003, de frases_exemplo.json), nunca uma das 59.
"""

import json
from pathlib import Path
from types import SimpleNamespace

from src.contratos import Contexto, Dissertacao, DissertacaoUnitarizada, Frase, TrechoRecuperado, Verbete

EXEMPLOS = Path(__file__).parent / "exemplos"
SAIDAS = EXEMPLOS / "saidas_llm"


def unitarizadas() -> dict[str, DissertacaoUnitarizada]:
    dados = json.loads((EXEMPLOS / "frases_exemplo.json").read_text(encoding="utf-8"))
    return {d["dissertacao"]["id"]: DissertacaoUnitarizada(dissertacao=Dissertacao(**d["dissertacao"]),
                                                           frases=[Frase(**f) for f in d["frases"]])
            for d in dados}


def contextos() -> dict[str, Contexto]:
    dados = json.loads((EXEMPLOS / "contexto_exemplo.json").read_text(encoding="utf-8"))
    return {c["dissertacao_id"]: Contexto(
        dissertacao_id=c["dissertacao_id"],
        tecnica=c["tecnica"],
        frases_tematicas=[TrechoRecuperado(**t) for t in c["frases_tematicas"]],
        frases_metodologia=[TrechoRecuperado(**t) for t in c["frases_metodologia"]],
        verbetes=[Verbete(**v) for v in c["verbetes"]],
        titulos_parecidos=c["titulos_parecidos"],
    ) for c in dados}


def saida(nome: str) -> str:
    """Uma resposta "crua" de modelo, de tests/exemplos/saidas_llm/."""
    return (SAIDAS / nome).read_text(encoding="utf-8")


class OllamaFalso:
    """Faz o papel do ollama.Client: devolve as saídas dadas, uma por chamada, e guarda
    os pedidos para o teste conferir. Uma Exception na lista é levantada na chamada."""

    def __init__(self, *saidas, pensa: bool = False, modelos=("qwen-falso:1b",)):
        self.saidas = list(saidas)
        self.pedidos: list[dict] = []
        self.pensa = pensa
        self.modelos = modelos

    def chat(self, **pedido):
        self.pedidos.append(pedido)
        proxima = self.saidas.pop(0)
        if isinstance(proxima, Exception):
            raise proxima
        return SimpleNamespace(message=SimpleNamespace(content=proxima))

    def show(self, modelo):
        return SimpleNamespace(capabilities=["completion", "thinking"] if self.pensa else ["completion"])

    def list(self):
        return SimpleNamespace(models=[SimpleNamespace(model=m) for m in self.modelos])
