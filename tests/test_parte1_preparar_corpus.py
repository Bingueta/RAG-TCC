"""Parte 1: testes da preparação do corpus a partir do original."""

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from src.contratos import Dissertacao
from src.preparar_dados import (
    ErroOriginal,
    carregar_corpus,
    limpar_resumo,
    preparar_corpus,
    preparar_dissertacoes,
    separar_palavras_chave,
    verificar_corpus,
)

EXEMPLOS = Path(__file__).parent / "exemplos"
RESUMO_OK = ("Texto bom. " * 60).strip()  # resumo longo, sem problema


def ler(nome):
    return json.loads((EXEMPLOS / nome).read_text(encoding="utf-8"))


def test_original_com_problemas_vira_exatamente_o_corpus_de_exemplo():
    # O original_exemplo tem de propósito: quebra de linha no título, palavra cortada por
    # hífen, espaços duplos, espaço não separável, sobra "Palavras-chave: …" e vírgula
    # sobrando. Preparado, tem que dar o corpus_exemplo, que está limpo.
    preparado = preparar_dissertacoes(ler("original_exemplo.json"), prefixo="E")
    obtido = [{k: v for k, v in asdict(d).items() if v is not None} for d in preparado]
    assert obtido == ler("corpus_exemplo.json")


def test_preparar_corpus_grava_arquivo_que_carrega(tmp_path):
    saida = tmp_path / "pasta_nova" / "corpus.json"
    preparar_corpus(EXEMPLOS / "original_exemplo.json", saida, prefixo="E")
    assert json.loads(saida.read_text(encoding="utf-8")) == ler("corpus_exemplo.json")
    assert [d.id for d in carregar_corpus(saida)] == ["E001", "E002", "E003"]
    assert "Gênero" in saida.read_text(encoding="utf-8")  # acentos gravados como texto, não ê


def test_ids_na_ordem_do_arquivo():
    original = [{"titulo": f"T{i}", "resumo": "R.", "palavras_chave": "a"} for i in range(12)]
    assert [d.id for d in preparar_dissertacoes(original)][:2] == ["D001", "D002"]
    assert preparar_dissertacoes(original)[-1].id == "D012"
    assert preparar_dissertacoes(original[:1], prefixo="C")[0].id == "C001"


def test_palavras_chave_viram_lista_limpa():
    assert separar_palavras_chave("Cooperativismo, Território,  Gênero,") == ["Cooperativismo", "Território", "Gênero"]
    assert separar_palavras_chave("Resolução SEE/MG nº 4.701/2022, Metodologia") == [
        "Resolução SEE/MG nº 4.701/2022", "Metodologia"]


@pytest.mark.parametrize(
    "resumo, esperado",
    [
        ("Texto do resumo. Palavras-chave: Referências C", "Texto do resumo."),
        ("Texto do resumo. PALAVRAS-CHAVE: A, B", "Texto do resumo."),
        ("Texto do resumo. Palavras chave: A", "Texto do resumo."),
        ("Texto do resumo. Palavra-chave: A", "Texto do resumo."),
        ("Texto sem sobra nenhuma.", "Texto sem sobra nenhuma."),
    ],
)
def test_sobra_de_palavras_chave_no_resumo_e_removida(resumo, esperado):
    assert limpar_resumo(resumo) == esperado


def test_original_sem_campo_e_erro_com_a_posicao():
    with pytest.raises(ErroOriginal, match="item 2: falta o campo 'resumo'"):
        preparar_dissertacoes([
            {"titulo": "A", "resumo": "R.", "palavras_chave": "a"},
            {"titulo": "B", "palavras_chave": "b"},
        ])


def test_original_que_nao_e_lista_e_erro():
    with pytest.raises(ErroOriginal, match="tem que ser uma lista"):
        preparar_dissertacoes({"titulo": "A"})


def test_avisos_do_corpus_de_exemplo():
    # E003 termina sem ponto final de propósito; as outras estão ok.
    avisos = verificar_corpus(carregar_corpus(EXEMPLOS / "corpus_exemplo.json"))
    assert len(avisos) == 1
    assert avisos[0].startswith("E003: resumo termina sem ponto final")


@pytest.mark.parametrize(
    "resumo, trecho_do_aviso",
    [
        (RESUMO_OK + " Abstract: This study", '"Abstract"'),
        (RESUMO_OK + " Keywords: a, b.", '"Keywords"'),
        ("RESUMO: " + RESUMO_OK, '"RESUMO:"'),
        ("Resumo curto.", "resumo muito curto"),
    ],
)
def test_avisos_de_problemas_na_copia(resumo, trecho_do_aviso):
    d = Dissertacao(id="D001", titulo="T", resumo=resumo, palavras_chave=["a"])
    assert any(trecho_do_aviso in aviso for aviso in verificar_corpus([d]))


def test_aviso_de_titulo_repetido():
    a = Dissertacao(id="D001", titulo="Mesmo Título", resumo=RESUMO_OK, palavras_chave=["a"])
    b = Dissertacao(id="D002", titulo="MESMO TÍTULO", resumo=RESUMO_OK, palavras_chave=["a"])
    assert verificar_corpus([a, b]) == ["D002: mesmo título de D001"]


def test_comando_de_calibracao_gera_ids_c(tmp_path, monkeypatch):
    import config
    from src.preparar_dados import main

    saida = tmp_path / "calibracao" / "corpus_calibracao.json"
    monkeypatch.setattr(config, "CAMINHO_ORIGINAL_CALIBRACAO", EXEMPLOS / "original_exemplo.json")
    monkeypatch.setattr(config, "CAMINHO_CALIBRACAO", saida)
    main(["--calibracao"])
    assert [d.id for d in carregar_corpus(saida)] == ["C001", "C002", "C003"]
