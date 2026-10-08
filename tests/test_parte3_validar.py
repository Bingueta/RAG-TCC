"""Parte 3: testes da validação (sem Ollama)."""

from src.contratos import Campo, RespostaIA
from src.validar import NAO_INFORMADO, chave_de_comparacao, normalizar_id, validar
from tests.parte3_exemplos import unitarizadas


def resposta(tematica_1, tematica_2, metodologias, did="E001"):
    return RespostaIA(dissertacao_id=did, tematica_1=tematica_1, tematica_2=tematica_2,
                      metodologias=metodologias, modelo="qwen-falso:1b", versao_prompt="v1", tecnica="hibrido")


def ok(texto, *ids):
    return Campo(texto=texto, evidencia=list(ids))


E001 = unitarizadas()["E001"]


def test_resposta_correta_fica_ok():
    r = validar(resposta(ok("Cooperativismo", "F1"), ok("Território", "F2"),
                         [ok("Pesquisa qualitativa", "F3"), ok("Entrevista semiestruturada", "F4")]), E001)
    assert [r.tematica_1.status, r.tematica_2.status] == ["ok", "ok"]
    assert [(m.texto, m.evidencia, m.status) for m in r.metodologias] == [
        ("Pesquisa qualitativa", ["F3"], "ok"), ("Entrevista semiestruturada", ["F4"], "ok")]


def test_frase_inexistente_vira_sem_evidencia_e_mantem_o_texto():
    r = validar(resposta(ok("Cooperativismo", "F1"), ok("Território", "F2"), [ok("Questionário", "F9")]), E001)
    assert (r.metodologias[0].texto, r.metodologias[0].evidencia, r.metodologias[0].status) == (
        "Questionário", [], "sem_evidencia")


def test_codigo_inexistente_sai_mas_o_valido_fica():
    r = validar(resposta(ok("Cooperativismo", "F1", "F9"), ok("Território", "F2"), [ok("Estudo de caso", "F3")]), E001)
    assert (r.tematica_1.evidencia, r.tematica_1.status) == (["F1"], "ok")


def test_sem_evidencia_quando_nao_cita_nada():
    r = validar(resposta(ok("Cooperativismo"), ok("Território", "F2"), [ok("Estudo de caso", "F3")]), E001)
    assert r.tematica_1.status == "sem_evidencia"


def test_frase_que_existe_mas_nao_foi_enviada_ao_modelo_nao_vale():
    # Com RAG o modelo viu só F1, F2 e F3; citar F4 é inventar, mesmo F4 existindo no resumo.
    r = validar(resposta(ok("Cooperativismo", "F1"), ok("Território", "F2"), [ok("Entrevista", "F4")]),
                E001, frases_enviadas={"F1", "F2", "F3"})
    assert r.metodologias[0].status == "sem_evidencia"
    # Sem dizer o que foi enviado, vale qualquer frase da dissertação.
    assert validar(resposta(ok("C", "F1"), ok("T", "F2"), [ok("Entrevista", "F4")]), E001).metodologias[0].status == "ok"


def test_codigos_escritos_de_outro_jeito_sao_aceitos():
    assert [normalizar_id(c) for c in ["F2", "f2", "F 2", "[F2]", "F02", "F2.", "frase", "2"]] == [
        "F2", "F2", "F2", "F2", "F2", "F2", None, None]
    r = validar(resposta(ok("Cooperativismo", "f1", "[F1]"), ok("Território", "F 2"), [ok("Estudo de caso", "F03")]), E001)
    assert (r.tematica_1.evidencia, r.tematica_2.evidencia, r.metodologias[0].evidencia) == (["F1"], ["F2"], ["F3"])


def test_metodologia_repetida_sai_e_junta_as_evidencias():
    r = validar(resposta(ok("C", "F1"), ok("T", "F2"), [
        ok("Entrevista semiestruturada", "F4"), ok("Estudo de caso", "F3"),
        ok("entrevista  SEMIESTRUTURADA.", "F4"), ok("Entrevista Semiestruturada", "F5")]), E001)
    assert [(m.texto, m.evidencia) for m in r.metodologias] == [
        ("Entrevista semiestruturada", ["F4", "F5"]), ("Estudo de caso", ["F3"])]


def test_repetida_sem_evidencia_ganha_a_evidencia_da_outra():
    r = validar(resposta(ok("C", "F1"), ok("T", "F2"), [ok("Estudo de caso"), ok("estudo de caso", "F3")]), E001)
    assert [(m.texto, m.evidencia, m.status) for m in r.metodologias] == [("Estudo de caso", ["F3"], "ok")]


def test_nao_informado_sozinho():
    e003 = unitarizadas()["E003"]
    r = validar(resposta(ok("Acessibilidade", "F1"), ok("Cidadania", "F4"),
                         [ok("não informado no resumo.")], did="E003"), e003)
    assert [(m.texto, m.evidencia, m.status) for m in r.metodologias] == [(NAO_INFORMADO, [], "nao_informado")]


def test_nao_informado_junto_com_metodo_sai():
    r = validar(resposta(ok("C", "F1"), ok("T", "F2"), [ok("Não informado no resumo"), ok("Estudo de caso", "F3")]), E001)
    assert [m.texto for m in r.metodologias] == ["Estudo de caso"]


def test_lista_de_metodologias_vazia_vira_nao_informado():
    r = validar(resposta(ok("C", "F1"), ok("T", "F2"), [ok("  ", "F3")]), E001)
    assert [(m.texto, m.status) for m in r.metodologias] == [(NAO_INFORMADO, "nao_informado")]


def test_tematica_vazia_ou_nao_informada_e_erro():
    r = validar(resposta(ok("  ", "F1"), ok("Não informado no resumo"), [ok("Estudo de caso", "F3")]), E001)
    assert [r.tematica_1.status, r.tematica_2.status] == ["erro", "erro"]
    assert r.metodologias[0].status == "ok"


def test_nao_altera_a_resposta_original():
    original = resposta(ok("C", "F9"), ok("T", "F2"), [ok("Estudo de caso", "F3")])
    validar(original, E001)
    assert (original.tematica_1.evidencia, original.tematica_1.status) == (["F9"], "ok")


def test_chave_de_comparacao():
    assert chave_de_comparacao("  Análise de Conteúdo. ") == chave_de_comparacao("analise de conteudo")
