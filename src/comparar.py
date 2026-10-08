"""Parte 5: avaliação das respostas da IA.

Agora, sem as respostas da análise manual:
- indicadores sem gabarito de cada execução: status de cada campo, tempo por dissertação
  e quantos eixos de metodologia cada resposta cobre;
- concordância entre execuções (modelos e técnicas) na mesma dissertação;
- comparação com uma referência da calibração: precisão, revocação e F1 nas
  metodologias; similaridade de sentido nas temáticas, como par sem ordem.

Uma execução é uma pasta com o respostas.json: a lista de RespostaIA gravada com
dataclasses.asdict (seção 3.4 de docs/divisao-tarefas.md). As funções trabalham com os
dicionários, não com as classes, para ler também execuções com campos a mais
(tempo_s, tentativas) ou de versões antigas do contrato.

Nada aqui lê a análise manual. Ela só entra depois, por src/importar_respostas.py.

Comando: python -m src.comparar   (detalhes em main)
"""

import argparse
import json
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field
from itertools import combinations
from pathlib import Path
from statistics import mean, median

import numpy as np

import config
from src.contratos import Verbete
from src.indexar import carregar_base

EIXOS = ["natureza", "objetivos", "abordagem", "procedimento", "coleta", "analise"]
# A tarefa 2 da Parte 5 manda contar a cobertura nestes 4. Natureza e objetivos quase
# nunca aparecem num resumo, e contá-los puxaria todas as execuções para baixo igual.
EIXOS_COBERTURA = ["abordagem", "procedimento", "coleta", "analise"]
STATUS = ["ok", "sem_evidencia", "nao_informado", "erro"]


# ---------- Termos de metodologia: separar e reconhecer ----------

def _singular(palavra: str) -> str:
    """Plural regular do português, só o bastante para "entrevistas" = "entrevista".

    Aplicado dos dois lados da comparação (base, referência e resposta), então um
    singular "errado" ("focais" → "focal") não atrapalha: vira o mesmo nos dois.
    """
    if len(palavra) <= 3:
        return palavra
    for fim, troca in (("oes", "ao"), ("aes", "ao"), ("ais", "al"), ("eis", "el")):
        if palavra.endswith(fim):
            return palavra[: -len(fim)] + troca
    return palavra[:-1] if palavra.endswith("s") else palavra


def _palavras_brutas(texto: str) -> list[str]:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z0-9]+", sem_acento.lower())


def chave(texto: str) -> str:
    """Forma de comparar dois termos: sem acento, minúsculas, no singular, sem espaço e hífen.

    Juntar as palavras faz "semi-estruturada", "semi estruturada" e "semiestruturada"
    virarem a mesma chave, que é o caso mais comum de grafia diferente nos resumos.
    """
    return "".join(_singular(p) for p in _palavras_brutas(texto))


_PALAVRAS_VAZIAS = {"de", "da", "do", "das", "dos", "e", "em", "com", "por", "para", "a", "o", "as",
                    "os", "um", "uma", "no", "na", "nos", "nas", "ao", "aos", "meio", "atraves",
                    "sobre", "entre", "que", "seu", "sua"}


def palavras(texto: str) -> frozenset[str]:
    """As palavras que dão sentido ao termo, no singular, sem "de", "com", "por"…"""
    return frozenset(_singular(p) for p in _palavras_brutas(texto) if p not in _PALAVRAS_VAZIAS)


# Expressões que qualificam o termo anterior em vez de nomear outro método:
# "Análise de conteúdo, proposta por Bardin", "Pesquisa-ação segundo Thiollent".
_QUALIFICADORES = ("proposta por", "proposto por", "segundo", "conforme", "de acordo com",
                   "baseada em", "baseado em", "com base em", "na perspectiva de")
_RE_QUALIFICADOR = re.compile(r"\s*,?\s+(?:" + "|".join(_QUALIFICADORES) + r")\b.*$", re.IGNORECASE)
_RE_PARENTESES = re.compile(r"\s*\([^)]*\)")
# "Análise temática de Laurence Bardin": "de" seguido de nome próprio é autor, não método.
_RE_AUTOR = re.compile(r"\s+(?:de|da|do)\s+[A-ZÀ-Ý][\w-]*(?:\s+[A-ZÀ-Ý][\w-]*)*\s*$")
# "Pesquisa de natureza qualitativa", "Estudo de caráter exploratório": palavra de
# enchimento entre o nome e o tipo. Sem ela, vira "Pesquisa qualitativa", que a base tem.
_RE_ENCHIMENTO = re.compile(r"\s+(?:de natureza|de cunho|de car[aá]ter|do tipo|de tipo|com abordagem)\s+",
                            re.IGNORECASE)


def _candidatos(termo: str) -> list[str]:
    """Formas do termo a procurar no vocabulário, da mais fiel para a mais cortada."""
    formas = [termo]
    for corte in (_RE_PARENTESES, _RE_QUALIFICADOR, _RE_AUTOR, _RE_ENCHIMENTO):
        cortado = corte.sub("", formas[-1]).strip(" ,.;")
        if cortado and cortado != formas[-1]:
            formas.append(cortado)
    return formas


class Vocabulario:
    """Liga cada forma de escrever um método a um id canônico e ao eixo dele.

    Começa com a base metodológica (termo + sinônimos). A referência acrescenta os termos
    que não estão na base, com os sinônimos que ela mesma lista. O que não for reconhecido
    vira "livre:<chave>": conta como termo, só não tem eixo conhecido.
    """

    def __init__(self, verbetes: list[Verbete]):
        self._mapa: dict[str, tuple[str, str | None]] = {}
        self._formas: list[tuple[frozenset[str], str, str | None]] = []
        for v in verbetes:
            self.acrescentar(v.id, v.eixo, [v.termo, *v.sinonimos])

    def acrescentar(self, id_: str, eixo: str | None, formas: list[str]) -> None:
        # setdefault: quem chegou primeiro fica. A base entra antes da referência, então
        # um sinônimo da referência nunca rouba um termo da base.
        for forma in formas:
            for candidato in (forma, _RE_PARENTESES.sub("", forma)):
                if chave(candidato) and chave(candidato) not in self._mapa:
                    self._mapa[chave(candidato)] = (id_, eixo)
                    self._formas.append((palavras(candidato), id_, eixo))

    def reconhecer(self, termo: str) -> tuple[str, str | None]:
        """(id canônico, eixo) do termo; eixo None se o termo não está no vocabulário."""
        for candidato in _candidatos(termo):
            if chave(candidato) in self._mapa:
                return self._mapa[chave(candidato)]
        return f"livre:{chave(_candidatos(termo)[-1])}", None

    def conhece(self, termo: str) -> bool:
        return not self.reconhecer(termo)[0].startswith("livre:")

    def contidos(self, termo: str) -> list[tuple[str, str | None]]:
        """Os métodos do vocabulário cujas palavras estão todas dentro do termo.

        Os modelos juntam vários métodos num item só ("Estudo observacional transversal
        analítico retrospectivo") ou descrevem em frase ("Análise de conteúdo das
        entrevistas para categorizar as falas"). A comparação exata não acha nada nesses
        casos e contaria um termo livre só, errado; aqui cada método dito conta.

        Um genérico que só aparece dentro de um mais específico sai: em "Entrevista
        semiestruturada com roteiro", fica a semiestruturada e não "entrevista".
        """
        alvo = palavras(termo)
        achados: dict[str, tuple[frozenset[str], str | None]] = {}
        for forma, id_, eixo in self._formas:
            if forma and forma <= alvo and (id_ not in achados or len(forma) > len(achados[id_][0])):
                achados[id_] = (forma, eixo)
        return [(id_, eixo) for id_, (forma, eixo) in achados.items()
                if not any(forma < outra for outro, (outra, _) in achados.items() if outro != id_)]

    def reconhecer_tudo(self, termo: str) -> list[tuple[str, str | None]]:
        """reconhecer; se não achar, os métodos contidos no termo; se nada, o termo livre."""
        id_, eixo = self.reconhecer(termo)
        if id_.startswith("livre:"):
            return self.contidos(termo) or [(id_, eixo)]
        return [(id_, eixo)]


_RE_SEPARADOR = re.compile(r"(\s*;\s*|\s*,\s*|\s+e\s+)")
_RE_COMECA_QUALIFICANDO = re.compile(r"^(?:" + "|".join(_QUALIFICADORES) + r")\b", re.IGNORECASE)
_RE_COMECA_PREPOSICAO = re.compile(r"^(?:de|da|do|das|dos|para)\s", re.IGNORECASE)


def separar_termos(texto: str, vocabulario: Vocabulario) -> list[str]:
    """Quebra um texto de metodologias em termos, por "; ", "," e " e " (tarefa 4).

    Consertos para o que a quebra cega estraga, na ordem em que são tentados:
    - pedaço que só qualifica o anterior ("proposta por Bardin") é descartado;
    - pedaço que sozinho não é método ganha a primeira palavra do anterior:
      "Pesquisa bibliográfica e documental" → "Pesquisa bibliográfica", "Pesquisa documental";
      "Estudo descritivo, de corte transversal" → "Estudo de corte transversal";
    - pedaço que começa com preposição volta para o anterior: "Inventário
      Sociodemográfico e de Saúde" é um instrumento só;
    - palavra solta que não é método ganha "Pesquisa": em "Revisão teórica e
      documental", o "documental" é a pesquisa documental.
    """
    partes = _RE_SEPARADOR.split(texto.strip())
    termos: list[str] = []
    for i in range(0, len(partes), 2):
        pedaco = partes[i].strip(" .")
        if not pedaco or _RE_COMECA_QUALIFICANDO.match(pedaco):
            continue
        if termos and not vocabulario.conhece(pedaco):
            emendado = f"{termos[-1].split()[0]} {pedaco}"
            if vocabulario.conhece(emendado):
                pedaco = emendado
            elif _RE_COMECA_PREPOSICAO.match(pedaco):
                termos[-1] = f"{termos[-1]}{partes[i - 1]}{pedaco}"
                continue
            elif len(pedaco.split()) == 1 and vocabulario.conhece(f"Pesquisa {pedaco}"):
                pedaco = f"Pesquisa {pedaco}"
        termos.append(pedaco)
    return termos


def _e_nao_informado(campo: dict) -> bool:
    return campo.get("status") == "nao_informado" or chave(campo.get("texto", "")) == chave(
        "Não informado no resumo")


def metodologias_da_resposta(resposta: dict, vocabulario: Vocabulario) -> dict[str, str | None]:
    """{id canônico: eixo} das metodologias que a IA afirmou.

    "Não informado no resumo" e campos com erro não são método: ficam de fora, e a
    resposta pode sair com o conjunto vazio (o certo, quando o resumo não diz o método).
    """
    achados: dict[str, str | None] = {}
    for campo in resposta.get("metodologias") or []:
        if _e_nao_informado(campo) or campo.get("status") == "erro":
            continue
        for termo in separar_termos(campo.get("texto", ""), vocabulario):
            for id_, eixo in vocabulario.reconhecer_tudo(termo):
                achados.setdefault(id_, eixo)
    return achados


# ---------- Precisão, revocação e F1 ----------

@dataclass
class Placar:
    """Precisão, revocação e F1 de uma dissertação, com as contagens para somar depois."""
    precisao: float
    revocacao: float
    f1: float
    acertos_precisao: int    # do que a IA disse, quanto estava na referência (obrigatório ou aceitável)
    previstos: int
    acertos_revocacao: int   # do que a referência exige, quanto a IA achou
    esperados: int


def _f1(p: float, r: float) -> float:
    return 2 * p * r / (p + r) if p + r else 0.0


def placar(previstos: set, obrigatorios: set, aceitaveis: set = frozenset()) -> Placar:
    """P, R e F1 de um conjunto de termos contra a referência.

    obrigatorios: o que o resumo diz e a IA tinha que achar (entra na revocação).
    aceitaveis: interpretação plausível que o resumo não diz. Citar não tira precisão;
    omitir não tira revocação. Sem aceitáveis, é o P/R/F1 comum.

    Casos de borda, escolhidos para não premiar quem não responde:
    - referência vazia e IA vazia ("Não informado no resumo" certo): 1, 1, 1;
    - IA vazia e referência com termos: 0, 0, 0;
    - referência vazia e IA com termos: revocação 1 (não havia o que achar), precisão
      pelo que estava nos aceitáveis.
    """
    validos = obrigatorios | aceitaveis
    acertos_p = len(previstos & validos)
    acertos_r = len(previstos & obrigatorios)
    if not previstos:
        p = r = 1.0 if not obrigatorios else 0.0
        return Placar(p, r, p, 0, 0, 0, len(obrigatorios))
    p = acertos_p / len(previstos)
    r = acertos_r / len(obrigatorios) if obrigatorios else 1.0
    return Placar(p, r, _f1(p, r), acertos_p, len(previstos), acertos_r, len(obrigatorios))


def _no_eixo(termos: dict[str, str | None], eixo: str) -> set:
    return {t for t, e in termos.items() if e == eixo}


def placar_por_eixo(previstos: dict, obrigatorios: dict, aceitaveis: dict) -> dict[str, Placar]:
    """O placar de cada eixo, só com os termos daquele eixo.

    Termo livre da IA (sem eixo conhecido) não entra em eixo nenhum; ele só pesa no
    placar geral. Eixo vazio dos dois lados fica de fora, para não inflar a média com 1.
    """
    saida = {}
    for eixo in EIXOS:
        p, o, a = (_no_eixo(x, eixo) for x in (previstos, obrigatorios, aceitaveis))
        if p or o:
            saida[eixo] = placar(p, o, a)
    return saida


def media_macro(placares: list[Placar]) -> dict[str, float]:
    """Média das dissertações: cada uma pesa igual, tenha 2 ou 10 métodos."""
    if not placares:
        return {"precisao": 0.0, "revocacao": 0.0, "f1": 0.0}
    return {"precisao": mean(p.precisao for p in placares),
            "revocacao": mean(p.revocacao for p in placares),
            "f1": mean(p.f1 for p in placares)}


def media_micro(placares: list[Placar]) -> dict[str, float]:
    """Soma das contagens antes de dividir: cada termo pesa igual.

    Mostra o efeito das dissertações com muitos métodos, que a média macro dilui.
    """
    previstos = sum(p.previstos for p in placares)
    esperados = sum(p.esperados for p in placares)
    pr = sum(p.acertos_precisao for p in placares) / previstos if previstos else 0.0
    rv = sum(p.acertos_revocacao for p in placares) / esperados if esperados else 0.0
    return {"precisao": pr, "revocacao": rv, "f1": _f1(pr, rv)}


def jaccard(a: set, b: set) -> float:
    """Concordância de dois conjuntos de termos: o que os dois têm ÷ o que um ou outro tem."""
    return len(a & b) / len(a | b) if a | b else 1.0


# ---------- Temáticas: similaridade de sentido ----------

class CodificadorE5:
    """Vetores das temáticas com o mesmo modelo de embedding da busca (config.MODELO_EMBEDDING).

    Temática com temática é comparação simétrica, e para isso o e5 pede o prefixo
    "query: " dos dois lados. Guarda os vetores já calculados: a mesma temática se repete
    entre execuções e na linha de base.
    """

    def __init__(self):
        self._cache: dict[str, np.ndarray] = {}

    def __call__(self, textos: list[str]) -> np.ndarray:
        faltam = [t for t in dict.fromkeys(textos) if t not in self._cache]
        if faltam:
            from src.indexar import vetorizar  # carrega o modelo só se for usado
            self._cache.update(zip(faltam, vetorizar(faltam, "query")))
        return np.stack([self._cache[t] for t in textos])


def similaridade_par(par_ia: tuple[str, str], par_ref: tuple[str, str], codificar) -> float:
    """Similaridade entre dois pares de temáticas, sem ordem (tarefa 4 da Parte 5).

    Compara (1 com 1, 2 com 2) e (1 com 2, 2 com 1) e fica com a melhor das duas médias:
    a IA não perde ponto por inverter temática 1 e temática 2. Temática vazia vale 0.

    codificar: função que recebe textos e devolve vetores normalizados (uma linha por
    texto). Nos testes é um codificador falso; no uso real, CodificadorE5.

    Atenção ao ler o número: no e5, até frases sem relação ficam perto de 0,7. O valor
    só diz algo comparado a outra coisa (outra execução, ou a linha de base de
    similaridade_linha_de_base), nunca sozinho.
    """
    a = [t.strip() for t in par_ia]
    b = [t.strip() for t in par_ref]
    textos = [t for t in a + b if t]
    if not textos:
        return 0.0
    vetores = dict(zip(textos, codificar(textos)))

    def cos(x: str, y: str) -> float:
        return float(vetores[x] @ vetores[y]) if x and y else 0.0

    direto = (cos(a[0], b[0]) + cos(a[1], b[1])) / 2
    cruzado = (cos(a[0], b[1]) + cos(a[1], b[0])) / 2
    return max(direto, cruzado)


def tematicas_da_resposta(resposta: dict) -> tuple[str, str]:
    """O par de temáticas; temática com erro conta como vazia."""
    def texto(campo: dict | None) -> str:
        if not campo or campo.get("status") == "erro":
            return ""
        return campo.get("texto", "")
    return texto(resposta.get("tematica_1")), texto(resposta.get("tematica_2"))


# ---------- Referência ----------

@dataclass
class Referencia:
    """O que se espera de uma dissertação: o par de temáticas e os métodos, por id canônico."""
    dissertacao_id: str
    tematicas: tuple[str, str]
    obrigatorios: dict[str, str | None]        # {id: eixo}
    aceitaveis: dict[str, str | None] = field(default_factory=dict)


def carregar_referencia(caminho: str | Path, vocabulario: Vocabulario) -> dict[str, Referencia]:
    """Lê uma referência no formato de data/calibracao/referencia_ia_calibracao.json.

    Os termos fora da base entram no vocabulário com os sinônimos da própria referência,
    e só depois cada termo é reconhecido. Assim o termo da referência e o da IA passam
    pelo mesmo caminho e caem no mesmo id.
    """
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    itens = dados["referencias"] if isinstance(dados, dict) else dados
    for item in itens:
        for m in item["metodologias"]:
            if not m.get("verbete"):
                vocabulario.acrescentar(f"ref:{chave(m['termo'])}", m.get("eixo"),
                                        [m["termo"], *m.get("sinonimos", [])])
    referencias = {}
    for item in itens:
        obrigatorios, aceitaveis = {}, {}
        for m in item["metodologias"]:
            id_, eixo = vocabulario.reconhecer(m["termo"])
            destino = obrigatorios if m.get("explicito", True) else aceitaveis
            destino.setdefault(id_, eixo or m.get("eixo"))
        for id_ in obrigatorios:  # termo que é obrigatório numa linha e aceitável noutra: obrigatório
            aceitaveis.pop(id_, None)
        referencias[item["dissertacao_id"]] = Referencia(
            item["dissertacao_id"], (item["tematica_1"], item["tematica_2"]), obrigatorios, aceitaveis)
    return referencias


def referencia_de_texto(dissertacao_id: str, tematica_1: str, tematica_2: str, metodologias: str,
                        vocabulario: Vocabulario) -> Referencia:
    """Referência a partir de texto livre, como uma RespostaHumana (metodologias numa string).

    É o caminho do gabarito humano e, depois, da análise manual: tudo vira obrigatório,
    porque o analista não marca o que é interpretação.
    """
    termos = {}
    for termo in separar_termos(metodologias, vocabulario):
        if chave(termo) == chave("Não informado no resumo"):
            continue
        for id_, eixo in vocabulario.reconhecer_tudo(termo):
            termos.setdefault(id_, eixo)
    return Referencia(dissertacao_id, (tematica_1, tematica_2), termos)


# ---------- Indicadores de uma execução ----------

def carregar_respostas(pasta: str | Path) -> list[dict]:
    """As respostas de uma execução (pasta com respostas.json)."""
    return json.loads((Path(pasta) / "respostas.json").read_text(encoding="utf-8"))


def campos_da_resposta(resposta: dict) -> list[dict]:
    return [resposta.get("tematica_1") or {}, resposta.get("tematica_2") or {},
            *(resposta.get("metodologias") or [])]


def status_da_dissertacao(resposta: dict) -> str:
    """Um status por dissertação, o pior dos campos.

    erro > sem_evidencia > nao_informado > ok. "nao_informado" não é falha: é a resposta
    certa quando o resumo não diz o método. Fica acima de "ok" só para ser contado à parte.
    """
    vistos = {c.get("status", "ok") for c in campos_da_resposta(resposta)}
    for status in ("erro", "sem_evidencia", "nao_informado"):
        if status in vistos:
            return status
    return "ok"


def contar_status(respostas: list[dict]) -> dict:
    """Quantos campos e quantas dissertações saíram em cada status."""
    por_campo = Counter(c.get("status", "ok") for r in respostas for c in campos_da_resposta(r))
    por_dissertacao = Counter(status_da_dissertacao(r) for r in respostas)
    return {"por_campo": {s: por_campo.get(s, 0) for s in STATUS} | dict(por_campo),
            "por_dissertacao": {s: por_dissertacao.get(s, 0) for s in STATUS} | dict(por_dissertacao)}


def eixos_cobertos(resposta: dict, vocabulario: Vocabulario) -> list[str]:
    """Dos 4 eixos de EIXOS_COBERTURA, quais a resposta cobre.

    É um piso: método fora da base e da referência não tem eixo conhecido e não conta.
    """
    eixos = set(metodologias_da_resposta(resposta, vocabulario).values())
    return [e for e in EIXOS_COBERTURA if e in eixos]


def resumo_tempo(segundos: dict[str, float]) -> dict | None:
    """Tempo de geração por dissertação, de execucao.json["segundos"] (a busca não entra)."""
    tempos = [s for s in segundos.values() if isinstance(s, (int, float))]
    if not tempos:
        return None
    return {"medio_s": mean(tempos), "mediano_s": median(tempos), "max_s": max(tempos),
            "total_s": sum(tempos), "n": len(tempos)}


def formato_das_metodologias(respostas: list[dict], vocabulario: Vocabulario) -> dict:
    """Como os itens de metodologia vêm escritos, independente de estarem certos.

    Cada item vira um pedaço da célula do Excel. "Estudo descritivo" serve; "Estudo
    observacional, descritivo, de corte transversal com abordagem qualitativa" tem o
    conteúdo certo, mas é uma frase. Medido à parte do P/R/F1, porque o reconhecimento por
    conteúdo (Vocabulario.contidos) dá o crédito do conteúdo de qualquer jeito.
    - itens_exatos: o item inteiro é termo(s) que o vocabulário reconhece como estão;
    - itens_com_varios_metodos: o item junta mais de um método.
    """
    itens = [c for r in respostas for c in (r.get("metodologias") or [])
             if not _e_nao_informado(c) and c.get("status") != "erro"]
    if not itens:
        return {"itens": 0, "palavras_por_item": 0.0, "itens_exatos": 0.0, "itens_com_varios_metodos": 0.0}
    termos = [separar_termos(c.get("texto", ""), vocabulario) for c in itens]
    metodos = [sum(len(vocabulario.reconhecer_tudo(t)) for t in ts) for ts in termos]
    return {"itens": len(itens),
            "palavras_por_item": mean(len(c.get("texto", "").split()) for c in itens),
            "itens_exatos": mean(bool(ts) and all(vocabulario.conhece(t) for t in ts) for ts in termos),
            "itens_com_varios_metodos": mean(m > 1 for m in metodos)}


def indicadores_sem_gabarito(respostas: list[dict], vocabulario: Vocabulario,
                             execucao: dict | None = None) -> dict:
    """Tarefa 2 da Parte 5: status, tempo e cobertura de eixos, sem precisar de referência.

    execucao: o execucao.json da mesma pasta. O tempo e as tentativas ficam lá, indexados
    pela dissertação, para o respostas.json continuar exatamente no contrato RespostaIA.
    tentativas: 1 = a primeira saída já era JSON válido; 2 = precisou da repetição.
    """
    execucao = execucao or {}
    cobertura = [eixos_cobertos(r, vocabulario) for r in respostas if status_da_dissertacao(r) != "erro"]
    tentativas = Counter((execucao.get("tentativas") or {}).values())
    n_metodos = [len(metodologias_da_resposta(r, vocabulario)) for r in respostas]
    return {
        "dissertacoes": len(respostas),
        "status": contar_status(respostas),
        "tempo": resumo_tempo(execucao.get("segundos") or {}),
        "tentativas": dict(sorted(tentativas.items())) or None,
        "metodologias_por_resposta": mean(n_metodos) if n_metodos else 0.0,
        "formato_metodologias": formato_das_metodologias(respostas, vocabulario),
        "palavras_por_tematica": mean(len(t.split()) for r in respostas for t in tematicas_da_resposta(r))
                                 if respostas else 0.0,
        "eixos_cobertos_medio": mean(len(c) for c in cobertura) if cobertura else 0.0,
        "respostas_por_eixo": {e: sum(e in c for c in cobertura) for e in EIXOS_COBERTURA},
        "termos_livres": sorted({t for r in respostas for t, e in
                                 metodologias_da_resposta(r, vocabulario).items() if e is None}),
    }


# ---------- Contra a referência ----------

def avaliar_contra_referencia(respostas: list[dict], referencias: dict[str, Referencia],
                              vocabulario: Vocabulario, codificar=None) -> dict:
    """Tarefa 4/5 da Parte 5: cada resposta contra a referência da mesma dissertação.

    Só entram as dissertações que estão na referência. Resposta com erro entra com nota
    zero, porque o Excel também sai com ela vazia.
    codificar=None pula as temáticas (útil sem o modelo de embedding).
    """
    linhas, placares, por_eixo = [], [], {e: [] for e in EIXOS}
    pares_ia, pares_ref = [], []
    for resposta in respostas:
        ref = referencias.get(resposta["dissertacao_id"])
        if ref is None:
            continue
        previstos = metodologias_da_resposta(resposta, vocabulario)
        pl = placar(set(previstos), set(ref.obrigatorios), set(ref.aceitaveis))
        estrito = placar(set(previstos), set(ref.obrigatorios))
        placares.append(pl)
        for eixo, pe in placar_por_eixo(previstos, ref.obrigatorios, ref.aceitaveis).items():
            por_eixo[eixo].append(pe)
        linha = {"dissertacao_id": ref.dissertacao_id, "status": status_da_dissertacao(resposta),
                 **{k: round(v, 4) if isinstance(v, float) else v for k, v in asdict(pl).items()},
                 "precisao_estrita": round(estrito.precisao, 4),
                 "nao_achados": sorted(set(ref.obrigatorios) - set(previstos)),
                 "fora_da_referencia": sorted(set(previstos) - set(ref.obrigatorios) - set(ref.aceitaveis))}
        if codificar is not None:
            par = tematicas_da_resposta(resposta)
            linha["similaridade_tematicas"] = round(similaridade_par(par, ref.tematicas, codificar), 4)
            pares_ia.append(par)
            pares_ref.append(ref.tematicas)
        linhas.append(linha)
    saida = {"dissertacoes": len(linhas),
             "metodologias": {"macro": media_macro(placares), "micro": media_micro(placares),
                              "precisao_estrita_macro": mean(l["precisao_estrita"] for l in linhas) if linhas else 0.0,
                              "por_eixo": {e: media_macro(p) | {"n": len(p)} for e, p in por_eixo.items() if p}},
             "por_dissertacao": linhas}
    if codificar is not None and linhas:
        saida["tematicas"] = {"similaridade_media": mean(l["similaridade_tematicas"] for l in linhas),
                              **acerto_das_tematicas(pares_ia, pares_ref, codificar)}
    f1s = [l["f1"] for l in linhas]
    saida["metodologias"]["f1_ic95"] = intervalo_bootstrap(f1s) if f1s else None
    return saida


def acerto_das_tematicas(pares_ia: list, pares_ref: list, codificar) -> dict:
    """Lê a similaridade das temáticas contra as outras dissertações, não sozinha.

    No e5 tudo fica perto de 0,9, então o número cru não diz se a IA acertou o tema.
    Compara cada resposta com a referência de todas as dissertações:
    - linha_de_base: média da similaridade com as referências das OUTRAS;
    - margem: similaridade com a própria menos a linha de base (quanto ela se destaca);
    - acerto_1: fração das respostas cujo par fica mais perto da própria referência do
      que de qualquer outra (empate não conta). É a leitura mais robusta a diferença de
      estilo, como temática com ou sem o nome do lugar.
    """
    n = len(pares_ia)
    if n < 2:
        return {"linha_de_base": None, "margem": None, "acerto_1": None}
    m = np.array([[similaridade_par(pares_ia[i], pares_ref[j], codificar) for j in range(n)] for i in range(n)])
    outras = ~np.eye(n, dtype=bool)
    linha_de_base = float(m[outras].mean())
    return {"linha_de_base": linha_de_base,
            "margem": float(np.diag(m).mean()) - linha_de_base,
            "acerto_1": float(np.mean([m[i, i] > m[i, outras[i]].max() for i in range(n)]))}


# ---------- Incerteza: só 20 dissertações na calibração ----------

def _reamostrar(valores: list[float], repeticoes: int, semente: int) -> list[float]:
    """Médias de reamostras com reposição (bootstrap), em ordem crescente."""
    sorteio = np.random.default_rng(semente)
    v = np.asarray(valores, dtype=float)
    return sorted(float(v[sorteio.integers(0, len(v), len(v))].mean()) for _ in range(repeticoes))


def intervalo_bootstrap(valores: list[float], repeticoes: int = None, semente: int = None) -> list[float]:
    """IC de 95% da média, por bootstrap: os percentis 2,5 e 97,5 das reamostras.

    Com 20 dissertações, diferença de 0,1 no F1 pode ser só sorte de quais caíram na
    calibração. O intervalo mostra isso; sem ele, qualquer ranking parece firme.
    """
    repeticoes = config.BOOTSTRAP_REPETICOES if repeticoes is None else repeticoes
    semente = config.BOOTSTRAP_SEMENTE if semente is None else semente
    medias = _reamostrar(valores, repeticoes, semente)
    return [medias[int(0.025 * len(medias))], medias[int(0.975 * len(medias)) - 1]]


def diferenca_pareada(a: dict[str, float], b: dict[str, float], repeticoes: int = None,
                      semente: int = None) -> dict:
    """A − B na mesma dissertação (ex.: F1 do v2 menos F1 do v1), com IC de 95%.

    Pareado porque as duas execuções respondem às mesmas dissertações: a dificuldade de
    cada uma se cancela, e o intervalo fica bem mais estreito que o de duas médias soltas.
    Só entram as dissertações que estão nas duas.
    """
    comuns = sorted(set(a) & set(b))
    if not comuns:
        return {"n": 0, "media": None, "ic95": None, "ganhou": 0, "perdeu": 0, "empatou": 0}
    d = [a[k] - b[k] for k in comuns]
    return {"n": len(comuns), "media": mean(d), "ic95": intervalo_bootstrap(d, repeticoes, semente),
            "ganhou": sum(x > 1e-9 for x in d), "perdeu": sum(x < -1e-9 for x in d),
            "empatou": sum(abs(x) <= 1e-9 for x in d)}


# ---------- Concordância entre execuções ----------

def concordancia(execucoes: dict[str, list[dict]], vocabulario: Vocabulario, codificar=None) -> dict:
    """Tarefa 3 da Parte 5: o quanto execuções diferentes concordam na mesma dissertação.

    Para cada par de execuções: Jaccard das metodologias e similaridade das temáticas,
    na média das dissertações que as duas têm. Por dissertação: a média de todos os pares,
    para achar as que mudam muito de um modelo para outro.
    """
    por_id = {nome: {r["dissertacao_id"]: r for r in rs} for nome, rs in execucoes.items()}
    pares, por_dissertacao = [], {}
    for a, b in combinations(sorted(por_id), 2):
        comuns = sorted(set(por_id[a]) & set(por_id[b]))
        jac, sim = [], []
        for d in comuns:
            ra, rb = por_id[a][d], por_id[b][d]
            j = jaccard(set(metodologias_da_resposta(ra, vocabulario)),
                        set(metodologias_da_resposta(rb, vocabulario)))
            jac.append(j)
            por_dissertacao.setdefault(d, {"jaccard": [], "tematicas": []})["jaccard"].append(j)
            if codificar is not None:
                s = similaridade_par(tematicas_da_resposta(ra), tematicas_da_resposta(rb), codificar)
                sim.append(s)
                por_dissertacao[d]["tematicas"].append(s)
        pares.append({"a": a, "b": b, "dissertacoes": len(comuns),
                      "jaccard_metodologias": mean(jac) if jac else None,
                      "similaridade_tematicas": mean(sim) if sim else None})
    return {"pares": pares,
            "por_dissertacao": {d: {k: mean(v) if v else None for k, v in x.items()}
                                for d, x in sorted(por_dissertacao.items())}}


# ---------- Relatório e comando ----------

def carregar_execucao(pasta: str | Path) -> dict:
    """O execucao.json da pasta (modelo, digest, prompt, máquina, segundos, tentativas…); {} se não houver."""
    arquivo = Path(pasta) / "execucao.json"
    return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}


def avaliar_execucao(pasta: str | Path, vocabulario: Vocabulario,
                     referencias: dict[str, Referencia] | None = None, codificar=None) -> dict:
    pasta = Path(pasta)
    respostas = carregar_respostas(pasta)
    execucao = carregar_execucao(pasta)
    primeira = respostas[0] if respostas else {}
    # O execucao.json manda, porque é gravado pela execução; o respostas.json é o reserva.
    meta = {k: execucao.get(k, primeira.get(k)) for k in ("modelo", "tecnica", "versao_prompt")}
    relatorio = {"execucao": pasta.name, **meta,
                 "configuracao": {k: v for k, v in execucao.items() if k not in ("segundos", "tentativas")},
                 "sem_gabarito": indicadores_sem_gabarito(respostas, vocabulario, execucao)}
    if referencias:
        relatorio["contra_referencia"] = avaliar_contra_referencia(respostas, referencias, vocabulario, codificar)
    return relatorio


def encontrar_execucoes(pasta_sugestoes: str | Path) -> list[Path]:
    """Todas as pastas com respostas.json abaixo de pasta_sugestoes, em ordem de nome."""
    return sorted(p.parent for p in Path(pasta_sugestoes).rglob("respostas.json"))


def linha_comparativa(relatorio: dict) -> dict:
    """Uma linha da tabela de comparar_execucoes: os números que importam lado a lado."""
    sg = relatorio["sem_gabarito"]
    campos = sum(v for k, v in sg["status"]["por_campo"].items())
    linha = {"execucao": relatorio["execucao"], "modelo": relatorio.get("modelo"),
             "tecnica": relatorio.get("tecnica"), "versao_prompt": relatorio.get("versao_prompt"),
             "n": sg["dissertacoes"],
             "campos_ok": sg["status"]["por_campo"]["ok"] / campos if campos else 0.0,
             "dissertacoes_com_erro": sg["status"]["por_dissertacao"]["erro"],
             "tempo_medio_s": sg["tempo"]["medio_s"] if sg["tempo"] else None,
             "eixos_cobertos": sg["eixos_cobertos_medio"],
             "itens_exatos": sg["formato_metodologias"]["itens_exatos"],
             "palavras_por_tematica": sg["palavras_por_tematica"]}
    cr = relatorio.get("contra_referencia")
    if cr:
        linha |= {f"met_{k}": v for k, v in cr["metodologias"]["macro"].items()}
        linha["met_precisao_estrita"] = cr["metodologias"]["precisao_estrita_macro"]
        if "tematicas" in cr:
            linha["tem_similaridade"] = cr["tematicas"]["similaridade_media"]
            linha["tem_linha_de_base"] = cr["tematicas"]["linha_de_base"]
            linha["tem_margem"] = cr["tematicas"]["margem"]
            linha["tem_acerto_1"] = cr["tematicas"]["acerto_1"]
    return linha


_ATRIBUTOS = ("modelo", "tecnica", "versao_prompt")


def _ordem_natural(valor) -> list:
    """Chave de ordenação em que "v10" vem depois de "v2" (número compara como número)."""
    return [(0, int(p)) if p.isdigit() else (1, p) for p in re.split(r"(\d+)", str(valor or "")) if p]


def diferencas_pareadas(relatorios: list[dict]) -> list[dict]:
    """A diferença pareada entre execuções que mudam UMA coisa só (modelo, técnica ou prompt).

    Ex.: qwen3.5:9b híbrido v2 × qwen3.5:9b híbrido v1 isola o efeito do prompt. Pares que
    mudam duas coisas ao mesmo tempo ficam de fora: não dá para dizer qual delas fez a
    diferença. Precisa da referência (usa o F1 e a similaridade de cada dissertação).
    """
    com_referencia = [r for r in relatorios if r.get("contra_referencia")]
    saida = []
    for a, b in combinations(com_referencia, 2):
        mudam = [k for k in _ATRIBUTOS if a.get(k) != b.get(k)]
        if len(mudam) != 1:
            continue
        # O "depois" fica em A: versão de prompt maior, ou a ordem de nome.
        if _ordem_natural(b.get(mudam[0])) > _ordem_natural(a.get(mudam[0])):
            a, b = b, a
        linhas_a = {l["dissertacao_id"]: l for l in a["contra_referencia"]["por_dissertacao"]}
        linhas_b = {l["dissertacao_id"]: l for l in b["contra_referencia"]["por_dissertacao"]}
        par = {"a": a["execucao"], "b": b["execucao"], "muda": mudam[0],
               "f1": diferenca_pareada({k: l["f1"] for k, l in linhas_a.items()},
                                       {k: l["f1"] for k, l in linhas_b.items()})}
        if all("similaridade_tematicas" in l for l in (*linhas_a.values(), *linhas_b.values())):
            par["similaridade_tematicas"] = diferenca_pareada(
                {k: l["similaridade_tematicas"] for k, l in linhas_a.items()},
                {k: l["similaridade_tematicas"] for k, l in linhas_b.items()})
        saida.append(par)
    return saida


def comparar_execucoes(pasta_sugestoes: str | Path, vocabulario: Vocabulario,
                       referencias: dict[str, Referencia] | None = None, codificar=None,
                       pasta_saida: str | Path | None = None) -> list[dict]:
    """Avalia todas as execuções e devolve a tabela, uma linha por execução.

    Com pasta_saida, grava o relatorio.json de cada execução e o comparacao.json
    (fora do git: data/avaliacao/ está no .gitignore).
    """
    pasta_sugestoes = Path(pasta_sugestoes)
    execucoes, linhas, relatorios = {}, [], []
    for pasta in encontrar_execucoes(pasta_sugestoes):
        relatorio = avaliar_execucao(pasta, vocabulario, referencias, codificar)
        execucoes[pasta.name] = carregar_respostas(pasta)
        linhas.append(linha_comparativa(relatorio))
        relatorios.append(relatorio)
        if pasta_saida is not None:
            destino = Path(pasta_saida) / pasta.relative_to(pasta_sugestoes)
            destino.mkdir(parents=True, exist_ok=True)
            (destino / "relatorio.json").write_text(
                json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    if pasta_saida is not None:
        comparacao = {"execucoes": linhas,
                      "diferencas_pareadas": diferencas_pareadas(relatorios),
                      "concordancia": concordancia(execucoes, vocabulario, codificar) if len(execucoes) > 1 else None}
        Path(pasta_saida).mkdir(parents=True, exist_ok=True)
        (Path(pasta_saida) / "comparacao.json").write_text(
            json.dumps(comparacao, ensure_ascii=False, indent=2), encoding="utf-8")
    return linhas


def tabela_markdown(linhas: list[dict]) -> str:
    if not linhas:
        return "(nenhuma execução encontrada)"
    colunas = list(dict.fromkeys(k for l in linhas for k in l))

    def fmt(v) -> str:
        return f"{v:.3f}" if isinstance(v, float) else ("" if v is None else str(v))
    return "\n".join(["| " + " | ".join(colunas) + " |", "|" + "---|" * len(colunas),
                      *("| " + " | ".join(fmt(l.get(c)) for c in colunas) + " |" for l in linhas)])


def main() -> None:
    """Comando: python -m src.comparar [--sugestoes PASTA] [--referencia ARQUIVO] [--sem-embedding]

    Avalia todas as execuções abaixo de --sugestoes, grava os relatórios em
    data/avaliacao/ (fora do git) e mostra a tabela comparativa.
    """
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--sugestoes", default=str(config.PASTA_SUGESTOES_CALIBRACAO))
    parser.add_argument("--referencia", default=str(config.CAMINHO_REFERENCIA_IA_CALIBRACAO),
                        help="referência da calibração; 'nenhuma' para só os indicadores sem gabarito")
    parser.add_argument("--sem-embedding", action="store_true",
                        help="não carrega o e5: pula as temáticas")
    args = parser.parse_args()

    vocabulario = Vocabulario(carregar_base(config.CAMINHO_BASE))
    referencias = None
    if args.referencia != "nenhuma" and Path(args.referencia).exists():
        referencias = carregar_referencia(args.referencia, vocabulario)
    codificar = None if args.sem_embedding else CodificadorE5()
    saida = config.PASTA_AVALIACAO / Path(args.sugestoes).name
    linhas = comparar_execucoes(args.sugestoes, vocabulario, referencias, codificar, pasta_saida=saida)
    print(tabela_markdown(linhas))
    pares = json.loads((saida / "comparacao.json").read_text(encoding="utf-8"))["diferencas_pareadas"]
    if pares:
        print("\nDiferença pareada de F1 (A − B; só pares que mudam uma coisa):")
        print(tabela_markdown([{"muda": p["muda"], "a": p["a"], "b": p["b"], "f1_media": p["f1"]["media"],
                                "ic95": "[{:+.3f}, {:+.3f}]".format(*p["f1"]["ic95"]),
                                "ganhou/perdeu/empatou": f'{p["f1"]["ganhou"]}/{p["f1"]["perdeu"]}/{p["f1"]["empatou"]}'}
                               for p in pares if p["muda"] != "modelo"]))


if __name__ == "__main__":
    main()
