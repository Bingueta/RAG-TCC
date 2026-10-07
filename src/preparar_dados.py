"""Parte 1: preparação dos dados.

- normalizar_texto: limpa o texto copiado do PDF (Unicode, aspas, espaços, quebras).
- preparar_corpus: gera o data/corpus.json a partir do original (data/brutos/).
  Comando: python -m src.preparar_dados
- verificar_corpus: lista avisos para o grupo revisar (sobras, resumo curto, sem ponto).
- carregar_corpus: lê o data/corpus.json, confere os campos e devolve a lista de
  Dissertacao.

Contratos em src/contratos.py; formato do corpus.json na seção 3.2 de
docs/divisao-tarefas.md.
"""

import json
import re
import unicodedata
from dataclasses import asdict
from pathlib import Path

import config
from src.contratos import Dissertacao


def _consertar_caractere_windows(caractere: str) -> str:
    """Converte um caractere de controle U+0080 a U+009F no símbolo que ele era no Windows.

    Ao copiar do PDF, aspas e apóstrofos "curvos" do Windows (cp1252) viraram caracteres
    de controle invisíveis. Ex.: U+0093 era “ e U+0092 era ’ ("Olhos D’água").
    """
    try:
        return bytes([ord(caractere)]).decode("cp1252")
    except UnicodeDecodeError:
        return ""  # posição sem símbolo no cp1252: é lixo, remove


_TABELA_WINDOWS = {codigo: _consertar_caractere_windows(chr(codigo)) for codigo in range(0x80, 0xA0)}


def normalizar_texto(texto: str) -> str:
    """Padroniza o texto copiado do PDF, sem mudar o conteúdo.

    - Unicode em NFC (junta letra + acento num caractere só). Não usa NFKC, que trocaria
      "n.º" por "n.o" e "1ª" por "1a".
    - Aspas e apóstrofos do Windows corrompidos voltam a ser “ ” ‘ ’.
    - Palavra cortada por hífen no fim da linha é juntada.
    - Quebras de linha (inclusive as do Windows, \\r\\n), tabulações, espaços não
      separáveis e espaços repetidos viram um espaço só; tira espaços do começo e do fim.
    """
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.translate(_TABELA_WINDOWS)
    texto = texto.replace("­", "")  # hífen invisível (soft hyphen)
    # Palavra cortada no fim da linha: "investiga-\nção" → "investigação". Só junta quando
    # há quebra de linha depois do hífen e letras dos dois lados; "NAF- Núcleo" (hífen +
    # espaço) e "2022-\n2023" (números) ficam como estão.
    texto = re.sub(r"([^\W\d_])-[ \t]*\r?\n[ \t]*([^\W\d_])", r"\1\2", texto)
    texto = re.sub(r"\s+", " ", texto)  # \s inclui \r, \n, \t e o espaço não separável
    return texto.strip()

CAMPOS_OBRIGATORIOS = ("id", "titulo", "resumo", "palavras_chave")
CAMPOS_OPCIONAIS = ("ano",)


class ErroCorpus(ValueError):
    """O corpus tem algum problema. A mensagem lista todos, um por linha."""


def _problemas_do_item(item, posicao: int) -> list[str]:
    """Confere um item do corpus e devolve a lista de problemas (vazia se estiver ok)."""
    if not isinstance(item, dict):
        return [f"item {posicao}: não é um objeto JSON"]

    nome = item.get("id") or f"item {posicao}"
    problemas = []

    for campo in CAMPOS_OBRIGATORIOS:
        if campo not in item:
            problemas.append(f"{nome}: falta o campo '{campo}'")
    for campo in item:
        if campo not in CAMPOS_OBRIGATORIOS + CAMPOS_OPCIONAIS:
            problemas.append(f"{nome}: campo desconhecido '{campo}' (erro de digitação?)")

    if "id" in item and not (isinstance(item["id"], str) and item["id"].strip()):
        problemas.append(f"item {posicao}: o 'id' está vazio ou não é texto")
    for campo, descricao in (("titulo", "título"), ("resumo", "resumo")):
        if campo in item and not (isinstance(item[campo], str) and item[campo].strip()):
            problemas.append(f"{nome} está sem {descricao}")
    if "palavras_chave" in item:
        pk = item["palavras_chave"]
        if not isinstance(pk, list) or not all(isinstance(p, str) and p.strip() for p in pk):
            problemas.append(f"{nome}: 'palavras_chave' tem que ser uma lista de textos não vazios")
    if item.get("ano") is not None and not isinstance(item["ano"], int):
        problemas.append(f"{nome}: 'ano' tem que ser um número inteiro")
    return problemas


class ErroOriginal(ValueError):
    """O arquivo original (data/brutos/) não está no formato esperado."""


# Sobra da cópia do PDF no fim do resumo: "… comunitários. Palavras-chave: Cooperativismo, Territ"
_SOBRA_PALAVRAS_CHAVE = re.compile(r"\s*\bpalavras?[- ]chaves?\s*:.*$", re.IGNORECASE | re.DOTALL)


def limpar_resumo(texto: str) -> str:
    """Normaliza o resumo e corta a sobra "Palavras-chave: …" que veio colada do PDF."""
    return _SOBRA_PALAVRAS_CHAVE.sub("", normalizar_texto(texto)).strip()


def separar_palavras_chave(texto: str) -> list[str]:
    """Transforma "Cooperativismo, Território,  Gênero," em ["Cooperativismo", "Território", "Gênero"].

    Separa por vírgula (e ponto e vírgula, por garantia), limpa cada termo e descarta os
    vazios. Mantém maiúsculas e minúsculas como estão no original.
    """
    termos = (normalizar_texto(termo) for termo in re.split(r"[,;]", texto))
    return [termo for termo in termos if termo]


def preparar_dissertacoes(original: list, prefixo: str = "D") -> list[Dissertacao]:
    """Transforma os itens do original em Dissertacao, com id na ordem do arquivo.

    O original tem só "titulo", "resumo" e "palavras_chave". O id é o prefixo + a posição
    com 3 dígitos: D001, D002… (a calibração usa outro prefixo, ex.: C001).
    """
    if not isinstance(original, list):
        raise ErroOriginal("o original tem que ser uma lista de dissertações")
    problemas = []
    for posicao, item in enumerate(original, start=1):
        if not isinstance(item, dict):
            problemas.append(f"item {posicao}: não é um objeto JSON")
            continue
        for campo in ("titulo", "resumo", "palavras_chave"):
            if not isinstance(item.get(campo), str):
                problemas.append(f"item {posicao}: falta o campo '{campo}' (ou não é texto)")
    if problemas:
        raise ErroOriginal(f"{len(problemas)} problema(s) no original:\n" + "\n".join(problemas))

    return [
        Dissertacao(
            id=f"{prefixo}{posicao:03d}",
            titulo=normalizar_texto(item["titulo"]),
            resumo=limpar_resumo(item["resumo"]),
            palavras_chave=separar_palavras_chave(item["palavras_chave"]),
        )
        for posicao, item in enumerate(original, start=1)
    ]


def _para_json(dissertacao: Dissertacao) -> dict:
    """Converte para o formato do corpus.json (seção 3.2), sem o 'ano' quando não existe."""
    return {campo: valor for campo, valor in asdict(dissertacao).items() if valor is not None}


def preparar_corpus(caminho_original: str | Path, caminho_saida: str | Path,
                    prefixo: str = "D") -> list[Dissertacao]:
    """Lê o original, prepara as dissertações e grava o corpus.json em UTF-8.

    Devolve as dissertações preparadas. O arquivo gravado é conferido com carregar_corpus.
    """
    with open(caminho_original, encoding="utf-8") as arquivo:
        dissertacoes = preparar_dissertacoes(json.load(arquivo), prefixo=prefixo)
    caminho_saida = Path(caminho_saida)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho_saida, "w", encoding="utf-8", newline="\n") as arquivo:
        json.dump([_para_json(d) for d in dissertacoes], arquivo, ensure_ascii=False, indent=2)
        arquivo.write("\n")
    carregar_corpus(caminho_saida)  # garante que o arquivo gravado é um corpus válido
    return dissertacoes


def carregar_corpus(caminho: str | Path) -> list[Dissertacao]:
    """Lê o corpus.json, confere os campos e devolve uma Dissertacao para cada item.

    Se houver qualquer problema, levanta ErroCorpus com todos eles, cada um citando o id.
    """
    with open(caminho, encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    if not isinstance(dados, list):
        raise ErroCorpus(f"{caminho}: o corpus tem que ser uma lista de dissertações")

    problemas = []
    for posicao, item in enumerate(dados, start=1):
        problemas.extend(_problemas_do_item(item, posicao))

    ids = [item.get("id") for item in dados if isinstance(item, dict)]
    repetidos = sorted({i for i in ids if i and ids.count(i) > 1})
    for id_repetido in repetidos:
        problemas.append(f"{id_repetido}: id repetido ({ids.count(id_repetido)} vezes)")

    if problemas:
        raise ErroCorpus(f"{caminho} tem {len(problemas)} problema(s):\n" + "\n".join(problemas))
    return [Dissertacao(**item) for item in dados]


# Limites e padrões dos avisos (tarefa 7.1). O menor resumo real tem 1.138 caracteres; um
# resumo com menos de 300 (umas 2 ou 3 frases) provavelmente foi cortado na cópia do PDF.
TAMANHO_MINIMO_RESUMO = 300
_TERMOS_FORA_DO_LUGAR = re.compile(r"\b(palavras?[- ]chaves?|abstract|keywords?)\b|\bresumo\s*:", re.IGNORECASE)
_TERMINA_FRASE = re.compile(r"[.!?…][”’»\"')\]]*$")


def verificar_corpus(dissertacoes: list[Dissertacao]) -> list[str]:
    """Procura sinais de problema na cópia do PDF. Devolve um aviso por linha (vazio = ok).

    Avisos não impedem nada: são para o grupo olhar e decidir.
    """
    avisos = []
    titulos_vistos: dict[str, str] = {}
    for d in dissertacoes:
        achado = _TERMOS_FORA_DO_LUGAR.search(d.resumo)
        if achado:
            avisos.append(f"{d.id}: o resumo contém \"{achado.group(0)}\" (sobra de outra parte do PDF?)")
        if len(d.resumo) < TAMANHO_MINIMO_RESUMO:
            avisos.append(f"{d.id}: resumo muito curto ({len(d.resumo)} caracteres; cortado na cópia?)")
        if not _TERMINA_FRASE.search(d.resumo):
            avisos.append(f"{d.id}: resumo termina sem ponto final (\"…{d.resumo[-40:]}\")")
        chave = d.titulo.casefold()
        if chave in titulos_vistos:
            avisos.append(f"{d.id}: mesmo título de {titulos_vistos[chave]}")
        titulos_vistos.setdefault(chave, d.id)
    return avisos


def _mostrar(caminho: Path) -> str:
    """Caminho relativo à raiz do repositório, quando possível (mais curto na tela)."""
    try:
        return str(Path(caminho).relative_to(config.RAIZ))
    except ValueError:
        return str(caminho)


def main(argumentos: list[str] | None = None) -> None:
    """Comando: python -m src.preparar_dados [--calibracao]

    Sem opção: gera o data/corpus.json a partir do original das 59.
    Com --calibracao: gera o corpus de calibração (ids C001…) a partir de
    data/brutos/calibracao.json. Caminhos no config.py.
    """
    import argparse

    leitor = argparse.ArgumentParser(description="Gera o corpus preparado a partir do original.")
    leitor.add_argument("--calibracao", action="store_true",
                        help="prepara as dissertações de calibração (de fora das 59)")
    opcoes = leitor.parse_args(argumentos)
    if opcoes.calibracao:
        origem, destino, prefixo = config.CAMINHO_ORIGINAL_CALIBRACAO, config.CAMINHO_CALIBRACAO, "C"
    else:
        origem, destino, prefixo = config.CAMINHO_ORIGINAL, config.CAMINHO_CORPUS, "D"
    if not origem.exists():
        raise SystemExit(f"Arquivo não encontrado: {_mostrar(origem)}")

    dissertacoes = preparar_corpus(origem, destino, prefixo=prefixo)
    print(f"Corpus gerado: {_mostrar(destino)}")
    print(f"  {len(dissertacoes)} dissertações ({dissertacoes[0].id} a {dissertacoes[-1].id})")
    print(f"  {sum(len(d.palavras_chave) for d in dissertacoes)} palavras-chave")
    avisos = verificar_corpus(dissertacoes)
    print(f"\nAvisos para o grupo revisar: {len(avisos)}")
    for aviso in avisos:
        print(f"  - {aviso}")


if __name__ == "__main__":
    main()
