"""Parte 1: testes do carregar_corpus (leitura e validação do corpus.json)."""

import json
from pathlib import Path

import pytest

from src.contratos import Dissertacao
from src.preparar_dados import ErroCorpus, carregar_corpus

EXEMPLOS = Path(__file__).parent / "exemplos"


def gravar(tmp_path, dados) -> Path:
    """Grava um corpus de teste num arquivo temporário e devolve o caminho."""
    caminho = tmp_path / "corpus.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return caminho


def item(**mudancas):
    """Um item válido; os argumentos trocam ou acrescentam campos."""
    base = {"id": "D001", "titulo": "Título", "resumo": "Resumo.", "palavras_chave": ["a", "b"]}
    base.update(mudancas)
    return base


def test_corpus_de_exemplo_carrega():
    corpus = carregar_corpus(EXEMPLOS / "corpus_exemplo.json")
    assert [d.id for d in corpus] == ["E001", "E002", "E003"]
    assert all(isinstance(d, Dissertacao) for d in corpus)
    assert corpus[1].palavras_chave == ["Tecnologias digitais", "Ensino médio", "Saúde do adolescente"]


def test_ano_e_opcional(tmp_path):
    corpus = carregar_corpus(gravar(tmp_path, [item(), item(id="D002", ano=2024)]))
    assert corpus[0].ano is None
    assert corpus[1].ano == 2024


def test_resumo_vazio_cita_o_id(tmp_path):
    with pytest.raises(ErroCorpus, match="D017 está sem resumo"):
        carregar_corpus(gravar(tmp_path, [item(id="D017", resumo="   ")]))


def test_titulo_vazio_cita_o_id(tmp_path):
    with pytest.raises(ErroCorpus, match="D005 está sem título"):
        carregar_corpus(gravar(tmp_path, [item(id="D005", titulo="")]))


def test_campo_faltando_cita_o_id(tmp_path):
    sem_resumo = item(id="D003")
    del sem_resumo["resumo"]
    with pytest.raises(ErroCorpus, match="D003: falta o campo 'resumo'"):
        carregar_corpus(gravar(tmp_path, [sem_resumo]))


def test_id_repetido(tmp_path):
    with pytest.raises(ErroCorpus, match=r"D001: id repetido \(2 vezes\)"):
        carregar_corpus(gravar(tmp_path, [item(), item(titulo="Outro")]))


def test_palavras_chave_em_texto_e_erro(tmp_path):
    with pytest.raises(ErroCorpus, match="'palavras_chave' tem que ser uma lista"):
        carregar_corpus(gravar(tmp_path, [item(palavras_chave="a, b")]))


def test_campo_com_nome_errado_e_erro(tmp_path):
    errado = item()
    errado["palavras-chave"] = errado.pop("palavras_chave")
    with pytest.raises(ErroCorpus, match="campo desconhecido 'palavras-chave'"):
        carregar_corpus(gravar(tmp_path, [errado]))


def test_todos_os_problemas_aparecem_juntos(tmp_path):
    with pytest.raises(ErroCorpus) as erro:
        carregar_corpus(gravar(tmp_path, [item(id="D001", resumo=""), item(id="D002", titulo="")]))
    mensagem = str(erro.value)
    assert "2 problema(s)" in mensagem
    assert "D001 está sem resumo" in mensagem
    assert "D002 está sem título" in mensagem


def test_corpus_que_nao_e_lista_e_erro(tmp_path):
    with pytest.raises(ErroCorpus, match="tem que ser uma lista"):
        carregar_corpus(gravar(tmp_path, item()))
