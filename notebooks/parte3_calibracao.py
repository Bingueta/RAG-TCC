"""Parte 3: roda a geração nas 20 dissertações de calibração e guarda as respostas.

Serve para escolher modelos e ajustar o prompt (tarefas 5.1 e 5.2 do PROGRESSO.md).
Só roda na calibração, de propósito: não existe opção para as 59 aqui (decisão C3).
O comando definitivo, com Excel e as 59, é o pipeline da Parte 4.

Uso (na raiz do repositório):
    .venv\\Scripts\\python notebooks/parte3_calibracao.py --modelos qwen3.5:9b-q4_K_M --tecnicas sem_rag hibrido
    ... --versao v2          outra versão do prompt
    ... --ids C001 C002      só algumas dissertações
    ... --sobrescrever       refaz o que já existe (sem isso, retoma de onde parou)

Saída, uma pasta por combinação (modelo × técnica × versão do prompt):
    data/sugestoes/calibracao/<modelo>__<tecnica>__<versao>/
        respostas.json   lista de RespostaIA (dataclasses.asdict), na ordem C001…C020
        execucao.json    máquina, versões, parâmetros e segundos por dissertação
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
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import config  # noqa: E402
from src.contratos import Campo, RespostaIA  # noqa: E402
from src.preparar_dados import carregar_corpus  # noqa: E402
from src.recuperar import recuperar  # noqa: E402
from src.sugerir import (PASTA_PROMPTS, SEPARADOR_TENTATIVAS, _cliente, gerar_resposta,  # noqa: E402
                         verificar_ollama)
from src.unitarizar import unitarizar  # noqa: E402

PASTA_SAIDA = RAIZ / "data" / "sugestoes" / "calibracao"


def nome_da_pasta(modelo: str, tecnica: str, versao: str) -> str:
    # O Windows não aceita ":" em nome de pasta (seção 3.4 da divisão).
    return f"{modelo.replace(':', '-').replace('/', '-')}__{tecnica}__{versao}"


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


def versao_do_ollama() -> str:
    try:
        with urllib.request.urlopen(f"{config.OLLAMA_HOST}/api/version", timeout=5) as resposta:
            return json.load(resposta).get("version", "")
    except Exception:
        return ""


def _de_dict(dados: dict) -> RespostaIA:
    campo = lambda c: Campo(**c)  # noqa: E731
    return RespostaIA(**{**dados, "tematica_1": campo(dados["tematica_1"]), "tematica_2": campo(dados["tematica_2"]),
                         "metodologias": [campo(m) for m in dados["metodologias"]]})


def _gravar(pasta: Path, respostas: dict, execucao: dict) -> None:
    # Grava a cada dissertação: se faltar luz, a rodada retoma de onde parou.
    ordenadas = [asdict(respostas[i]) for i in sorted(respostas)]
    (pasta / "respostas.json").write_text(json.dumps(ordenadas, ensure_ascii=False, indent=2), encoding="utf-8")
    (pasta / "execucao.json").write_text(json.dumps(execucao, ensure_ascii=False, indent=2), encoding="utf-8")


def tentativas(resposta: RespostaIA) -> int:
    """Quantas respostas o modelo deu (1 = a primeira já serviu; 2 = precisou repetir).

    Conta pela saida_bruta, sem os avisos que o gerar_resposta acrescenta ("[falha: …]",
    "[não lida: …]"), para não mudar o contrato só para isso."""
    partes = resposta.saida_bruta.split(SEPARADOR_TENTATIVAS)
    return sum(1 for p in partes if p and not p.startswith(("[falha:", "[não lida:")))


def _status(resposta: RespostaIA) -> str:
    todos = [resposta.tematica_1.status, resposta.tematica_2.status] + [m.status for m in resposta.metodologias]
    return "erro" if "erro" in todos else ("sem_evidencia" if "sem_evidencia" in todos else "ok")


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


def rodar(modelo: str, tecnica: str, versao: str, corpus, sobrescrever: bool) -> Path:
    pasta = PASTA_SAIDA / nome_da_pasta(modelo, tecnica, versao)
    pasta.mkdir(parents=True, exist_ok=True)
    respostas: dict[str, RespostaIA] = {}
    segundos: dict[str, float] = {}
    if not sobrescrever and (pasta / "respostas.json").exists():
        anteriores = json.loads((pasta / "respostas.json").read_text(encoding="utf-8"))
        respostas = {r["dissertacao_id"]: _de_dict(r) for r in anteriores}
        segundos = json.loads((pasta / "execucao.json").read_text(encoding="utf-8")).get("segundos", {})
        segundos = {i: s for i, s in segundos.items() if i in respostas}

    cliente = _cliente()
    digest = next((m.digest for m in cliente.list().models if m.model == modelo), "")
    # Lido como texto (quebra de linha normalizada): o git no Windows troca LF por CRLF no
    # checkout, e o hash não pode mudar por causa disso — o texto que vai ao modelo não muda.
    prompt = (PASTA_PROMPTS / f"{versao}.txt").read_text(encoding="utf-8").encode("utf-8")
    execucao = {
        "inicio": datetime.now().isoformat(timespec="seconds"),
        "modelo": modelo, "digest_do_modelo": digest, "tecnica": tecnica, "versao_prompt": versao,
        # O hash prova que o v1 desta rodada é o mesmo v1 de hoje (prompt editado sem mudar de versão).
        "sha256_do_prompt": hashlib.sha256(prompt).hexdigest(),
        "temperatura": config.TEMPERATURA, "seed": config.SEED, "num_ctx": config.NUM_CTX, "pensar": config.PENSAR,
        "tentativas": config.TENTATIVAS, "modelo_embedding": config.MODELO_EMBEDDING,
        "top_k_frases": config.TOP_K_FRASES, "top_k_verbetes": config.TOP_K_VERBETES,
        "ollama": versao_do_ollama(), "maquina": maquina(), "carga": aquecer(cliente, modelo),
        "segundos": segundos,
        "tentativas": {i: tentativas(r) for i, r in respostas.items()},
    }
    faltam = [u for u in corpus if u.dissertacao.id not in respostas]
    print(f"\n== {pasta.name}: {len(faltam)} de {len(corpus)} por fazer "
          f"({execucao['carga'].get('fracao_na_vram', '?')} do modelo na VRAM)")
    for numero, unitarizada in enumerate(faltam, start=1):
        did = unitarizada.dissertacao.id
        contexto = recuperar(unitarizada, tecnica)
        inicio = time.perf_counter()
        resposta = gerar_resposta(unitarizada, contexto, modelo, versao, cliente=cliente)
        segundos[did] = round(time.perf_counter() - inicio, 2)
        respostas[did] = resposta
        execucao["tentativas"][did] = tentativas(resposta)
        _gravar(pasta, respostas, execucao)
        print(f"  {did} ({numero}/{len(faltam)}) {segundos[did]:6.1f} s  {_status(resposta)}"
              f"{'  (repetiu)' if execucao['tentativas'][did] > 1 else ''}")
    execucao["fim"] = datetime.now().isoformat(timespec="seconds")
    execucao["erros"] = sum(_status(r) == "erro" for r in respostas.values())
    _gravar(pasta, respostas, execucao)
    return pasta


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modelos", nargs="+", default=list(config.MODELOS_LLM.values()))
    parser.add_argument("--tecnicas", nargs="+", default=list(config.TECNICAS), choices=config.TECNICAS)
    parser.add_argument("--versao", default=config.VERSAO_PROMPT)
    parser.add_argument("--ids", nargs="+", help="só estas dissertações (ex.: C001 C002)")
    parser.add_argument("--sobrescrever", action="store_true")
    args = parser.parse_args()

    for modelo in args.modelos:
        verificar_ollama(modelo)  # para já, com mensagem clara, se faltar Ollama ou modelo
    corpus = [unitarizar(d) for d in carregar_corpus(config.CAMINHO_CALIBRACAO)]
    if args.ids:
        corpus = [u for u in corpus if u.dissertacao.id in set(args.ids)]
    cliente = _cliente()
    for modelo in args.modelos:
        for tecnica in args.tecnicas:
            rodar(modelo, tecnica, args.versao, corpus, args.sobrescrever)
        cliente.generate(model=modelo, keep_alive=0)  # libera a placa para o próximo modelo


if __name__ == "__main__":
    main()
