"""Parte 2: testes do carregar_base (base metodológica)."""

import json
from pathlib import Path

import pytest

import config
from src.contratos import Verbete
from src.indexar import EIXOS, ErroBase, carregar_base

EXEMPLOS = Path(__file__).parent / "exemplos"


def gravar(tmp_path, dados) -> Path:
    caminho = tmp_path / "base.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return caminho


def verbete(**mudancas):
    base = {"id": "x", "termo": "X", "eixo": "coleta", "definicao": "Def.", "sinais": ["a"], "sinonimos": []}
    base.update(mudancas)
    return base


def test_base_de_exemplo_tem_um_verbete_por_eixo():
    base = carregar_base(EXEMPLOS / "base_metodologia_exemplo.json")
    assert all(isinstance(v, Verbete) for v in base)
    assert sorted(v.eixo for v in base) == sorted(EIXOS)


def test_base_real_carrega_e_cobre_todos_os_eixos():
    base = carregar_base(config.CAMINHO_BASE)
    assert {v.eixo for v in base} == set(EIXOS)


def test_eixo_inexistente_e_erro(tmp_path):
    with pytest.raises(ErroBase, match="eixo 'metodo' não existe"):
        carregar_base(gravar(tmp_path, [verbete(eixo="metodo")]))


def test_id_repetido_e_erro(tmp_path):
    with pytest.raises(ErroBase, match=r"x: id repetido \(2 vezes\)"):
        carregar_base(gravar(tmp_path, [verbete(), verbete(termo="Outro")]))


def test_campo_faltando_e_sinais_em_texto_sao_erro(tmp_path):
    sem_definicao = verbete(id="a", sinais="roteiro, entrevista")
    del sem_definicao["definicao"]
    with pytest.raises(ErroBase) as erro:
        carregar_base(gravar(tmp_path, [sem_definicao]))
    assert "a: falta o campo 'definicao'" in str(erro.value)
    assert "a: 'sinais' tem que ser uma lista de textos" in str(erro.value)
