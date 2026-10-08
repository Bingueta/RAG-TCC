"""Parte 3: confere que os contratos da Parte 3 existem com os campos combinados (seção 3.1)."""

from dataclasses import fields

from src.contratos import Campo, RespostaIA


def nomes_dos_campos(tipo):
    return [campo.name for campo in fields(tipo)]


def test_campos_da_parte_3():
    assert nomes_dos_campos(Campo) == ["texto", "evidencia", "status"]
    assert nomes_dos_campos(RespostaIA) == [
        "dissertacao_id", "tematica_1", "tematica_2", "metodologias", "modelo", "versao_prompt", "tecnica",
        "saida_bruta"]


def test_padroes():
    assert Campo(texto="Estudo de caso", evidencia=["F3"]).status == "ok"
    campo = Campo(texto="", evidencia=[])
    resposta = RespostaIA(dissertacao_id="E001", tematica_1=campo, tematica_2=campo, metodologias=[campo],
                          modelo="m", versao_prompt="v1", tecnica="sem_rag")
    assert resposta.saida_bruta == ""
