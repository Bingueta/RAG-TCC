"""Parte 4: o comando que liga as partes e grava a planilha (seção "Parte 4" da divisão).

    python -m src.pipeline                      modelo e técnica padrão, no corpus de config.CORPUS_ATIVO
    python -m src.pipeline --modelo qwen3.5:4b-q4_K_M --tecnica denso
    python -m src.pipeline --todos              todos os modelos × todas as técnicas do config.py
    python -m src.pipeline --corpus calibracao  as 20 de calibração em vez das 59
    python -m src.pipeline --mock               dados de exemplo, sem Ollama, sem índice e sem spaCy
    python -m src.pipeline --sobrescrever       refaz do zero (sem isso, retoma de onde parou)

Cada execução (modelo × técnica × versão do prompt) tem uma pasta:
    data/sugestoes/<modelo>__<tecnica>__<versao>/              as 59
    data/sugestoes/calibracao/<modelo>__<tecnica>__<versao>/   as 20 de calibração
    data/sugestoes/mock/…                                      --mock (fora do git)
com respostas.json (lista de RespostaIA), execucao.json (máquina, versões, parâmetros,
hashes e, por dissertação, segundos e tentativas) e respostas.xlsx (src/exportar.py).

Cada resposta é gravada assim que fica pronta: se o programa parar, a próxima vez retoma
de onde parou. Uma execução completa não é refeita nem regravada — os JSON são o registro
do que rodou —, só a planilha é gerada de novo.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict
from datetime import datetime
from importlib import metadata
from pathlib import Path

import config
from src.contratos import Campo, DissertacaoUnitarizada, RespostaIA
from src.exportar import exportar_excel
from src.sugerir import SEPARADOR_TENTATIVAS, resposta_de_erro

PASTA_SUGESTOES = config.RAIZ / "data" / "sugestoes"
CORPORA = {"corpus": config.CAMINHO_CORPUS, "calibracao": config.CAMINHO_CALIBRACAO}
BIBLIOTECAS = ("ollama", "sentence-transformers", "torch", "spacy", "rank-bm25", "numpy", "openpyxl")


class CorpusDesconhecido(ValueError):
    """Nome de corpus que não existe (use "corpus" ou "calibracao")."""


# ---------- Nomes, hashes e registro da máquina ----------

def nome_da_pasta(modelo: str, tecnica: str, versao: str, sufixo: str = "") -> str:
    # O Windows não aceita ":" em nome de pasta (seção 3.4 da divisão). O sufixo separa
    # rodadas com o mesmo prompt e outra busca (ex.: "busca-corrigida"), sem apagar as antigas.
    nome = f"{modelo.replace(':', '-').replace('/', '-')}__{tecnica}__{versao}"
    return f"{nome}__{sufixo}" if sufixo else nome


def pasta_da_execucao(modelo: str, tecnica: str, versao: str, corpus: str, sufixo: str = "",
                      mock: bool = False, base: Path | None = None) -> Path:
    base = Path(base or PASTA_SUGESTOES)
    if mock:
        base = base / "mock"
    elif corpus == "calibracao":
        base = base / "calibracao"
    return base / nome_da_pasta(modelo, tecnica, versao, sufixo)


def sha256_do_texto(caminho: Path) -> str:
    # Lido como texto (quebra de linha normalizada): o git no Windows troca LF por CRLF no
    # checkout, e o hash não pode mudar por causa disso.
    return hashlib.sha256(Path(caminho).read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def _texto_de_comando(*comando) -> str:
    try:
        return subprocess.run(comando, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ""


def maquina() -> dict:
    """CPU, RAM e GPU, para a rodada ficar registrada com a máquina em que rodou."""
    cpu = _texto_de_comando("powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name")
    ram = _texto_de_comando("powershell", "-NoProfile", "-Command",
                            "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)")
    gpu = _texto_de_comando("nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader")
    return {"sistema": platform.platform(), "cpu": cpu or platform.processor(), "ram_gb": ram, "gpu": gpu,
            "python": platform.python_version()}


def bibliotecas() -> dict:
    versoes = {}
    for nome in BIBLIOTECAS:
        try:
            versoes[nome] = metadata.version(nome)
        except metadata.PackageNotFoundError:
            versoes[nome] = "não instalada"
    return versoes


def versao_do_ollama() -> str:
    try:
        with urllib.request.urlopen(f"{config.OLLAMA_HOST}/api/version", timeout=5) as resposta:
            return json.load(resposta).get("version", "")
    except Exception:
        return ""


# ---------- Respostas ----------

def tentativas(resposta: RespostaIA) -> int:
    """Quantas respostas o modelo deu (1 = a primeira já serviu; 2 = precisou repetir).

    Conta pela saida_bruta, sem os avisos que o gerar_resposta acrescenta ("[falha: …]",
    "[não lida: …]"), para não mudar o contrato só para isso."""
    partes = resposta.saida_bruta.split(SEPARADOR_TENTATIVAS)
    return sum(1 for p in partes if p and not p.startswith(("[falha:", "[não lida:")))


def status_geral(resposta: RespostaIA) -> str:
    todos = [resposta.tematica_1.status, resposta.tematica_2.status] + [m.status for m in resposta.metodologias]
    return "erro" if "erro" in todos else ("sem_evidencia" if "sem_evidencia" in todos else "ok")


def resposta_de_dict(dados: dict) -> RespostaIA:
    campo = lambda c: Campo(**c)  # noqa: E731
    return RespostaIA(**{**dados, "tematica_1": campo(dados["tematica_1"]), "tematica_2": campo(dados["tematica_2"]),
                         "metodologias": [campo(m) for m in dados["metodologias"]]})


def _ler_json(caminho: Path, padrao):
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else padrao


def _gravar(pasta: Path, respostas: dict[str, RespostaIA], ordem: list[str], execucao: dict) -> None:
    ordenadas = [asdict(respostas[i]) for i in ordem if i in respostas]
    ordenadas += [asdict(r) for i, r in sorted(respostas.items()) if i not in ordem]
    (pasta / "respostas.json").write_text(json.dumps(ordenadas, ensure_ascii=False, indent=2), encoding="utf-8")
    (pasta / "execucao.json").write_text(json.dumps(execucao, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- Ollama ----------

def aquecer(cliente, modelo: str) -> dict:
    """Carrega o modelo na placa antes de medir, para o tempo de carga não cair na 1ª dissertação.

    Devolve quanto tempo levou para carregar e quanto do modelo ficou na VRAM.
    """
    inicio = time.perf_counter()
    cliente.generate(model=modelo, prompt="ok", options={"num_ctx": config.NUM_CTX, "num_predict": 1})
    carga = round(time.perf_counter() - inicio, 1)
    for m in cliente.ps().models:
        if m.model == modelo:
            return {"segundos_para_carregar": carga, "tamanho_gb": round(m.size / 1e9, 2),
                    "na_vram_gb": round(m.size_vram / 1e9, 2), "fracao_na_vram": round(m.size_vram / m.size, 3)}
    return {"segundos_para_carregar": carga}


def _componentes(mock: bool):
    """As funções das Partes 1, 2 e 3: as de verdade ou as de exemplo (src/mocks.py)."""
    if mock:
        from src import mocks

        return mocks.carregar_corpus, mocks.unitarizar, mocks.recuperar, mocks.gerar_resposta
    from src.preparar_dados import carregar_corpus
    from src.recuperar import recuperar
    from src.sugerir import gerar_resposta
    from src.unitarizar import unitarizar

    return carregar_corpus, unitarizar, recuperar, gerar_resposta


# ---------- Execução ----------

def executar(modelo: str, tecnica: str, corpus: str = "corpus", versao: str | None = None,
             sobrescrever: bool = False, sufixo: str = "", ids: list[str] | None = None,
             mock: bool = False, base: Path | None = None, cliente=None) -> Path:
    """Roda uma combinação (modelo × técnica) em todo o corpus e devolve a pasta da execução.

    Erro numa dissertação não para as outras: ela sai com status "erro" e o motivo na
    saida_bruta, e uma rodada nova (sem --sobrescrever) não a refaz — para refazer, use
    --sobrescrever ou apague a pasta.
    """
    if corpus not in CORPORA:
        raise CorpusDesconhecido(f"corpus '{corpus}' não existe (use um de: {', '.join(CORPORA)})")
    versao = versao or config.VERSAO_PROMPT
    carregar_corpus, unitarizar, recuperar, gerar_resposta = _componentes(mock)
    caminho_corpus = None if mock else CORPORA[corpus]
    dissertacoes = carregar_corpus(caminho_corpus)
    if ids:
        dissertacoes = [d for d in dissertacoes if d.id in set(ids)]
    unitarizadas: list[DissertacaoUnitarizada] = [unitarizar(d) for d in dissertacoes]
    ordem = [d.id for d in dissertacoes]

    pasta = pasta_da_execucao(modelo, tecnica, versao, corpus, sufixo, mock, base)
    pasta.mkdir(parents=True, exist_ok=True)
    respostas: dict[str, RespostaIA] = {}
    anterior: dict = {}
    if not sobrescrever:
        respostas = {r["dissertacao_id"]: resposta_de_dict(r) for r in _ler_json(pasta / "respostas.json", [])}
        anterior = _ler_json(pasta / "execucao.json", {}) if respostas else {}
    faltam = [u for u in unitarizadas if u.dissertacao.id not in respostas]
    if not faltam:
        print(f"== {pasta.name}: completa ({len(unitarizadas)}); só a planilha é gerada de novo")
        exportar_excel([respostas[i] for i in ordem], unitarizadas, pasta, anterior)
        return pasta

    if not mock:
        from src.sugerir import _cliente, verificar_ollama

        cliente = cliente or _cliente()
        verificar_ollama(modelo, cliente)
    prompt = config.RAIZ / "src" / "prompts" / f"{versao}.txt"
    execucao = {
        "inicio": anterior.get("inicio") or datetime.now().isoformat(timespec="seconds"),
        "corpus": "mock" if mock else corpus,
        "sha256_do_corpus": "" if mock else sha256_do_texto(caminho_corpus),
        "modelo": modelo,
        "digest_do_modelo": "" if mock else next((m.digest for m in cliente.list().models if m.model == modelo), ""),
        "tecnica": tecnica, "versao_prompt": versao,
        # Os hashes provam com que prompt, base e busca a rodada foi feita (um arquivo editado
        # sem mudar de nome não passa despercebido).
        "sha256_do_prompt": sha256_do_texto(prompt),
        "sha256_da_base": sha256_do_texto(config.CAMINHO_BASE),
        "sha256_do_recuperar": sha256_do_texto(config.RAIZ / "src" / "recuperar.py"),
        "temperatura": config.TEMPERATURA, "seed": config.SEED, "num_ctx": config.NUM_CTX, "pensar": config.PENSAR,
        "tentativas_maximas": config.TENTATIVAS, "modelo_embedding": config.MODELO_EMBEDDING,
        "top_k_frases": config.TOP_K_FRASES, "top_k_verbetes": config.TOP_K_VERBETES,
        "ollama": "" if mock else versao_do_ollama(), "bibliotecas": bibliotecas(), "maquina": maquina(),
        "carga": {} if mock else aquecer(cliente, modelo),
        "segundos": {i: s for i, s in anterior.get("segundos", {}).items() if i in respostas},
        "tentativas": {i: tentativas(r) for i, r in respostas.items()},
    }
    if anterior:
        execucao["retomada_em"] = datetime.now().isoformat(timespec="seconds")
    print(f"== {pasta.name}: {len(faltam)} de {len(unitarizadas)} por fazer"
          f" ({execucao['carga'].get('fracao_na_vram', '-')} do modelo na VRAM)", flush=True)

    for numero, unitarizada in enumerate(faltam, start=1):
        did = unitarizada.dissertacao.id
        inicio = time.perf_counter()
        try:
            contexto = recuperar(unitarizada, tecnica)
            resposta = gerar_resposta(unitarizada, contexto, modelo, versao, cliente=cliente)
        except Exception as erro:  # a busca falhou: o gerar_resposta em si nunca levanta
            resposta = resposta_de_erro(did, modelo, versao, tecnica, f"[falha: {type(erro).__name__}: {erro}]")
        execucao["segundos"][did] = round(time.perf_counter() - inicio, 2)
        execucao["tentativas"][did] = tentativas(resposta)
        respostas[did] = resposta
        _gravar(pasta, respostas, ordem, execucao)
        repetiu = "  (repetiu)" if execucao["tentativas"][did] > 1 else ""
        print(f"  {did} ({numero}/{len(faltam)}) {execucao['segundos'][did]:6.1f} s  {status_geral(resposta)}{repetiu}",
              flush=True)

    execucao["fim"] = datetime.now().isoformat(timespec="seconds")
    execucao["erros"] = sum(status_geral(r) == "erro" for r in respostas.values())
    _gravar(pasta, respostas, ordem, execucao)
    exportar_excel([respostas[i] for i in ordem], unitarizadas, pasta, execucao)
    return pasta


def main(argumentos: list[str] | None = None) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modelo", default=config.MODELO_PADRAO)
    parser.add_argument("--tecnica", default=config.TECNICA_PADRAO, choices=config.TECNICAS)
    parser.add_argument("--todos", action="store_true", help="todos os modelos × todas as técnicas do config.py")
    parser.add_argument("--corpus", default=config.CORPUS_ATIVO, choices=list(CORPORA))
    parser.add_argument("--versao", default=config.VERSAO_PROMPT, help="versão do prompt (src/prompts/)")
    parser.add_argument("--mock", action="store_true", help="dados de exemplo, sem Ollama")
    parser.add_argument("--sobrescrever", action="store_true", help="refaz do zero em vez de retomar")
    args = parser.parse_args(argumentos)

    if args.mock:
        modelos, tecnicas = ["mock"], (config.TECNICAS if args.todos else [args.tecnica])
    elif args.todos:
        modelos, tecnicas = list(config.MODELOS_LLM.values()), list(config.TECNICAS)
    else:
        modelos, tecnicas = [args.modelo], [args.tecnica]
    cliente = None
    if not args.mock:
        from src.sugerir import _cliente, verificar_ollama

        cliente = _cliente()
        for modelo in modelos:
            verificar_ollama(modelo, cliente)  # para já, com mensagem clara, se faltar Ollama ou modelo
    for modelo in modelos:
        for tecnica in tecnicas:
            pasta = executar(modelo, tecnica, args.corpus, args.versao, args.sobrescrever, mock=args.mock,
                             cliente=cliente)
            planilha = pasta / "respostas.xlsx"
            print(f"   planilha: {planilha.relative_to(config.RAIZ) if planilha.is_relative_to(config.RAIZ) else planilha}")
        if cliente is not None:
            cliente.generate(model=modelo, keep_alive=0)  # libera a placa para o próximo modelo


if __name__ == "__main__":
    main()
