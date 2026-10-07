"""Parte 2: base de conhecimento (metodologias) e índice de vetores.

- carregar_base: lê o data/base_metodologia.json, confere os campos e devolve a lista
  de Verbete.
- vetorizar: transforma textos em vetores (embeddings) com o multilingual-e5.
- construir_indice / Indice: guardam e carregam os vetores de todas as frases e verbetes
  (data/indices/, fora do git). Comando: python -m src.indexar

Formato da base na seção 3.3 de docs/divisao-tarefas.md.
"""

import json
from pathlib import Path

import numpy as np

import config
from src.contratos import Verbete

_modelo = None


def _modelo_embedding():
    """Carrega o modelo de embedding uma vez só (a primeira carga baixa ~1 GB e demora)."""
    global _modelo
    if _modelo is None:
        from sentence_transformers import SentenceTransformer  # importa só quando precisa

        _modelo = SentenceTransformer(config.MODELO_EMBEDDING, device=config.DISPOSITIVO_EMBEDDING)
    return _modelo


def vetorizar(textos: list[str], tipo: str) -> np.ndarray:
    """Transforma textos em vetores normalizados (tamanho 1), um por linha.

    O e5 exige um prefixo: tipo="query" para o que se procura (a consulta) e
    tipo="passage" para os textos onde se procura (frases e verbetes). Com vetores
    normalizados, o produto de dois vetores é a similaridade de cosseno (de -1 a 1).
    """
    if tipo not in ("query", "passage"):
        raise ValueError("tipo tem que ser 'query' ou 'passage'")
    if not textos:
        return np.zeros((0, 0), dtype=np.float32)
    com_prefixo = [f"{tipo}: {texto}" for texto in textos]
    return _modelo_embedding().encode(com_prefixo, normalize_embeddings=True, convert_to_numpy=True)


def texto_do_verbete(verbete: Verbete) -> str:
    """O texto que representa o verbete na busca por sentido: o termo e seus sinônimos.

    Testado na calibração (20 dissertações de 2022): com termo + sinônimos, 20 de 26 termos
    citados literalmente nas frases de método ficaram entre os 5 verbetes escolhidos; com
    termo + definição + sinais, só 16. A definição longa deixava o vetor genérico demais.
    """
    return "; ".join([verbete.termo, *verbete.sinonimos])

EIXOS = ("natureza", "objetivos", "abordagem", "procedimento", "coleta", "analise")
CAMPOS = ("id", "termo", "eixo", "definicao", "sinais", "sinonimos")


class ErroBase(ValueError):
    """A base metodológica tem algum problema. A mensagem lista todos, um por linha."""


def _problemas_do_verbete(item, posicao: int) -> list[str]:
    if not isinstance(item, dict):
        return [f"verbete {posicao}: não é um objeto JSON"]
    nome = item.get("id") or f"verbete {posicao}"
    problemas = [f"{nome}: falta o campo '{campo}'" for campo in CAMPOS if campo not in item]
    problemas += [f"{nome}: campo desconhecido '{campo}'" for campo in item if campo not in CAMPOS]
    for campo in ("id", "termo", "definicao"):
        if campo in item and not (isinstance(item[campo], str) and item[campo].strip()):
            problemas.append(f"{nome}: '{campo}' vazio ou não é texto")
    if "eixo" in item and item["eixo"] not in EIXOS:
        problemas.append(f"{nome}: eixo '{item['eixo']}' não existe (use um de: {', '.join(EIXOS)})")
    for campo in ("sinais", "sinonimos"):
        if campo in item:
            valor = item[campo]
            if not isinstance(valor, list) or not all(isinstance(t, str) and t.strip() for t in valor):
                problemas.append(f"{nome}: '{campo}' tem que ser uma lista de textos")
    return problemas


def carregar_base(caminho: str | Path) -> list[Verbete]:
    """Lê a base metodológica, confere os campos e devolve um Verbete para cada item.

    Se houver qualquer problema, levanta ErroBase com todos eles.
    """
    with open(caminho, encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    if not isinstance(dados, list):
        raise ErroBase(f"{caminho}: a base tem que ser uma lista de verbetes")

    problemas = []
    for posicao, item in enumerate(dados, start=1):
        problemas.extend(_problemas_do_verbete(item, posicao))
    ids = [item.get("id") for item in dados if isinstance(item, dict)]
    for id_repetido in sorted({i for i in ids if i and ids.count(i) > 1}):
        problemas.append(f"{id_repetido}: id repetido ({ids.count(id_repetido)} vezes)")

    if problemas:
        raise ErroBase(f"{caminho} tem {len(problemas)} problema(s):\n" + "\n".join(problemas))
    return [Verbete(**item) for item in dados]


# ---------- Índice: os vetores de todas as frases e verbetes, guardados em disco ----------

class IndiceDesatualizado(RuntimeError):
    """O índice foi feito com outro modelo de embedding: rode python -m src.indexar de novo."""


def chave_da_frase(dissertacao_id: str, frase_id: str) -> str:
    return f"{dissertacao_id}#{frase_id}"  # ex.: "D001#F3"


def construir_indice(corpus, verbetes: list[Verbete], pasta: str | Path = None) -> None:
    """Calcula os vetores de todas as frases do corpus e de todos os verbetes e salva em disco.

    corpus: list[DissertacaoUnitarizada]. Arquivos gravados na pasta (fora do git):
    frases.npy + frases.json (chaves "D001#F3"), verbetes.npy + verbetes.json (id e texto
    de cada verbete) e info.json (modelo usado e quantidades).
    """
    pasta = Path(pasta or config.PASTA_INDICES)
    pasta.mkdir(parents=True, exist_ok=True)
    chaves = [chave_da_frase(u.dissertacao.id, f.id) for u in corpus for f in u.frases]
    textos = [f.texto for u in corpus for f in u.frases]
    np.save(pasta / "frases.npy", vetorizar(textos, "passage"))
    (pasta / "frases.json").write_text(json.dumps(chaves), encoding="utf-8")
    np.save(pasta / "verbetes.npy", vetorizar([texto_do_verbete(v) for v in verbetes], "passage"))
    textos_verbetes = {v.id: texto_do_verbete(v) for v in verbetes}
    (pasta / "verbetes.json").write_text(json.dumps(textos_verbetes, ensure_ascii=False), encoding="utf-8")
    info = {"modelo": config.MODELO_EMBEDDING, "frases": len(chaves), "verbetes": len(verbetes)}
    (pasta / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


class Indice:
    """Vetores carregados do disco, procurados pela chave da frase ou pelo id do verbete."""

    def __init__(self, pasta: str | Path = None):
        pasta = Path(pasta or config.PASTA_INDICES)
        info = json.loads((pasta / "info.json").read_text(encoding="utf-8"))
        if info["modelo"] != config.MODELO_EMBEDDING:
            raise IndiceDesatualizado(
                f"o índice foi feito com {info['modelo']}, mas o config.py pede "
                f"{config.MODELO_EMBEDDING}: rode python -m src.indexar")
        frases = np.load(pasta / "frases.npy")
        chaves = json.loads((pasta / "frases.json").read_text(encoding="utf-8"))
        self.frases = dict(zip(chaves, frases))
        verbetes = np.load(pasta / "verbetes.npy")
        textos = json.loads((pasta / "verbetes.json").read_text(encoding="utf-8"))
        self.verbetes = dict(zip(textos, verbetes))  # id → vetor
        self.textos_verbetes = textos                # id → texto usado no vetor

    def vetor_do_verbete(self, verbete: Verbete):
        """Vetor guardado, só se foi feito com o texto atual do verbete; senão, None."""
        if self.textos_verbetes.get(verbete.id) == texto_do_verbete(verbete):
            return self.verbetes[verbete.id]
        return None


def main() -> None:
    """Comando: python -m src.indexar

    Gera o índice das frases das 59 dissertações e da calibração e dos verbetes da base.
    Rode de novo sempre que o corpus, a base ou o modelo de embedding mudarem.
    """
    from src.preparar_dados import carregar_corpus
    from src.unitarizar import unitarizar

    corpus = []
    for caminho in (config.CAMINHO_CORPUS, config.CAMINHO_CALIBRACAO):
        if Path(caminho).exists():
            corpus += [unitarizar(d) for d in carregar_corpus(caminho)]
    verbetes = carregar_base(config.CAMINHO_BASE)
    construir_indice(corpus, verbetes)
    total = sum(len(u.frases) for u in corpus)
    print(f"Índice gerado em {config.PASTA_INDICES.relative_to(config.RAIZ)}: "
          f"{len(corpus)} dissertações, {total} frases, {len(verbetes)} verbetes")


if __name__ == "__main__":
    main()
