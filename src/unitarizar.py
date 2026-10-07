"""Parte 1: unitarização, isto é, dividir cada resumo em frases numeradas.

Cada frase é uma unidade de registro (Bardin) e recebe um código (F1, F2…) que a IA cita
como evidência. Nenhuma frase é descartada: num resumo, toda frase pode ser evidência.
"""

import re

import spacy

import config
from src.contratos import Dissertacao, DissertacaoUnitarizada, Frase

_nlp = None


def _modelo():
    """Carrega o spaCy uma vez só (carregar demora cerca de 1 segundo)."""
    global _nlp
    if _nlp is None:
        # Só precisamos do fim de frase: desliga o que não é usado, para ficar mais rápido.
        _nlp = spacy.load(config.MODELO_SPACY, exclude=["ner", "lemmatizer"])
    return _nlp


# Abreviações que terminam em ponto mas não terminam a frase. O spaCy corta errado depois
# de algumas delas, ex.: "Segundo Souza et al. | (2019), …" e "(cf. | Prof. | Silva, 2020)".
# "etc." fica de fora de propósito: muitas vezes ele termina a frase de verdade.
ABREVIACOES = (
    "et al.", "cf.", "Prof.", "Profa.", "Dr.", "Dra.", "Sr.", "Sra.", "p.", "pp.", "n.",
    "v.", "vol.", "ed.", "org.", "orgs.", "coord.", "i.e.", "e.g.", "ex.", "art.", "aprox.",
)


FECHA_ASPAS = "”’»"
FIM_DE_FRASE = re.compile(r"[.!?…][”’»\"')\]]*$")


def _deve_juntar(anterior: str, seguinte: str) -> bool:
    """True se o spaCy cortou no lugar errado e os dois pedaços são a mesma frase."""
    # 1. O anterior termina numa abreviação: "Souza et al. | (2019)".
    if any(anterior.endswith(" " + abrev) or anterior == abrev or anterior.endswith("(" + abrev)
           for abrev in ABREVIACOES):
        return True
    # 2. O anterior não termina como frase: frase termina em ". ! ? …", podendo vir aspas ou
    #    parêntese depois. Pega ":", ";", aspas abertas e cortes como
    #    "…os entrevistados de Pingo | D’Água…" e "cinco temáticas: 1) | …".
    if not FIM_DE_FRASE.search(anterior):
        return True
    if anterior[-1] == '"' and anterior.count('"') % 2 == 1:  # aspas retas ainda abertas
        return True
    # 3. O seguinte é continuação: começa com minúscula, "(", pontuação ou fechando aspas
    #    ('acesso à "cidade formal | " para a população…').
    primeiro = seguinte[0]
    if primeiro.islower() or primeiro in "(),;:" + FECHA_ASPAS:
        return True
    return primeiro == '"' and anterior.count('"') % 2 == 1


def dividir_em_frases(texto: str) -> list[str]:
    """Divide um texto em frases, na ordem, sem descartar nenhuma.

    As frases são recortadas do próprio texto (pela posição), então juntar dois pedaços
    nunca acrescenta nem tira espaço ou letra.
    """
    trechos: list[list[int]] = []  # [início, fim] de cada frase dentro do texto
    for sentenca in _modelo()(texto).sents:
        if not sentenca.text.strip():
            continue
        inicio, fim = sentenca.start_char, sentenca.end_char
        if trechos:
            anterior = texto[trechos[-1][0]:trechos[-1][1]].strip()
            if _deve_juntar(anterior, texto[inicio:fim].strip()):
                trechos[-1][1] = fim
                continue
        trechos.append([inicio, fim])
    return [texto[inicio:fim].strip() for inicio, fim in trechos]


def unitarizar(dissertacao: Dissertacao) -> DissertacaoUnitarizada:
    """Divide o resumo em frases e numera F1, F2… (a numeração recomeça em cada dissertação)."""
    textos = dividir_em_frases(dissertacao.resumo)
    frases = [Frase(id=f"F{numero}", texto=texto) for numero, texto in enumerate(textos, start=1)]
    return DissertacaoUnitarizada(dissertacao=dissertacao, frases=frases)
