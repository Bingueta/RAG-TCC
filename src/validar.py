"""Parte 3: validação da resposta do modelo contra as frases da própria dissertação.

A função principal é validar(resposta, dissertacao), que devolve uma RespostaIA nova com
o status de cada campo calculado aqui, nunca pelo modelo. Regras:

- Evidência: todo código citado (F1, F2…) tem que existir no resumo. Código inexistente é
  descartado; se não sobrar nenhum, o campo fica "sem_evidencia" (o texto é mantido, para
  quem for conferir ver o que o modelo disse). Citar uma frase que não existe prova que o
  modelo inventou, e é por isso que a resposta não pode aparecer como certa.
- Metodologia repetida sai (comparando sem acento, maiúsculas e espaços), e as evidências
  das repetidas se juntam na que ficou.
- "Não informado no resumo" vira status "nao_informado", e só vale sozinho: se o modelo
  listou métodos e também disse "não informado", o "não informado" sai.
- Temática vazia vira status "erro": o formulário exige duas temáticas, e todo resumo tem
  um tema. "Não informado" não se aplica a temática.
"""

import re
import unicodedata
from dataclasses import replace

from src.contratos import Campo, DissertacaoUnitarizada, RespostaIA

NAO_INFORMADO = "Não informado no resumo"


def normalizar_id(codigo) -> str | None:
    """Código de frase no formato do contrato ("F2"), ou None se não parecer um.

    Aceita as variações que modelos pequenos escrevem: "f2", "F 2", "[F2]", "F02", "F2.".
    """
    achado = re.search(r"[Ff]\s*0*(\d+)", str(codigo))
    return f"F{achado.group(1)}" if achado else None


def chave_de_comparacao(texto: str) -> str:
    """Texto sem acento, em minúsculas, com espaços simples e sem pontuação nas pontas.

    "Entrevistas  Semiestruturadas." e "entrevistas semiestruturadas" viram a mesma chave.
    """
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                         if unicodedata.category(c) != "Mn")
    return " ".join(sem_acento.split()).strip(" .;:,-")


def _nao_informado(texto: str) -> bool:
    return chave_de_comparacao(texto).startswith("nao informad")


def _ids_validos(evidencia: list[str], validos: set[str]) -> list[str]:
    """Os códigos citados que existem, na ordem e sem repetir."""
    ids = []
    for codigo in evidencia:
        normalizado = normalizar_id(codigo)
        if normalizado in validos and normalizado not in ids:
            ids.append(normalizado)
    return ids


def _conferir(campo: Campo, validos: set[str]) -> Campo:
    if campo.status == "erro":
        return replace(campo, evidencia=list(campo.evidencia))
    texto = campo.texto.strip()
    if _nao_informado(texto):
        return Campo(texto=NAO_INFORMADO, evidencia=[], status="nao_informado")
    ids = _ids_validos(campo.evidencia, validos)
    return Campo(texto=texto, evidencia=ids, status="ok" if ids else "sem_evidencia")


def _tematica(campo: Campo, validos: set[str]) -> Campo:
    if campo.status != "erro" and (not campo.texto.strip() or _nao_informado(campo.texto)):
        return Campo(texto=campo.texto.strip(), evidencia=[], status="erro")
    return _conferir(campo, validos)


def _metodologias(campos: list[Campo], validos: set[str]) -> list[Campo]:
    if any(c.status == "erro" for c in campos):
        return [replace(c, evidencia=list(c.evidencia)) for c in campos]
    unicas: dict[str, Campo] = {}
    for campo in campos:
        conferido = _conferir(campo, validos)
        if not conferido.texto:
            continue
        chave = chave_de_comparacao(conferido.texto)
        if chave not in unicas:
            unicas[chave] = conferido
            continue
        # Repetida: junta as evidências na primeira, que fica com o nome que apareceu antes.
        primeira = unicas[chave]
        primeira.evidencia += [i for i in conferido.evidencia if i not in primeira.evidencia]
        if primeira.status == "sem_evidencia" and primeira.evidencia:
            primeira.status = "ok"
    informadas = [c for c in unicas.values() if c.status != "nao_informado"]
    return informadas or [Campo(texto=NAO_INFORMADO, evidencia=[], status="nao_informado")]


def validar(resposta: RespostaIA, dissertacao: DissertacaoUnitarizada,
            frases_enviadas: set[str] | None = None) -> RespostaIA:
    """Confere a resposta contra as frases da dissertação e recalcula os status.

    frases_enviadas (opcional): os códigos que o modelo viu no prompt. Com RAG, o modelo vê
    só algumas frases; citar uma que não foi mostrada também é inventar, mesmo que ela
    exista no resumo. Sem esse argumento, vale qualquer frase da dissertação.
    """
    validos = {f.id for f in dissertacao.frases}
    if frases_enviadas is not None:
        validos &= set(frases_enviadas)
    return replace(
        resposta,
        tematica_1=_tematica(resposta.tematica_1, validos),
        tematica_2=_tematica(resposta.tematica_2, validos),
        metodologias=_metodologias(resposta.metodologias, validos),
    )
