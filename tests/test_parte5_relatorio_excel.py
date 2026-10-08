"""Parte 5: testes do relatório em Excel, com execuções inventadas.

O Excel só transcreve os JSON do comparar; o teste confere que nada se perde no caminho
(linhas, colunas, valores) e que os gráficos saem para os indicadores que existem.
"""

import json
from pathlib import Path

import numpy as np
import pytest

openpyxl = pytest.importorskip("openpyxl")

from src.comparar import Vocabulario, carregar_referencia, comparar_execucoes  # noqa: E402
from src.indexar import carregar_base  # noqa: E402
from src.relatorio_excel import converter_pasta  # noqa: E402

EXEMPLOS = Path(__file__).parent / "exemplos"
VETORES = {"Saúde do idoso": [1.0, 0.0], "Adesão ao tratamento": [0.0, 1.0],
           "Tratamento": [0.0, 1.0], "Envelhecimento e saúde": [0.8, 0.6]}


def codificar_falso(textos):
    return np.array([VETORES[t] for t in textos])


def campo(texto, status="ok"):
    return {"texto": texto, "evidencia": ["F1"], "status": status}


def resposta(id_, t1, t2, metodologias, modelo):
    return {"dissertacao_id": id_, "tematica_1": campo(t1), "tematica_2": campo(t2), "metodologias": metodologias,
            "modelo": modelo, "versao_prompt": "v1", "tecnica": "hibrido", "saida_bruta": ""}


REFERENCIA = {"referencias": [
    {"dissertacao_id": "X001", "tematica_1": "Saúde do idoso", "tematica_2": "Adesão ao tratamento",
     "metodologias": [{"termo": "Abordagem qualitativa", "verbete": "abordagem_qualitativa", "eixo": "abordagem",
                       "explicito": True}]},
    {"dissertacao_id": "X002", "tematica_1": "Tratamento", "tematica_2": "Envelhecimento e saúde",
     "metodologias": []},
]}


@pytest.fixture
def avaliacao(tmp_path):
    """Duas execuções inventadas avaliadas pelo comparar, com os JSON gravados em tmp_path/avaliacao."""
    vocab = Vocabulario(carregar_base(EXEMPLOS / "base_metodologia_exemplo.json"))
    ref = tmp_path / "ref.json"
    ref.write_text(json.dumps(REFERENCIA, ensure_ascii=False), encoding="utf-8")
    referencias = carregar_referencia(ref, vocab)
    sugestoes = tmp_path / "sugestoes"
    for nome, modelo, metodo in (("falso-1b__hibrido__v1", "falso:1b", "Pesquisa qualitativa"),
                                 ("falso-2b__hibrido__v1", "falso:2b", "Estudo de caso")):
        (sugestoes / nome).mkdir(parents=True)
        respostas = [resposta("X001", "Saúde do idoso", "Adesão ao tratamento", [campo(metodo)], modelo),
                     resposta("X002", "Tratamento", "Envelhecimento e saúde",
                              [campo("Não informado no resumo", "nao_informado")], modelo)]
        (sugestoes / nome / "respostas.json").write_text(json.dumps(respostas, ensure_ascii=False), encoding="utf-8")
    saida = tmp_path / "avaliacao"
    linhas = comparar_execucoes(sugestoes, vocab, referencias, codificar_falso, pasta_saida=saida)
    return saida, linhas


def test_converte_comparacao_e_cada_relatorio(avaliacao):
    saida, _ = avaliacao
    feitos = converter_pasta(saida)
    assert sorted(p.relative_to(saida).as_posix() for p in feitos) == [
        "comparacao.xlsx", "falso-1b__hibrido__v1/relatorio.xlsx", "falso-2b__hibrido__v1/relatorio.xlsx"]


def test_comparacao_tem_as_execucoes_lado_a_lado_e_os_graficos(avaliacao):
    saida, linhas = avaliacao
    converter_pasta(saida)
    livro = openpyxl.load_workbook(saida / "comparacao.xlsx")
    assert livro.sheetnames[0] == "execucoes"
    assert {"concordancia", "concordancia_por_dissertacao", "graficos"} <= set(livro.sheetnames)
    aba = livro["execucoes"]
    cabecalho = [c.value for c in aba[1]]
    assert cabecalho[0] == "execucao" and "met_f1" in cabecalho
    assert aba.max_row == 1 + len(linhas)
    # O F1 da planilha é o mesmo do JSON: X001 acerta a qualitativa (1) e X002 é
    # "não informado" certo (1) → 1,0; o 2b diz estudo de caso (0) → média 0,5.
    f1 = {aba.cell(row=r, column=1).value: aba.cell(row=r, column=cabecalho.index("met_f1") + 1).value
          for r in range(2, aba.max_row + 1)}
    assert f1 == pytest.approx({"falso-1b__hibrido__v1": 1.0, "falso-2b__hibrido__v1": 0.5})
    assert len(livro["graficos"]._charts) >= 5


def test_relatorio_tem_resumo_e_por_dissertacao(avaliacao):
    saida, _ = avaliacao
    converter_pasta(saida)
    livro = openpyxl.load_workbook(saida / "falso-2b__hibrido__v1" / "relatorio.xlsx")
    assert livro.sheetnames == ["resumo", "por_dissertacao"]   # sem execucao.json, sem aba de configuração
    resumo = {l[0].value: l[1].value for l in livro["resumo"].iter_rows(min_row=2)}
    assert resumo["modelo"] == "falso:2b"
    assert resumo["contra_referencia.metodologias.macro.f1"] == pytest.approx(0.5)
    por = livro["por_dissertacao"]
    cabecalho = [c.value for c in por[1]]
    x1 = [c.value for c in por[2]]
    assert x1[cabecalho.index("dissertacao_id")] == "X001"
    assert x1[cabecalho.index("fora_da_referencia")] == "estudo_de_caso"   # lista vira texto com "; "


def test_sem_referencia_nao_quebra(tmp_path):
    from src.relatorio_excel import gravar_comparacao
    caminho = gravar_comparacao({"execucoes": [{"execucao": "a", "modelo": "m", "eixos_cobertos": 2.0,
                                                "itens_exatos": 0.5, "met_f1": None}],
                                 "diferencas_pareadas": [], "concordancia": None}, tmp_path / "c.xlsx")
    livro = openpyxl.load_workbook(caminho)
    assert livro.sheetnames == ["execucoes", "graficos"]
    assert len(livro["graficos"]._charts) == 2              # met_f1 vazio não vira gráfico
