"""Parte 5: testes das métricas, com dados inventados e valores calculados à mão.

Cada conta esperada está escrita no comentário do teste, para dar para conferir no papel.
Nenhum dado aqui vem das 59 nem da calibração.
"""

import json
from pathlib import Path

import numpy as np
import pytest

import config
from src.comparar import (
    CodificadorE5, Vocabulario, avaliar_contra_referencia, carregar_referencia, chave,
    comparar_execucoes, concordancia, contar_status, eixos_cobertos, indicadores_sem_gabarito,
    jaccard, media_macro, media_micro, metodologias_da_resposta, placar, placar_por_eixo,
    referencia_de_texto, separar_termos, similaridade_par, status_da_dissertacao,
)
from src.indexar import carregar_base

EXEMPLOS = Path(__file__).parent / "exemplos"


@pytest.fixture
def vocab() -> Vocabulario:
    """Os 6 verbetes inventados de base_metodologia_exemplo.json, um por eixo."""
    return Vocabulario(carregar_base(EXEMPLOS / "base_metodologia_exemplo.json"))


@pytest.fixture
def vocab_real() -> Vocabulario:
    """A base de verdade (28 verbetes), para os casos de separação que dependem dela."""
    return Vocabulario(carregar_base(config.CAMINHO_BASE))


def campo(texto: str, status: str = "ok", evidencia=None) -> dict:
    return {"texto": texto, "evidencia": evidencia if evidencia is not None else ["F1"], "status": status}


def resposta(id_: str, t1: str, t2: str, metodologias: list[dict], **extra) -> dict:
    return {"dissertacao_id": id_, "tematica_1": campo(t1), "tematica_2": campo(t2),
            "metodologias": metodologias, "modelo": "falso:1b", "versao_prompt": "v1",
            "tecnica": "hibrido", "saida_bruta": "", **extra}


NAO_INFORMADO = campo("Não informado no resumo", "nao_informado", [])

# Vetores falsos, já normalizados: dá para fazer as contas de cosseno à mão.
VETORES = {
    "Saúde do idoso": [1.0, 0.0],
    "Adesão ao tratamento": [0.0, 1.0],
    "Tratamento": [0.0, 1.0],
    "Envelhecimento e saúde": [0.8, 0.6],
}


def codificar_falso(textos: list[str]) -> np.ndarray:
    return np.array([VETORES[t] for t in textos])


# ---------- chave e vocabulário ----------

def test_chave_iguala_grafias_do_mesmo_termo():
    assert chave("Entrevista semi-estruturada") == chave("entrevistas semiestruturadas")
    assert chave("Entrevista Semi Estruturada") == chave("entrevista semiestruturada")
    assert chave("Análise de Conteúdo") == "analisedeconteudo"
    assert chave("Grupos focais") == chave("grupo focal")
    assert chave("Observações") == chave("observação")


def test_reconhece_sinonimo_e_corta_parenteses_qualificador_e_autor(vocab):
    assert vocab.reconhecer("Estudo descritivo") == ("pesquisa_descritiva", "objetivos")
    assert vocab.reconhecer("Estudo de caso (único)") == ("estudo_de_caso", "procedimento")
    assert vocab.reconhecer("Análise de conteúdo proposta por Bardin") == ("analise_de_conteudo", "analise")
    assert vocab.reconhecer("Análise de Conteúdo de Laurence Bardin") == ("analise_de_conteudo", "analise")


def test_reconhece_sem_a_palavra_de_enchimento(vocab):
    assert vocab.reconhecer("Pesquisa de natureza qualitativa") == ("abordagem_qualitativa", "abordagem")
    assert vocab.reconhecer("Estudo de caráter descritivo") == ("pesquisa_descritiva", "objetivos")


def test_termo_fora_da_base_vira_livre_sem_eixo(vocab):
    assert vocab.reconhecer("Etnografia digital") == ("livre:etnografiadigital", None)


def test_termo_da_referencia_nao_rouba_termo_da_base(vocab):
    vocab.acrescentar("ref:outro", "coleta", ["Estudo descritivo"])
    assert vocab.reconhecer("Estudo descritivo") == ("pesquisa_descritiva", "objetivos")


# ---------- separar termos ----------

def test_separa_por_ponto_e_virgula_virgula_e_e(vocab_real):
    texto = "Pesquisa qualitativa; estudo de caso, entrevista semiestruturada e análise de conteúdo"
    assert separar_termos(texto, vocab_real) == [
        "Pesquisa qualitativa", "estudo de caso", "entrevista semiestruturada", "análise de conteúdo"]


def test_pedaco_solto_ganha_a_palavra_do_termo_anterior(vocab_real):
    assert separar_termos("Pesquisa bibliográfica e documental", vocab_real) == [
        "Pesquisa bibliográfica", "Pesquisa documental"]
    vocab_real.acrescentar("ref:estudotransversal", "procedimento",
                           ["Estudo transversal", "estudo de corte transversal"])
    assert separar_termos("Estudo descritivo, de corte transversal", vocab_real) == [
        "Estudo descritivo", "Estudo de corte transversal"]


def test_preposicao_volta_para_o_termo_anterior_e_palavra_solta_vira_pesquisa(vocab_real):
    assert separar_termos("Inventário Sociodemográfico e de Saúde", vocab_real) == [
        "Inventário Sociodemográfico e de Saúde"]
    assert separar_termos("Revisão teórica e documental", vocab_real) == ["Revisão teórica", "Pesquisa documental"]


def test_varios_metodos_num_item_so_contam_cada_um(vocab_real):
    vocab_real.acrescentar("ref:estudoobservacional", "procedimento", ["Estudo observacional"])
    vocab_real.acrescentar("ref:estudotransversal", "procedimento", ["Estudo transversal"])
    vocab_real.acrescentar("ref:estudoretrospectivo", "procedimento", ["Estudo retrospectivo"])
    vocab_real.acrescentar("ref:entrevista", "coleta", ["Entrevista"])
    r = resposta("X", "a", "b", [campo("Estudo observacional transversal analítico retrospectivo"),
                                 campo("Análise de dados secundários"),
                                 campo("Entrevista semiestruturada com roteiro")])
    assert set(metodologias_da_resposta(r, vocab_real)) == {
        "ref:estudoobservacional", "ref:estudotransversal", "ref:estudoretrospectivo",
        "dados_secundarios", "entrevista_semiestruturada"}  # sem "ref:entrevista": está dentro da semiestruturada


def test_frase_sem_metodo_nenhum_continua_um_termo_livre(vocab_real):
    r = resposta("X", "a", "b", [campo("plugin SCP")])
    assert metodologias_da_resposta(r, vocab_real) == {"livre:pluginscp": None}


def test_qualificador_depois_da_virgula_nao_vira_metodo(vocab_real):
    assert separar_termos("Análise de conteúdo, proposta por Bardin", vocab_real) == ["Análise de conteúdo"]


def test_metodologias_da_resposta_ignora_nao_informado_e_erro(vocab):
    r = resposta("X", "a", "b", [campo("Pesquisa qualitativa"),
                                 campo("Entrevistas semi-estruturadas", "sem_evidencia"),
                                 campo("Questionário online"),
                                 campo("lixo", "erro")])
    assert metodologias_da_resposta(r, vocab) == {
        "abordagem_qualitativa": "abordagem", "entrevista_semiestruturada": "coleta",
        "livre:questionarioonline": None}
    assert metodologias_da_resposta(resposta("X", "a", "b", [NAO_INFORMADO]), vocab) == {}


# ---------- placar ----------

def test_placar_exemplo_da_divisao_de_tarefas():
    # Referência: qualitativa, estudo de caso, entrevista. IA: qualitativa, entrevista, questionário.
    # P = 2/3 (do que a IA disse, 2 certos), R = 2/3 (da referência, 2 achados), F1 = 2/3.
    p = placar({"qual", "entrev", "quest"}, {"qual", "caso", "entrev"})
    assert (p.precisao, p.revocacao, p.f1) == pytest.approx((2 / 3, 2 / 3, 2 / 3))


def test_placar_com_aceitaveis():
    # Obrigatórios {a, b}, aceitável {c}, IA {a, c, d}.
    # P = |{a, c}| / 3 = 2/3 (c não tira precisão); R = |{a}| / 2 = 1/2 (c não conta).
    # F1 = 2 · (2/3)(1/2) / (2/3 + 1/2) = (2/3) / (7/6) = 4/7.
    p = placar({"a", "c", "d"}, {"a", "b"}, {"c"})
    assert (p.precisao, p.revocacao, p.f1) == pytest.approx((2 / 3, 1 / 2, 4 / 7))


def test_placar_casos_de_borda():
    assert placar(set(), set()).f1 == 1.0                  # "não informado" certo
    vazio = placar(set(), {"a"})
    assert (vazio.precisao, vazio.revocacao, vazio.f1, vazio.esperados) == (0.0, 0.0, 0.0, 1)
    inventou = placar({"a"}, set())
    assert (inventou.precisao, inventou.revocacao, inventou.f1) == (0.0, 1.0, 0.0)
    assert placar({"c"}, set(), {"c"}).f1 == 1.0           # só disse o que era aceitável


def test_medias_macro_e_micro():
    # D1: IA {a, b}, ref {a} → P 1/2, R 1, F1 2/3.  D2: IA {x}, ref {x, y, z} → P 1, R 1/3, F1 1/2.
    # Macro: P (1/2 + 1)/2 = 3/4; R (1 + 1/3)/2 = 2/3; F1 (2/3 + 1/2)/2 = 7/12.
    # Micro: P (1 + 1)/(2 + 1) = 2/3; R (1 + 1)/(1 + 3) = 1/2; F1 = 4/7.
    placares = [placar({"a", "b"}, {"a"}), placar({"x"}, {"x", "y", "z"})]
    assert media_macro(placares) == pytest.approx({"precisao": 3 / 4, "revocacao": 2 / 3, "f1": 7 / 12})
    assert media_micro(placares) == pytest.approx({"precisao": 2 / 3, "revocacao": 1 / 2, "f1": 4 / 7})


def test_placar_por_eixo():
    previstos = {"qual": "abordagem", "entrev": "coleta", "livre:x": None}
    obrigatorios = {"qual": "abordagem", "caso": "procedimento"}
    por_eixo = placar_por_eixo(previstos, obrigatorios, {})
    assert set(por_eixo) == {"abordagem", "coleta", "procedimento"}  # natureza etc.: vazios dos dois lados
    assert por_eixo["abordagem"].f1 == 1.0
    assert (por_eixo["coleta"].precisao, por_eixo["coleta"].revocacao) == (0.0, 1.0)
    assert por_eixo["procedimento"].f1 == 0.0


def test_jaccard():
    assert jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)
    assert jaccard(set(), set()) == 1.0


# ---------- temáticas ----------

def test_similaridade_par_sem_ordem():
    # Direto: cos(idoso, tratamento) = 0 e cos(adesão, envelhecimento) = 0,6 → 0,3.
    # Cruzado: cos(idoso, envelhecimento) = 0,8 e cos(adesão, tratamento) = 1 → 0,9. Fica 0,9.
    s = similaridade_par(("Saúde do idoso", "Adesão ao tratamento"),
                         ("Tratamento", "Envelhecimento e saúde"), codificar_falso)
    assert s == pytest.approx(0.9)


def test_similaridade_par_tematica_vazia_vale_zero():
    # Direto: (cos(idoso, idoso) = 1 + 0) / 2 = 0,5. Cruzado: (0 + 0) / 2 = 0.
    s = similaridade_par(("Saúde do idoso", ""), ("Saúde do idoso", "Tratamento"), codificar_falso)
    assert s == pytest.approx(0.5)
    assert similaridade_par(("", ""), ("", ""), codificar_falso) == 0.0


def test_e5_de_verdade_aproxima_temas_parecidos():
    pytest.importorskip("sentence_transformers")
    codificar = CodificadorE5()
    perto = similaridade_par(("Saúde do idoso com diabetes", "Adesão ao tratamento"),
                             ("Tratamento do diabetes em idosos", "Envelhecimento e saúde"), codificar)
    longe = similaridade_par(("Saúde do idoso com diabetes", "Adesão ao tratamento"),
                             ("Conflitos ambientais em parques", "Direito ao esquecimento"), codificar)
    assert perto > longe


# ---------- indicadores sem gabarito ----------

def test_status_por_campo_e_por_dissertacao(vocab):
    boa = resposta("X1", "a", "b", [campo("Pesquisa qualitativa")])
    sem_ev = resposta("X2", "a", "b", [campo("Estudo de caso", "sem_evidencia")])
    nao_inf = resposta("X3", "a", "b", [NAO_INFORMADO])
    quebrada = {"dissertacao_id": "X4", "tematica_1": campo("", "erro", []),
                "tematica_2": campo("", "erro", []), "metodologias": []}
    assert [status_da_dissertacao(r) for r in (boa, sem_ev, nao_inf, quebrada)] == [
        "ok", "sem_evidencia", "nao_informado", "erro"]
    contagem = contar_status([boa, sem_ev, nao_inf, quebrada])
    # Campos: 3 respostas × 2 temáticas ok = 6, + 1 metodologia ok = 7; 1 sem_evidencia;
    # 1 nao_informado; 2 temáticas com erro.
    assert contagem["por_campo"] == {"ok": 7, "sem_evidencia": 1, "nao_informado": 1, "erro": 2}
    assert contagem["por_dissertacao"] == {"ok": 1, "sem_evidencia": 1, "nao_informado": 1, "erro": 1}


def test_eixos_cobertos(vocab):
    r = resposta("X", "a", "b", [campo("Pesquisa qualitativa"), campo("Entrevista semiestruturada"),
                                 campo("Pesquisa descritiva"), campo("Etnografia digital")])
    # objetivos não está entre os 4 contados; etnografia digital não tem eixo conhecido.
    assert eixos_cobertos(r, vocab) == ["abordagem", "coleta"]


def test_formato_das_metodologias(vocab):
    from src.comparar import formato_das_metodologias
    # 3 itens (o "não informado" não conta): 2, 4 e 7 palavras → média 13/3.
    # Exatos: os 2 primeiros (o parêntese sai). O 3º junta 2 métodos numa frase.
    r = resposta("X", "a", "b", [campo("Estudo descritivo"), campo("Estudo de caso (único)"),
                                 campo("Estudo descritivo com abordagem qualitativa sobre idosos"),
                                 NAO_INFORMADO])
    f = formato_das_metodologias([r], vocab)
    assert f == pytest.approx({"itens": 3, "palavras_por_item": 13 / 3, "itens_exatos": 2 / 3,
                               "itens_com_varios_metodos": 1 / 3})


def test_indicadores_leem_tempo_e_tentativas_do_execucao_json(vocab):
    respostas = [resposta(i, "a", "b", [campo("Pesquisa qualitativa")]) for i in ("X1", "X2", "X3")]
    execucao = {"segundos": {"X1": 10.0, "X2": 20.0, "X3": 30.0}, "tentativas": {"X1": 1, "X2": 1, "X3": 2}}
    ind = indicadores_sem_gabarito(respostas, vocab, execucao)
    assert ind["tempo"] == {"medio_s": 20.0, "mediano_s": 20.0, "max_s": 30.0, "total_s": 60.0, "n": 3}
    assert ind["tentativas"] == {1: 2, 2: 1}
    assert ind["eixos_cobertos_medio"] == 1.0
    assert indicadores_sem_gabarito(respostas, vocab)["tempo"] is None


# ---------- contra a referência ----------

REFERENCIA = {"referencias": [
    {"dissertacao_id": "X001", "tematica_1": "Saúde do idoso", "tematica_2": "Adesão ao tratamento",
     "metodologias": [
         {"termo": "Abordagem qualitativa", "verbete": "abordagem_qualitativa", "eixo": "abordagem", "explicito": True},
         {"termo": "Estudo transversal", "verbete": None, "eixo": "procedimento", "explicito": True,
          "sinonimos": ["estudo de corte transversal"]},
         {"termo": "Entrevista semiestruturada", "verbete": "entrevista_semiestruturada", "eixo": "coleta",
          "explicito": True},
         {"termo": "Análise de conteúdo", "verbete": "analise_de_conteudo", "eixo": "analise", "explicito": False},
     ]},
    {"dissertacao_id": "X002", "tematica_1": "Tratamento", "tematica_2": "Envelhecimento e saúde",
     "metodologias": []},
]}


@pytest.fixture
def referencias(tmp_path, vocab):
    caminho = tmp_path / "referencia.json"
    caminho.write_text(json.dumps(REFERENCIA, ensure_ascii=False), encoding="utf-8")
    return carregar_referencia(caminho, vocab)


def respostas_a() -> list[dict]:
    return [
        # Temáticas trocadas de ordem: par sem ordem, similaridade 1.
        resposta("X001", "Adesão ao tratamento", "Saúde do idoso",
                 [campo("Pesquisa qualitativa"), campo("Estudo de corte transversal"),
                  campo("Análise de conteúdo"), campo("Questionário")]),
        resposta("X002", "Envelhecimento e saúde", "Tratamento", [NAO_INFORMADO]),
        resposta("X999", "fora", "da referência", [campo("Estudo de caso")]),
    ]


def test_carregar_referencia_separa_obrigatorio_de_aceitavel(referencias):
    x1 = referencias["X001"]
    assert set(x1.obrigatorios) == {"abordagem_qualitativa", "ref:estudotransversal", "entrevista_semiestruturada"}
    assert x1.obrigatorios["ref:estudotransversal"] == "procedimento"
    assert x1.aceitaveis == {"analise_de_conteudo": "analise"}
    assert referencias["X002"].obrigatorios == {}


def test_avaliar_contra_referencia(referencias, vocab):
    # X001: IA {qualitativa, transversal, análise de conteúdo (aceitável), questionário (livre)}.
    #   P = 3/4; R = 2/3 (faltou a entrevista); F1 = 2·(3/4)(2/3)/(3/4 + 2/3) = 12/17.
    #   Precisão estrita (aceitável conta como erro) = 2/4.
    # X002: "não informado" e a referência vazia → 1, 1, 1.
    # X999: não está na referência, fica de fora.
    # Macro: P (3/4 + 1)/2 = 7/8; R (2/3 + 1)/2 = 5/6; F1 (12/17 + 1)/2 = 29/34.
    # Micro: P 3/4; R 2/3; F1 12/17.
    av = avaliar_contra_referencia(respostas_a(), referencias, vocab, codificar_falso)
    assert av["dissertacoes"] == 2
    met = av["metodologias"]
    assert met["macro"] == pytest.approx({"precisao": 7 / 8, "revocacao": 5 / 6, "f1": 29 / 34})
    assert met["micro"] == pytest.approx({"precisao": 3 / 4, "revocacao": 2 / 3, "f1": 12 / 17})
    x1 = av["por_dissertacao"][0]
    assert x1["precisao_estrita"] == 0.5
    assert x1["nao_achados"] == ["entrevista_semiestruturada"]
    assert x1["fora_da_referencia"] == ["livre:questionario"]
    # Por eixo (só X001 tem termos): abordagem e procedimento certos, coleta perdida,
    # análise só com o aceitável (P 1, R 1).
    assert met["por_eixo"]["coleta"] == pytest.approx({"precisao": 0.0, "revocacao": 0.0, "f1": 0.0, "n": 1})
    assert met["por_eixo"]["analise"]["f1"] == 1.0
    # Temáticas: as duas respostas acertam o par (1 e 1) → média 1.
    # Linha de base: X001 contra a referência do X002 = 0,9 (direto: 1 e 0,8);
    # X002 contra a do X001 = 0,9 (direto: 0,8 e 1). Média 0,9.
    assert av["tematicas"]["similaridade_media"] == pytest.approx(1.0)
    assert av["tematicas"]["linha_de_base"] == pytest.approx(0.9)
    # Margem = 1 − 0,9. Acerto@1: cada par fica mais perto da própria referência (1 > 0,9) → 2/2.
    assert av["tematicas"]["margem"] == pytest.approx(0.1)
    assert av["tematicas"]["acerto_1"] == 1.0


# ---------- incerteza ----------

def test_intervalo_bootstrap():
    from src.comparar import intervalo_bootstrap
    assert intervalo_bootstrap([0.5] * 5) == [0.5, 0.5]       # sem variação, sem intervalo
    baixo, alto = intervalo_bootstrap([0.0, 1.0] * 10)
    assert 0.0 < baixo < 0.5 < alto < 1.0
    assert intervalo_bootstrap([0.0, 1.0] * 10) == [baixo, alto]  # semente fixa: sai igual


def test_diferenca_pareada():
    from src.comparar import diferenca_pareada
    # Só x, y e z estão nos dois. Diferenças: 1, 0, 0 → média 1/3; ganhou 1, empatou 2.
    d = diferenca_pareada({"x": 1.0, "y": 1.0, "z": 0.0, "so_a": 1.0}, {"x": 0.0, "y": 1.0, "z": 0.0})
    assert (d["n"], d["ganhou"], d["perdeu"], d["empatou"]) == (3, 1, 0, 2)
    assert d["media"] == pytest.approx(1 / 3)
    assert 0.0 <= d["ic95"][0] <= 1 / 3 <= d["ic95"][1] <= 1.0
    assert diferenca_pareada({"x": 1.0}, {"y": 1.0})["media"] is None


def test_diferencas_pareadas_so_quando_muda_uma_coisa():
    from src.comparar import diferencas_pareadas

    def relatorio(nome, modelo, versao, f1s):
        return {"execucao": nome, "modelo": modelo, "tecnica": "hibrido", "versao_prompt": versao,
                "contra_referencia": {"por_dissertacao": [{"dissertacao_id": k, "f1": v} for k, v in f1s.items()]}}
    v1 = relatorio("m__v1", "m", "v1", {"X1": 0.5, "X2": 0.5})
    v2 = relatorio("m__v2", "m", "v2", {"X1": 1.0, "X2": 0.5})
    v10 = relatorio("m__v10", "m", "v10", {"X1": 1.0, "X2": 1.0})
    outro = relatorio("n__v2", "n", "v1", {"X1": 0.0, "X2": 0.0})  # muda o modelo só em relação ao v1
    pares = diferencas_pareadas([v1, v2, v10, outro])
    por_par = {(p["a"], p["b"]): p for p in pares}
    # v2 × v1: +0,25 (1 − 0,5 e 0). O depois fica em A, e v10 vem depois de v2.
    assert por_par[("m__v2", "m__v1")]["f1"]["media"] == pytest.approx(0.25)
    assert ("m__v10", "m__v2") in por_par and ("m__v10", "m__v1") in por_par
    assert por_par[("n__v2", "m__v1")]["muda"] == "modelo"
    assert not any({p["a"], p["b"]} == {"n__v2", "m__v2"} for p in pares)  # muda modelo e prompt


def test_referencia_de_texto_como_resposta_humana(vocab_real):
    ref = referencia_de_texto("X", "t1", "t2", "Pesquisa qualitativa; estudo de caso e entrevistas semi-estruturadas",
                              vocab_real)
    assert set(ref.obrigatorios) == {"abordagem_qualitativa", "estudo_de_caso", "entrevista_semiestruturada"}
    assert referencia_de_texto("X", "t1", "t2", "Não informado no resumo", vocab_real).obrigatorios == {}


# ---------- concordância e comparação ----------

def respostas_b() -> list[dict]:
    return [resposta("X001", "Saúde do idoso", "Tratamento",
                     [campo("Abordagem qualitativa"), campo("Entrevista semiestruturada")]),
            resposta("X002", "Tratamento", "Envelhecimento e saúde", [NAO_INFORMADO])]


def test_concordancia_entre_execucoes(vocab, referencias):
    # X001: A {qualitativa, transversal, conteúdo, questionário} × B {qualitativa, entrevista}
    #   → em comum 1, na união 5 → 1/5. X002: os dois vazios → 1. Média (0,2 + 1)/2 = 0,6.
    # Temáticas X001: A (adesão, idoso) × B (idoso, tratamento): cruzado = (cos(adesão, tratamento) = 1
    #   + cos(idoso, idoso) = 1)/2 = 1. X002: mesmo par trocado → 1. Média 1.
    c = concordancia({"a": respostas_a(), "b": respostas_b()}, vocab, codificar_falso)
    par = c["pares"][0]
    assert (par["a"], par["b"], par["dissertacoes"]) == ("a", "b", 2)  # X999 só existe em a
    assert par["jaccard_metodologias"] == pytest.approx(0.6)
    assert par["similaridade_tematicas"] == pytest.approx(1.0)
    assert c["por_dissertacao"]["X001"]["jaccard"] == pytest.approx(0.2)


def test_comparar_execucoes_grava_relatorios_e_tabela(tmp_path, vocab, referencias):
    sugestoes = tmp_path / "sugestoes" / "calibracao"
    for nome, respostas in (("falso-1b__hibrido__v1", respostas_a()), ("falso-2b__hibrido__v1", respostas_b())):
        (sugestoes / nome).mkdir(parents=True)
        (sugestoes / nome / "respostas.json").write_text(json.dumps(respostas, ensure_ascii=False), encoding="utf-8")
    (sugestoes / "falso-1b__hibrido__v1" / "execucao.json").write_text(
        json.dumps({"modelo": "falso:1b", "tecnica": "hibrido", "versao_prompt": "v1",
                    "segundos": {"X001": 4.0, "X002": 6.0}, "tentativas": {"X001": 1, "X002": 2}}),
        encoding="utf-8")
    saida = tmp_path / "avaliacao"
    linhas = comparar_execucoes(sugestoes, vocab, referencias, codificar_falso, pasta_saida=saida)
    assert [l["execucao"] for l in linhas] == ["falso-1b__hibrido__v1", "falso-2b__hibrido__v1"]
    assert linhas[0]["tempo_medio_s"] == 5.0
    assert linhas[1]["tempo_medio_s"] is None              # sem execucao.json
    assert linhas[0]["met_f1"] == pytest.approx(29 / 34)
    relatorio = json.loads((saida / "falso-1b__hibrido__v1" / "relatorio.json").read_text(encoding="utf-8"))
    assert "segundos" not in relatorio["configuracao"]     # vai para o indicador, não se repete
    comparacao = json.loads((saida / "comparacao.json").read_text(encoding="utf-8"))
    assert comparacao["concordancia"]["pares"][0]["jaccard_metodologias"] == pytest.approx(0.6)
