"""Parte 3: geração, isto é, transformar dissertação + Contexto numa RespostaIA com um LLM local.

- montar_prompt(dissertacao, contexto, versao): o texto que vai para o modelo. Testável
  sem Ollama.
- gerar_resposta(dissertacao, contexto, modelo): chama o Ollama, lê o JSON e valida.
  Nunca trava: qualquer falha vira uma RespostaIA com status "erro" e a saída guardada.
- verificar_ollama(modelo): confere, antes de uma rodada, se o Ollama está no ar e tem
  o modelo. Melhor uma mensagem clara no começo do que 20 respostas com erro.

O modelo escreve só texto e evidência de cada campo; o status é sempre calculado pelo
validar (src/validar.py), nunca aceito do modelo.
"""

import json
import re
from pathlib import Path
from string import Template

import config
from src.contratos import Campo, Contexto, DissertacaoUnitarizada, RespostaIA, TrechoRecuperado
from src.validar import validar

PASTA_PROMPTS = Path(__file__).resolve().parent / "prompts"

# Nome dos eixos como aparece para o modelo (no JSON da base, sem acento).
EIXOS_LEGIVEIS = {"natureza": "natureza", "objetivos": "objetivos", "abordagem": "abordagem",
                  "procedimento": "procedimento", "coleta": "coleta", "analise": "análise"}


class VersaoDesconhecida(ValueError):
    """Não existe src/prompts/<versão>.txt."""


class SaidaInvalida(ValueError):
    """A resposta do modelo não pôde ser lida como o JSON combinado."""


class OllamaIndisponivel(RuntimeError):
    """O Ollama não respondeu, ou não tem o modelo pedido."""


# ---------- Prompt ----------

def _posicao(frase_id: str) -> int:
    return int(frase_id[1:])


def _bloco_frases(titulo: str, trechos: list[TrechoRecuperado]) -> str:
    # Na ordem do resumo, não na do score: o modelo lê melhor o texto na sequência original,
    # e os códigos (F2, F7…) continuam mostrando de onde cada frase veio.
    linhas = [f"[{t.frase_id}] {t.texto}" for t in sorted(trechos, key=lambda t: _posicao(t.frase_id))]
    return titulo + "\n" + "\n".join(linhas) + "\n"


def _frases(contexto: Contexto) -> str:
    tematicas, metodologia = contexto.frases_tematicas, contexto.frases_metodologia
    # No sem_rag (e num resumo curto, em que a busca devolve todas) as duas listas têm as
    # mesmas frases: mostra uma vez só, para o modelo não ler o resumo duas vezes.
    if {t.frase_id for t in tematicas} == {t.frase_id for t in metodologia}:
        return _bloco_frases("FRASES DO RESUMO", tematicas)
    return (_bloco_frases("FRASES DO RESUMO QUE FALAM DO TEMA", tematicas) + "\n"
            + _bloco_frases("FRASES DO RESUMO QUE FALAM DO MÉTODO", metodologia))


def _verbetes(contexto: Contexto) -> str:
    if not contexto.verbetes:
        return ""
    linhas = [f"- {v.termo} ({EIXOS_LEGIVEIS.get(v.eixo, v.eixo)}): {v.definicao}" for v in contexto.verbetes]
    return "\nVERBETES DE REFERÊNCIA (ajudam a nomear o método; não são lista fechada)\n" + "\n".join(linhas) + "\n"


def _titulos(contexto: Contexto) -> str:
    if not contexto.titulos_parecidos:
        return ""
    linhas = [f"- {t}" for t in contexto.titulos_parecidos]
    return ("\nTÍTULOS DE OUTRAS DISSERTAÇÕES PARECIDAS (só para manter os nomes dos temas "
            "consistentes; não são esta dissertação)\n" + "\n".join(linhas) + "\n")


def carregar_prompt(versao: str) -> Template:
    caminho = PASTA_PROMPTS / f"{versao}.txt"
    if not caminho.exists():
        existentes = ", ".join(sorted(p.stem for p in PASTA_PROMPTS.glob("*.txt")))
        raise VersaoDesconhecida(f"prompt '{versao}' não existe em src/prompts/ (há: {existentes})")
    return Template(caminho.read_text(encoding="utf-8"))


def montar_prompt(dissertacao: DissertacaoUnitarizada, contexto: Contexto, versao: str | None = None) -> str:
    """O texto completo que vai para o modelo: instruções da versão + dados desta dissertação."""
    d = dissertacao.dissertacao
    texto = carregar_prompt(versao or config.VERSAO_PROMPT).substitute(
        titulo=d.titulo,
        palavras_chave="; ".join(d.palavras_chave) or "(não informadas)",
        frases=_frases(contexto),
        verbetes=_verbetes(contexto),
        titulos=_titulos(contexto),
    )
    return re.sub(r"\n{3,}", "\n\n", texto)


# ---------- Formato da resposta ----------

# Código de frase: "F" + número. Sem isso, o qwen3.5:2b copiava a frase inteira dentro da
# evidência ("F1: Esta pesquisa…"), e cada resposta ficava com ~3 mil caracteres e 25 s.
_CODIGO_DE_FRASE = {"type": "string", "pattern": "^F[0-9]{1,3}$"}

_CAMPO = {
    "type": "object",
    "properties": {"texto": {"type": "string"}, "evidencia": {"type": "array", "items": _CODIGO_DE_FRASE}},
    "required": ["texto", "evidencia"],
}

# Passado ao Ollama em "format": o modelo só consegue escrever um JSON com esta forma.
# O esquema força o FORMATO do código, mas não diz quais códigos existem, de propósito: se
# listasse só os válidos, o modelo nunca citaria uma frase inexistente, e perderíamos a
# medida de quanto ele inventa (status "sem_evidencia").
ESQUEMA_RESPOSTA = {
    "type": "object",
    "properties": {
        "tematica_1": _CAMPO,
        "tematica_2": _CAMPO,
        "metodologias": {"type": "array", "items": _CAMPO, "minItems": 1},
    },
    "required": ["tematica_1", "tematica_2", "metodologias"],
}


def _campo(valor, nome: str) -> Campo:
    if isinstance(valor, str):  # o modelo escreveu só o nome, sem evidência
        return Campo(texto=valor, evidencia=[])
    if not isinstance(valor, dict):
        raise SaidaInvalida(f"'{nome}' não é um objeto")
    evidencia = valor.get("evidencia", [])
    if isinstance(evidencia, str):  # "F2" em vez de ["F2"]
        evidencia = [evidencia]
    if not isinstance(evidencia, list):
        raise SaidaInvalida(f"'{nome}.evidencia' não é uma lista")
    return Campo(texto=str(valor.get("texto") or ""), evidencia=[str(e) for e in evidencia])


def interpretar_saida(texto: str) -> tuple[Campo, Campo, list[Campo]]:
    """Lê a saída do modelo: (temática 1, temática 2, metodologias). Status ainda não conferido.

    Tolera o que modelos pequenos costumam fazer em volta do JSON (cercas de código,
    texto antes ou depois). Levanta SaidaInvalida se não houver JSON com os três campos.
    """
    if not texto or not texto.strip():
        raise SaidaInvalida("resposta vazia")
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim < inicio:
        raise SaidaInvalida("não há JSON na resposta")
    try:
        dados = json.loads(texto[inicio:fim + 1])
    except json.JSONDecodeError as erro:
        raise SaidaInvalida(f"JSON quebrado ({erro.msg}, posição {erro.pos})") from None
    faltando = [c for c in ("tematica_1", "tematica_2", "metodologias") if c not in dados]
    if faltando:
        raise SaidaInvalida(f"faltam os campos: {', '.join(faltando)}")
    metodologias = dados["metodologias"]
    if isinstance(metodologias, (dict, str)):
        metodologias = [metodologias]
    if not isinstance(metodologias, list):
        raise SaidaInvalida("'metodologias' não é uma lista")
    return (_campo(dados["tematica_1"], "tematica_1"), _campo(dados["tematica_2"], "tematica_2"),
            [_campo(m, f"metodologias[{i}]") for i, m in enumerate(metodologias)])


# ---------- Chamada ao Ollama ----------

def _cliente():
    import ollama  # importa só quando precisa: os testes usam um cliente falso

    return ollama.Client(host=config.OLLAMA_HOST, timeout=config.TEMPO_LIMITE)


_pensa: dict[str, bool] = {}


def _modelo_pensa(cliente, modelo: str) -> bool:
    """True se o modelo tem o modo de "pensar" (Qwen3/3.5). Só para esses o pedido leva
    think=False: nos outros, mandar o parâmetro dá erro no Ollama."""
    if modelo not in _pensa:
        try:
            _pensa[modelo] = "thinking" in (cliente.show(modelo).capabilities or [])
        except Exception:
            _pensa[modelo] = False
    return _pensa[modelo]


def _chamar(cliente, modelo: str, mensagens: list[dict]) -> str:
    extra = {"think": config.PENSAR} if _modelo_pensa(cliente, modelo) else {}
    resposta = cliente.chat(
        model=modelo,
        messages=mensagens,
        format=ESQUEMA_RESPOSTA,
        options={"temperature": config.TEMPERATURA, "seed": config.SEED, "num_ctx": config.NUM_CTX},
        **extra,
    )
    return resposta.message.content or ""


def resposta_de_erro(dissertacao_id: str, modelo: str, versao: str, tecnica: str, saida: str) -> RespostaIA:
    """RespostaIA com todos os campos em "erro", guardando o que aconteceu em saida_bruta."""
    return RespostaIA(
        dissertacao_id=dissertacao_id,
        tematica_1=Campo(texto="", evidencia=[], status="erro"),
        tematica_2=Campo(texto="", evidencia=[], status="erro"),
        metodologias=[Campo(texto="", evidencia=[], status="erro")],
        modelo=modelo, versao_prompt=versao, tecnica=tecnica, saida_bruta=saida,
    )


SEPARADOR_TENTATIVAS = "\n\n----- nova tentativa -----\n\n"


def gerar_resposta(dissertacao: DissertacaoUnitarizada, contexto: Contexto, modelo: str,
                   versao: str | None = None, cliente=None) -> RespostaIA:
    """Pergunta ao modelo e devolve a RespostaIA já validada. Nunca levanta exceção.

    Se o JSON vier quebrado, pede de novo mandando o erro (com temperatura 0, repetir o
    mesmo pedido daria a mesma resposta). saida_bruta guarda todas as tentativas.
    """
    versao = versao or config.VERSAO_PROMPT
    ids = dict(dissertacao_id=dissertacao.dissertacao.id, modelo=modelo, versao=versao, tecnica=contexto.tecnica)
    saidas: list[str] = []
    try:
        mensagens = [{"role": "user", "content": montar_prompt(dissertacao, contexto, versao)}]
        cliente = cliente or _cliente()
        for _ in range(config.TENTATIVAS):
            texto = _chamar(cliente, modelo, mensagens)
            saidas.append(texto)
            try:
                tematica_1, tematica_2, metodologias = interpretar_saida(texto)
            except SaidaInvalida as erro:
                motivo = str(erro)
                mensagens += [
                    {"role": "assistant", "content": texto},
                    {"role": "user", "content": f"A resposta acima não pôde ser lida: {erro}. "
                                                "Responda de novo, só com o JSON no formato pedido."},
                ]
                continue
            resposta = RespostaIA(
                dissertacao_id=ids["dissertacao_id"], tematica_1=tematica_1, tematica_2=tematica_2,
                metodologias=metodologias, modelo=modelo, versao_prompt=versao, tecnica=contexto.tecnica,
                saida_bruta=SEPARADOR_TENTATIVAS.join(saidas),
            )
            enviadas = {t.frase_id for t in contexto.frases_tematicas + contexto.frases_metodologia}
            return validar(resposta, dissertacao, frases_enviadas=enviadas)
        saidas.append(f"[não lida: {motivo}]")
    except Exception as erro:  # Ollama fora do ar, modelo não baixado, tempo esgotado…
        saidas.append(f"[falha: {type(erro).__name__}: {erro}]")
    return resposta_de_erro(saida=SEPARADOR_TENTATIVAS.join(saidas), **ids)


def verificar_ollama(modelo: str, cliente=None) -> None:
    """Levanta OllamaIndisponivel com uma mensagem clara se não der para usar o modelo."""
    try:
        cliente = cliente or _cliente()
        instalados = [m.model for m in cliente.list().models]
    except Exception as erro:
        raise OllamaIndisponivel(
            f"o Ollama não respondeu em {config.OLLAMA_HOST} ({type(erro).__name__}). "
            "Abra o aplicativo Ollama e tente de novo.") from None
    if modelo not in instalados:
        raise OllamaIndisponivel(f"o modelo '{modelo}' não está baixado. Rode: ollama pull {modelo}")
