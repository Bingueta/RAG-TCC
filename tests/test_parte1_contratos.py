"""Parte 1: confere que os contratos da Parte 1 existem com os campos combinados."""

from dataclasses import fields

from src.contratos import Dissertacao, DissertacaoUnitarizada, Frase


def nomes_dos_campos(tipo):
    return [campo.name for campo in fields(tipo)]


def test_campos_da_dissertacao():
    assert nomes_dos_campos(Dissertacao) == ["id", "titulo", "resumo", "palavras_chave", "ano"]


def test_ano_e_opcional():
    d = Dissertacao(id="D001", titulo="t", resumo="r", palavras_chave=[])
    assert d.ano is None


def test_campos_da_frase_e_da_dissertacao_unitarizada():
    assert nomes_dos_campos(Frase) == ["id", "texto"]
    assert nomes_dos_campos(DissertacaoUnitarizada) == ["dissertacao", "frases"]
