"""Versões falsas das Partes 1, 2 e 3, para o pipeline rodar sem Ollama, sem índice e sem
spaCy (python -m src.pipeline --mock). Seção 3.9 de docs/divisao-tarefas.md.

Devolvem só os dados de exemplo de tests/exemplos/: 3 dissertações inventadas (E001 a E003),
nunca uma das 59. A geração passa pelo gerar_resposta de verdade, com um Ollama falso que
responde as saídas de tests/exemplos/saidas_llm/: assim o --mock também confere a leitura do
JSON e a validação.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import config
from src.contratos import (Contexto, Dissertacao, DissertacaoUnitarizada, Frase, RespostaIA,
                           TrechoRecuperado, Verbete)
from src.preparar_dados import carregar_corpus as _carregar_corpus
from src.sugerir import gerar_resposta as _gerar_resposta

EXEMPLOS = config.RAIZ / "tests" / "exemplos"
MODELO = "mock"

# A saída "crua" que o Ollama falso devolve para cada dissertação de exemplo.
_SAIDAS = {"E001": "correta.json", "E002": "e002.json", "E003": "nao_informado.json"}


def _ler(nome: str):
    return json.loads((EXEMPLOS / nome).read_text(encoding="utf-8"))


def carregar_corpus(caminho: str | Path | None = None) -> list[Dissertacao]:
    return _carregar_corpus(caminho or EXEMPLOS / "corpus_exemplo.json")


def unitarizar(dissertacao: Dissertacao) -> DissertacaoUnitarizada:
    for item in _ler("frases_exemplo.json"):
        if item["dissertacao"]["id"] == dissertacao.id:
            return DissertacaoUnitarizada(dissertacao=dissertacao, frases=[Frase(**f) for f in item["frases"]])
    raise KeyError(f"{dissertacao.id} não está em frases_exemplo.json")


def recuperar(dissertacao: DissertacaoUnitarizada, tecnica: str) -> Contexto:
    """sem_rag: todas as frases, nenhum verbete (como o de verdade). As outras: o contexto
    pronto de contexto_exemplo.json, com o nome da técnica pedida."""
    if tecnica == "sem_rag":
        todas = [TrechoRecuperado(frase_id=f.id, texto=f.texto, score=1.0) for f in dissertacao.frases]
        return Contexto(dissertacao_id=dissertacao.dissertacao.id, tecnica=tecnica,
                        frases_tematicas=list(todas), frases_metodologia=list(todas), verbetes=[])
    for c in _ler("contexto_exemplo.json"):
        if c["dissertacao_id"] == dissertacao.dissertacao.id:
            return Contexto(
                dissertacao_id=c["dissertacao_id"], tecnica=tecnica,
                frases_tematicas=[TrechoRecuperado(**t) for t in c["frases_tematicas"]],
                frases_metodologia=[TrechoRecuperado(**t) for t in c["frases_metodologia"]],
                verbetes=[Verbete(**v) for v in c["verbetes"]], titulos_parecidos=c["titulos_parecidos"])
    raise KeyError(f"{dissertacao.dissertacao.id} não está em contexto_exemplo.json")


class _OllamaFalso:
    def __init__(self, saida: str):
        self._saida = saida

    def chat(self, **pedido):
        return SimpleNamespace(message=SimpleNamespace(content=self._saida))

    def show(self, modelo):
        return SimpleNamespace(capabilities=["completion"])


def gerar_resposta(dissertacao: DissertacaoUnitarizada, contexto: Contexto, modelo: str = MODELO,
                   versao: str | None = None, cliente=None) -> RespostaIA:
    saida = (EXEMPLOS / "saidas_llm" / _SAIDAS[dissertacao.dissertacao.id]).read_text(encoding="utf-8")
    return _gerar_resposta(dissertacao, contexto, modelo, versao, cliente=_OllamaFalso(saida))
