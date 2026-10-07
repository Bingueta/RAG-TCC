"""Parte 2: confere que os contratos da Parte 2 existem com os campos combinados."""

from dataclasses import fields

from src.contratos import Contexto, TrechoRecuperado, Verbete


def nomes_dos_campos(tipo):
    return [campo.name for campo in fields(tipo)]


def test_campos_da_parte_2():
    assert nomes_dos_campos(Verbete) == ["id", "termo", "eixo", "definicao", "sinais", "sinonimos"]
    assert nomes_dos_campos(TrechoRecuperado) == ["frase_id", "texto", "score"]
    assert nomes_dos_campos(Contexto) == [
        "dissertacao_id", "tecnica", "frases_tematicas", "frases_metodologia", "verbetes", "titulos_parecidos"]


def test_titulos_parecidos_e_opcional_e_nao_compartilhado():
    a = Contexto(dissertacao_id="D001", tecnica="sem_rag", frases_tematicas=[], frases_metodologia=[], verbetes=[])
    b = Contexto(dissertacao_id="D002", tecnica="sem_rag", frases_tematicas=[], frases_metodologia=[], verbetes=[])
    a.titulos_parecidos.append("X")
    assert b.titulos_parecidos == []
