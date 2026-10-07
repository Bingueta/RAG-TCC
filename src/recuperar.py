"""Parte 2: recuperação, isto é, escolher o que vai para o modelo em cada dissertação.

A função principal é recuperar(dissertacao, tecnica), que devolve um Contexto.
Técnicas (config.TECNICAS):
- sem_rag: linha de base. Manda todas as frases do resumo, na ordem, e nenhum verbete.
- denso: busca por sentido (embeddings). Escolhe as frases do resumo mais parecidas com
  consultas fixas (uma para temáticas, outra para metodologias) e os verbetes da base
  mais parecidos com as frases de método escolhidas.
- hibrido: junta a busca por sentido com a busca por palavra exata (BM25), pela posição
  de cada frase nas duas listas (Reciprocal Rank Fusion). A palavra exata pega termos
  como "documental" ou "grupo focal", que a busca por sentido às vezes deixa passar.

A busca é sempre dentro do resumo da própria dissertação: nenhuma frase de outra
dissertação entra no Contexto. As frases saem da mais parecida para a menos parecida.
"""

import re
import unicodedata

import numpy as np
from rank_bm25 import BM25Okapi

import config
from src.contratos import Contexto, DissertacaoUnitarizada, TrechoRecuperado, Verbete
from src.indexar import Indice, carregar_base, chave_da_frase, texto_do_verbete, vetorizar


class TecnicaDesconhecida(ValueError):
    """Nome de técnica que não existe."""


# Consultas fixas, iguais para todas as dissertações (definidas a partir da tarefa do
# formulário, não das 59). Temáticas: também usa o título da própria dissertação.
CONSULTA_TEMATICA = "objetivo da pesquisa, tema central e objeto de estudo"
CONSULTA_METODOLOGIA = ("procedimentos metodológicos da pesquisa: tipo de estudo, abordagem, "
                        "participantes, coleta de dados, instrumentos e análise dos dados")

_cache: dict = {}


def _recursos():
    """Carrega uma vez só: base metodológica, índice (se existir) e vetores das consultas."""
    if not _cache:
        _cache["verbetes"] = carregar_base(config.CAMINHO_BASE)
        try:
            _cache["indice"] = Indice()
        except FileNotFoundError:
            _cache["indice"] = None  # sem índice: calcula os vetores na hora (mais lento)
        consultas = vetorizar([CONSULTA_TEMATICA, CONSULTA_METODOLOGIA], "query")
        _cache["consulta_tematica"], _cache["consulta_metodologia"] = consultas
    return _cache


def _vetores_das_frases(dissertacao: DissertacaoUnitarizada) -> np.ndarray:
    """Vetores das frases: do índice, quando estão lá; se não, calculados na hora."""
    indice = _recursos()["indice"]
    chaves = [chave_da_frase(dissertacao.dissertacao.id, f.id) for f in dissertacao.frases]
    if indice is not None and all(c in indice.frases for c in chaves):
        return np.stack([indice.frases[c] for c in chaves])
    return vetorizar([f.texto for f in dissertacao.frases], "passage")


def _vetores_dos_verbetes(verbetes: list[Verbete]) -> np.ndarray:
    """Vetores dos verbetes: do índice, se ele foi feito com o texto atual de cada verbete."""
    indice = _recursos()["indice"]
    if indice is not None:
        guardados = [indice.vetor_do_verbete(v) for v in verbetes]
        if all(g is not None for g in guardados):
            return np.stack(guardados)
    return vetorizar([texto_do_verbete(v) for v in verbetes], "passage")


def _melhores(dissertacao: DissertacaoUnitarizada, scores: np.ndarray, k: int) -> list[TrechoRecuperado]:
    ordem = np.argsort(-scores, kind="stable")[:k]
    return [TrechoRecuperado(frase_id=dissertacao.frases[i].id, texto=dissertacao.frases[i].texto,
                             score=round(float(scores[i]), 4)) for i in ordem]


def scores_densos(dissertacao: DissertacaoUnitarizada) -> tuple[np.ndarray, np.ndarray]:
    """Similaridade de cada frase com a consulta de temáticas e com a de metodologias."""
    recursos = _recursos()
    frases = _vetores_das_frases(dissertacao)
    titulo = vetorizar([dissertacao.dissertacao.titulo], "query")[0]
    # Temáticas: média entre a consulta fixa e o título da própria dissertação.
    tematica = (frases @ recursos["consulta_tematica"] + frases @ titulo) / 2
    metodologia = frases @ recursos["consulta_metodologia"]
    return tematica, metodologia


def verbetes_para(frases_metodologia: list[TrechoRecuperado], dissertacao: DissertacaoUnitarizada,
                  verbetes: list[Verbete], k: int) -> list[tuple[Verbete, float]]:
    """Verbetes mais parecidos com as frases de método escolhidas.

    O score de cada verbete é a maior similaridade dele com alguma dessas frases.
    """
    if not frases_metodologia or not verbetes:
        return []
    posicao = {f.id: i for i, f in enumerate(dissertacao.frases)}
    frases = _vetores_das_frases(dissertacao)[[posicao[t.frase_id] for t in frases_metodologia]]
    scores = (_vetores_dos_verbetes(verbetes) @ frases.T).max(axis=1)
    ordem = np.argsort(-scores, kind="stable")[:k]
    return [(verbetes[i], float(scores[i])) for i in ordem]


def _sem_rag(dissertacao: DissertacaoUnitarizada) -> Contexto:
    # Sem busca, todas as frases têm o mesmo peso (score 1.0) e ficam na ordem do resumo.
    todas = [TrechoRecuperado(frase_id=f.id, texto=f.texto, score=1.0) for f in dissertacao.frases]
    return Contexto(
        dissertacao_id=dissertacao.dissertacao.id,
        tecnica="sem_rag",
        frases_tematicas=list(todas),
        frases_metodologia=list(todas),
        verbetes=[],
    )


def _denso(dissertacao: DissertacaoUnitarizada) -> Contexto:
    tematica, metodologia = scores_densos(dissertacao)
    frases_metodologia = _melhores(dissertacao, metodologia, config.TOP_K_FRASES)
    verbetes = verbetes_para(frases_metodologia, dissertacao, _recursos()["verbetes"], config.TOP_K_VERBETES)
    return Contexto(
        dissertacao_id=dissertacao.dissertacao.id,
        tecnica="denso",
        frases_tematicas=_melhores(dissertacao, tematica, config.TOP_K_FRASES),
        frases_metodologia=frases_metodologia,
        verbetes=[v for v, _ in verbetes],
    )


# ---------- Técnica "hibrido": sentido + palavra exata ----------

# Palavras muito comuns, que não ajudam a achar nada.
_PALAVRAS_VAZIAS = set("""a o as os de da do das dos e em no na nos nas um uma uns umas que com por para
pelo pela pelos pelas se ao aos como mais foi foram ser sua seu suas seus este esta esse essa isso
entre sobre sao tem ter ou""".split())


def _tokens(texto: str) -> list[str]:
    """Palavras sem acento, em minúsculas, cortadas nas 6 primeiras letras.

    O corte junta variações da mesma palavra: "entrevista"/"entrevistas" → "entrev",
    "qualitativa"/"qualitativo" → "qualit", "documental"/"documentos" → "docume".
    """
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                         if unicodedata.category(c) != "Mn")
    return [p[:6] for p in re.findall(r"[a-z]+", sem_acento) if len(p) >= 3 and p not in _PALAVRAS_VAZIAS]


def _vocabulario_de_metodo(verbetes: list[Verbete]) -> list[str]:
    """Todas as palavras da base metodológica: é o que a busca exata procura nas frases."""
    palavras = set()
    for v in verbetes:
        for texto in [v.termo, *v.sinonimos, *v.sinais]:
            palavras.update(_tokens(texto))
    return sorted(palavras)


def _posicoes(scores: np.ndarray, so_positivos: bool = False) -> dict[int, int]:
    """Posição (1 = melhor) de cada item na lista ordenada pelo score."""
    ordem = [i for i in np.argsort(-scores, kind="stable") if not so_positivos or scores[i] > 0]
    return {i: posicao for posicao, i in enumerate(ordem, start=1)}


def _rrf(*listas_de_posicoes: dict[int, int], tamanho: int) -> np.ndarray:
    """Reciprocal Rank Fusion: soma 1 / (k + posição) de cada lista. Usa só a posição,
    porque o score de cada busca está numa escala diferente."""
    total = np.zeros(tamanho)
    for posicoes in listas_de_posicoes:
        for i, posicao in posicoes.items():
            total[i] += 1.0 / (config.RRF_K + posicao)
    return total


def _bm25(dissertacao: DissertacaoUnitarizada, consulta: list[str]) -> np.ndarray:
    frases = [_tokens(f.texto) or ["_"] for f in dissertacao.frases]
    return np.array(BM25Okapi(frases).get_scores(consulta))


def _verbetes_hibrido(frases_metodologia, dissertacao, verbetes, k):
    """Verbetes: junta a lista por sentido com a contagem de termos escritos nas frases."""
    densos = verbetes_para(frases_metodologia, dissertacao, verbetes, len(verbetes))
    posicao_denso = {verbetes.index(v): p for p, (v, _) in enumerate(densos, start=1)}
    texto = " " + " ".join(_tokens(" ".join(t.texto for t in frases_metodologia))) + " "
    contagem = np.zeros(len(verbetes))
    for i, v in enumerate(verbetes):
        for peso, expressoes in ((2, [v.termo, *v.sinonimos]), (1, v.sinais)):
            for expressao in expressoes:
                if " " + " ".join(_tokens(expressao)) + " " in texto and _tokens(expressao):
                    contagem[i] += peso
    total = _rrf(posicao_denso, _posicoes(contagem, so_positivos=True), tamanho=len(verbetes))
    return [verbetes[i] for i in np.argsort(-total, kind="stable")[:k]]


def _hibrido(dissertacao: DissertacaoUnitarizada) -> Contexto:
    verbetes = _recursos()["verbetes"]
    tematica, metodologia = scores_densos(dissertacao)
    d = dissertacao.dissertacao
    consulta_tematica = _tokens(" ".join([d.titulo, *d.palavras_chave]))
    n = len(dissertacao.frases)
    rrf_tematica = _rrf(_posicoes(tematica), _posicoes(_bm25(dissertacao, consulta_tematica), True), tamanho=n)
    rrf_metodologia = _rrf(_posicoes(metodologia),
                           _posicoes(_bm25(dissertacao, _vocabulario_de_metodo(verbetes)), True), tamanho=n)
    frases_metodologia = _melhores(dissertacao, rrf_metodologia, config.TOP_K_FRASES)
    return Contexto(
        dissertacao_id=d.id,
        tecnica="hibrido",
        frases_tematicas=_melhores(dissertacao, rrf_tematica, config.TOP_K_FRASES),
        frases_metodologia=frases_metodologia,
        verbetes=_verbetes_hibrido(frases_metodologia, dissertacao, verbetes, config.TOP_K_VERBETES),
    )


TECNICAS = {"sem_rag": _sem_rag, "denso": _denso, "hibrido": _hibrido}


def recuperar(dissertacao: DissertacaoUnitarizada, tecnica: str) -> Contexto:
    """Escolhe as frases e os verbetes que vão para o modelo, conforme a técnica."""
    if tecnica not in TECNICAS:
        raise TecnicaDesconhecida(f"técnica '{tecnica}' não existe (use uma de: {', '.join(TECNICAS)})")
    return TECNICAS[tecnica](dissertacao)
