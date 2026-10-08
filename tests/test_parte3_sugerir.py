"""Parte 3: testes do prompt e da geração, com um Ollama falso (sem modelo nenhum)."""

import pytest

import config
from src import sugerir
from src.contratos import Contexto, TrechoRecuperado
from src.sugerir import (ESQUEMA_RESPOSTA, OllamaIndisponivel, SaidaInvalida, VersaoDesconhecida, gerar_resposta,
                         interpretar_saida, montar_prompt, verificar_ollama)
from tests.parte3_exemplos import OllamaFalso, contextos, saida, unitarizadas

MODELO = "qwen-falso:1b"


@pytest.fixture(autouse=True)
def esquecer_modelos():
    sugerir._pensa.clear()


def sem_rag(unitarizada):
    todas = [TrechoRecuperado(frase_id=f.id, texto=f.texto, score=1.0) for f in unitarizada.frases]
    return Contexto(dissertacao_id=unitarizada.dissertacao.id, tecnica="sem_rag",
                    frases_tematicas=list(todas), frases_metodologia=list(todas), verbetes=[])


# ---------- montar_prompt ----------

def test_prompt_tem_titulo_palavras_chave_frases_e_verbetes():
    u, c = unitarizadas()["E001"], contextos()["E001"]
    prompt = montar_prompt(u, c, "v1")
    assert u.dissertacao.titulo in prompt
    assert "Cooperativismo; Território; Gênero; Agricultura familiar" in prompt
    for trecho in c.frases_tematicas + c.frases_metodologia:
        assert f"[{trecho.frase_id}] {trecho.texto}" in prompt
    assert "Estudo de caso (procedimento):" in prompt
    assert "$" not in prompt  # nenhum marcador do modelo de prompt ficou sem preencher


def test_prompt_mostra_as_frases_na_ordem_do_resumo():
    prompt = montar_prompt(unitarizadas()["E001"], contextos()["E001"], "v1")
    # frases_tematicas veio como F2, F1, F6 (ordem do score)
    assert prompt.index("[F1]") < prompt.index("[F2]") < prompt.index("[F6]")


def test_sem_rag_mostra_o_resumo_uma_vez_so_e_sem_verbetes():
    u = unitarizadas()["E002"]
    prompt = montar_prompt(u, sem_rag(u), "v1")
    for frase in u.frases:
        assert prompt.count(f"[{frase.id}] {frase.texto}") == 1
    assert "FRASES DO RESUMO\n" in prompt
    assert "VERBETES" not in prompt


def test_com_rag_separa_tema_e_metodo():
    prompt = montar_prompt(unitarizadas()["E001"], contextos()["E001"], "v1")
    assert "FALAM DO TEMA" in prompt and "FALAM DO MÉTODO" in prompt


def test_titulos_parecidos_entram_quando_existem():
    u, c = unitarizadas()["E001"], contextos()["E001"]
    assert "PARECIDAS" not in montar_prompt(u, c, "v1")
    c.titulos_parecidos = ["Outra dissertação sobre cooperativas"]
    assert "- Outra dissertação sobre cooperativas" in montar_prompt(u, c, "v1")


def test_versao_desconhecida_e_erro_claro():
    with pytest.raises(VersaoDesconhecida, match="prompt 'v999' não existe"):
        montar_prompt(unitarizadas()["E001"], contextos()["E001"], "v999")


def test_versao_padrao_vem_do_config():
    u, c = unitarizadas()["E001"], contextos()["E001"]
    assert montar_prompt(u, c) == montar_prompt(u, c, config.VERSAO_PROMPT)


# ---------- interpretar_saida ----------

def test_le_a_saida_correta():
    t1, t2, metodologias = interpretar_saida(saida("correta.json"))
    assert (t1.texto, t1.evidencia) == ("Mulheres agricultoras no cooperativismo rural", ["F1"])
    assert [m.texto for m in metodologias] == [
        "Pesquisa qualitativa", "Estudo de caso", "Entrevista semiestruturada", "Análise de conteúdo"]


def test_tolera_cerca_de_codigo_e_texto_em_volta():
    t1, _, _ = interpretar_saida("Claro! Aqui está:\n```json\n" + saida("correta.json") + "\n```\nEspero ter ajudado.")
    assert t1.evidencia == ["F1"]


def test_tolera_evidencia_como_texto_e_campo_como_texto():
    t1, t2, metodologias = interpretar_saida(
        '{"tematica_1": {"texto": "A", "evidencia": "F1"}, "tematica_2": "B", "metodologias": {"texto": "C", "evidencia": []}}')
    assert (t1.evidencia, t2.texto, t2.evidencia, len(metodologias)) == (["F1"], "B", [], 1)


@pytest.mark.parametrize("texto, motivo", [
    (saida("json_quebrado.txt"), "JSON quebrado"),
    (saida("vazia.txt"), "resposta vazia"),
    ("não sei responder", "não há JSON"),
    ('{"tematica_1": {"texto": "A", "evidencia": []}}', "faltam os campos: tematica_2, metodologias"),
])
def test_saidas_ruins_levantam_saida_invalida(texto, motivo):
    with pytest.raises(SaidaInvalida, match=motivo):
        interpretar_saida(texto)


# ---------- gerar_resposta ----------

def test_gera_resposta_valida_e_manda_os_parametros_combinados():
    ollama = OllamaFalso(saida("correta.json"))
    r = gerar_resposta(unitarizadas()["E001"], contextos()["E001"], MODELO, "v1", cliente=ollama)
    assert (r.dissertacao_id, r.modelo, r.versao_prompt, r.tecnica) == ("E001", MODELO, "v1", "hibrido")
    assert [r.tematica_1.status, r.tematica_2.status] + [m.status for m in r.metodologias] == ["ok"] * 6
    assert r.saida_bruta == saida("correta.json")
    pedido = ollama.pedidos[0]
    assert pedido["model"] == MODELO
    assert pedido["format"] == ESQUEMA_RESPOSTA
    assert pedido["options"] == {"temperature": config.TEMPERATURA, "seed": config.SEED, "num_ctx": config.NUM_CTX}
    assert "think" not in pedido  # modelo sem modo de pensar: o parâmetro nem vai


def test_esquema_forca_so_o_codigo_da_frase_na_evidencia():
    item = ESQUEMA_RESPOSTA["properties"]["tematica_1"]["properties"]["evidencia"]["items"]
    assert item["pattern"] == "^F[0-9]{1,3}$"
    assert ESQUEMA_RESPOSTA["properties"]["metodologias"]["items"]["properties"]["evidencia"]["items"] == item


def test_modelo_que_pensa_recebe_think_desligado():
    ollama = OllamaFalso(saida("correta.json"), pensa=True)
    gerar_resposta(unitarizadas()["E001"], contextos()["E001"], MODELO, "v1", cliente=ollama)
    assert ollama.pedidos[0]["think"] is config.PENSAR is False


def test_json_quebrado_tenta_de_novo_mandando_o_erro():
    ollama = OllamaFalso(saida("json_quebrado.txt"), saida("correta.json"))
    r = gerar_resposta(unitarizadas()["E001"], contextos()["E001"], MODELO, "v1", cliente=ollama)
    assert r.tematica_1.status == "ok"
    segunda = ollama.pedidos[1]["messages"]
    assert segunda[1] == {"role": "assistant", "content": saida("json_quebrado.txt")}
    assert "JSON quebrado" in segunda[2]["content"]
    assert saida("json_quebrado.txt") in r.saida_bruta and "nova tentativa" in r.saida_bruta


def test_json_quebrado_duas_vezes_vira_erro_sem_travar():
    ollama = OllamaFalso(saida("json_quebrado.txt"), saida("json_quebrado.txt"))
    r = gerar_resposta(unitarizadas()["E001"], contextos()["E001"], MODELO, "v1", cliente=ollama)
    assert len(ollama.pedidos) == config.TENTATIVAS
    assert [r.tematica_1.status, r.tematica_2.status, r.metodologias[0].status] == ["erro"] * 3
    assert "não lida: JSON quebrado" in r.saida_bruta


def test_resposta_vazia_vira_erro():
    r = gerar_resposta(unitarizadas()["E001"], contextos()["E001"], MODELO, "v1",
                       cliente=OllamaFalso(saida("vazia.txt"), saida("vazia.txt")))
    assert r.tematica_1.status == "erro" and "resposta vazia" in r.saida_bruta


def test_frase_inexistente_vira_sem_evidencia():
    r = gerar_resposta(unitarizadas()["E001"], contextos()["E001"], MODELO, "v1",
                       cliente=OllamaFalso(saida("frase_inexistente.json")))
    questionario = [m for m in r.metodologias if m.texto == "Questionário"][0]
    assert (questionario.evidencia, questionario.status) == ([], "sem_evidencia")


def test_frase_nao_enviada_ao_modelo_vira_sem_evidencia():
    # Tira F4 do contexto: o modelo não viu F4, então citá-la é inventar, mesmo existindo no resumo.
    c = contextos()["E001"]
    c.frases_metodologia = [t for t in c.frases_metodologia if t.frase_id != "F4"]
    r = gerar_resposta(unitarizadas()["E001"], c, MODELO, "v1", cliente=OllamaFalso(saida("correta.json")))
    entrevista = [m for m in r.metodologias if m.texto == "Entrevista semiestruturada"][0]
    assert entrevista.status == "sem_evidencia"


def test_nao_informado():
    r = gerar_resposta(unitarizadas()["E003"], contextos()["E003"], MODELO, "v1",
                       cliente=OllamaFalso(saida("nao_informado.json")))
    assert [(m.texto, m.status) for m in r.metodologias] == [("Não informado no resumo", "nao_informado")]


def test_ollama_fora_do_ar_vira_erro_sem_travar():
    r = gerar_resposta(unitarizadas()["E001"], contextos()["E001"], MODELO, "v1",
                       cliente=OllamaFalso(ConnectionError("recusada")))
    assert r.tematica_1.status == "erro"
    assert "ConnectionError: recusada" in r.saida_bruta


def test_versao_inexistente_vira_erro_sem_travar():
    r = gerar_resposta(unitarizadas()["E001"], contextos()["E001"], MODELO, "v999", cliente=OllamaFalso())
    assert r.tematica_1.status == "erro" and "VersaoDesconhecida" in r.saida_bruta


# ---------- verificar_ollama ----------

def test_verificar_ollama():
    verificar_ollama(MODELO, cliente=OllamaFalso())
    with pytest.raises(OllamaIndisponivel, match="ollama pull outro:7b"):
        verificar_ollama("outro:7b", cliente=OllamaFalso())


def test_verificar_ollama_fora_do_ar():
    class Desligado:
        def list(self):
            raise ConnectionError("recusada")

    with pytest.raises(OllamaIndisponivel, match="Abra o aplicativo Ollama"):
        verificar_ollama(MODELO, cliente=Desligado())
