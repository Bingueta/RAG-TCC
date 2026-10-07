"""Parte 2: testes da recuperação."""

import json
from pathlib import Path

import pytest

import config
from src.contratos import Contexto, Dissertacao, DissertacaoUnitarizada, Frase, TrechoRecuperado
from src.indexar import carregar_base
from src.recuperar import TecnicaDesconhecida, recuperar, verbetes_para

EXEMPLOS = Path(__file__).parent / "exemplos"


def exemplos_unitarizados() -> list[DissertacaoUnitarizada]:
    """As 3 dissertações inventadas, já divididas em frases (frases_exemplo.json)."""
    dados = json.loads((EXEMPLOS / "frases_exemplo.json").read_text(encoding="utf-8"))
    return [
        DissertacaoUnitarizada(dissertacao=Dissertacao(**d["dissertacao"]),
                               frases=[Frase(**f) for f in d["frases"]])
        for d in dados
    ]


def test_sem_rag_manda_todas_as_frases_na_ordem_e_nenhum_verbete():
    for unitarizada in exemplos_unitarizados():
        contexto = recuperar(unitarizada, "sem_rag")
        ids = [f.id for f in unitarizada.frases]
        assert isinstance(contexto, Contexto)
        assert contexto.dissertacao_id == unitarizada.dissertacao.id
        assert contexto.tecnica == "sem_rag"
        assert [t.frase_id for t in contexto.frases_tematicas] == ids
        assert [t.frase_id for t in contexto.frases_metodologia] == ids
        assert contexto.verbetes == []


def test_tecnica_desconhecida_e_erro():
    with pytest.raises(TecnicaDesconhecida, match="técnica 'magica' não existe"):
        recuperar(exemplos_unitarizados()[0], "magica")


# ---------- Técnica "denso" (carrega o modelo de embedding: leva alguns segundos) ----------

def test_denso_escolhe_frases_so_da_propria_dissertacao():
    for unitarizada in exemplos_unitarizados():
        contexto = recuperar(unitarizada, "denso")
        ids_da_dissertacao = {f.id for f in unitarizada.frases}
        assert contexto.tecnica == "denso"
        assert {t.frase_id for t in contexto.frases_tematicas} <= ids_da_dissertacao
        assert {t.frase_id for t in contexto.frases_metodologia} <= ids_da_dissertacao
        assert len(contexto.frases_metodologia) == min(config.TOP_K_FRASES, len(unitarizada.frases))
        assert len(contexto.verbetes) == config.TOP_K_VERBETES
        # da mais parecida para a menos parecida
        scores = [t.score for t in contexto.frases_metodologia]
        assert scores == sorted(scores, reverse=True)


def test_denso_acha_a_frase_de_metodo():
    # E001: "Foram realizadas entrevistas semiestruturadas…" (F4) e "Trata-se de uma
    # pesquisa qualitativa, desenvolvida como estudo de caso." (F3) descrevem o método.
    e001 = exemplos_unitarizados()[0]
    melhores = [t.frase_id for t in recuperar(e001, "denso").frases_metodologia[:3]]
    assert "F4" in melhores or "F3" in melhores


def test_frase_de_entrevista_traz_o_verbete_de_entrevista():
    unitarizada = DissertacaoUnitarizada(
        dissertacao=Dissertacao(id="T001", titulo="Teste", resumo="", palavras_chave=[]),
        frases=[Frase(id="F1", texto="Foram realizadas entrevistas semiestruturadas com os participantes.")])
    trecho = [TrechoRecuperado(frase_id="F1", texto=unitarizada.frases[0].texto, score=1.0)]
    base = carregar_base(EXEMPLOS / "base_metodologia_exemplo.json")
    tres_primeiros = [v.id for v, _ in verbetes_para(trecho, unitarizada, base, 3)]
    assert "entrevista_semiestruturada" in tres_primeiros


# ---------- Técnica "hibrido" ----------

def test_hibrido_escolhe_frases_so_da_propria_dissertacao():
    for unitarizada in exemplos_unitarizados():
        contexto = recuperar(unitarizada, "hibrido")
        ids_da_dissertacao = {f.id for f in unitarizada.frases}
        assert contexto.tecnica == "hibrido"
        assert {t.frase_id for t in contexto.frases_tematicas} <= ids_da_dissertacao
        assert {t.frase_id for t in contexto.frases_metodologia} <= ids_da_dissertacao
        assert len(contexto.verbetes) == config.TOP_K_VERBETES


def test_hibrido_pega_termo_escrito_na_frase():
    # E002: "Aplicou-se um questionário estruturado…" e "tratamento estatístico descritivo".
    e002 = exemplos_unitarizados()[1]
    contexto = recuperar(e002, "hibrido")
    assert "F2" in [t.frase_id for t in contexto.frases_metodologia]
    ids = [v.id for v in contexto.verbetes]
    assert "questionario" in ids
    assert "estatistica_descritiva" in ids


def test_rrf_usa_so_a_posicao():
    from src.recuperar import _posicoes, _rrf

    import numpy as np
    a = _posicoes(np.array([0.9, 0.1, 0.5]))            # ordem: 0, 2, 1
    b = _posicoes(np.array([0.0, 30.0, 2.0]), True)     # ordem: 1, 2 (o 0 tem score zero e fica fora)
    total = _rrf(a, b, tamanho=3)
    k = config.RRF_K
    assert total[2] == pytest.approx(1 / (k + 2) + 1 / (k + 2))
    assert total[0] == pytest.approx(1 / (k + 1))
    assert total[1] == pytest.approx(1 / (k + 3) + 1 / (k + 1))
    # 1/63 + 1/61 (0,032266) é um pouco mais que 2/62 (0,032258): o item 1 fica na frente
    assert list(np.argsort(-total)) == [1, 2, 0]


def test_tokens_juntam_variacoes_da_palavra():
    from src.recuperar import _tokens

    assert _tokens("Entrevistas") == _tokens("entrevista") == ["entrev"]
    assert _tokens("Análise documental de uma escola") == ["analis", "docume", "escola"]
