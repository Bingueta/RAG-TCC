"""Parte 1: testes da unitarização (divisão do resumo em frases numeradas)."""

import json
from pathlib import Path

import pytest

from src.contratos import DissertacaoUnitarizada
from src.preparar_dados import carregar_corpus
from src.unitarizar import dividir_em_frases, unitarizar

EXEMPLOS = Path(__file__).parent / "exemplos"


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Segundo Bardin (2016), a análise organiza os dados. Depois vem a inferência.",
         ["Segundo Bardin (2016), a análise organiza os dados.", "Depois vem a inferência."]),
        ("Conforme o Dr. Paulo Mendes, a lei é pouco aplicada. O texto discorda.",
         ["Conforme o Dr. Paulo Mendes, a lei é pouco aplicada.", "O texto discorda."]),
        ("A média foi de 2,5 horas por dia. O desvio foi pequeno.",
         ["A média foi de 2,5 horas por dia.", "O desvio foi pequeno."]),
        ("A reflexão parte da Lei n.º 12.318/2010, que trata do tema. Outra frase.",
         ["A reflexão parte da Lei n.º 12.318/2010, que trata do tema.", "Outra frase."]),
        ("Segundo Souza et al. (2019), o tempo reduz o sono. Outra frase.",
         ["Segundo Souza et al. (2019), o tempo reduz o sono.", "Outra frase."]),
        ("Foram entrevistados 12 participantes (cf. Prof. Silva, 2020). Outra frase.",
         ["Foram entrevistados 12 participantes (cf. Prof. Silva, 2020).", "Outra frase."]),
        # "etc." pode terminar a frase de verdade: aqui são duas frases
        ("Foram consultados 2 mil documentos etc. Os resultados mostram avanço.",
         ["Foram consultados 2 mil documentos etc.", "Os resultados mostram avanço."]),
        # Casos encontrados nas 59 reais (tarefa 5.3), com texto inventado parecido:
        # citação entre aspas curvas depois de ":"
        ("Foram analisados três eventos: “A praça ‘que mudou de lugar’”; “Aqui fica o rio”; e, “O mapa”. "
         "Outra frase.",
         ["Foram analisados três eventos: “A praça ‘que mudou de lugar’”; “Aqui fica o rio”; e, “O mapa”.",
          "Outra frase."]),
        # aspas retas no meio da frase
        ('O acesso à "cidade formal" é desigual para a população. Outra frase.',
         ['O acesso à "cidade formal" é desigual para a população.', "Outra frase."]),
        # lista numerada depois de ":" e itens separados por ";"
        ("Surgiram cinco temáticas: 1) trabalho; 2) família; 3) escola. Outra frase.",
         ["Surgiram cinco temáticas: 1) trabalho; 2) família; 3) escola.", "Outra frase."]),
        # nome próprio com apóstrofo
        ("Os moradores de Pingo D’Água relataram conflitos. Outra frase.",
         ["Os moradores de Pingo D’Água relataram conflitos.", "Outra frase."]),
    ],
)
def test_casos_dificeis_de_fim_de_frase(texto, esperado):
    assert dividir_em_frases(texto) == esperado


def test_frase_curta_nao_e_descartada():
    assert dividir_em_frases("Pesquisa qualitativa. Fim.") == ["Pesquisa qualitativa.", "Fim."]


def test_exemplos_batem_com_o_gabarito_feito_a_mao():
    gabarito = json.loads((EXEMPLOS / "frases_exemplo.json").read_text(encoding="utf-8"))
    corpus = carregar_corpus(EXEMPLOS / "corpus_exemplo.json")
    for dissertacao, esperado in zip(corpus, gabarito):
        unitarizada = unitarizar(dissertacao)
        obtido = [{"id": f.id, "texto": f.texto} for f in unitarizada.frases]
        assert obtido == esperado["frases"], dissertacao.id


def test_ids_sequenciais_e_nada_se_perde():
    for dissertacao in carregar_corpus(EXEMPLOS / "corpus_exemplo.json"):
        unitarizada = unitarizar(dissertacao)
        assert isinstance(unitarizada, DissertacaoUnitarizada)
        assert unitarizada.dissertacao is dissertacao
        assert [f.id for f in unitarizada.frases] == [f"F{i}" for i in range(1, len(unitarizada.frases) + 1)]
        # juntar as frases devolve o resumo inteiro: nenhuma palavra foi descartada
        assert " ".join(f.texto for f in unitarizada.frases) == dissertacao.resumo
